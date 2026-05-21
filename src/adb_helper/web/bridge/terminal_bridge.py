"""TerminalBridge — PtySession ↔ xterm.js + macros + command history.

PTY raw bytes are base64-encoded on the way to JS so binary-safe transit
through QWebChannel. xterm.js decodes with a single TextDecoder pass.
"""
from __future__ import annotations

import base64
import threading
from typing import List, Optional

from PySide6.QtCore import QTimer, Signal, Slot

from ...core import platform as _platform
from ...core.adb_service import AdbService
from ...core.db_manager import DatabaseManager
from ...core.logger import get_logger
from ...core.pty_session import PtySession
from .base import BridgeBase

_log = get_logger(__name__)


class TerminalBridge(BridgeBase):
    output = Signal(str)        # base64 chunk
    exited = Signal(int)        # exit code
    started = Signal(str)       # serial

    def __init__(self, adb: AdbService, db: DatabaseManager) -> None:
        super().__init__()
        self._adb = adb
        self._db = db
        self._pty: Optional[PtySession] = None
        self._current_serial: Optional[str] = None

    # --- lifecycle ------------------------------------------------------
    @Slot(str, result=bool)
    def start(self, serial: str) -> bool:
        if not _platform.IS_LINUX:
            _log.warning("PTY shell requested on non-Linux host; rejected.")
            return False
        if self._pty is not None:
            if self._pty.is_running() and self._current_serial == serial:
                return True
            self._dispose_pty()
        session = PtySession(serial=serial, parent=self)
        session.output_ready.connect(self._on_pty_output)
        session.process_exited.connect(self._on_pty_exit)
        ok = session.start()
        if not ok:
            session.deleteLater()
            return False
        self._pty = session
        self._current_serial = serial
        self.started.emit(serial)
        return True

    def _dispose_pty(self) -> None:
        """Detach + asynchronously close so the UI thread stays responsive.

        ``PtySession.close()`` joins the reader thread with a 3 s grace
        period — blocking the UI for that long visibly stalls Vue
        animations (Bug § audit "medium 8").  We detach the reference
        immediately and run close() on a daemon thread; deleteLater()
        runs back on the main thread via QTimer.singleShot(0).
        """
        if self._pty is None:
            return
        old = self._pty
        self._pty = None
        self._current_serial = None

        def _close_and_finalise() -> None:
            try:
                old.close()
            except Exception as exc:  # noqa: BLE001 — logged, never re-raised
                _log.warning("PtySession.close raised: %s", exc)
            # deleteLater must be invoked on the GUI thread.
            QTimer.singleShot(0, old.deleteLater)

        threading.Thread(
            target=_close_and_finalise,
            name="pty-dispose",
            daemon=True,
        ).start()

    @Slot(str)
    def write(self, data: str) -> None:
        if self._pty is None or not self._pty.is_running():
            return
        try:
            self._pty.write(data.encode("utf-8"))
        except UnicodeEncodeError:
            self._pty.write(data.encode("utf-8", errors="replace"))

    @Slot()
    def close(self) -> None:
        self._dispose_pty()

    @Slot(result=bool)
    def isRunning(self) -> bool:
        return self._pty is not None and self._pty.is_running()

    @Slot(result=bool)
    def supportsPty(self) -> bool:
        return _platform.IS_LINUX

    # --- internal handlers ---------------------------------------------
    def _on_pty_output(self, data: bytes) -> None:
        if not data:
            return
        self.output.emit(base64.b64encode(data).decode("ascii"))

    def _on_pty_exit(self, rc: int) -> None:
        # PtySession finalises its own state machine before emitting.
        # We don't call close() here (already exited) but still schedule
        # deleteLater() so the QObject parent doesn't accumulate sessions.
        if self._pty is not None:
            self._pty.deleteLater()
            self._pty = None
            self._current_serial = None
        self.exited.emit(int(rc))

    # --- history --------------------------------------------------------
    @Slot(result="QVariant")
    def history(self) -> List[str]:
        return self._db.get_command_history()

    @Slot(str)
    def appendHistory(self, command: str) -> None:
        self._db.add_command_history(command)

    # --- macros ---------------------------------------------------------
    @Slot(result="QVariant")
    def listMacros(self) -> List[dict]:
        return self._db.get_macros()

    @Slot(str, "QVariant", result=int)
    def saveMacro(self, name: str, commands: List[str]) -> int:
        return int(self._db.save_macro(name, list(commands)))

    @Slot(int, str)
    def renameMacro(self, macro_id: int, name: str) -> None:
        self._db.rename_macro(int(macro_id), name)

    @Slot(int)
    def deleteMacro(self, macro_id: int) -> None:
        self._db.delete_macro(int(macro_id))


__all__ = ["TerminalBridge"]
