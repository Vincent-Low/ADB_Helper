"""Module: Device Buttons (Spec §3.5).

Simulates hardware/software button presses on the active device. All eleven
buttons from §3.5 are wired up; ADB I/O goes through :class:`AdbService`
(invariant 1). Strings come from :mod:`core.strings` (invariant 3).

Screenshot capture (Spec §3.5.1):
- Primary path uses ``adb -s <serial> exec-out screencap -p`` via
  :meth:`AdbService.spawn_adb`; raw PNG bytes are accumulated from
  ``processOutput`` and written to ``screenshots_folder``.
- If the primary path produces no PNG signature (older devices /
  ``exec-out`` unsupported), fall back to ``screencap`` to ``/sdcard``,
  ``adb pull``, ``adb shell rm``.
"""
from __future__ import annotations

import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import strings
from ..core.adb_service import get_adb_service
from ..core.command_runner import Priority
from ..core.device_context import DeviceContext
from ..core.imodule import IModule
from ..core.logger import get_logger
from ..core.settings_manager import SettingsManager

_log = get_logger(__name__)

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_KEYEVENT_TIMEOUT_S = 10
_REBOOT_TIMEOUT_S = 15
_PULL_TIMEOUT_S = 30
_SHELL_TIMEOUT_S = 15

# (label_key, keyevent) — Reboot/Screenshot/Screen Rotate are special-cased.
_KEYEVENT_BUTTONS = (
    ("DB_LABEL_HOME", "KEYCODE_HOME"),
    ("DB_LABEL_BACK", "KEYCODE_BACK"),
    ("DB_LABEL_RECENT", "KEYCODE_APP_SWITCH"),
    ("DB_LABEL_VOLUME_UP", "KEYCODE_VOLUME_UP"),
    ("DB_LABEL_VOLUME_DOWN", "KEYCODE_VOLUME_DOWN"),
    ("DB_LABEL_MUTE", "KEYCODE_VOLUME_MUTE"),
    ("DB_LABEL_CAMERA", "KEYCODE_CAMERA"),
    ("DB_LABEL_POWER", "KEYCODE_POWER"),
)


class DeviceButtonsModule(IModule):
    """Device Buttons screen (§3.5)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        self._buttons: list[QPushButton] = []
        # process_id -> bytearray of PNG bytes
        self._screencap_buffers: dict[str, bytearray] = {}
        # process_id -> {"serial": ..., "dest": Path}
        self._screencap_meta: dict[str, dict] = {}
        # cmd_id -> dict (for screen rotate get/put + screencap fallback)
        self._pending: dict[str, dict] = {}
        self._build_ui()
        self._wire_signals()
        self._sync_enabled(self._adb.active_device)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._status = QLabel("", self)
        self._status.setWordWrap(True)
        self._status.setProperty("secondary", "true")
        root.addWidget(self._status)

        grid = QGridLayout()
        grid.setSpacing(10)
        cols = 4

        def _add(label: str, slot, row: int, col: int) -> QPushButton:
            btn = QPushButton(label, self)
            btn.clicked.connect(slot)
            grid.addWidget(btn, row, col)
            self._buttons.append(btn)
            return btn

        idx = 0
        for label_key, keyevent in _KEYEVENT_BUTTONS:
            label = getattr(strings, label_key)
            _add(label, lambda _=False, k=keyevent: self._press_key(k),
                 idx // cols, idx % cols)
            idx += 1

        _add(strings.DB_LABEL_REBOOT, self._on_reboot, idx // cols, idx % cols)
        idx += 1
        _add(strings.DB_LABEL_SCREENSHOT, self._on_screenshot,
             idx // cols, idx % cols)
        idx += 1
        _add(strings.DB_LABEL_SCREEN_ROTATE, self._on_screen_rotate,
             idx // cols, idx % cols)
        idx += 1

        root.addLayout(grid)
        root.addStretch(1)

    def _wire_signals(self) -> None:
        self._adb.activeDeviceChanged.connect(self._sync_enabled)
        self._adb.processes.processOutput.connect(self._on_proc_output)
        self._adb.processes.processStopped.connect(self._on_proc_stopped)
        self._adb.commands.commandFinished.connect(self._on_cmd_finished)
        self._adb.commands.commandFailed.connect(self._on_cmd_failed)

    # ----------------------------------------------------- IModule lifecycle
    def on_activate(self) -> None:
        self._sync_enabled(self._adb.active_device)

    def on_deactivate(self) -> None:
        return None

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._sync_enabled(ctx)

    def on_device_disconnected(self) -> None:
        self._set_buttons_enabled(False)
        self._status.setText(strings.DB_MSG_NO_DEVICE)

    def _sync_enabled(self, ctx: Optional[DeviceContext]) -> None:
        online = ctx is not None and ctx.status == "online"
        self._set_buttons_enabled(online)
        if not online:
            self._status.setText(strings.DB_MSG_NO_DEVICE)
        else:
            self._status.setText("")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._buttons:
            btn.setEnabled(enabled)

    # -------------------------------------------------------- Active device
    def _active_serial(self) -> Optional[str]:
        ctx = self._adb.active_device
        return ctx.serial if ctx else None

    # ----------------------------------------------------------- Key events
    def _press_key(self, keycode: str) -> None:
        serial = self._active_serial()
        if not serial:
            return
        self._adb.commands.submit(
            serial,
            ["shell", "input", "keyevent", keycode],
            _KEYEVENT_TIMEOUT_S,
            Priority.HIGH,
        )

    # ---------------------------------------------------------------- Reboot
    def _on_reboot(self) -> None:
        serial = self._active_serial()
        if not serial:
            return
        ans = QMessageBox.question(
            self,
            strings.DB_TITLE_REBOOT_CONFIRM,
            strings.CONFIRM_REBOOT,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._adb.commands.submit(
            serial,
            ["reboot"],
            _REBOOT_TIMEOUT_S,
            Priority.HIGH,
        )

    # ------------------------------------------------------------ Screenshot
    def _on_screenshot(self) -> None:
        serial = self._active_serial()
        if not serial:
            return
        pid = f"screencap-{uuid.uuid4()}"
        dest = self._screenshot_dest()
        self._screencap_buffers[pid] = bytearray()
        self._screencap_meta[pid] = {"serial": serial, "dest": dest}
        ok = self._adb.spawn_adb(pid, serial, ["exec-out", "screencap", "-p"])
        if not ok:
            self._screencap_buffers.pop(pid, None)
            self._screencap_meta.pop(pid, None)
            self._screenshot_fallback(serial)

    def _screenshot_dest(self) -> Path:
        folder = Path(SettingsManager.instance().get(
            "screenshots_folder",
            "",
        ) or "")
        if not folder:
            from ..core import paths as _paths
            folder = _paths.screenshots_dir()
        folder.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        return folder / f"adb_helper_screenshot_{ts}.png"

    @Slot(str, bytes)
    def _on_proc_output(self, pid: str, data: bytes) -> None:
        buf = self._screencap_buffers.get(pid)
        if buf is not None:
            buf.extend(data)

    @Slot(str, int)
    def _on_proc_stopped(self, pid: str, returncode: int) -> None:
        if pid not in self._screencap_buffers:
            return
        buf = bytes(self._screencap_buffers.pop(pid))
        meta = self._screencap_meta.pop(pid, {})
        dest: Path = meta.get("dest")  # type: ignore[assignment]
        serial: str = meta.get("serial", "")  # type: ignore[assignment]

        if returncode == 0 and buf.startswith(_PNG_MAGIC) and dest is not None:
            try:
                dest.write_bytes(buf)
            except OSError as exc:
                _log.error("screenshot write failed: %s", exc)
                self._show_status(strings.DB_MSG_SCREENSHOT_FAILED.format(error=str(exc)))
                return
            self._notify_screenshot(dest)
            return

        _log.info(
            "exec-out screencap fallback rc=%s bytes=%d", returncode, len(buf)
        )
        if serial:
            self._screenshot_fallback(serial)

    def _screenshot_fallback(self, serial: str) -> None:
        """Older devices: ``screencap`` → ``adb pull`` → ``adb shell rm``."""
        ts = time.strftime("%Y%m%d_%H%M%S")
        remote = f"/sdcard/adb_helper_screenshot_{ts}.png"
        cmd_id = self._adb.commands.submit(
            serial,
            ["shell", "screencap", "-p", remote],
            _SHELL_TIMEOUT_S,
            Priority.HIGH,
        )
        self._pending[cmd_id] = {
            "kind": "screencap_to_sdcard",
            "serial": serial,
            "remote": remote,
        }

    def _notify_screenshot(self, dest: Path) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(strings.DB_TITLE_SCREENSHOT)
        box.setText(strings.MSG_SCREENSHOT_SAVED.format(path=str(dest)))
        open_btn = box.addButton(
            strings.DB_BTN_OPEN_FOLDER, QMessageBox.ButtonRole.ActionRole
        )
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() is open_btn:
            try:
                subprocess.Popen(
                    ["xdg-open", str(dest.parent)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            except OSError as exc:
                _log.warning("xdg-open failed: %s", exc)

    # --------------------------------------------------------- Screen rotate
    def _on_screen_rotate(self) -> None:
        serial = self._active_serial()
        if not serial:
            return
        cmd_id = self._adb.commands.submit(
            serial,
            ["shell", "settings", "get", "system", "accelerometer_rotation"],
            _SHELL_TIMEOUT_S,
            Priority.HIGH,
        )
        self._pending[cmd_id] = {"kind": "rotate_get", "serial": serial}

    # ----------------------------------------------------- Command callbacks
    @Slot(str, object)
    def _on_cmd_finished(self, cmd_id: str, result: object) -> None:
        info = self._pending.pop(cmd_id, None)
        if info is None:
            return
        self._handle_cmd(info, result, success=True)

    @Slot(str, object)
    def _on_cmd_failed(self, cmd_id: str, result: object) -> None:
        info = self._pending.pop(cmd_id, None)
        if info is None:
            return
        self._handle_cmd(info, result, success=False)

    def _handle_cmd(self, info: dict, result: object, success: bool) -> None:
        kind = info.get("kind")
        stdout = (getattr(result, "stdout", "") or "").strip()
        stderr = (getattr(result, "stderr", "") or "").strip()
        serial = info.get("serial", "")

        if kind == "rotate_get":
            if not success:
                self._show_status(
                    strings.DB_MSG_ROTATION_FAILED.format(error=stderr or "rc!=0")
                )
                return
            current = stdout.strip()
            new_val = "0" if current == "1" else "1"
            cmd_id = self._adb.commands.submit(
                serial,
                [
                    "shell", "settings", "put", "system",
                    "accelerometer_rotation", new_val,
                ],
                _SHELL_TIMEOUT_S,
                Priority.HIGH,
            )
            self._pending[cmd_id] = {
                "kind": "rotate_set",
                "serial": serial,
                "value": new_val,
            }
            return

        if kind == "rotate_set":
            if success:
                self._show_status(
                    strings.DB_MSG_ROTATION_TOGGLED.format(value=info.get("value", ""))
                )
            else:
                self._show_status(
                    strings.DB_MSG_ROTATION_FAILED.format(error=stderr or "rc!=0")
                )
            return

        if kind == "screencap_to_sdcard":
            if not success:
                self._show_status(
                    strings.DB_MSG_SCREENSHOT_FAILED.format(error=stderr or "rc!=0")
                )
                return
            dest = self._screenshot_dest()
            remote = info.get("remote", "")
            cmd_id = self._adb.commands.submit(
                serial,
                ["pull", remote, str(dest)],
                _PULL_TIMEOUT_S,
                Priority.HIGH,
            )
            self._pending[cmd_id] = {
                "kind": "screencap_pull",
                "serial": serial,
                "remote": remote,
                "dest": dest,
            }
            return

        if kind == "screencap_pull":
            dest: Path = info.get("dest")  # type: ignore[assignment]
            remote = info.get("remote", "")
            # cleanup remote regardless of pull outcome
            self._adb.commands.submit(
                serial,
                ["shell", "rm", "-f", remote],
                _SHELL_TIMEOUT_S,
                Priority.NORMAL,
            )
            if success and dest is not None and dest.exists():
                self._notify_screenshot(dest)
            else:
                self._show_status(
                    strings.DB_MSG_SCREENSHOT_FAILED.format(error=stderr or "pull failed")
                )
            return

    # ------------------------------------------------------------ Status bar
    def _show_status(self, text: str) -> None:
        self._status.setText(text)


__all__ = ["DeviceButtonsModule"]
