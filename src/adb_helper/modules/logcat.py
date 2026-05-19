"""Module: Logcat (Spec §3.8).

One-shot export of ``adb logcat -d`` to a host file. Filename format
``logcat_<DD.MM.YY_HH.mm>_<TZ>.txt`` using the host timezone offset.
Streaming/live logcat is out of scope (§9).
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, List, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
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
from ..ui.style_utils import set_variant as _set_variant
from ..core import platform as _platform

_log = get_logger(__name__)

_RECENT_MAX = 10
_RECENT_KEY = "logcat_recent"
_PATH_ROLE = Qt.ItemDataRole.UserRole + 1


class _LogcatErrorDialog(QDialog):
    """Error dialog with collapsible raw-output section."""

    def __init__(
        self, message: str, raw: str, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(strings.LOG_TITLE_ERROR)
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

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
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        # --- Export Logcat Buffer card -----------------------------------
        buffer_card = QGroupBox(strings.LOG_TITLE_BUFFER, self)
        buffer_lay = QHBoxLayout(buffer_card)
        buffer_lay.setSpacing(16)

        # Left column: description + command preview + action row
        left = QWidget(buffer_card)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        self._desc_lbl = QLabel(strings.LOG_HINT_DESC, left)
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setProperty("secondary", "true")
        self._desc_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        left_lay.addWidget(self._desc_lbl)

        self._cmd_preview = QLabel("", left)
        self._cmd_preview.setObjectName("logcatCmdPreview")
        self._cmd_preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._cmd_preview.setWordWrap(True)
        self._cmd_preview.setStyleSheet(
            "QLabel#logcatCmdPreview {"
            " font-family: monospace;"
            " padding: 10px 12px;"
            " border: 1px solid palette(mid);"
            " border-radius: 4px;"
            " background: palette(alternate-base);"
            "}"
        )
        self._cmd_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        left_lay.addWidget(self._cmd_preview)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self._export_btn = QPushButton(strings.LOG_BTN_EXPORT, left)
        _set_variant(self._export_btn, "primary")
        self._export_btn.setEnabled(False)
        self._export_btn.setMinimumHeight(36)
        self._export_btn.clicked.connect(self._on_export)
        action_row.addWidget(self._export_btn, 1)

        self._open_folder_btn = QPushButton(strings.DB_BTN_OPEN_FOLDER, left)
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        action_row.addWidget(self._open_folder_btn, 0)
        left_lay.addLayout(action_row)

        self._progress = QProgressBar(left)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        left_lay.addWidget(self._progress)

        self._status_lbl = QLabel("", left)
        self._status_lbl.setProperty("secondary", "true")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        left_lay.addWidget(self._status_lbl)

        left_lay.addStretch(1)
        buffer_lay.addWidget(left, 1)

        # Right column: configuration panel
        right = QFrame(buffer_card)
        right.setFrameShape(QFrame.Shape.StyledPanel)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(10, 8, 10, 8)
        right_lay.setSpacing(6)

        cfg_title = QLabel(strings.LOG_TITLE_CONFIG, right)
        cfg_title.setProperty("muted", "true")
        right_lay.addWidget(cfg_title)

        cfg_form = QFormLayout()
        cfg_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        cfg_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        cfg_form.setHorizontalSpacing(10)
        cfg_form.setVerticalSpacing(4)

        sm = SettingsManager.instance()
        self._folder_value = QLineEdit(right)
        self._folder_value.setReadOnly(True)
        self._folder_value.setText(str(sm.get("logcat_folder", str(paths.logcat_dir()))))
        self._folder_value.setCursorPosition(0)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        folder_row.addWidget(self._folder_value, 1)
        self._browse_btn = QPushButton(strings.LOG_BTN_BROWSE, right)
        self._browse_btn.clicked.connect(self._on_browse_folder)
        folder_row.addWidget(self._browse_btn, 0)
        folder_wrap = QWidget(right)
        folder_wrap.setLayout(folder_row)
        cfg_form.addRow(QLabel(strings.LOG_LABEL_SAVE_FOLDER, right), folder_wrap)

        filename_val = QLabel(strings.LOG_VAL_FILENAME_PATTERN, right)
        filename_val.setWordWrap(True)
        filename_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cfg_form.addRow(QLabel(strings.LOG_LABEL_FILENAME, right), filename_val)

        mode_val = QLabel(strings.LOG_VAL_MODE, right)
        mode_val.setWordWrap(True)
        cfg_form.addRow(QLabel(strings.LOG_LABEL_MODE, right), mode_val)

        self._tz_val = QLabel(self._current_tz_label(), right)
        cfg_form.addRow(QLabel(strings.LOG_LABEL_TIMEZONE, right), self._tz_val)

        right_lay.addLayout(cfg_form)
        right_lay.addStretch(1)
        buffer_lay.addWidget(right, 1)

        root.addWidget(buffer_card)

        # --- Recent Exports card -----------------------------------------
        recent_card = QGroupBox(strings.LOG_TITLE_RECENT, self)
        recent_lay = QVBoxLayout(recent_card)
        recent_lay.setSpacing(6)

        header_row = QHBoxLayout()
        self._recent_count_lbl = QLabel("", recent_card)
        self._recent_count_lbl.setProperty("secondary", "true")
        header_row.addWidget(self._recent_count_lbl, 1)
        recent_lay.addLayout(header_row)

        self._recent_list = QListWidget(recent_card)
        self._recent_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._recent_list.customContextMenuRequested.connect(self._on_recent_context_menu)
        self._recent_list.itemDoubleClicked.connect(self._on_recent_open)
        self._recent_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        recent_lay.addWidget(self._recent_list, 1)

        root.addWidget(recent_card, 1)

        self._refresh_cmd_preview(None)
        self._load_recent()

    def _wire_signals(self) -> None:
        self._adb.processes.processOutput.connect(self._on_proc_output)
        self._adb.processes.processStopped.connect(self._on_proc_stopped)

    # --------------------------------------------------------- helpers
    def _current_tz_label(self) -> str:
        now = datetime.now(timezone.utc).astimezone()
        offset = now.utcoffset()
        total_s = int(offset.total_seconds()) if offset else 0
        sign = "+" if total_s >= 0 else "-"
        hh = abs(total_s) // 3600
        return f"GMT{sign}{hh}"

    def _current_folder(self) -> Path:
        sm = SettingsManager.instance()
        return Path(sm.get("logcat_folder", str(paths.logcat_dir())))

    def _refresh_cmd_preview(self, serial: Optional[str]) -> None:
        folder = str(self._current_folder())
        token = serial or "<serial>"
        self._cmd_preview.setText(
            f"$ adb -s {token} logcat -d >\n"
            f"  {folder}/logcat_DD.MM.YY_HH.mm_GMT±N.txt"
        )

    def _on_open_folder(self) -> None:
        folder = self._current_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log.warning("logcat folder mkdir failed: %s", exc)
        _open_folder(folder)

    def _on_browse_folder(self) -> None:
        current = str(self._current_folder())
        chosen = QFileDialog.getExistingDirectory(
            self, strings.LOG_LABEL_SAVE_FOLDER, current
        )
        if not chosen:
            return
        SettingsManager.instance().set("logcat_folder", chosen)
        self._folder_value.setText(chosen)
        self._folder_value.setCursorPosition(0)
        self._refresh_cmd_preview(self._serial)

    # --------------------------------------------------------- recent list
    def _load_recent(self) -> None:
        sm = SettingsManager.instance()
        raw = sm.get(_RECENT_KEY, "[]")
        try:
            entries = json.loads(raw) if isinstance(raw, str) else list(raw)
        except (ValueError, TypeError):
            entries = []
        self._recent_list.clear()
        for entry in entries[:_RECENT_MAX]:
            path = entry.get("path", "")
            ts = entry.get("ts", "")
            if not path:
                continue
            item = QListWidgetItem(f"{Path(path).name}    {ts}")
            item.setData(_PATH_ROLE, path)
            item.setToolTip(path)
            self._recent_list.addItem(item)
        self._update_recent_count()

    def _save_recent(self, entries: List[dict]) -> None:
        SettingsManager.instance().set(
            _RECENT_KEY, json.dumps(entries[:_RECENT_MAX], ensure_ascii=False)
        )

    def _record_recent(self, path: Path) -> None:
        sm = SettingsManager.instance()
        raw = sm.get(_RECENT_KEY, "[]")
        try:
            entries = json.loads(raw) if isinstance(raw, str) else list(raw)
        except (ValueError, TypeError):
            entries = []
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entries.insert(0, {"path": str(path), "ts": ts})
        # de-dupe by path while preserving order
        seen: set = set()
        deduped: List[dict] = []
        for e in entries:
            p = e.get("path")
            if not p or p in seen:
                continue
            seen.add(p)
            deduped.append(e)
        self._save_recent(deduped)
        self._load_recent()

    def _update_recent_count(self) -> None:
        n = self._recent_list.count()
        if n == 0:
            self._recent_count_lbl.setText(strings.LOG_RECENT_EMPTY)
        else:
            self._recent_count_lbl.setText(strings.LOG_FILE_COUNT.format(n=n))

    def _on_recent_open(self, item: QListWidgetItem) -> None:
        path = item.data(_PATH_ROLE)
        if not path:
            return
        p = Path(path)
        if not p.exists():
            QMessageBox.warning(self, strings.LOG_TITLE_EXPORT, str(p))
            return
        _open_folder(p.parent)

    def _on_recent_context_menu(self, pos) -> None:
        item = self._recent_list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        open_action = menu.addAction(strings.LOG_BTN_OPEN_FILE)
        remove_action = menu.addAction(strings.LOG_BTN_REMOVE)
        chosen = menu.exec(self._recent_list.viewport().mapToGlobal(pos))
        if chosen is open_action:
            self._on_recent_open(item)
        elif chosen is remove_action:
            self._remove_recent(item)

    def _remove_recent(self, item: QListWidgetItem) -> None:
        path = item.data(_PATH_ROLE)
        if not path:
            return
        sm = SettingsManager.instance()
        raw = sm.get(_RECENT_KEY, "[]")
        try:
            entries = json.loads(raw) if isinstance(raw, str) else list(raw)
        except (ValueError, TypeError):
            entries = []
        entries = [e for e in entries if e.get("path") != path]
        self._save_recent(entries)
        self._load_recent()

    # ----------------------------------------------------- IModule lifecycle
    def on_activate(self) -> None:
        self._tz_val.setText(self._current_tz_label())
        self._load_recent()
        ctx = self._adb.active_device
        if ctx is not None and ctx.status == "online":
            self._serial = ctx.serial
            self._export_btn.setEnabled(self._logcat_pid is None)
            self._status_lbl.setText("")
        else:
            self._serial = None
            self._export_btn.setEnabled(False)
            self._status_lbl.setText(strings.LOG_MSG_NO_DEVICE)
        self._refresh_cmd_preview(self._serial)

    def on_deactivate(self) -> None:
        pass

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        if ctx is not None and ctx.status == "online":
            self._serial = ctx.serial
            self._export_btn.setEnabled(self._logcat_pid is None)
        else:
            self._serial = None
            self._export_btn.setEnabled(False)
        self._refresh_cmd_preview(self._serial)

    def on_device_disconnected(self) -> None:
        self._serial = None
        self._export_btn.setEnabled(False)
        self._refresh_cmd_preview(None)

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
            self._record_recent(path)  # type: ignore[arg-type]
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
