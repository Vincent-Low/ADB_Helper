"""Module: Terminal (Spec §3.2).

Wires a :class:`TerminalWidget` to a :class:`PtySession` (Linux ``pty``;
Windows ConPTY belongs in core, out of scope here). Adds the side panel
with command history, macro list, recording, and sequential playback.

CLAUDE.md invariants:
  - 1 (ADB I/O): all ADB traffic goes through :class:`PtySession` (core).
    No ``subprocess``/``QProcess``/``adb`` strings here.
  - 2 (IModule): full lifecycle implemented; PTY is started/stopped from
    ``on_activate``/``on_deactivate`` and restarted on device change.
  - 3 (strings): all user-facing text is read from :mod:`adb_helper.core.strings`.
  - 4 (platform): platform branching is delegated to :mod:`core.platform`
    (via :class:`PtySession`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core import strings
from ..core.adb_service import get_adb_service
from ..core.db_manager import DatabaseManager
from ..core.device_context import DeviceContext
from ..core.imodule import IModule
from ..core.logger import get_logger
from ..core.pty_session import PtySession
from ..ui.style_utils import set_variant as _set_variant
from ..ui.terminal_widget import TerminalWidget
from ..ui.theme_manager import Theme, get_theme_manager

_log = get_logger(__name__)

_PLAYBACK_STEP_MS = 600
_MACRO_ID_ROLE = Qt.ItemDataRole.UserRole + 1
_MACRO_CMDS_ROLE = Qt.ItemDataRole.UserRole + 2


class _SaveMacroDialog(QDialog):
    """Name-the-macro dialog (Spec §3.2.3)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(strings.TERM_LABEL_SAVE_MACRO_TITLE)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel(strings.TERM_FIELD_NAME, self))
        self._name = QLineEdit(self)
        row.addWidget(self._name, 1)
        lay.addLayout(row)

        buttons = QDialogButtonBox(self)
        save_btn = buttons.addButton(strings.TERM_BTN_SAVE, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton(strings.TERM_BTN_CANCEL, QDialogButtonBox.ButtonRole.RejectRole)
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(buttons)

    def macro_name(self) -> str:
        return self._name.text().strip()


class _HistoryDialog(QDialog):
    """Modal list of recent commands. Click to insert."""

    command_chosen = Signal(str)

    def __init__(self, history: List[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(strings.TERM_LABEL_HISTORY_TITLE)
        self.resize(520, 380)
        lay = QVBoxLayout(self)
        self._list = QListWidget(self)
        for entry in history:
            self._list.addItem(QListWidgetItem(entry))
        self._list.itemActivated.connect(self._on_activated)
        self._list.itemClicked.connect(self._on_activated)
        lay.addWidget(self._list, 1)

    def _on_activated(self, item: QListWidgetItem) -> None:
        self.command_chosen.emit(item.text())
        self.accept()


class TerminalModule(IModule):
    """Terminal screen (§3.2)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        try:
            self._db: Optional[DatabaseManager] = DatabaseManager.instance()
        except Exception as exc:  # pragma: no cover — defensive
            _log.warning("DatabaseManager unavailable: %s", exc)
            self._db = None

        self._pty: Optional[PtySession] = None
        self._active_serial: Optional[str] = None
        self._activated = False

        # History state.
        self._history: List[str] = []
        self._history_index = -1  # -1 means "fresh input line".

        # Recording state.
        self._recording = False
        self._recorded: List[str] = []

        # Playback state.
        self._playback_cmds: List[str] = []
        self._playback_index = 0
        self._playback_active = False
        self._playback_timer = QTimer(self)
        self._playback_timer.setSingleShot(True)
        self._playback_timer.timeout.connect(self._tick_playback)

        self._build_ui()
        self._wire_signals()
        self._reload_history()
        self._reload_macros()
        self._sync_buttons()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(splitter, 1)

        # Left: terminal pane + clear/history actions.
        left = QWidget(splitter)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)
        self._status_label = QLabel("", left)
        top_bar.addWidget(self._status_label, 1)
        self._clear_btn = QPushButton(strings.TERM_BTN_CLEAR, left)
        top_bar.addWidget(self._clear_btn, 0)
        self._history_btn = QPushButton(strings.TERM_BTN_HISTORY, left)
        top_bar.addWidget(self._history_btn, 0)
        left_lay.addLayout(top_bar)

        self._term = TerminalWidget(left, dark=self._resolve_dark())
        left_lay.addWidget(self._term, 1)

        splitter.addWidget(left)

        # Right: macros + recording.
        right = QWidget(splitter)
        right.setObjectName("macroPanel")
        right.setMinimumWidth(200)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(10, 8, 10, 8)
        right_lay.setSpacing(6)

        right_lay.addWidget(QLabel(strings.TERM_LABEL_MACROS, right))

        actions = QHBoxLayout()
        self._record_btn = QPushButton(strings.TERM_BTN_RECORD, right)
        _set_variant(self._record_btn, "primary")
        actions.addWidget(self._record_btn, 0)
        self._play_btn = QPushButton(strings.TERM_BTN_PLAY, right)
        self._play_btn.setEnabled(False)
        actions.addWidget(self._play_btn, 0)
        actions.addStretch(1)
        right_lay.addLayout(actions)

        self._macro_list = QListWidget(right)
        self._macro_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._macro_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        from PySide6.QtWidgets import QSizePolicy as _QSP
        self._macro_list.setSizePolicy(_QSP.Expanding, _QSP.Expanding)
        right_lay.addWidget(self._macro_list, 1)

        self._playback_label = QLabel("", right)
        self._playback_label.setWordWrap(True)
        right_lay.addWidget(self._playback_label, 0)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

    def _wire_signals(self) -> None:
        self._adb.activeDeviceChanged.connect(self._on_active_device_changed)

        self._clear_btn.clicked.connect(self._term.clear_output)
        self._history_btn.clicked.connect(self._open_history_dialog)

        self._term.command_entered.connect(self._on_command_entered)
        self._term.history_up_pressed.connect(self._on_history_up)
        self._term.history_down_pressed.connect(self._on_history_down)
        self._term.interrupt_pressed.connect(self._on_interrupt)

        self._record_btn.clicked.connect(self._on_toggle_record)
        self._play_btn.clicked.connect(self._on_play_stop)
        self._macro_list.itemSelectionChanged.connect(self._sync_buttons)
        self._macro_list.itemDoubleClicked.connect(self._on_macro_double_clicked)
        self._macro_list.customContextMenuRequested.connect(self._on_macro_context_menu)

        theme_mgr = self._theme_manager()
        if theme_mgr is not None:
            theme_mgr.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------
    # IModule lifecycle
    # ------------------------------------------------------------------
    def on_activate(self) -> None:
        self._activated = True
        self._term.set_dark(self._resolve_dark())
        self._reload_history()
        self._reload_macros()
        ctx = self._adb.active_device
        current_serial = ctx.serial if ctx is not None else None
        if self._is_pty_alive() and current_serial == self._active_serial:
            self._term.focus_input()
            return
        self._sync_session_for(ctx)
        self._term.focus_input()

    def on_deactivate(self) -> None:
        self._activated = False
        self._stop_playback(quiet=True)
        # PTY survives navigation away — only torn down on device change,
        # disconnect, or app shutdown. Bug A1.

    def _is_pty_alive(self) -> bool:
        if self._pty is None:
            return False
        return self._pty.is_running()

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._sync_session_for(ctx)

    def on_device_disconnected(self) -> None:
        self._stop_playback(quiet=True)
        self._close_session()
        self._term.write_local_line(strings.TERM_MSG_DEVICE_DISCONNECTED)
        self._term.set_input_enabled(False)
        self._term.set_prompt_serial(None)
        self._status_label.setText(strings.TERM_MSG_DEVICE_DISCONNECTED)

    # ------------------------------------------------------------------
    # PTY session management
    # ------------------------------------------------------------------
    def _sync_session_for(self, ctx: Optional[DeviceContext]) -> None:
        if not self._activated:
            return
        serial = ctx.serial if ctx is not None else None
        if serial == self._active_serial and self._pty is not None and self._pty.is_running():
            return
        self._close_session()
        if not serial:
            self._term.set_prompt_serial(None)
            self._term.set_input_enabled(False)
            self._status_label.setText(strings.TERM_MSG_NO_DEVICE)
            self._term.write_local_line(strings.TERM_MSG_NO_DEVICE)
            return
        self._open_session(serial)

    def _open_session(self, serial: str) -> None:
        session = PtySession(serial, self)
        session.output_ready.connect(self._on_pty_output)
        session.process_exited.connect(self._on_pty_exited)
        if not session.start():
            session.deleteLater()
            self._term.write_local_line(strings.TERM_MSG_NO_DEVICE)
            self._term.set_input_enabled(False)
            return
        self._pty = session
        self._active_serial = serial
        self._term.set_prompt_serial(serial)
        self._term.set_input_enabled(True)
        self._status_label.setText(
            strings.TERM_MSG_SESSION_STARTING.format(serial=serial)
        )
        self._term.write_local_line(
            strings.TERM_MSG_SESSION_STARTING.format(serial=serial)
        )

    def _close_session(self) -> None:
        if self._pty is None:
            return
        try:
            self._pty.close()
        except Exception as exc:  # pragma: no cover — defensive
            _log.warning("pty close failed: %s", exc)
        self._pty.deleteLater()
        self._pty = None
        self._active_serial = None

    @Slot(bytes)
    def _on_pty_output(self, data: bytes) -> None:
        self._term.feed_bytes(data)

    @Slot(int)
    def _on_pty_exited(self, rc: int) -> None:
        self._term.write_local_line(strings.TERM_MSG_SESSION_EXITED.format(rc=rc))
        self._term.set_input_enabled(False)
        self._status_label.setText(strings.TERM_MSG_SESSION_EXITED.format(rc=rc))
        # Drop the reference — the underlying QThread has emitted finished.
        if self._pty is not None:
            self._pty.deleteLater()
        self._pty = None
        self._active_serial = None

    # ------------------------------------------------------------------
    # Active device wiring
    # ------------------------------------------------------------------
    @Slot(object)
    def _on_active_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        if not self._activated:
            return
        self._sync_session_for(ctx)

    # ------------------------------------------------------------------
    # Command entry + history
    # ------------------------------------------------------------------
    def _on_command_entered(self, text: str) -> None:
        cmd = text.rstrip("\n")
        self._history_index = -1
        if self._pty is None or not self._pty.is_running():
            return
        # Echo handled by adb shell; do not duplicate it locally.
        self._pty.write((cmd + "\n").encode("utf-8"))
        if cmd.strip():
            self._record_if_active(cmd)
            self._persist_history(cmd)

    def _on_history_up(self) -> None:
        if not self._history:
            return
        if self._history_index + 1 < len(self._history):
            self._history_index += 1
        self._term.set_input_text(self._history[self._history_index])

    def _on_history_down(self) -> None:
        if self._history_index <= 0:
            self._history_index = -1
            self._term.set_input_text("")
            return
        self._history_index -= 1
        self._term.set_input_text(self._history[self._history_index])

    def _on_interrupt(self) -> None:
        if self._pty is None or not self._pty.is_running():
            return
        self._pty.write(b"\x03")

    def _reload_history(self) -> None:
        if self._db is None:
            self._history = []
            return
        try:
            self._history = self._db.get_command_history()
        except Exception as exc:
            _log.warning("get_command_history failed: %s", exc)
            self._history = []
        self._history_index = -1

    def _persist_history(self, command: str) -> None:
        if self._db is None:
            return
        try:
            self._db.add_command_history(command)
        except Exception as exc:
            _log.warning("add_command_history failed: %s", exc)
        self._reload_history()

    def _open_history_dialog(self) -> None:
        dlg = _HistoryDialog(self._history, self)
        dlg.command_chosen.connect(self._term.set_input_text)
        dlg.exec()

    # ------------------------------------------------------------------
    # Macro recording
    # ------------------------------------------------------------------
    def _record_if_active(self, cmd: str) -> None:
        if self._recording:
            self._recorded.append(cmd)

    def _on_toggle_record(self) -> None:
        if not self._recording:
            self._recording = True
            self._recorded = []
            self._record_btn.setText(strings.TERM_BTN_STOP_RECORDING)
            self._status_label.setText(strings.TERM_MSG_RECORDING)
            return
        self._recording = False
        self._record_btn.setText(strings.TERM_BTN_RECORD)
        commands = list(self._recorded)
        self._recorded = []
        if not commands:
            self._status_label.setText(strings.TERM_MSG_RECORDING_EMPTY)
            return
        dlg = _SaveMacroDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self._status_label.setText(strings.TERM_MSG_RECORDING_DISCARDED)
            return
        name = dlg.macro_name()
        if not name:
            QMessageBox.warning(
                self,
                strings.TERM_LABEL_SAVE_MACRO_TITLE,
                strings.TERM_MSG_NAME_REQUIRED,
            )
            return
        if self._db is None:
            return
        try:
            self._db.save_macro(name, commands)
        except Exception as exc:
            _log.warning("save_macro failed: %s", exc)
            return
        self._status_label.setText(
            strings.TERM_MSG_MACRO_SAVED.format(name=name, count=len(commands))
        )
        self._reload_macros()

    # ------------------------------------------------------------------
    # Macro list
    # ------------------------------------------------------------------
    def _reload_macros(self) -> None:
        self._macro_list.clear()
        if self._db is None:
            return
        try:
            macros = self._db.get_macros()
        except Exception as exc:
            _log.warning("get_macros failed: %s", exc)
            return
        for m in macros:
            item = QListWidgetItem(m["name"])
            item.setData(_MACRO_ID_ROLE, int(m["id"]))
            item.setData(_MACRO_CMDS_ROLE, list(m["commands"]))
            self._macro_list.addItem(item)
        self._sync_buttons()

    def _selected_macro_item(self) -> Optional[QListWidgetItem]:
        items = self._macro_list.selectedItems()
        return items[0] if items else None

    def _sync_buttons(self) -> None:
        if self._playback_active:
            self._play_btn.setText(strings.TERM_BTN_STOP_PLAYBACK)
            self._play_btn.setEnabled(True)
        else:
            self._play_btn.setText(strings.TERM_BTN_PLAY)
            self._play_btn.setEnabled(self._selected_macro_item() is not None)

    def _on_macro_double_clicked(self, item: QListWidgetItem) -> None:
        self._start_playback_from_item(item)

    def _on_macro_context_menu(self, pos) -> None:
        item = self._macro_list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        rename_action = menu.addAction(strings.TERM_MENU_RENAME)
        delete_action = menu.addAction(strings.TERM_MENU_DELETE)
        export_action = menu.addAction(strings.TERM_MENU_EXPORT)
        chosen = menu.exec(self._macro_list.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is rename_action:
            self._rename_macro(item)
        elif chosen is delete_action:
            self._delete_macro(item)
        elif chosen is export_action:
            self._export_macro(item)

    def _rename_macro(self, item: QListWidgetItem) -> None:
        if self._db is None:
            return
        macro_id = int(item.data(_MACRO_ID_ROLE))
        current = item.text()
        new_name, ok = QInputDialog.getText(
            self,
            strings.TERM_LABEL_RENAME_MACRO_TITLE,
            strings.TERM_FIELD_NAME,
            QLineEdit.EchoMode.Normal,
            current,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(
                self,
                strings.TERM_LABEL_RENAME_MACRO_TITLE,
                strings.TERM_MSG_NAME_REQUIRED,
            )
            return
        try:
            self._db.rename_macro(macro_id, new_name)
        except Exception as exc:
            _log.warning("rename_macro failed: %s", exc)
            return
        self._reload_macros()

    def _delete_macro(self, item: QListWidgetItem) -> None:
        if self._db is None:
            return
        name = item.text()
        confirm = QMessageBox.question(
            self,
            strings.TERM_LABEL_DELETE_MACRO_TITLE,
            strings.TERM_CONFIRM_DELETE_MACRO.format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        macro_id = int(item.data(_MACRO_ID_ROLE))
        try:
            self._db.delete_macro(macro_id)
        except Exception as exc:
            _log.warning("delete_macro failed: %s", exc)
            return
        self._reload_macros()

    def _export_macro(self, item: QListWidgetItem) -> None:
        name = item.text()
        commands = list(item.data(_MACRO_CMDS_ROLE) or [])
        default_path = str(Path.home() / f"{name}.json")
        path, _filter = QFileDialog.getSaveFileName(
            self,
            strings.TERM_LABEL_EXPORT_MACRO_TITLE,
            default_path,
            strings.TERM_FILTER_JSON,
        )
        if not path:
            return
        payload = {"name": name, "commands": commands}
        try:
            Path(path).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            _log.warning("export macro failed: %s", exc)
            return
        self._status_label.setText(
            strings.TERM_MSG_MACRO_EXPORTED.format(path=path)
        )

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    def _on_play_stop(self) -> None:
        if self._playback_active:
            self._stop_playback()
            return
        item = self._selected_macro_item()
        if item is not None:
            self._start_playback_from_item(item)

    def _start_playback_from_item(self, item: QListWidgetItem) -> None:
        if self._pty is None or not self._pty.is_running():
            return
        commands = list(item.data(_MACRO_CMDS_ROLE) or [])
        if not commands:
            return
        self._playback_cmds = commands
        self._playback_index = 0
        self._playback_active = True
        self._sync_buttons()
        self._tick_playback()

    def _tick_playback(self) -> None:
        if not self._playback_active:
            return
        if self._playback_index >= len(self._playback_cmds):
            self._stop_playback(done=True)
            return
        if self._pty is None or not self._pty.is_running():
            self._stop_playback()
            return
        cmd = self._playback_cmds[self._playback_index]
        n = self._playback_index + 1
        m = len(self._playback_cmds)
        self._playback_label.setText(
            strings.TERM_MSG_RUNNING.format(n=n, m=m, cmd=cmd)
        )
        self._pty.write((cmd + "\n").encode("utf-8"))
        self._playback_index += 1
        self._playback_timer.start(_PLAYBACK_STEP_MS)

    def _stop_playback(self, done: bool = False, quiet: bool = False) -> None:
        self._playback_timer.stop()
        was_active = self._playback_active
        self._playback_active = False
        self._playback_cmds = []
        self._playback_index = 0
        self._sync_buttons()
        if not was_active:
            self._playback_label.setText("")
            return
        if quiet:
            self._playback_label.setText("")
            return
        if done:
            self._playback_label.setText(strings.TERM_MSG_PLAYBACK_DONE)
        else:
            self._playback_label.setText(strings.TERM_MSG_PLAYBACK_STOPPED)

    # ------------------------------------------------------------------
    # Theme glue
    # ------------------------------------------------------------------
    def _theme_manager(self):
        mgr = get_theme_manager()
        if mgr is not None:
            return mgr
        win = self.window()
        return getattr(win, "_theme", None)

    def _resolve_dark(self) -> bool:
        mgr = self._theme_manager()
        if mgr is None:
            return True
        try:
            current = mgr.current_theme()
        except Exception:
            return True
        if current == Theme.LIGHT:
            return False
        if current == Theme.DARK:
            return True
        # SYSTEM — fall back to the manager's internal effective theme.
        effective = getattr(mgr, "_effective", Theme.DARK)
        return effective != Theme.LIGHT

    @Slot(object)
    def _on_theme_changed(self, effective: object) -> None:
        try:
            is_light = effective == Theme.LIGHT
        except Exception:
            is_light = False
        self._term.set_dark(not is_light)


__all__ = ["TerminalModule"]
