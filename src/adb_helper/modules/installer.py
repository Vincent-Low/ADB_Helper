"""Module: Installer (Spec §3.3; Redesign §5.3).

Independent of the global active device — maintains its own multi-device
checklist. Installs ``.apk``, ``.apks``, ``.xapk``, and ``.apkm`` sequentially
across N devices. ``.aab`` is unsupported (developer signing key required — §9).

Layout (Redesign §5.3): 4 stacked cards (Files / Targets / Installation /
Results) wrapped in a ``QScrollArea`` so the whole page scrolls — individual
tables grow with their contents (``AdjustToContents`` + scroll-bar always
off). The Installation card carries a primary ``Install`` button, ``Cancel``,
a 6 px ``QProgressBar``, a percent label, and a state-driven
``QFrame#InstallStatus`` row (``state="idle|running|done|error"``).

Drop targets (handoff §5.3): the page accepts file drops; .apk / .apks /
.xapk / .apkm files are added, .aab triggers the unsupported notice.

Sequential semantics (§3.3.3):
  - File × device order: file 1 → dev A, file 1 → dev B, …, file 2 → dev A, …
  - Per-file errors don't abort the batch — continue on remaining ops.
  - Mid-run disconnect: mark that device's remaining ops Failed, keep going.

All ADB I/O routes through :class:`AdbService`. ``.apks`` install spawns
``java -jar bundletool.jar install-apks`` via
:meth:`AdbService.spawn_process` (non-ADB child).
"""
from __future__ import annotations

import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core import paths, strings
from ..core.adb_service import get_adb_service
from ..core.device_context import DeviceContext
from ..core.error_parser import parse as parse_error
from ..core.imodule import IModule
from ..core.logger import get_logger
from ..ui.style_utils import card, page_header
from ..ui.style_utils import set_variant as _set_variant

_log = get_logger(__name__)

_SUPPORTED_EXTS = (".apk", ".apks", ".xapk", ".apkm")
_AAB_EXT = ".aab"

# Result roles on the result-table items.
_RES_OK = "ok"
_RES_FAIL = "fail"
_RES_SKIP = "skip"


# ----------------------------- data model -----------------------------

@dataclass
class _FileEntry:
    path: Path
    size: int

    @property
    def ext(self) -> str:
        return self.path.suffix.lower()


@dataclass
class _DeviceEntry:
    serial: str
    model: str


@dataclass
class _ResultEntry:
    file_name: str
    serial: str
    model: str
    state: str = _RES_FAIL          # ok / fail / skip
    human: str = ""
    raw: str = ""


@dataclass
class _Job:
    file_entry: _FileEntry
    device_entry: _DeviceEntry
    result: _ResultEntry = field(default=None)  # type: ignore[assignment]


# ----------------------------- result dialog --------------------------

class _SummaryDialog(QDialog):
    """Modal summary with per-job result + collapsible raw output (§7)."""

    def __init__(
        self, results: list[_ResultEntry], parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(strings.INSTALLER_TITLE_SUMMARY)
        self.setMinimumWidth(640)
        self.setMinimumHeight(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        ok = sum(1 for r in results if r.state == _RES_OK)
        fail = sum(1 for r in results if r.state != _RES_OK)
        root.addWidget(
            QLabel(strings.INSTALLER_MSG_DONE.format(ok=ok, fail=fail), self)
        )

        self._table = QTableWidget(len(results), 4, self)
        self._table.setHorizontalHeaderLabels([
            strings.INSTALLER_COL_FILE,
            strings.INSTALLER_COL_SERIAL,
            strings.INSTALLER_COL_MODEL,
            strings.INSTALLER_COL_RESULT,
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        for row, r in enumerate(results):
            self._table.setItem(row, 0, QTableWidgetItem(r.file_name))
            self._table.setItem(row, 1, QTableWidgetItem(r.serial))
            self._table.setItem(row, 2, QTableWidgetItem(r.model or ""))
            res_text = _result_text(r)
            res_item = QTableWidgetItem(res_text)
            self._table.setItem(row, 3, res_item)
        self._table.currentCellChanged.connect(self._on_row_changed)
        root.addWidget(self._table, 1)

        self._details_btn = QPushButton(strings.INSTALLER_BTN_SHOW_DETAILS, self)
        self._details_btn.setCheckable(True)
        self._details_btn.toggled.connect(self._on_toggle)
        root.addWidget(self._details_btn)

        self._raw = QTextEdit(self)
        self._raw.setReadOnly(True)
        self._raw.setVisible(False)
        self._raw.setFixedHeight(180)
        root.addWidget(self._raw)

        actions = QHBoxLayout()
        actions.addStretch(1)
        close = QPushButton(strings.INSTALLER_BTN_CLOSE, self)
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        root.addLayout(actions)

        self._results = results
        if results:
            self._table.selectRow(0)
            self._on_row_changed(0, 0, -1, -1)

    def _on_row_changed(
        self, row: int, _c: int, _pr: int, _pc: int
    ) -> None:
        if row < 0 or row >= len(self._results):
            self._raw.setPlainText("")
            return
        r = self._results[row]
        body = r.human or ""
        if r.raw:
            body = f"{body}\n\n--- raw output ---\n{r.raw}" if body else r.raw
        self._raw.setPlainText(body)

    def _on_toggle(self, checked: bool) -> None:
        self._details_btn.setText(
            strings.INSTALLER_BTN_HIDE_DETAILS
            if checked
            else strings.INSTALLER_BTN_SHOW_DETAILS
        )
        self._raw.setVisible(checked)
        self.adjustSize()


def _result_text(r: _ResultEntry) -> str:
    if r.state == _RES_OK:
        return strings.INSTALLER_RESULT_OK
    if r.state == _RES_SKIP:
        return strings.INSTALLER_RESULT_SKIPPED
    return strings.INSTALLER_RESULT_FAIL


# ----------------------------- module ---------------------------------

class InstallerModule(IModule):
    """Installer screen (§3.3; Redesign §5.3)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        self._files: list[_FileEntry] = []
        self._results_log: list[_ResultEntry] = []

        # Job runner state.
        self._queue: list[_Job] = []
        self._running_job: Optional[_Job] = None
        self._running_pid: Optional[str] = None
        self._running_stdout = bytearray()
        # device serial -> True if disconnected mid-run
        self._dropped_serials: set[str] = set()
        # serial -> last known model for result rendering
        self._serial_model: dict[str, str] = {}
        # temp extraction dirs to clean up after the batch
        self._scratch_dirs: list[Path] = []
        self._cancel_requested = False
        self._batch_total = 0

        self._build_ui()
        self._wire_signals()
        self._refresh_devices()
        self._set_install_state("idle")
        self.setAcceptDrops(True)

    # ----------------------------- UI ----------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(14)

        outer.addWidget(
            page_header(
                strings.LABEL_INSTALLER,
                strings.PAGE_SUBTITLE_INSTALLER,
                parent=self,
            )
        )

        scroll = QScrollArea(self)
        scroll.setObjectName("installerScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll, 1)

        stack_host = QWidget(scroll)
        stack = QVBoxLayout(stack_host)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(14)

        stack.addWidget(self._build_files_card())
        stack.addWidget(self._build_targets_card())
        stack.addWidget(self._build_installation_card())
        stack.addWidget(self._build_results_card())
        stack.addStretch(1)

        scroll.setWidget(stack_host)

    def _build_files_card(self) -> QWidget:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        self._files_table = QTableWidget(0, 4)
        self._files_table.setHorizontalHeaderLabels([
            "",
            strings.INSTALLER_COL_FILE,
            strings.INSTALLER_COL_TYPE,
            strings.INSTALLER_COL_SIZE,
        ])
        self._files_table.verticalHeader().setVisible(False)
        self._files_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._files_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._files_table.horizontalHeader().setStretchLastSection(True)
        self._files_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self._files_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Fixed
        )
        self._files_table.setColumnWidth(0, 28)
        # Whole-page scrolling: table grows with content, no inner scroll bar.
        self._files_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self._files_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._files_table.setMinimumHeight(96)
        body_lay.addWidget(self._files_table, 1)

        self._files_empty = QLabel(strings.INSTALLER_EMPTY_FILES, body)
        self._files_empty.setProperty("role", "hint")
        self._files_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._files_empty.setMinimumHeight(96)
        body_lay.addWidget(self._files_empty)
        self._files_empty.setVisible(True)
        self._files_table.setVisible(False)

        file_actions = QHBoxLayout()
        self._add_btn = QPushButton(strings.INSTALLER_BTN_ADD_FILES, body)
        self._add_btn.clicked.connect(self._on_add_files)
        self._remove_btn = QPushButton(strings.INSTALLER_BTN_REMOVE, body)
        _set_variant(self._remove_btn, "destructive")
        self._remove_btn.clicked.connect(self._on_remove_file)
        self._clear_btn = QPushButton(strings.INSTALLER_BTN_CLEAR, body)
        self._clear_btn.clicked.connect(self._on_clear_files)
        for b in (self._add_btn, self._remove_btn, self._clear_btn):
            file_actions.addWidget(b)
        file_actions.addStretch(1)
        body_lay.addLayout(file_actions)

        return card(strings.INSTALLER_LABEL_FILES, body, parent=self)

    def _build_targets_card(self) -> QWidget:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        self._devices_list = QListWidget(body)
        self._devices_list.setSelectionMode(QAbstractItemView.NoSelection)
        self._devices_list.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self._devices_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._devices_list.setMinimumHeight(96)
        body_lay.addWidget(self._devices_list, 1)

        self._devices_empty = QLabel(strings.INSTALLER_EMPTY_DEVICES, body)
        self._devices_empty.setProperty("role", "hint")
        self._devices_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._devices_empty.setMinimumHeight(96)
        body_lay.addWidget(self._devices_empty)
        self._devices_empty.setVisible(True)
        self._devices_list.setVisible(False)

        return card(strings.INSTALLER_LABEL_DEVICES, body, parent=self)

    def _build_installation_card(self) -> QWidget:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        run_row = QHBoxLayout()
        run_row.setSpacing(10)
        self._install_btn = QPushButton(strings.INSTALLER_BTN_INSTALL, body)
        _set_variant(self._install_btn, "primary")
        self._install_btn.setEnabled(False)
        self._install_btn.clicked.connect(self._on_install)
        self._cancel_btn = QPushButton(strings.INSTALLER_BTN_CANCEL, body)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setEnabled(False)
        run_row.addWidget(self._install_btn)
        run_row.addWidget(self._cancel_btn)

        self._progress = QProgressBar(body)
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        run_row.addWidget(self._progress, 1)

        self._pct_label = QLabel("0%", body)
        self._pct_label.setMinimumWidth(40)
        self._pct_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._pct_label.setFont(_mono_font(self._pct_label))
        run_row.addWidget(self._pct_label)
        body_lay.addLayout(run_row)

        # Install status row — QFrame#InstallStatus with semantic state property.
        self._status_frame = QFrame(body)
        self._status_frame.setObjectName("InstallStatus")
        sf_row = QHBoxLayout(self._status_frame)
        sf_row.setContentsMargins(10, 6, 10, 6)
        sf_row.setSpacing(8)
        self._status_dot = QLabel(self._status_frame)
        self._status_dot.setObjectName("statusDot")
        self._status_dot.setFixedSize(8, 8)
        self._status_text = QLabel(strings.INSTALL_STATUS_IDLE, self._status_frame)
        self._status_text.setObjectName("statusText")
        sf_row.addWidget(self._status_dot)
        sf_row.addWidget(self._status_text, 1)
        body_lay.addWidget(self._status_frame)

        # Legacy attribute name still used by some flows (kept as alias).
        self._status_lbl = self._status_text

        return card(strings.INSTALLER_LABEL_INSTALLATION, body, parent=self)

    def _build_results_card(self) -> QWidget:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        self._results_table = QTableWidget(0, 4)
        self._results_table.setHorizontalHeaderLabels([
            strings.INSTALLER_COL_FILE,
            strings.INSTALLER_COL_SERIAL,
            strings.INSTALLER_COL_MODEL,
            strings.INSTALLER_COL_RESULT,
        ])
        self._results_table.verticalHeader().setVisible(False)
        self._results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self._results_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self._results_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._results_table.setMinimumHeight(132)
        body_lay.addWidget(self._results_table, 1)

        self._results_empty = QLabel(strings.INSTALLER_EMPTY_RESULTS, body)
        self._results_empty.setProperty("role", "hint")
        self._results_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._results_empty.setMinimumHeight(132)
        body_lay.addWidget(self._results_empty)
        self._results_empty.setVisible(True)
        self._results_table.setVisible(False)

        return card(strings.INSTALLER_LABEL_RESULTS, body, parent=self)

    def _wire_signals(self) -> None:
        self._adb.devices.deviceConnected.connect(self._on_device_event)
        self._adb.devices.deviceDisconnected.connect(self._on_device_disconnected_signal)
        self._adb.devices.deviceStateChanged.connect(self._on_device_event)
        self._adb.processes.processOutput.connect(self._on_proc_output)
        self._adb.processes.processStopped.connect(self._on_proc_stopped)
        self._files_table.itemChanged.connect(lambda _: self._update_install_btn())
        self._devices_list.itemChanged.connect(lambda _: self._update_install_btn())

    # ------------------------ IModule lifecycle ------------------------
    def on_activate(self) -> None:
        self._refresh_devices()

    def on_deactivate(self) -> None:
        return None

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        # Installer is independent of the global active device (§3.3).
        return None

    def on_device_disconnected(self) -> None:
        return None

    # ------------------------- Drop targets ---------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: D401
        if event.mimeData().hasUrls() and self._has_droppable(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: D401
        if event.mimeData().hasUrls() and self._has_droppable(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: D401
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        accepted = False
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() not in _SUPPORTED_EXTS + (_AAB_EXT,):
                continue
            self._add_one_file(path)
            accepted = True
        if accepted:
            event.acceptProposedAction()
        else:
            event.ignore()

    @staticmethod
    def _has_droppable(event) -> bool:
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            if Path(url.toLocalFile()).suffix.lower() in _SUPPORTED_EXTS + (_AAB_EXT,):
                return True
        return False

    # -------------------------- Files panel ----------------------------
    def _on_add_files(self) -> None:
        # Adding new files clears the prior results log (§3.3.3).
        if self._results_log:
            self._results_log = []
            self._results_table.setRowCount(0)
            self._refresh_empty_states()
        paths_picked, _ = QFileDialog.getOpenFileNames(
            self,
            strings.INSTALLER_TITLE_ADD,
            str(Path.home()),
            strings.INSTALLER_FILTER_PACKAGES,
        )
        if not paths_picked:
            return
        for p in paths_picked:
            self._add_one_file(Path(p))

    def _add_one_file(self, path: Path) -> None:
        ext = path.suffix.lower()
        if ext == _AAB_EXT:
            self._status_text.setText(strings.INSTALLER_MSG_AAB_UNSUPPORTED)
            return
        if ext not in _SUPPORTED_EXTS:
            self._status_text.setText(
                strings.INSTALLER_MSG_UNSUPPORTED_FORMAT.format(ext=ext)
            )
            return
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        entry = _FileEntry(path=path, size=size)
        self._files.append(entry)
        row = self._files_table.rowCount()
        self._files_table.insertRow(row)
        chk_item = QTableWidgetItem()
        chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        chk_item.setCheckState(Qt.Checked)
        self._files_table.setItem(row, 0, chk_item)
        name_item = QTableWidgetItem(path.name)
        name_item.setData(Qt.UserRole, str(path))
        self._files_table.setItem(row, 1, name_item)
        self._files_table.setItem(row, 2, QTableWidgetItem(ext.lstrip(".")))
        self._files_table.setItem(row, 3, QTableWidgetItem(_fmt_size(size)))
        self._refresh_empty_states()
        self._update_install_btn()

    def _on_remove_file(self) -> None:
        rows = sorted(
            [
                r for r in range(self._files_table.rowCount())
                if (it := self._files_table.item(r, 0)) is not None
                and it.checkState() == Qt.Checked
            ],
            reverse=True,
        )
        for r in rows:
            self._files_table.removeRow(r)
            if 0 <= r < len(self._files):
                del self._files[r]
        self._refresh_empty_states()
        self._update_install_btn()

    def _on_clear_files(self) -> None:
        self._files_table.setRowCount(0)
        self._files.clear()
        self._refresh_empty_states()
        self._update_install_btn()

    def _refresh_empty_states(self) -> None:
        has_files = self._files_table.rowCount() > 0
        self._files_table.setVisible(has_files)
        self._files_empty.setVisible(not has_files)
        has_devices = self._devices_list.count() > 0
        self._devices_list.setVisible(has_devices)
        self._devices_empty.setVisible(not has_devices)
        has_results = self._results_table.rowCount() > 0
        self._results_table.setVisible(has_results)
        self._results_empty.setVisible(not has_results)

    # -------------------------- Devices panel --------------------------
    def _refresh_devices(self) -> None:
        # Preserve checked serials across refresh.
        checked = self._checked_serials()
        self._devices_list.clear()
        connected = sorted(
            self._adb.devices.known_devices(), key=lambda c: c.serial
        )
        for ctx in connected:
            if ctx.status != "online":
                continue
            label = f"{ctx.model or '?'} ({ctx.serial})"
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setData(Qt.UserRole, ctx.serial)
            item.setData(Qt.UserRole + 1, ctx.model or "")
            item.setCheckState(
                Qt.Checked if ctx.serial in checked else Qt.Unchecked
            )
            self._devices_list.addItem(item)
            self._serial_model[ctx.serial] = ctx.model or ""
        self._refresh_empty_states()
        self._update_install_btn()

    def _checked_serials(self) -> set[str]:
        out: set[str] = set()
        for i in range(self._devices_list.count()):
            it = self._devices_list.item(i)
            if it.checkState() == Qt.Checked:
                out.add(str(it.data(Qt.UserRole)))
        return out

    def _update_install_btn(self) -> None:
        if self._running_job is not None or self._queue:
            return
        has_files = any(
            (it := self._files_table.item(r, 0)) is not None
            and it.checkState() == Qt.Checked
            for r in range(self._files_table.rowCount())
        )
        self._install_btn.setEnabled(has_files and bool(self._checked_serials()))

    @Slot(object)
    def _on_device_event(self, _ctx: DeviceContext) -> None:
        # Mid-run: don't rebuild list (would lose the active row context).
        if self._running_job is not None or self._queue:
            return
        self._refresh_devices()

    @Slot(str)
    def _on_device_disconnected_signal(self, serial: str) -> None:
        if self._running_job is None and not self._queue:
            self._refresh_devices()
            return
        # Active batch: mark serial as dropped and let the runner skip its
        # remaining queued jobs (§3.3.3 / §7).
        self._dropped_serials.add(serial)
        running = self._running_job
        if running is not None and running.device_entry.serial == serial:
            # Kill the in-flight process; processStopped handler will record
            # a skipped result and advance.
            if self._running_pid is not None:
                self._adb.processes.stop(self._running_pid)

    # ------------------- install state helpers -----------------------
    def _set_install_state(self, state: str, text: Optional[str] = None) -> None:
        if state not in ("idle", "running", "done", "error"):
            state = "idle"
        self._status_frame.setProperty("state", state)
        # Re-polish to apply state-dependent QSS rules.
        st = self._status_frame.style()
        st.unpolish(self._status_frame)
        st.polish(self._status_frame)
        if text is None:
            if state == "idle":
                text = strings.INSTALL_STATUS_IDLE
            elif state == "error":
                text = strings.INSTALL_STATUS_ERROR
        if text is not None:
            self._status_text.setText(text)

    def _update_percent(self, value: int, total: int) -> None:
        self._progress.setRange(0, max(total, 1))
        self._progress.setValue(value)
        pct = int(round(100 * value / max(total, 1))) if total else 0
        self._pct_label.setText(f"{pct}%")

    # -------------------------- Install run ----------------------------
    def _on_install(self) -> None:
        if self._running_job is not None or self._queue:
            return
        files_to_install = [
            self._files[r]
            for r in range(self._files_table.rowCount())
            if (it := self._files_table.item(r, 0)) is not None
            and it.checkState() == Qt.Checked
            and r < len(self._files)
        ]
        if not files_to_install:
            self._set_install_state("error", strings.INSTALLER_MSG_NO_FILES)
            return
        devices = [
            _DeviceEntry(
                serial=str(self._devices_list.item(i).data(Qt.UserRole)),
                model=str(self._devices_list.item(i).data(Qt.UserRole + 1)),
            )
            for i in range(self._devices_list.count())
            if self._devices_list.item(i).checkState() == Qt.Checked
        ]
        if not devices:
            self._set_install_state("error", strings.INSTALLER_MSG_NO_DEVICES)
            return

        # Build the file × device queue (§3.3.3 sequential order).
        self._queue = []
        for f in files_to_install:
            for d in devices:
                self._queue.append(_Job(file_entry=f, device_entry=d))

        # Reset display state.
        self._results_log = []
        self._dropped_serials.clear()
        self._scratch_dirs.clear()
        self._cancel_requested = False
        self._results_table.setRowCount(0)
        self._refresh_empty_states()

        self._install_btn.setEnabled(False)
        self._add_btn.setEnabled(False)
        self._remove_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._batch_total = len(self._queue)
        self._update_percent(0, self._batch_total)
        self._set_install_state("running", strings.INSTALL_STATUS_RUNNING.format(
            n=1, m=self._batch_total,
            file=self._queue[0].file_entry.path.name,
            device=self._queue[0].device_entry.model
            or self._queue[0].device_entry.serial,
        ))
        self._dispatch_next()

    def _on_cancel(self) -> None:
        self._cancel_requested = True
        # In-flight job still completes; remaining queue is dropped after it.
        self._set_install_state("running", strings.INSTALLER_BTN_CANCEL + "…")

    def _dispatch_next(self) -> None:
        if self._cancel_requested or not self._queue:
            self._finalize_batch()
            return
        job = self._queue.pop(0)
        # Skip if device was dropped mid-batch.
        if job.device_entry.serial in self._dropped_serials:
            self._record_result(job, _ResultEntry(
                file_name=job.file_entry.path.name,
                serial=job.device_entry.serial,
                model=job.device_entry.model,
                state=_RES_SKIP,
                human=strings.INSTALLER_RESULT_SKIPPED,
            ))
            self._dispatch_next()
            return

        self._running_job = job
        self._running_stdout = bytearray()
        completed = self._batch_total - len(self._queue)
        self._set_install_state("running", strings.INSTALL_STATUS_RUNNING.format(
            n=completed,
            m=self._batch_total,
            file=job.file_entry.path.name,
            device=job.device_entry.model or job.device_entry.serial,
        ))
        self._append_result_row(_ResultEntry(
            file_name=job.file_entry.path.name,
            serial=job.device_entry.serial,
            model=job.device_entry.model,
            state="",
            human=strings.INSTALLER_RESULT_RUNNING,
        ), final=False)

        ext = job.file_entry.ext
        try:
            if ext == ".apk":
                ok = self._spawn_apk(job)
            elif ext == ".apks":
                ok = self._spawn_apks(job)
            elif ext in (".xapk", ".apkm"):
                ok = self._spawn_split(job)
            else:
                ok = False
                self._fail_job(
                    job,
                    strings.INSTALLER_MSG_UNSUPPORTED_FORMAT.format(ext=ext),
                    "",
                )
                return
        except Exception as exc:  # pragma: no cover — defensive
            _log.error("install spawn crashed: %s", exc)
            ok = False
            self._fail_job(job, str(exc), "")
            return

        if not ok:
            # Spawn helper already recorded the failure.
            return

    # ------------------- per-format spawners ---------------------------
    def _spawn_apk(self, job: _Job) -> bool:
        pid = f"install-{uuid.uuid4()}"
        self._running_pid = pid
        ok = self._adb.spawn_adb(
            pid,
            job.device_entry.serial,
            ["install", "-r", str(job.file_entry.path)],
        )
        if not ok:
            self._fail_job(job, strings.INSTALLER_RESULT_FAIL, "spawn failed")
        return ok

    def _spawn_apks(self, job: _Job) -> bool:
        jar = paths.bundletool_dir() / "bundletool.jar"
        if not jar.exists():
            self._fail_job(job, strings.INSTALLER_MSG_BUNDLETOOL_MISSING, "")
            return False
        java = shutil.which("java")
        if java is None:
            self._fail_job(job, strings.INSTALLER_MSG_JRE_MISSING, "")
            return False
        # Tell bundletool which adb binary to use.
        from ..core.command_runner import resolve_adb_binary
        adb_bin = resolve_adb_binary()
        argv = [
            java, "-jar", str(jar), "install-apks",
            f"--apks={job.file_entry.path}",
            f"--adb={adb_bin}",
            f"--device-id={job.device_entry.serial}",
        ]
        pid = f"install-apks-{uuid.uuid4()}"
        self._running_pid = pid
        ok = self._adb.spawn_process(pid, argv)
        if not ok:
            self._fail_job(job, strings.INSTALLER_RESULT_FAIL, "spawn failed")
        return ok

    def _spawn_split(self, job: _Job) -> bool:
        """Install .xapk / .apkm via ``install-multiple`` after unzipping."""
        try:
            scratch = Path(tempfile.mkdtemp(prefix="adb_helper_install_"))
        except OSError as exc:
            self._fail_job(job, strings.INSTALLER_RESULT_FAIL, str(exc))
            return False
        self._scratch_dirs.append(scratch)
        try:
            with zipfile.ZipFile(job.file_entry.path) as zf:
                # Reject path traversal entries before extracting.
                for n in zf.namelist():
                    norm = n.replace("\\", "/")
                    if norm.startswith("/") or ".." in norm.split("/"):
                        raise zipfile.BadZipFile(f"unsafe path: {n!r}")
                zf.extractall(scratch)
        except (zipfile.BadZipFile, OSError) as exc:
            self._fail_job(job, strings.INSTALLER_RESULT_FAIL, str(exc))
            return False

        apks = sorted(p for p in scratch.rglob("*.apk") if p.is_file())
        if not apks:
            self._fail_job(job, strings.INSTALLER_RESULT_FAIL, "No APKs in archive")
            return False

        pid = f"install-multi-{uuid.uuid4()}"
        self._running_pid = pid
        args = ["install-multiple", "-r"] + [str(p) for p in apks]
        ok = self._adb.spawn_adb(pid, job.device_entry.serial, args)
        if not ok:
            self._fail_job(job, strings.INSTALLER_RESULT_FAIL, "spawn failed")
        return ok

    # ------------------ process output / completion --------------------
    @Slot(str, bytes)
    def _on_proc_output(self, pid: str, data: bytes) -> None:
        if pid != self._running_pid:
            return
        self._running_stdout.extend(data)

    @Slot(str, int)
    def _on_proc_stopped(self, pid: str, rc: int) -> None:
        if pid != self._running_pid:
            return
        job = self._running_job
        raw = bytes(self._running_stdout).decode("utf-8", errors="replace")
        self._running_pid = None
        self._running_job = None
        self._running_stdout = bytearray()

        if job is None:
            self._dispatch_next()
            return

        # Skipped (device dropped mid-flight).
        if job.device_entry.serial in self._dropped_serials:
            self._record_result(job, _ResultEntry(
                file_name=job.file_entry.path.name,
                serial=job.device_entry.serial,
                model=job.device_entry.model,
                state=_RES_SKIP,
                human=strings.INSTALLER_RESULT_SKIPPED,
                raw=raw,
            ))
            self._dispatch_next()
            return

        ok = rc == 0 and ("Success" in raw or job.file_entry.ext == ".apks")
        if ok:
            self._record_result(job, _ResultEntry(
                file_name=job.file_entry.path.name,
                serial=job.device_entry.serial,
                model=job.device_entry.model,
                state=_RES_OK,
                human=strings.INSTALLER_RESULT_OK,
                raw=raw,
            ))
        else:
            human, _ = parse_error(raw)
            self._record_result(job, _ResultEntry(
                file_name=job.file_entry.path.name,
                serial=job.device_entry.serial,
                model=job.device_entry.model,
                state=_RES_FAIL,
                human=human,
                raw=raw,
            ))
        self._dispatch_next()

    def _fail_job(self, job: _Job, human: str, raw: str) -> None:
        self._record_result(job, _ResultEntry(
            file_name=job.file_entry.path.name,
            serial=job.device_entry.serial,
            model=job.device_entry.model,
            state=_RES_FAIL,
            human=human,
            raw=raw,
        ))
        self._running_pid = None
        self._running_job = None
        self._running_stdout = bytearray()
        self._dispatch_next()

    # ----------------------- results table -----------------------------
    def _append_result_row(
        self, r: _ResultEntry, final: bool
    ) -> int:
        row = self._results_table.rowCount()
        self._results_table.insertRow(row)
        self._results_table.setItem(row, 0, QTableWidgetItem(r.file_name))
        self._results_table.setItem(row, 1, QTableWidgetItem(r.serial))
        self._results_table.setItem(row, 2, QTableWidgetItem(r.model or ""))
        self._results_table.setItem(
            row, 3, QTableWidgetItem(r.human if not final else _result_text(r))
        )
        self._refresh_empty_states()
        return row

    def _record_result(self, job: _Job, r: _ResultEntry) -> None:
        self._results_log.append(r)
        # Update the last row (which was appended in dispatch with state="").
        row = self._results_table.rowCount() - 1
        if row < 0:
            self._append_result_row(r, final=True)
            return
        self._results_table.setItem(row, 3, QTableWidgetItem(_result_text(r)))
        completed = sum(
            1 for rr in self._results_log if rr.state in (_RES_OK, _RES_FAIL, _RES_SKIP)
        )
        self._update_percent(completed, max(self._batch_total, 1))
        _log.info(
            "install result file=%s serial=%s state=%s",
            r.file_name, r.serial, r.state,
        )

    # -------------------------- finalize -------------------------------
    def _finalize_batch(self) -> None:
        self._running_job = None
        self._running_pid = None
        self._running_stdout = bytearray()
        self._queue = []
        self._cancel_requested = False
        self._dropped_serials.clear()
        self._update_install_btn()
        self._add_btn.setEnabled(True)
        self._remove_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

        ok = sum(1 for r in self._results_log if r.state == _RES_OK)
        fail = sum(1 for r in self._results_log if r.state != _RES_OK)
        total = max(self._batch_total, 1)
        self._update_percent(ok + fail, total)
        if fail and not ok:
            self._set_install_state("error", strings.INSTALL_STATUS_ERROR)
        else:
            self._set_install_state(
                "done",
                strings.INSTALL_STATUS_DONE.format(
                    ok=ok, total=total, fail=fail
                ),
            )

        # Clean up temp extraction dirs.
        for d in self._scratch_dirs:
            try:
                shutil.rmtree(d, ignore_errors=True)
            except OSError:
                pass
        self._scratch_dirs.clear()

        if self._results_log:
            _SummaryDialog(self._results_log, self).exec()

        # Refresh device list now that the batch is done.
        self._refresh_devices()


# --------------------------- helpers ---------------------------------

def _fmt_size(n: int) -> str:
    if n <= 0:
        return "—"
    units = ("B", "KB", "MB", "GB")
    f = float(n)
    for u in units:
        if f < 1024.0 or u == units[-1]:
            return f"{f:.1f} {u}" if u != "B" else f"{int(f)} {u}"
        f /= 1024.0
    return f"{int(n)} B"


def _mono_font(widget: QWidget):
    font = widget.font()
    font.setFamily("JetBrains Mono")
    font.setStyleHint(font.StyleHint.Monospace)
    return font


__all__ = ["InstallerModule"]
