"""ADB device monitor.

Spec §5.3. Primary: ``adb track-devices`` via :class:`ProcessManager`
(server-push). Fallback: ``adb devices`` polled every 3 s if track-devices
fails to emit within 2 s.

Emits :class:`DeviceContext` objects with manufacturer/model/sdk/abi
populated by a one-shot ``getprop`` per newly seen serial.
"""
from __future__ import annotations

import re
import threading
import uuid
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from .command_runner import AdbCommand, AdbResult, CommandRunner, Priority
from .device_context import DeviceContext
from .logger import get_logger
from .process_manager import ProcessManager

_log = get_logger(__name__)

_TRACK_PROCESS_ID = "device-monitor-track"
_TRACK_INIT_TIMEOUT_S = 2.0
_FALLBACK_POLL_MS = 3000
_GETPROP_TIMEOUT_S = 5

# adb track-devices line format: "<serial>\t<state>" within a length-prefixed
# message. We strip the 4-byte hex length prefix and parse line-wise.
_LINE_RE = re.compile(r"^([^\s]+)\s+(\S+)\s*$")
_HEX_PREFIX_RE = re.compile(r"^[0-9a-fA-F]{4}")


class DeviceMonitor(QObject):
    """Track connected ADB devices (§5.3)."""

    deviceConnected = Signal(object)       # DeviceContext
    deviceDisconnected = Signal(str)       # serial
    deviceStateChanged = Signal(object)    # DeviceContext

    def __init__(
        self,
        command_runner: CommandRunner,
        process_manager: ProcessManager,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._cmds = command_runner
        self._procs = process_manager
        self._known: dict[str, DeviceContext] = {}
        self._buf = b""
        self._track_received = False
        self._track_active = False
        self._fallback_active = False
        self._init_timer: Optional[QTimer] = None
        self._poll_timer: Optional[QTimer] = None
        self._pending_getprop: dict[str, str] = {}  # cmd_id -> serial
        self._lock = threading.Lock()

        self._procs.processOutput.connect(self._on_process_output)
        self._procs.processStopped.connect(self._on_process_stopped)
        self._cmds.commandFinished.connect(self._on_cmd_finished)
        self._cmds.commandFailed.connect(self._on_cmd_failed)

    def start(self) -> None:
        from .command_runner import resolve_adb_binary
        adb = resolve_adb_binary()
        ok = self._procs.start(_TRACK_PROCESS_ID, [adb, "track-devices"])
        if not ok:
            _log.warning("track-devices start failed; using poll fallback")
            self._start_fallback()
            return
        self._track_active = True
        self._init_timer = QTimer(self)
        self._init_timer.setSingleShot(True)
        self._init_timer.timeout.connect(self._check_track_init)
        self._init_timer.start(int(_TRACK_INIT_TIMEOUT_S * 1000))

    def stop(self) -> None:
        if self._init_timer is not None:
            self._init_timer.stop()
            self._init_timer = None
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer = None
        if self._track_active:
            self._procs.stop(_TRACK_PROCESS_ID)
            self._track_active = False
        self._fallback_active = False

    def known_devices(self) -> list[DeviceContext]:
        with self._lock:
            return list(self._known.values())

    # --- track-devices path ---------------------------------------------
    @Slot(str, bytes)
    def _on_process_output(self, pid: str, data: bytes) -> None:
        if pid != _TRACK_PROCESS_ID:
            return
        self._track_received = True
        self._buf += data
        text = self._buf.decode("utf-8", errors="replace")
        # adb track-devices emits length-prefixed messages, but each message
        # is itself a newline-separated device list. Strip the 4-char hex
        # prefix once per message and treat the rest line-wise.
        cleaned = _HEX_PREFIX_RE.sub("", text, count=text.count("\n") + 1)
        self._parse_listing(cleaned)
        # keep tail for next chunk
        if not text.endswith("\n"):
            tail = text.rsplit("\n", 1)[-1]
            self._buf = tail.encode("utf-8", errors="replace")
        else:
            self._buf = b""

    @Slot(str, int)
    def _on_process_stopped(self, pid: str, rc: int) -> None:
        if pid != _TRACK_PROCESS_ID:
            return
        was_active = self._track_active
        self._track_active = False
        if was_active and not self._fallback_active:
            _log.warning("track-devices exited rc=%s; switching to poll", rc)
            self._start_fallback()

    def _check_track_init(self) -> None:
        if not self._track_received and not self._fallback_active:
            _log.warning("track-devices silent for %ss; using poll", _TRACK_INIT_TIMEOUT_S)
            if self._track_active:
                self._procs.stop(_TRACK_PROCESS_ID)
                self._track_active = False
            self._start_fallback()

    # --- poll fallback --------------------------------------------------
    def _start_fallback(self) -> None:
        if self._fallback_active:
            return
        self._fallback_active = True
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_once)
        self._poll_timer.start(_FALLBACK_POLL_MS)
        self._poll_once()

    def _poll_once(self) -> None:
        cmd_id = f"devmon-poll-{uuid.uuid4()}"
        cmd = AdbCommand(
            id=cmd_id,
            serial=None,
            args=["devices"],
            timeout=10,
            priority=Priority.NORMAL,
        )
        with self._lock:
            self._pending_getprop[cmd_id] = "__poll__"
        self._cmds.run(cmd)

    # --- listing parser -------------------------------------------------
    def _parse_listing(self, text: str) -> None:
        seen: dict[str, str] = {}
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.lower().startswith("list of devices"):
                continue
            m = _LINE_RE.match(line)
            if not m:
                continue
            serial, state = m.group(1), m.group(2)
            seen[serial] = state

        with self._lock:
            known_snapshot = dict(self._known)

        for serial, state in seen.items():
            existing = known_snapshot.get(serial)
            status = _state_to_status(state)
            if existing is None:
                placeholder = DeviceContext(
                    serial=serial,
                    model="",
                    manufacturer="",
                    sdk_version="",
                    abi="",
                    connection_type=_connection_type(serial),
                    status=status,
                )
                with self._lock:
                    self._known[serial] = placeholder
                self.deviceConnected.emit(placeholder)
                if status == "online":
                    self._fetch_props(serial)
            else:
                if existing.status != status:
                    updated = _replace_status(existing, status)
                    with self._lock:
                        self._known[serial] = updated
                    self.deviceStateChanged.emit(updated)
                    if status == "online" and not existing.model:
                        self._fetch_props(serial)

        for serial in list(known_snapshot.keys()):
            if serial not in seen:
                with self._lock:
                    self._known.pop(serial, None)
                self.deviceDisconnected.emit(serial)

    # --- getprop completion ---------------------------------------------
    def _fetch_props(self, serial: str) -> None:
        cmd_id = f"devmon-getprop-{serial}-{uuid.uuid4()}"
        cmd = AdbCommand(
            id=cmd_id,
            serial=serial,
            args=["shell", "getprop"],
            timeout=_GETPROP_TIMEOUT_S,
            priority=Priority.HIGH,
        )
        with self._lock:
            self._pending_getprop[cmd_id] = serial
        self._cmds.run(cmd)

    @Slot(str, object)
    def _on_cmd_finished(self, cmd_id: str, result: object) -> None:
        with self._lock:
            target = self._pending_getprop.pop(cmd_id, None)
        if target is None:
            return
        res: AdbResult = result  # type: ignore[assignment]
        if target == "__poll__":
            self._parse_listing(res.stdout)
            return
        self._apply_props(target, res.stdout)

    @Slot(str, object)
    def _on_cmd_failed(self, cmd_id: str, result: object) -> None:
        with self._lock:
            self._pending_getprop.pop(cmd_id, None)

    def _apply_props(self, serial: str, getprop_out: str) -> None:
        props = _parse_getprop(getprop_out)
        with self._lock:
            existing = self._known.get(serial)
            if existing is None:
                return
            updated = DeviceContext(
                serial=existing.serial,
                model=props.get("ro.product.model", existing.model),
                manufacturer=props.get("ro.product.manufacturer", existing.manufacturer),
                sdk_version=props.get("ro.build.version.sdk", existing.sdk_version),
                abi=props.get("ro.product.cpu.abi", existing.abi),
                connection_type=existing.connection_type,
                status=existing.status,
            )
            self._known[serial] = updated
        self.deviceStateChanged.emit(updated)


def _state_to_status(state: str) -> str:
    s = state.lower()
    if s == "device":
        return "online"
    if s == "unauthorized":
        return "unauthorized"
    return "offline"


def _connection_type(serial: str) -> str:
    return "wifi" if ":" in serial and serial.count(".") >= 3 else "usb"


def _replace_status(ctx: DeviceContext, status: str) -> DeviceContext:
    return DeviceContext(
        serial=ctx.serial,
        model=ctx.model,
        manufacturer=ctx.manufacturer,
        sdk_version=ctx.sdk_version,
        abi=ctx.abi,
        connection_type=ctx.connection_type,
        status=status,  # type: ignore[arg-type]
    )


def _parse_getprop(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            key_part, val_part = line.split("]:", 1)
        except ValueError:
            continue
        key = key_part[1:].strip()
        val = val_part.strip()
        if val.startswith("[") and val.endswith("]"):
            val = val[1:-1]
        if key:
            out[key] = val
    return out
