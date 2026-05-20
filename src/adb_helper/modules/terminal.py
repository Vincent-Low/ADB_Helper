"""Module: Terminal (Spec §3.2; Redesign §5.2).

Wires a :class:`TerminalWidget` to a :class:`PtySession` (Linux ``pty``;
Windows ConPTY belongs in core, out of scope here).

Layout (Redesign §5.2):
    Page header (title + subtitle showing active serial, History/Clear)
    ├── Terminal card (stretch=1) — status line + TerminalWidget
    └── #macroPanel (fixedWidth 260) — placeholder per plan, recording
        and playback intentionally disabled with "Not implemented yet"
        tooltip until the macro UX is reinstated.

Behaviour preserved from prior version: PTY lifecycle (start on activation,
restart on device change, stop on disconnect), command history (DB-backed),
Ctrl+C interrupt, theme tracking. Macro recording/playback UI is removed
per plan §5.2; the macros DB schema is untouched.

CLAUDE.md invariants:
  - 1 (ADB I/O): all ADB traffic goes through :class:`PtySession` (core).
  - 2 (IModule): full lifecycle implemented.
  - 3 (strings): all user-facing text comes from :mod:`adb_helper.core.strings`.
  - 4 (platform): platform branching is delegated to :class:`PtySession`.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
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
from ..ui.style_utils import card
from ..ui.style_utils import set_variant as _set_variant
from ..ui.terminal_widget import TerminalWidget
from ..ui.theme_manager import Theme, get_theme_manager

_log = get_logger(__name__)


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
    """Terminal screen (§3.2; Redesign §5.2)."""

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

        self._build_ui()
        self._wire_signals()
        self._reload_history()
        self._update_subtitle(self._adb.active_device)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        # --- page header --------------------------------------------------
        self._history_btn = QPushButton(strings.TERM_BTN_HISTORY)
        self._clear_btn = QPushButton(strings.TERM_BTN_CLEAR)

        header = QWidget(self)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        title_lbl = QLabel(strings.LABEL_TERMINAL, header)
        title_lbl.setProperty("role", "page-title")
        self._subtitle_lbl = QLabel("", header)
        self._subtitle_lbl.setProperty("role", "hint")
        text_col.addWidget(title_lbl)
        text_col.addWidget(self._subtitle_lbl)
        header_row.addLayout(text_col, 1)
        header_row.addWidget(self._history_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        header_row.addWidget(self._clear_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(header)

        # --- body: terminal card + macro panel ----------------------------
        body = QWidget(self)
        body_row = QHBoxLayout(body)
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(14)

        body_row.addWidget(self._build_terminal_card(), 1)
        body_row.addWidget(self._build_macro_panel(), 0)
        root.addWidget(body, 1)

    def _build_terminal_card(self) -> QWidget:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        self._status_label = QLabel("")
        self._status_label.setObjectName("TerminalStatus")
        self._status_label.setWordWrap(True)
        body_lay.addWidget(self._status_label)

        self._term = TerminalWidget(body, dark=self._resolve_dark())
        body_lay.addWidget(self._term, 1)

        return card(strings.LABEL_TERMINAL.upper(), body, parent=self)

    def _build_macro_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setObjectName("macroPanel")
        panel.setFixedWidth(260)
        panel_lay = QVBoxLayout(panel)
        panel_lay.setContentsMargins(14, 14, 14, 14)
        panel_lay.setSpacing(10)

        header = QLabel(strings.TERM_CARD_MACROS, panel)
        header.setProperty("role", "section-label")
        panel_lay.addWidget(header)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self._record_btn = QPushButton(strings.TERM_BTN_RECORD_SHORT, panel)
        self._record_btn.setEnabled(False)
        self._record_btn.setToolTip(strings.TOOLTIP_NOT_IMPLEMENTED)
        self._play_btn = QPushButton(strings.TERM_BTN_PLAY, panel)
        self._play_btn.setEnabled(False)
        self._play_btn.setToolTip(strings.TOOLTIP_NOT_IMPLEMENTED)
        actions_row.addWidget(self._record_btn)
        actions_row.addWidget(self._play_btn)
        actions_row.addStretch(1)
        panel_lay.addLayout(actions_row)

        panel_lay.addStretch(1)
        empty_lbl = QLabel(strings.TERM_MACROS_EMPTY, panel)
        empty_lbl.setProperty("role", "hint")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_lay.addWidget(empty_lbl)
        panel_lay.addStretch(2)

        return panel

    def _wire_signals(self) -> None:
        self._adb.activeDeviceChanged.connect(self._on_active_device_changed)

        self._clear_btn.clicked.connect(self._term.clear_output)
        self._history_btn.clicked.connect(self._open_history_dialog)

        self._term.command_entered.connect(self._on_command_entered)
        self._term.history_up_pressed.connect(self._on_history_up)
        self._term.history_down_pressed.connect(self._on_history_down)
        self._term.interrupt_pressed.connect(self._on_interrupt)

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
        ctx = self._adb.active_device
        self._update_subtitle(ctx)
        current_serial = ctx.serial if ctx is not None else None
        if self._is_pty_alive() and current_serial == self._active_serial:
            self._term.focus_input()
            return
        self._sync_session_for(ctx)
        self._term.focus_input()

    def on_deactivate(self) -> None:
        self._activated = False
        # PTY survives navigation away — only torn down on device change,
        # disconnect, or app shutdown.

    def _is_pty_alive(self) -> bool:
        if self._pty is None:
            return False
        return self._pty.is_running()

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._update_subtitle(ctx)
        self._sync_session_for(ctx)

    def on_device_disconnected(self) -> None:
        self._close_session()
        self._term.write_local_line(strings.TERM_MSG_DEVICE_DISCONNECTED)
        self._term.set_input_enabled(False)
        self._term.set_prompt_serial(None)
        self._status_label.setText(strings.TERM_MSG_DEVICE_DISCONNECTED)
        self._update_subtitle(None)

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
        if self._pty is not None:
            self._pty.deleteLater()
        self._pty = None
        self._active_serial = None

    # ------------------------------------------------------------------
    # Active device wiring + subtitle
    # ------------------------------------------------------------------
    @Slot(object)
    def _on_active_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._update_subtitle(ctx)
        if not self._activated:
            return
        self._sync_session_for(ctx)

    def _update_subtitle(self, ctx: Optional[DeviceContext]) -> None:
        serial = ctx.serial if ctx is not None else "—"
        self._subtitle_lbl.setText(
            strings.PAGE_SUBTITLE_TERMINAL.format(serial=serial)
        )

    # ------------------------------------------------------------------
    # Command entry + history
    # ------------------------------------------------------------------
    def _on_command_entered(self, text: str) -> None:
        cmd = text.rstrip("\n")
        self._history_index = -1
        if self._pty is None or not self._pty.is_running():
            return
        self._pty.write((cmd + "\n").encode("utf-8"))
        if cmd.strip():
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
