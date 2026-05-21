"""ButtonsBridge — virtual key events, reboot, screenshot, rotation toggle."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Signal, Slot

from ...core import paths
from ...core.adb_service import AdbService
from ...core.command_runner import Priority
from ...core.logger import get_logger
from ...core.settings_manager import SettingsManager
from .base import BridgeBase, to_jsonable

_log = get_logger(__name__)

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_KEYEVENT_TIMEOUT_S = 10
_REBOOT_TIMEOUT_S = 15
_SHELL_TIMEOUT_S = 15

# Public key → Android keycode mapping.
KEYCODES: Dict[str, str] = {
    "home":          "KEYCODE_HOME",
    "back":          "KEYCODE_BACK",
    "recent":        "KEYCODE_APP_SWITCH",
    "volume_up":     "KEYCODE_VOLUME_UP",
    "volume_down":   "KEYCODE_VOLUME_DOWN",
    "mute":          "KEYCODE_VOLUME_MUTE",
    "camera":        "KEYCODE_CAMERA",
    "power":         "KEYCODE_POWER",
}


class ButtonsBridge(BridgeBase):
    actionFinished = Signal("QVariant")  # {cmd_id, key, ok, message}
    screenshotSaved = Signal(str)        # absolute file path

    def __init__(self, adb: AdbService, settings: SettingsManager) -> None:
        super().__init__()
        self._adb = adb
        self._settings = settings
        self._pending: dict[str, dict] = {}
        self._screencap_bufs: dict[str, bytearray] = {}
        self._screencap_meta: dict[str, dict] = {}

        adb.commands.commandFinished.connect(self._on_cmd_finished)
        adb.commands.commandFailed.connect(self._on_cmd_failed)
        adb.processes.processOutput.connect(self._on_process_output)
        adb.processes.processStopped.connect(self._on_process_stopped)

    # --- key events ----------------------------------------------------
    @Slot(str, result=str)
    def pressKey(self, key: str) -> str:
        ctx = self._adb.active_device
        if ctx is None:
            return ""
        kc = KEYCODES.get(key.lower())
        if kc is None:
            return ""
        cmd_id = self._adb.run_command(
            ctx.serial, ["shell", "input", "keyevent", kc],
            priority=Priority.HIGH, timeout=_KEYEVENT_TIMEOUT_S,
        )
        self._pending[cmd_id] = {"action": f"key:{key}"}
        return cmd_id

    # --- reboot --------------------------------------------------------
    @Slot(str, result=str)
    def reboot(self, mode: str) -> str:
        """mode ∈ {"normal","bootloader","recovery"}"""
        ctx = self._adb.active_device
        if ctx is None:
            return ""
        args = ["reboot"]
        if mode in ("bootloader", "recovery"):
            args.append(mode)
        cmd_id = self._adb.run_command(
            ctx.serial, args,
            priority=Priority.HIGH, timeout=_REBOOT_TIMEOUT_S,
        )
        self._pending[cmd_id] = {"action": f"reboot:{mode}"}
        return cmd_id

    # --- rotation toggle ----------------------------------------------
    @Slot(result=str)
    def toggleRotation(self) -> str:
        ctx = self._adb.active_device
        if ctx is None:
            return ""
        # Two-step: read then write. We chain via pending entries.
        get_id = self._adb.run_command(
            ctx.serial,
            ["shell", "settings", "get", "system", "accelerometer_rotation"],
            priority=Priority.HIGH, timeout=_SHELL_TIMEOUT_S,
        )
        self._pending[get_id] = {"action": "rot_get", "serial": ctx.serial}
        return get_id

    # --- screenshot ----------------------------------------------------
    @Slot(result=str)
    def screenshot(self) -> str:
        ctx = self._adb.active_device
        if ctx is None:
            return ""
        folder = Path(self._settings.get("screenshots_folder",
                                         str(paths.screenshots_dir())))
        folder.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_model = "".join(c for c in (ctx.model or "device") if c.isalnum() or c in "._-")
        dest = folder / f"screenshot_{safe_model}_{ts}.png"

        pid = f"screencap-{uuid.uuid4()}"
        self._screencap_bufs[pid] = bytearray()
        self._screencap_meta[pid] = {"serial": ctx.serial, "dest": dest}
        ok = self._adb.spawn_adb(pid, ctx.serial, ["exec-out", "screencap", "-p"])
        if not ok:
            self._screencap_bufs.pop(pid, None)
            self._screencap_meta.pop(pid, None)
            return ""
        return str(dest)

    # --- service signal relays ----------------------------------------
    def _on_cmd_finished(self, cmd_id: str, result: Any) -> None:
        entry = self._pending.pop(cmd_id, None)
        if entry is None:
            return
        action = entry.get("action", "")
        if action == "rot_get":
            current = (result.stdout or "").strip()
            new_val = "0" if current == "1" else "1"
            serial = entry["serial"]
            put_id = self._adb.run_command(
                serial,
                ["shell", "settings", "put", "system", "accelerometer_rotation", new_val],
                priority=Priority.HIGH, timeout=_SHELL_TIMEOUT_S,
            )
            self._pending[put_id] = {"action": "rot_put", "new_value": new_val}
            return
        if action == "rot_put":
            self.actionFinished.emit({
                "cmd_id": cmd_id, "action": "rotation",
                "ok": True, "message": f"auto-rotate set to {entry['new_value']}",
            })
            return
        self.actionFinished.emit({
            "cmd_id": cmd_id, "action": action,
            "ok": True, "message": to_jsonable(result),
        })

    def _on_cmd_failed(self, cmd_id: str, result: Any) -> None:
        entry = self._pending.pop(cmd_id, None)
        if entry is None:
            return
        self.actionFinished.emit({
            "cmd_id": cmd_id, "action": entry.get("action", ""),
            "ok": False, "message": to_jsonable(result),
        })

    def _on_process_output(self, pid: str, data: bytes) -> None:
        buf = self._screencap_bufs.get(pid)
        if buf is None:
            return
        buf.extend(data)

    def _on_process_stopped(self, pid: str, rc: int) -> None:
        if pid not in self._screencap_bufs:
            return
        buf = self._screencap_bufs.pop(pid)
        meta = self._screencap_meta.pop(pid)
        dest: Path = meta["dest"]
        if rc != 0 or not buf or not bytes(buf).startswith(_PNG_MAGIC):
            self.actionFinished.emit({
                "cmd_id": pid, "action": "screenshot",
                "ok": False, "message": "screencap produced no PNG",
            })
            return
        try:
            dest.write_bytes(bytes(buf))
        except OSError as exc:
            self.actionFinished.emit({
                "cmd_id": pid, "action": "screenshot",
                "ok": False, "message": str(exc),
            })
            return
        self.screenshotSaved.emit(str(dest))
        self.actionFinished.emit({
            "cmd_id": pid, "action": "screenshot",
            "ok": True, "message": str(dest),
        })


__all__ = ["ButtonsBridge", "KEYCODES"]
