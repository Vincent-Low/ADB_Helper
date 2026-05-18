"""Module: Installer (Spec §3.3).

Independent of the global active device — maintains its own multi-device
checklist. Installs ``.apk``, ``.apks``, ``.xapk``, and ``.apkm`` sequentially
across N devices. ``.aab`` is unsupported (developer signing key required — §9).

Sequential semantics (§3.3.3):
  - File × device order: file 1 → dev A, file 1 → dev B, …, file 2 → dev A, …
  - Per-file errors don't abort the batch — continue on remaining ops.
  - Mid-run disconnect: mark that device's remaining ops Failed, keep going.

All ADB I/O routes through :class:`AdbService`. ``.apks`` install spawns
``java -jar bundletool.jar install-apks`` via
:meth:`AdbService.spawn_process` (non-ADB child).
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
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
from ..core import platform as _platform

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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

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
    """Installer screen (§3.3)."""

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

        self._build_ui()
        self._wire_signals()
        self._refresh_devices()

    # ----------------------------- UI ----------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Files
        files_box = QGroupBox(strings.INSTALLER_LABEL_FILES, self)
        fb = QVBoxLayout(files_box)
        fb.setContentsMargins(12, 8, 12, 8)
        self._files_table = QTableWidget(0, 3, self)
        self._files_table.setHorizontalHeaderLabels([
            strings.INSTALLER_COL_FILE,
            strings.INSTALLER_COL_TYPE,
            strings.INSTALLER_COL_SIZE,
        ])
        self._files_table.verticalHeader().setVisible(False)
        self._files_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._files_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._files_table.setDragDropMode(QAbstractItemView.InternalMove)
        self._files_table.horizontalHeader().setStretchLastSection(True)
        self._files_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        fb.addWidget(self._files_table, 1)

        file_actions = QHBoxLayout()
        self._add_btn = QPushButton(strings.INSTALLER_BTN_ADD_FILES, self)
        self._add_btn.clicked.connect(self._on_add_files)
        self._remove_btn = QPushButton(strings.INSTALLER_BTN_REMOVE, self)
        self._remove_btn.clicked.connect(self._on_remove_file)
        self._clear_btn = QPushButton(strings.INSTALLER_BTN_CLEAR, self)
        self._clear_btn.clicked.connect(self._on_clear_files)
        for b in (self._add_btn, self._remove_btn, self._clear_btn):
            file_actions.addWidget(b)
        file_actions.addStretch(1)
        fb.addLayout(file_actions)
        root.addWidget(files_box, 2)

        # Devices
        dev_box = QGroupBox(strings.INSTALLER_LABEL_DEVICES, self)
        db = QVBoxLayout(dev_box)
        db.setContentsMargins(12, 8, 12, 8)
        self._devices_list = QListWidget(self)
        self._devices_list.setSelectionMode(QAbstractItemView.NoSelection)
        db.addWidget(self._devices_list, 1)
        root.addWidget(dev_box, 1)

        # Run controls
        run_row = QHBoxLayout()
        self._install_btn = QPushButton(strings.INSTALLER_BTN_INSTALL, self)
        self._install_btn.clicked.connect(self._on_install)
        self._cancel_btn = QPushButton(strings.INSTALLER_BTN_CANCEL, self)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setEnabled(False)
        run_row.addWidget(self._install_btn)
        run_row.addWidget(self._cancel_btn)
        run_row.addStretch(1)
        self._status_lbl = QLabel("", self)
        self._status_lbl.setProperty("secondary", "true")
        run_row.addWidget(self._status_lbl)
        root.addLayout(run_row)

        self._progress = QProgressBar(self)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Live results table.
        res_box = QGroupBox(strings.INSTALLER_LABEL_RESULTS, self)
        rb = QVBoxLayout(res_box)
        rb.setContentsMargins(12, 8, 12, 8)
        self._results_table = QTableWidget(0, 4, self)
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
        rb.addWidget(self._results_table, 1)
        root.addWidget(res_box, 2)

    def _wire_signals(self) -> None:
        self._adb.devices.deviceConnected.connect(self._on_device_event)
        self._adb.devices.deviceDisconnected.connect(self._on_device_disconnected_signal)
        self._adb.devices.deviceStateChanged.connect(self._on_device_event)
        self._adb.processes.processOutput.connect(self._on_proc_output)
        self._adb.processes.processStopped.connect(self._on_proc_stopped)

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

    # -------------------------- Files panel ----------------------------
    def _on_add_files(self) -> None:
        # Adding new files clears the prior results log (§3.3.3).
        if self._results_log:
            self._results_log = []
            self._results_table.setRowCount(0)
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
            self._status_lbl.setText(strings.INSTALLER_MSG_AAB_UNSUPPORTED)
            return
        if ext not in _SUPPORTED_EXTS:
            self._status_lbl.setText(
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
        name_item = QTableWidgetItem(path.name)
        name_item.setData(Qt.UserRole, str(path))
        self._files_table.setItem(row, 0, name_item)
        self._files_table.setItem(row, 1, QTableWidgetItem(ext.lstrip(".")))
        self._files_table.setItem(row, 2, QTableWidgetItem(_fmt_size(size)))

    def _on_remove_file(self) -> None:
        rows = sorted({i.row() for i in self._files_table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self._files_table.removeRow(r)
            if 0 <= r < len(self._files):
                del self._files[r]

    def _on_clear_files(self) -> None:
        self._files_table.setRowCount(0)
        self._files.clear()

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

    def _checked_serials(self) -> set[str]:
        out: set[str] = set()
        for i in range(self._devices_list.count()):
            it = self._devices_list.item(i)
            if it.checkState() == Qt.Checked:
                out.add(str(it.data(Qt.UserRole)))
        return out

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

    # -------------------------- Install run ----------------------------
    def _on_install(self) -> None:
        if self._running_job is not None or self._queue:
            return
        if not self._files:
            self._status_lbl.setText(strings.INSTALLER_MSG_NO_FILES)
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
            self._status_lbl.setText(strings.INSTALLER_MSG_NO_DEVICES)
            return

        # Build the file × device queue (§3.3.3 sequential order).
        self._queue = []
        for f in self._files:
            for d in devices:
                self._queue.append(_Job(file_entry=f, device_entry=d))

        # Reset display state.
        self._results_log = []
        self._dropped_serials.clear()
        self._scratch_dirs.clear()
        self._cancel_requested = False
        self._results_table.setRowCount(0)

        self._install_btn.setEnabled(False)
        self._add_btn.setEnabled(False)
        self._remove_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, len(self._queue))
        self._progress.setValue(0)
        self._dispatch_next()

    def _on_cancel(self) -> None:
        self._cancel_requested = True
        # In-flight job still completes; remaining queue is dropped after it.
        self._status_lbl.setText(strings.INSTALLER_BTN_CANCEL + "…")

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
        self._status_lbl.setText(
            strings.INSTALLER_MSG_RUNNING.format(
                file=job.file_entry.path.name,
                device=f"{job.device_entry.model or '?'} ({job.device_entry.serial})",
            )
        )
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
        self._progress.setValue(completed)
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
        self._install_btn.setEnabled(True)
        self._add_btn.setEnabled(True)
        self._remove_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setVisible(False)

        ok = sum(1 for r in self._results_log if r.state == _RES_OK)
        fail = sum(1 for r in self._results_log if r.state != _RES_OK)
        self._status_lbl.setText(
            strings.INSTALLER_MSG_DONE.format(ok=ok, fail=fail)
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


__all__ = ["InstallerModule"]
