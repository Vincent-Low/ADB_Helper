"""Module: Device Buttons (Spec §3.5; Redesign §5.5).

Simulates hardware/software button presses on the active device. All eleven
buttons from §3.5 are wired up; ADB I/O goes through :class:`AdbService`
(invariant 1). Strings come from :mod:`core.strings` (invariant 3).

Layout (Redesign §5.5): a fixed ``QGridLayout`` of 4 columns × 3 rows with
``QPushButton#ButtonTile`` tiles (min-height 64). Tile background, border
and radius come from the QSS template — no QSS literals here. A "Recent
actions" card sits below the grid via the shared :func:`card` helper.

Each tile carries an icon-left glyph + label-right text. Real SVG icons
would be the ideal endpoint (handoff: "icon color = accent via SVG
``currentColor``"); for v1.0 we fall back to unicode glyphs prefixed to the
label so the visual hierarchy still reads as icon + text.

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
from collections import deque
from pathlib import Path
from typing import Deque, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
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
from ..ui.style_utils import card, page_header

_log = get_logger(__name__)

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_KEYEVENT_TIMEOUT_S = 10
_REBOOT_TIMEOUT_S = 15
_PULL_TIMEOUT_S = 30
_SHELL_TIMEOUT_S = 15
_RECENT_MAX = 15

_GRID_COLS = 4
_GRID_ROWS = 3

# (label_key, keyevent, glyph) — Reboot/Screenshot/Screen Rotate special-cased.
_KEYEVENT_BUTTONS = (
    ("DB_LABEL_HOME",        "KEYCODE_HOME",        "⌂"),
    ("DB_LABEL_BACK",        "KEYCODE_BACK",        "◀"),
    ("DB_LABEL_RECENT",      "KEYCODE_APP_SWITCH",  "▣"),
    ("DB_LABEL_VOLUME_UP",   "KEYCODE_VOLUME_UP",   "+"),
    ("DB_LABEL_VOLUME_DOWN", "KEYCODE_VOLUME_DOWN", "−"),
    ("DB_LABEL_MUTE",        "KEYCODE_VOLUME_MUTE", "⊘"),
    ("DB_LABEL_CAMERA",      "KEYCODE_CAMERA",      "📷"),
    ("DB_LABEL_POWER",       "KEYCODE_POWER",       "⏻"),
)

_GLYPH_REBOOT = "⟳"
_GLYPH_SCREENSHOT = "⌗"
_GLYPH_ROTATE = "↻"


def _tile_text(glyph: str, label: str) -> str:
    return f"{glyph}  {label}"


class DeviceButtonsModule(IModule):
    """Device Buttons screen (§3.5; Redesign §5.5)."""

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
        # cmd_id -> recent-entry-id (so finished/failed updates the right row).
        self._cmd_to_recent: dict[str, int] = {}
        self._recent: Deque[dict] = deque(maxlen=_RECENT_MAX)
        self._build_ui()
        self._wire_signals()
        self._sync_enabled(self._adb.active_device)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        root.addWidget(
            page_header(
                strings.LABEL_DEVICE_BUTTONS,
                strings.PAGE_SUBTITLE_DEVICE_BUTTONS,
                parent=self,
            )
        )

        self._status = QLabel("", self)
        self._status.setWordWrap(True)
        self._status.setProperty("role", "hint")
        root.addWidget(self._status)

        # --- 4×3 tile grid (always 4 columns; no resizeEvent breakpoint) ---
        grid_widget = QWidget(self)
        grid_widget.setObjectName("deviceButtonsGrid")
        grid_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        for i in range(_GRID_COLS):
            grid.setColumnStretch(i, 1)
        for i in range(_GRID_ROWS):
            grid.setRowStretch(i, 0)

        def _add(text: str, slot, row: int, col: int) -> QPushButton:
            btn = QPushButton(text, grid_widget)
            btn.setObjectName("ButtonTile")
            btn.setMinimumHeight(64)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(slot)
            grid.addWidget(btn, row, col)
            self._buttons.append(btn)
            return btn

        idx = 0
        for label_key, keyevent, glyph in _KEYEVENT_BUTTONS:
            text = _tile_text(glyph, getattr(strings, label_key))
            _add(
                text,
                lambda _=False, k=keyevent: self._press_key(k),
                idx // _GRID_COLS, idx % _GRID_COLS,
            )
            idx += 1

        _add(
            _tile_text(_GLYPH_REBOOT, strings.DB_LABEL_REBOOT),
            self._on_reboot, idx // _GRID_COLS, idx % _GRID_COLS,
        )
        idx += 1
        _add(
            _tile_text(_GLYPH_SCREENSHOT, strings.DB_LABEL_SCREENSHOT),
            self._on_screenshot, idx // _GRID_COLS, idx % _GRID_COLS,
        )
        idx += 1
        _add(
            _tile_text(_GLYPH_ROTATE, strings.DB_LABEL_SCREEN_ROTATE),
            self._on_screen_rotate, idx // _GRID_COLS, idx % _GRID_COLS,
        )
        idx += 1

        root.addWidget(grid_widget)

        # --- Recent actions card --------------------------------------
        recent_body = QWidget()
        recent_lay = QVBoxLayout(recent_body)
        recent_lay.setContentsMargins(0, 0, 0, 0)
        recent_lay.setSpacing(8)

        self._recent_table = QTableWidget(0, 4, recent_body)
        self._recent_table.setHorizontalHeaderLabels([
            strings.DB_RECENT_COL_TIME,
            strings.DB_RECENT_COL_ACTION,
            strings.DB_RECENT_COL_DEVICE,
            strings.DB_RECENT_COL_RESULT,
        ])
        self._recent_table.verticalHeader().setVisible(False)
        self._recent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._recent_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._recent_table.setFocusPolicy(Qt.NoFocus)
        self._recent_table.setShowGrid(False)
        self._recent_table.setAlternatingRowColors(True)
        header = self._recent_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._recent_table.setMinimumHeight(140)
        recent_lay.addWidget(self._recent_table, 1)

        self._recent_empty = QLabel(strings.DB_RECENT_EMPTY, recent_body)
        self._recent_empty.setProperty("role", "hint")
        self._recent_empty.setAlignment(Qt.AlignCenter)
        recent_lay.addWidget(self._recent_empty)
        self._recent_table.hide()

        root.addWidget(card(strings.DB_RECENT_TITLE, recent_body, parent=self), 1)

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
        cmd_id = self._adb.commands.submit(
            serial,
            ["shell", "input", "keyevent", keycode],
            _KEYEVENT_TIMEOUT_S,
            Priority.HIGH,
        )
        label = self._label_for_keycode(keycode)
        self._record_action(cmd_id, label, serial)

    @staticmethod
    def _label_for_keycode(keycode: str) -> str:
        for label_key, kc, _glyph in _KEYEVENT_BUTTONS:
            if kc == keycode:
                return getattr(strings, label_key)
        return keycode

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
        cmd_id = self._adb.commands.submit(
            serial,
            ["reboot"],
            _REBOOT_TIMEOUT_S,
            Priority.HIGH,
        )
        self._record_action(cmd_id, strings.DB_LABEL_REBOOT, serial)

    # ------------------------------------------------------------ Screenshot
    def _on_screenshot(self) -> None:
        serial = self._active_serial()
        if not serial:
            return
        pid = f"screencap-{uuid.uuid4()}"
        dest = self._screenshot_dest()
        self._screencap_buffers[pid] = bytearray()
        self._screencap_meta[pid] = {"serial": serial, "dest": dest}
        recent_id = self._record_action(None, strings.DB_LABEL_SCREENSHOT, serial)
        self._screencap_meta[pid]["recent_id"] = recent_id
        ok = self._adb.spawn_adb(pid, serial, ["exec-out", "screencap", "-p"])
        if not ok:
            self._screencap_buffers.pop(pid, None)
            self._screencap_meta.pop(pid, None)
            self._screenshot_fallback(serial, recent_id=recent_id)

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
        recent_id = meta.get("recent_id")

        if returncode == 0 and buf.startswith(_PNG_MAGIC) and dest is not None:
            try:
                dest.write_bytes(buf)
            except OSError as exc:
                _log.error("screenshot write failed: %s", exc)
                self._show_status(strings.DB_MSG_SCREENSHOT_FAILED.format(error=str(exc)))
                self._finalize_recent(recent_id, success=False)
                return
            self._notify_screenshot(dest)
            self._finalize_recent(recent_id, success=True)
            return

        _log.info(
            "exec-out screencap fallback rc=%s bytes=%d", returncode, len(buf)
        )
        if serial:
            self._screenshot_fallback(serial, recent_id=recent_id)

    def _screenshot_fallback(self, serial: str, recent_id: Optional[int] = None) -> None:
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
            "recent_id": recent_id,
        }
        if recent_id is not None:
            self._cmd_to_recent[cmd_id] = recent_id

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
        self._record_action(cmd_id, strings.DB_LABEL_SCREEN_ROTATE, serial)

    # ----------------------------------------------------- Command callbacks
    @Slot(str, object)
    def _on_cmd_finished(self, cmd_id: str, result: object) -> None:
        info = self._pending.pop(cmd_id, None)
        recent_id = self._cmd_to_recent.pop(cmd_id, None)
        if info is None:
            if recent_id is not None:
                self._finalize_recent(recent_id, success=True)
            return
        self._handle_cmd(info, result, success=True, recent_id=recent_id)

    @Slot(str, object)
    def _on_cmd_failed(self, cmd_id: str, result: object) -> None:
        info = self._pending.pop(cmd_id, None)
        recent_id = self._cmd_to_recent.pop(cmd_id, None)
        if info is None:
            if recent_id is not None:
                self._finalize_recent(recent_id, success=False)
            return
        self._handle_cmd(info, result, success=False, recent_id=recent_id)

    def _handle_cmd(
        self,
        info: dict,
        result: object,
        success: bool,
        recent_id: Optional[int] = None,
    ) -> None:
        kind = info.get("kind")
        stdout = (getattr(result, "stdout", "") or "").strip()
        stderr = (getattr(result, "stderr", "") or "").strip()
        serial = info.get("serial", "")

        if kind == "rotate_get":
            if not success:
                self._show_status(
                    strings.DB_MSG_ROTATION_FAILED.format(error=stderr or "rc!=0")
                )
                self._finalize_recent(recent_id, success=False)
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
            if recent_id is not None:
                self._cmd_to_recent[cmd_id] = recent_id
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
            self._finalize_recent(recent_id, success=success)
            return

        if kind == "screencap_to_sdcard":
            if not success:
                self._show_status(
                    strings.DB_MSG_SCREENSHOT_FAILED.format(error=stderr or "rc!=0")
                )
                self._finalize_recent(recent_id, success=False)
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
            if recent_id is not None:
                self._cmd_to_recent[cmd_id] = recent_id
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
            ok = success and dest is not None and dest.exists()
            if ok:
                self._notify_screenshot(dest)
            else:
                self._show_status(
                    strings.DB_MSG_SCREENSHOT_FAILED.format(error=stderr or "pull failed")
                )
            self._finalize_recent(recent_id, success=ok)
            return

    # ------------------------------------------------------------ Status bar
    def _show_status(self, text: str) -> None:
        self._status.setText(text)

    # ------------------------------------------------------- Recent actions
    def _record_action(
        self,
        cmd_id: Optional[str],
        action: str,
        serial: str,
    ) -> int:
        ctx = self._adb.active_device
        device_label = ctx.model if ctx and ctx.serial == serial and ctx.model else serial
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "action": action,
            "device": device_label,
            "result": "…",
            "_id": None,
        }
        entry["_id"] = id(entry)
        self._recent.appendleft(entry)
        self._rebuild_recent_table()
        if cmd_id is not None:
            self._cmd_to_recent[cmd_id] = entry["_id"]
        return entry["_id"]

    def _finalize_recent(self, recent_id: Optional[int], success: bool) -> None:
        if recent_id is None:
            return
        text = (
            strings.DB_RECENT_RESULT_OK
            if success
            else strings.DB_RECENT_RESULT_FAIL
        )
        for entry in self._recent:
            if entry.get("_id") == recent_id:
                entry["result"] = text
                break
        self._rebuild_recent_table()

    def _rebuild_recent_table(self) -> None:
        table = self._recent_table
        table.setRowCount(0)
        if not self._recent:
            table.hide()
            self._recent_empty.show()
            return
        self._recent_empty.hide()
        table.show()
        for row, data in enumerate(self._recent):
            table.insertRow(row)
            for col, key in enumerate(("time", "action", "device", "result")):
                item = QTableWidgetItem(data.get(key, ""))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col, item)


__all__ = ["DeviceButtonsModule"]
