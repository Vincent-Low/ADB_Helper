"""Module: Logcat (Spec §3.8).

One-shot export of ``adb logcat -d`` to a host file. Filename format
``logcat_<DD.MM.YY_HH.mm>_<TZ>.txt`` using the host timezone offset.
Streaming/live logcat is out of scope (§9).
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core import paths, strings
from ..core.adb_service import get_adb_service
from ..core.device_context import DeviceContext
from ..core.imodule import IModule
from ..core.logger import get_logger
from ..core.settings_manager import SettingsManager
from ..core import platform as _platform

_log = get_logger(__name__)


class _LogcatErrorDialog(QDialog):
    """Error dialog with collapsible raw-output section."""

    def __init__(
        self, message: str, raw: str, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(strings.LOG_TITLE_ERROR)
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        root.addWidget(QLabel(message, self))

        self._details_btn = QPushButton(strings.LOG_BTN_SHOW_DETAILS, self)
        self._details_btn.setCheckable(True)
        self._details_btn.setVisible(bool(raw))
        self._details_btn.toggled.connect(self._on_toggle)
        root.addWidget(self._details_btn)

        self._raw_edit = QTextEdit(self)
        self._raw_edit.setReadOnly(True)
        self._raw_edit.setPlainText(raw)
        self._raw_edit.setFixedHeight(200)
        self._raw_edit.setVisible(False)
        root.addWidget(self._raw_edit)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton(strings.LOG_BTN_CLOSE, self)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    def _on_toggle(self, checked: bool) -> None:
        self._details_btn.setText(
            strings.LOG_BTN_HIDE_DETAILS if checked else strings.LOG_BTN_SHOW_DETAILS
        )
        self._raw_edit.setVisible(checked)
        self.adjustSize()


class LogcatModule(IModule):
    """Logcat export screen (§3.8)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        self._serial: Optional[str] = None
        self._logcat_pid: Optional[str] = None
        self._logcat_path: Optional[Path] = None
        self._logcat_file: Optional[IO[bytes]] = None
        self._build_ui()
        self._wire_signals()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        btn_row = QHBoxLayout()
        self._export_btn = QPushButton(strings.LOG_BTN_EXPORT, self)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        btn_row.addWidget(self._export_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status_lbl = QLabel("", self)
        self._status_lbl.setProperty("secondary", "true")
        root.addWidget(self._status_lbl)

        root.addStretch(1)

    def _wire_signals(self) -> None:
        self._adb.processes.processOutput.connect(self._on_proc_output)
        self._adb.processes.processStopped.connect(self._on_proc_stopped)

    # ----------------------------------------------------- IModule lifecycle
    def on_activate(self) -> None:
        ctx = self._adb.active_device
        if ctx is not None and ctx.status == "online":
            self._serial = ctx.serial
            self._export_btn.setEnabled(self._logcat_pid is None)
            self._status_lbl.setText("")
        else:
            self._serial = None
            self._export_btn.setEnabled(False)
            self._status_lbl.setText(strings.LOG_MSG_NO_DEVICE)

    def on_deactivate(self) -> None:
        pass

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        if ctx is not None and ctx.status == "online":
            self._serial = ctx.serial
            self._export_btn.setEnabled(self._logcat_pid is None)
        else:
            self._serial = None
            self._export_btn.setEnabled(False)

    def on_device_disconnected(self) -> None:
        self._serial = None
        self._export_btn.setEnabled(False)

    # ------------------------------------------------------------ Export
    def _on_export(self) -> None:
        if not self._serial or self._logcat_pid is not None:
            return

        now = datetime.now(timezone.utc).astimezone()
        offset = now.utcoffset()
        total_s = int(offset.total_seconds()) if offset else 0
        sign = "+" if total_s >= 0 else "-"
        hh = abs(total_s) // 3600
        tz_str = f"GMT{sign}{hh}"
        filename = now.strftime("%d.%m.%y_%H.%M")
        filename = f"logcat_{filename}_{tz_str}.txt"

        sm = SettingsManager.instance()
        folder = Path(sm.get("logcat_folder", str(paths.logcat_dir())))
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log.error("logcat folder create failed: %s", exc)
            _LogcatErrorDialog(str(exc), "", self).exec()
            return

        self._logcat_path = folder / filename
        try:
            self._logcat_file = self._logcat_path.open("wb")
        except OSError as exc:
            _log.error("logcat file open failed: %s", exc)
            _LogcatErrorDialog(str(exc), "", self).exec()
            return

        self._logcat_pid = f"logcat_{self._serial}_{id(self)}"
        _log.info("logcat export start serial=%s path=%s", self._serial, self._logcat_path)

        ok = self._adb.spawn_adb(self._logcat_pid, self._serial, ["logcat", "-d"])
        if not ok:
            try:
                self._logcat_file.close()
            except OSError:
                pass
            self._logcat_file = None
            self._logcat_pid = None
            _LogcatErrorDialog(strings.LOG_MSG_ERROR, "", self).exec()
            return

        self._export_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._status_lbl.setText(strings.LOG_MSG_EXPORTING)

    @Slot(str, bytes)
    def _on_proc_output(self, pid: str, data: bytes) -> None:
        if pid != self._logcat_pid:
            return
        if self._logcat_file is not None:
            try:
                self._logcat_file.write(data)
            except OSError as exc:
                _log.error("logcat write failed: %s", exc)

    @Slot(str, int)
    def _on_proc_stopped(self, pid: str, rc: int) -> None:
        if pid != self._logcat_pid:
            return
        self._logcat_pid = None
        self._progress.setVisible(False)

        if self._logcat_file is not None:
            try:
                self._logcat_file.close()
            except OSError:
                pass
            self._logcat_file = None

        path = self._logcat_path
        self._logcat_path = None

        ok = rc == 0 and path is not None and path.exists() and path.stat().st_size > 0
        if ok:
            _log.info("logcat exported rc=%s path=%s", rc, path)
            self._status_lbl.setText(strings.MSG_LOGCAT_SAVED.format(path=path))
            self._notify_success(path)  # type: ignore[arg-type]
        else:
            _log.error("logcat export failed rc=%s path=%s", rc, path)
            raw = ""
            if path is not None and path.exists():
                try:
                    raw = path.read_text(encoding="utf-8", errors="replace")[:4000]
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            _LogcatErrorDialog(strings.LOG_MSG_ERROR, raw, self).exec()
            self._status_lbl.setText("")

        self._export_btn.setEnabled(self._serial is not None)

    def _notify_success(self, path: Path) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(strings.LOG_TITLE_EXPORT)
        box.setText(strings.MSG_LOGCAT_SAVED.format(path=path))
        open_btn = box.addButton(
            strings.DB_BTN_OPEN_FOLDER, QMessageBox.ButtonRole.ActionRole
        )
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() is open_btn:
            _open_folder(path.parent)


def _open_folder(folder: Path) -> None:
    cmd = ["explorer", str(folder)] if _platform.IS_WINDOWS else ["xdg-open", str(folder)]
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        _log.warning("open folder failed: %s", exc)


__all__ = ["LogcatModule"]
