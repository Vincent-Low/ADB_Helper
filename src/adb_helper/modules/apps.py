"""Module: Apps (Spec §3.7).

Lists installed apps via ``pm list packages``. No icon extraction (§9). System
apps can be disabled but not uninstalled. RAM and Storage bars refresh on
demand only — no background polling.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Slot,
)
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..core import paths, strings
from ..core.adb_service import get_adb_service
from ..core.command_runner import AdbResult, Priority
from ..core.device_context import DeviceContext
from ..core.imodule import IModule
from ..core.logger import get_logger

_log = get_logger(__name__)

_LIST_TIMEOUT_S = 30
_DUMP_TIMEOUT_S = 15
_RESOURCE_TIMEOUT_S = 10
_UNINSTALL_TIMEOUT_S = 60
_PULL_TIMEOUT_S = 120
_TOGGLE_TIMEOUT_S = 20

_COL_CHECK = 0
_COL_NAME = 1
_COL_PACKAGE = 2
_COL_STATUS = 3
_COL_TYPE = 4

_ROLE_PACKAGE = Qt.ItemDataRole.UserRole + 1
_ROLE_APK_PATH = Qt.ItemDataRole.UserRole + 2
_ROLE_TYPE_RAW = Qt.ItemDataRole.UserRole + 3
_ROLE_STATUS_RAW = Qt.ItemDataRole.UserRole + 4

_TYPE_USER = "user"
_TYPE_SYSTEM = "system"
_STATUS_ACTIVE = "active"
_STATUS_DISABLED = "disabled"

_DISABLED_ENABLED_CODES = {"2", "3", "4"}


@dataclass
class AppEntry:
    package: str
    apk_path: str
    app_type: str          # "user" | "system"
    name: str = ""         # display label (defaults to package)
    status: str = _STATUS_ACTIVE


@dataclass
class _PendingOp:
    kind: str              # "list_user"|"list_system"|"dump"|"meminfo"|"df"
                           # |"uninstall"|"backup_pull"|"disable"|"enable"
    package: str = ""
    extra: dict = field(default_factory=dict)


class _AppsProxyModel(QSortFilterProxyModel):
    """Filters by search text, type visibility, and status visibility."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._needle = ""
        self._show_system = True
        self._show_disabled = True

    def set_search(self, text: str) -> None:
        self._needle = text.strip().lower()
        self.invalidateFilter()

    def set_show_system(self, show: bool) -> None:
        self._show_system = show
        self.invalidateFilter()

    def set_show_disabled(self, show: bool) -> None:
        self._show_disabled = show
        self.invalidateFilter()

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        src = self.sourceModel()
        if src is None:
            return True
        check_item = src.item(row, _COL_CHECK)
        if check_item is None:
            return False
        app_type = check_item.data(_ROLE_TYPE_RAW) or _TYPE_USER
        status = check_item.data(_ROLE_STATUS_RAW) or _STATUS_ACTIVE
        if app_type == _TYPE_SYSTEM and not self._show_system:
            return False
        if status == _STATUS_DISABLED and not self._show_disabled:
            return False
        if self._needle:
            name = (src.item(row, _COL_NAME).text() if src.item(row, _COL_NAME) else "").lower()
            pkg = (src.item(row, _COL_PACKAGE).text() if src.item(row, _COL_PACKAGE) else "").lower()
            if self._needle not in name and self._needle not in pkg:
                return False
        return True


class AppsModule(IModule):
    """Apps screen (§3.7)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        self._serial: Optional[str] = None
        self._model_name: str = "device"
        self._apps: dict[str, AppEntry] = {}  # pkg -> entry
        self._pending: dict[str, _PendingOp] = {}  # cmd_id -> op
        # Sequential op queue for delete/disable/enable.
        self._op_kind: Optional[str] = None
        self._op_queue: list[dict] = []  # each: {"package": str, "apk_path": str, ...}
        self._op_total: int = 0
        self._op_ok: int = 0
        self._op_fail: int = 0
        self._backup_dir: Optional[Path] = None
        self._build_ui()
        self._wire_signals()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # --- Storage / RAM bars (§3.7.3) -----------------------------------
        bars = QGroupBox(self)
        bars_l = QHBoxLayout(bars)
        bars_l.setContentsMargins(12, 8, 12, 8)
        bars_l.setSpacing(16)

        ram_col = QVBoxLayout()
        ram_col.setSpacing(2)
        self._ram_title = QLabel(strings.APPS_LABEL_RAM, self)
        self._ram_bar = QProgressBar(self)
        self._ram_bar.setRange(0, 1)
        self._ram_bar.setValue(0)
        self._ram_label = QLabel("—", self)
        self._ram_label.setProperty("secondary", "true")
        ram_col.addWidget(self._ram_title)
        ram_col.addWidget(self._ram_bar)
        ram_col.addWidget(self._ram_label)
        bars_l.addLayout(ram_col, 1)

        sto_col = QVBoxLayout()
        sto_col.setSpacing(2)
        self._sto_title = QLabel(strings.APPS_LABEL_STORAGE, self)
        self._sto_bar = QProgressBar(self)
        self._sto_bar.setRange(0, 1)
        self._sto_bar.setValue(0)
        self._sto_label = QLabel("—", self)
        self._sto_label.setProperty("secondary", "true")
        sto_col.addWidget(self._sto_title)
        sto_col.addWidget(self._sto_bar)
        sto_col.addWidget(self._sto_label)
        bars_l.addLayout(sto_col, 1)

        self._refresh_btn = QPushButton(strings.APPS_BTN_REFRESH, self)
        self._refresh_btn.clicked.connect(self._on_refresh)
        bars_l.addWidget(self._refresh_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(bars)

        # --- Filter row (§3.7.2) -------------------------------------------
        filt = QHBoxLayout()
        filt.setSpacing(8)
        self._search = QLineEdit(self)
        self._search.setPlaceholderText(strings.APPS_SEARCH_HINT)
        self._search.textChanged.connect(self._on_search)
        filt.addWidget(self._search, 1)

        self._chk_system = QCheckBox(strings.APPS_CHK_SHOW_SYSTEM, self)
        self._chk_system.setChecked(True)
        self._chk_system.toggled.connect(self._on_show_system)
        filt.addWidget(self._chk_system)

        self._chk_disabled = QCheckBox(strings.APPS_CHK_SHOW_DISABLED, self)
        self._chk_disabled.setChecked(True)
        self._chk_disabled.toggled.connect(self._on_show_disabled)
        filt.addWidget(self._chk_disabled)
        root.addLayout(filt)

        # --- Table ---------------------------------------------------------
        self._table_model = QStandardItemModel(0, 5, self)
        self._table_model.setHorizontalHeaderLabels([
            "",
            strings.APPS_COL_NAME,
            strings.APPS_COL_PACKAGE,
            strings.APPS_COL_STATUS,
            strings.APPS_COL_TYPE,
        ])
        self._table_model.itemChanged.connect(self._on_item_changed)

        self._proxy = _AppsProxyModel(self)
        self._proxy.setSourceModel(self._table_model)

        self._table = QTableView(self)
        self._table.setModel(self._proxy)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnHidden(_COL_TYPE, True)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(_COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_PACKAGE, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self._table, 1)

        # --- Action bar ----------------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._delete_btn = QPushButton(strings.APPS_BTN_DELETE, self)
        self._delete_btn.clicked.connect(self._on_delete)
        self._disable_btn = QPushButton(strings.APPS_BTN_DISABLE, self)
        self._disable_btn.clicked.connect(self._on_disable)
        self._enable_btn = QPushButton(strings.APPS_BTN_ENABLE, self)
        self._enable_btn.clicked.connect(self._on_enable)
        self._export_btn = QPushButton(strings.APPS_BTN_EXPORT, self)
        self._export_btn.clicked.connect(self._on_export)
        for b in (self._delete_btn, self._disable_btn,
                  self._enable_btn, self._export_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        self._status_lbl = QLabel("", self)
        self._status_lbl.setProperty("secondary", "true")
        actions.addWidget(self._status_lbl)
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(160)
        self._progress.setVisible(False)
        actions.addWidget(self._progress)
        root.addLayout(actions)

        self._set_controls_enabled(False)

    def _wire_signals(self) -> None:
        self._adb.commands.commandFinished.connect(self._on_cmd_finished)
        self._adb.commands.commandFailed.connect(self._on_cmd_failed)

    # ----------------------------------------------------- IModule lifecycle
    def on_activate(self) -> None:
        ctx = self._adb.active_device
        if ctx is not None and ctx.status == "online":
            self._serial = ctx.serial
            self._model_name = ctx.model or "device"
            self._load_all()
        else:
            self._serial = None
            self._clear_all()

    def on_deactivate(self) -> None:
        self._cancel_pending()

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        if ctx is not None and ctx.status == "online":
            self._serial = ctx.serial
            self._model_name = ctx.model or "device"
            self._load_all()
        else:
            self._serial = None
            self._cancel_pending()
            self._clear_all()

    def on_device_disconnected(self) -> None:
        self._serial = None
        self._cancel_pending()
        self._clear_all()

    # ------------------------------------------------------------- Loading
    def _load_all(self) -> None:
        self._cancel_pending()
        self._apps.clear()
        self._table_model.removeRows(0, self._table_model.rowCount())
        self._status_lbl.setText(strings.APPS_MSG_LOADING)
        self._set_controls_enabled(False)
        self._refresh_meters()
        self._submit("shell", ["shell", "pm list packages -f -3"],
                     _LIST_TIMEOUT_S, Priority.HIGH,
                     _PendingOp(kind="list_user"))
        self._submit("shell", ["shell", "pm list packages -f -s"],
                     _LIST_TIMEOUT_S, Priority.HIGH,
                     _PendingOp(kind="list_system"))

    def _refresh_meters(self) -> None:
        if not self._serial:
            return
        self._submit("shell", ["shell", "cat /proc/meminfo"],
                     _RESOURCE_TIMEOUT_S, Priority.NORMAL,
                     _PendingOp(kind="meminfo"))
        self._submit("shell", ["shell", "df /data"],
                     _RESOURCE_TIMEOUT_S, Priority.NORMAL,
                     _PendingOp(kind="df"))

    def _submit(
        self,
        _tag: str,
        args: list,
        timeout: int,
        priority: Priority,
        op: _PendingOp,
    ) -> str:
        cid = self._adb.commands.submit(self._serial, args, timeout, priority)
        self._pending[cid] = op
        return cid

    def _cancel_pending(self) -> None:
        for cid in list(self._pending):
            self._adb.commands.cancel(cid)
        self._pending.clear()
        self._op_kind = None
        self._op_queue.clear()
        self._op_total = 0
        self._op_ok = 0
        self._op_fail = 0
        self._progress.setVisible(False)

    def _clear_all(self) -> None:
        self._apps.clear()
        self._table_model.removeRows(0, self._table_model.rowCount())
        self._ram_bar.setRange(0, 1)
        self._ram_bar.setValue(0)
        self._ram_label.setText("—")
        self._sto_bar.setRange(0, 1)
        self._sto_bar.setValue(0)
        self._sto_label.setText("—")
        self._status_lbl.setText(strings.APPS_MSG_NO_DEVICE)
        self._set_controls_enabled(False)

    # -------------------------------------------------------- Cmd callbacks
    @Slot(str, object)
    def _on_cmd_finished(self, cid: str, result: AdbResult) -> None:
        op = self._pending.pop(cid, None)
        if op is None:
            return
        self._dispatch_result(op, result, success=True)

    @Slot(str, object)
    def _on_cmd_failed(self, cid: str, result: AdbResult) -> None:
        op = self._pending.pop(cid, None)
        if op is None:
            return
        self._dispatch_result(op, result, success=False)

    def _dispatch_result(
        self, op: _PendingOp, result: AdbResult, success: bool
    ) -> None:
        if op.kind in ("list_user", "list_system"):
            self._handle_list(op, result, success)
        elif op.kind == "dump":
            self._handle_dump(op, result, success)
        elif op.kind == "meminfo":
            if success:
                self._apply_meminfo(result.stdout)
        elif op.kind == "df":
            if success:
                self._apply_df(result.stdout)
        elif op.kind == "uninstall":
            self._handle_uninstall(op, result, success)
        elif op.kind == "backup_pull":
            self._handle_backup_pull(op, result, success)
        elif op.kind in ("disable", "enable"):
            self._handle_toggle(op, result, success)

    # --------------------------------------------------------- List parsing
    def _handle_list(
        self, op: _PendingOp, result: AdbResult, success: bool
    ) -> None:
        if success:
            kind_str = _TYPE_USER if op.kind == "list_user" else _TYPE_SYSTEM
            for apk_path, pkg in _parse_pm_list(result.stdout):
                if pkg in self._apps:
                    continue
                self._apps[pkg] = AppEntry(
                    package=pkg, apk_path=apk_path,
                    app_type=kind_str, name=pkg,
                )
        # Only finalise once both list ops have returned.
        list_pending = any(
            o.kind in ("list_user", "list_system")
            for o in self._pending.values()
        )
        if list_pending:
            return
        self._populate_table()
        # Queue per-package dump for label + status.
        for pkg in list(self._apps.keys()):
            cmd = f"pm dump {pkg} 2>/dev/null | grep -E 'enabled|label'"
            self._submit(
                "shell", ["shell", cmd], _DUMP_TIMEOUT_S, Priority.NORMAL,
                _PendingOp(kind="dump", package=pkg),
            )
        if not self._apps:
            self._status_lbl.setText(strings.APPS_MSG_LOADED.format(count=0))
            self._set_controls_enabled(True)
        else:
            self._status_lbl.setText(
                strings.APPS_MSG_LOADED.format(count=len(self._apps))
            )
            self._set_controls_enabled(True)

    def _populate_table(self) -> None:
        self._table_model.blockSignals(True)
        try:
            self._table_model.removeRows(0, self._table_model.rowCount())
            for entry in sorted(self._apps.values(), key=lambda e: e.package.lower()):
                self._append_row(entry)
        finally:
            self._table_model.blockSignals(False)
        self._table_model.layoutChanged.emit()

    def _append_row(self, entry: AppEntry) -> None:
        chk = QStandardItem()
        chk.setCheckable(True)
        chk.setCheckState(Qt.CheckState.Unchecked)
        chk.setEditable(False)
        chk.setData(entry.package, _ROLE_PACKAGE)
        chk.setData(entry.apk_path, _ROLE_APK_PATH)
        chk.setData(entry.app_type, _ROLE_TYPE_RAW)
        chk.setData(entry.status, _ROLE_STATUS_RAW)
        name_item = QStandardItem(entry.name or entry.package)
        name_item.setEditable(False)
        pkg_item = QStandardItem(entry.package)
        pkg_item.setEditable(False)
        status_text = (
            strings.APPS_STATUS_DISABLED
            if entry.status == _STATUS_DISABLED
            else strings.APPS_STATUS_ACTIVE
        )
        status_item = QStandardItem(status_text)
        status_item.setEditable(False)
        type_text = (
            strings.APPS_TYPE_SYSTEM
            if entry.app_type == _TYPE_SYSTEM
            else strings.APPS_TYPE_USER
        )
        type_item = QStandardItem(type_text)
        type_item.setEditable(False)
        self._table_model.appendRow([chk, name_item, pkg_item, status_item, type_item])
        if entry.status == _STATUS_DISABLED:
            self._apply_row_disabled_style(self._table_model.rowCount() - 1, True)

    # --------------------------------------------------------- Dump parsing
    def _handle_dump(
        self, op: _PendingOp, result: AdbResult, success: bool
    ) -> None:
        if not success:
            return
        entry = self._apps.get(op.package)
        if entry is None:
            return
        label, disabled = _parse_pm_dump(result.stdout)
        if label:
            entry.name = label
        if disabled is not None:
            entry.status = _STATUS_DISABLED if disabled else _STATUS_ACTIVE
        self._refresh_row(op.package)

    def _refresh_row(self, package: str) -> None:
        entry = self._apps.get(package)
        row = self._find_row(package)
        if entry is None or row < 0:
            return
        name_item = self._table_model.item(row, _COL_NAME)
        if name_item is not None:
            name_item.setText(entry.name or entry.package)
        status_item = self._table_model.item(row, _COL_STATUS)
        if status_item is not None:
            status_item.setText(
                strings.APPS_STATUS_DISABLED
                if entry.status == _STATUS_DISABLED
                else strings.APPS_STATUS_ACTIVE
            )
        chk = self._table_model.item(row, _COL_CHECK)
        if chk is not None:
            chk.setData(entry.status, _ROLE_STATUS_RAW)
        self._apply_row_disabled_style(row, entry.status == _STATUS_DISABLED)

    def _apply_row_disabled_style(self, row: int, disabled: bool) -> None:
        brush = QBrush(QColor(128, 128, 128)) if disabled else QBrush()
        for col in (_COL_NAME, _COL_PACKAGE, _COL_STATUS, _COL_TYPE):
            it = self._table_model.item(row, col)
            if it is not None:
                it.setForeground(brush)

    def _find_row(self, package: str) -> int:
        for r in range(self._table_model.rowCount()):
            chk = self._table_model.item(r, _COL_CHECK)
            if chk is not None and chk.data(_ROLE_PACKAGE) == package:
                return r
        return -1

    # --------------------------------------------------------- Meters apply
    def _apply_meminfo(self, text: str) -> None:
        kib = _parse_meminfo(text)
        total = kib.get("MemTotal", 0)
        avail = kib.get("MemAvailable", 0)
        if total <= 0:
            return
        used = max(total - avail, 0)
        total_mb = total // 1024
        used_mb = used // 1024
        self._ram_bar.setRange(0, total_mb)
        self._ram_bar.setValue(used_mb)
        self._ram_label.setText(
            strings.APPS_LABEL_USED_TOTAL.format(used=used_mb, total=total_mb)
        )

    def _apply_df(self, text: str) -> None:
        total_kib, used_kib = _parse_df(text)
        if total_kib <= 0:
            return
        total_mb = total_kib // 1024
        used_mb = used_kib // 1024
        self._sto_bar.setRange(0, total_mb)
        self._sto_bar.setValue(used_mb)
        self._sto_label.setText(
            strings.APPS_LABEL_USED_TOTAL.format(used=used_mb, total=total_mb)
        )

    # ------------------------------------------------------------- Filters
    def _on_search(self, text: str) -> None:
        self._proxy.set_search(text)

    def _on_show_system(self, checked: bool) -> None:
        self._proxy.set_show_system(checked)

    def _on_show_disabled(self, checked: bool) -> None:
        self._proxy.set_show_disabled(checked)

    # ---------------------------------------------------------- Selection
    def _selected_entries(self) -> list[AppEntry]:
        out: list[AppEntry] = []
        for r in range(self._table_model.rowCount()):
            chk = self._table_model.item(r, _COL_CHECK)
            if chk is None or chk.checkState() != Qt.CheckState.Checked:
                continue
            pkg = chk.data(_ROLE_PACKAGE)
            entry = self._apps.get(pkg)
            if entry is not None:
                out.append(entry)
        return out

    def _on_item_changed(self, _item: QStandardItem) -> None:
        sel = self._selected_entries()
        has_system = any(e.app_type == _TYPE_SYSTEM for e in sel)
        self._delete_btn.setEnabled(bool(sel) and not has_system and self._serial is not None)
        if has_system:
            self._delete_btn.setToolTip(strings.APPS_TOOLTIP_SYSTEM_DELETE)
        else:
            self._delete_btn.setToolTip("")

    # ----------------------------------------------------------- Refresh
    def _on_refresh(self) -> None:
        if not self._serial:
            return
        self._load_all()

    def _set_controls_enabled(self, enabled: bool) -> None:
        on = enabled and self._serial is not None
        self._refresh_btn.setEnabled(on)
        self._search.setEnabled(on)
        self._chk_system.setEnabled(on)
        self._chk_disabled.setEnabled(on)
        self._disable_btn.setEnabled(on)
        self._enable_btn.setEnabled(on)
        self._export_btn.setEnabled(on)
        # Delete enable depends on selection.
        if not on:
            self._delete_btn.setEnabled(False)
        else:
            self._on_item_changed(QStandardItem())

    # ------------------------------------------------------------- Delete
    def _on_delete(self) -> None:
        if not self._serial or self._op_kind is not None:
            return
        sel = self._selected_entries()
        users = [e for e in sel if e.app_type == _TYPE_USER]
        if not users:
            QMessageBox.information(
                self, strings.APPS_TITLE_DELETE,
                strings.APPS_MSG_NO_USER_APPS_SELECTED,
            )
            return
        box = QMessageBox(self)
        box.setWindowTitle(strings.APPS_TITLE_DELETE)
        listing = "\n".join(f"• {e.name} ({e.package})" for e in users)
        box.setText(strings.INSTALL_BACKUP_PROMPT + "\n\n" + listing)
        backup_btn = box.addButton(
            strings.APPS_BTN_BACKUP_DELETE, QMessageBox.ButtonRole.AcceptRole
        )
        no_backup_btn = box.addButton(
            strings.APPS_BTN_DELETE_NO_BACKUP, QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_btn = box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is cancel_btn or clicked is None:
            return
        do_backup = clicked is backup_btn
        if do_backup:
            self._backup_dir = (
                paths.app_data_root() / "apk_backup"
                / f"{self._model_name}_{date.today().isoformat()}"
            )
            try:
                self._backup_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                _log.error("backup dir create failed: %s", exc)
                self._backup_dir = None
                do_backup = False
        else:
            self._backup_dir = None
        self._begin_op(
            "uninstall",
            [
                {"package": e.package, "apk_path": e.apk_path,
                 "do_backup": do_backup}
                for e in users
            ],
        )

    # ------------------------------------------------------------ Disable
    def _on_disable(self) -> None:
        if not self._serial or self._op_kind is not None:
            return
        sel = [
            e for e in self._selected_entries()
            if e.status == _STATUS_ACTIVE
        ]
        if not sel:
            QMessageBox.information(
                self, strings.APPS_TITLE_DISABLE,
                strings.APPS_MSG_NO_ACTIVE_SELECTED,
            )
            return
        listing = "\n".join(f"• {e.name} ({e.package})" for e in sel)
        ans = QMessageBox.question(
            self, strings.APPS_TITLE_DISABLE,
            strings.CONFIRM_DISABLE + "\n\n" + listing,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._begin_op(
            "disable",
            [{"package": e.package} for e in sel],
        )

    # ------------------------------------------------------------- Enable
    def _on_enable(self) -> None:
        if not self._serial or self._op_kind is not None:
            return
        sel = [
            e for e in self._selected_entries()
            if e.status == _STATUS_DISABLED
        ]
        if not sel:
            QMessageBox.information(
                self, strings.APPS_TITLE_ENABLE,
                strings.APPS_MSG_NO_DISABLED_SELECTED,
            )
            return
        listing = "\n".join(f"• {e.name} ({e.package})" for e in sel)
        ans = QMessageBox.question(
            self, strings.APPS_TITLE_ENABLE,
            strings.CONFIRM_ENABLE + "\n\n" + listing,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._begin_op(
            "enable",
            [{"package": e.package} for e in sel],
        )

    # ------------------------------------------------------- Sequential ops
    def _begin_op(self, kind: str, items: list[dict]) -> None:
        self._op_kind = kind
        self._op_queue = list(items)
        self._op_total = len(items)
        self._op_ok = 0
        self._op_fail = 0
        self._progress.setRange(0, max(self._op_total, 1))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._set_controls_enabled(False)
        self._dispatch_next_op()

    def _dispatch_next_op(self) -> None:
        if not self._op_queue:
            self._finish_op()
            return
        item = self._op_queue[0]
        pkg = item["package"]
        if self._op_kind == "uninstall":
            if item.get("do_backup") and self._backup_dir is not None:
                dest = self._backup_dir / f"{pkg}.apk"
                self._submit(
                    "pull", ["pull", item["apk_path"], str(dest)],
                    _PULL_TIMEOUT_S, Priority.HIGH,
                    _PendingOp(kind="backup_pull", package=pkg,
                               extra={"dest": dest}),
                )
            else:
                self._submit(
                    "uninstall",
                    ["shell", f"pm uninstall --user 0 {pkg}"],
                    _UNINSTALL_TIMEOUT_S, Priority.HIGH,
                    _PendingOp(kind="uninstall", package=pkg),
                )
        elif self._op_kind == "disable":
            self._submit(
                "disable",
                ["shell", f"pm disable-user --user 0 {pkg}"],
                _TOGGLE_TIMEOUT_S, Priority.HIGH,
                _PendingOp(kind="disable", package=pkg),
            )
        elif self._op_kind == "enable":
            self._submit(
                "enable",
                ["shell", f"pm enable {pkg}"],
                _TOGGLE_TIMEOUT_S, Priority.HIGH,
                _PendingOp(kind="enable", package=pkg),
            )

    def _advance_op(self, ok: bool) -> None:
        if self._op_queue:
            self._op_queue.pop(0)
        if ok:
            self._op_ok += 1
        else:
            self._op_fail += 1
        self._progress.setValue(self._op_ok + self._op_fail)
        self._dispatch_next_op()

    def _finish_op(self) -> None:
        self._status_lbl.setText(
            strings.APPS_MSG_OP_DONE.format(ok=self._op_ok, fail=self._op_fail)
        )
        self._op_kind = None
        self._op_queue.clear()
        self._op_total = 0
        self._op_ok = 0
        self._op_fail = 0
        self._progress.setVisible(False)
        self._set_controls_enabled(True)

    def _handle_uninstall(
        self, op: _PendingOp, result: AdbResult, success: bool
    ) -> None:
        ok = success and "Success" in (result.stdout or "")
        if ok:
            self._apps.pop(op.package, None)
            row = self._find_row(op.package)
            if row >= 0:
                self._table_model.removeRow(row)
        else:
            err = (result.stderr or result.stdout or "rc!=0").strip()[:200]
            _log.warning("uninstall failed pkg=%s err=%s", op.package, err)
            self._status_lbl.setText(
                strings.APPS_MSG_UNINSTALL_FAILED.format(pkg=op.package, error=err)
            )
        self._advance_op(ok)

    def _handle_backup_pull(
        self, op: _PendingOp, result: AdbResult, success: bool
    ) -> None:
        dest = op.extra.get("dest")
        if not success or not (dest and Path(dest).exists()):
            err = (result.stderr or result.stdout or "pull failed").strip()[:200]
            _log.warning("backup pull failed pkg=%s err=%s", op.package, err)
            self._status_lbl.setText(
                strings.APPS_MSG_BACKUP_FAILED.format(pkg=op.package, error=err)
            )
            self._advance_op(False)
            return
        _log.info("apk backed up pkg=%s dest=%s", op.package, dest)
        # Proceed to uninstall now that backup succeeded.
        self._submit(
            "uninstall",
            ["shell", f"pm uninstall --user 0 {op.package}"],
            _UNINSTALL_TIMEOUT_S, Priority.HIGH,
            _PendingOp(kind="uninstall", package=op.package),
        )

    def _handle_toggle(
        self, op: _PendingOp, result: AdbResult, success: bool
    ) -> None:
        # `pm disable-user` / `pm enable` print "Package X new state: ..." on success.
        ok = success and (
            "new state" in (result.stdout or "")
            or "new state" in (result.stderr or "")
            or result.returncode == 0
        )
        if ok:
            entry = self._apps.get(op.package)
            if entry is not None:
                entry.status = (
                    _STATUS_DISABLED if op.kind == "disable" else _STATUS_ACTIVE
                )
                self._refresh_row(op.package)
        else:
            err = (result.stderr or result.stdout or "rc!=0").strip()[:200]
            msg = (
                strings.APPS_MSG_DISABLE_FAILED
                if op.kind == "disable"
                else strings.APPS_MSG_ENABLE_FAILED
            )
            _log.warning("%s failed pkg=%s err=%s", op.kind, op.package, err)
            self._status_lbl.setText(msg.format(pkg=op.package, error=err))
        self._advance_op(ok)

    # ----------------------------------------------------------- Export CSV
    def _on_export(self) -> None:
        safe_model = re.sub(r"[^\w\-]", "_", self._model_name)
        today = date.today().strftime("%Y-%m-%d")
        default_name = f"apps_{safe_model}_{today}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, strings.APPS_TITLE_EXPORT, default_name,
            strings.APPS_FILTER_CSV,
        )
        if not path:
            return
        rows: list[tuple[str, str, str, str]] = []
        for r in range(self._proxy.rowCount()):
            src_index = self._proxy.mapToSource(self._proxy.index(r, _COL_CHECK))
            row = src_index.row()
            chk = self._table_model.item(row, _COL_CHECK)
            if chk is None:
                continue
            pkg = chk.data(_ROLE_PACKAGE) or ""
            entry = self._apps.get(pkg)
            if entry is None:
                continue
            status = (
                strings.APPS_STATUS_DISABLED
                if entry.status == _STATUS_DISABLED
                else strings.APPS_STATUS_ACTIVE
            )
            type_ = (
                strings.APPS_TYPE_SYSTEM
                if entry.app_type == _TYPE_SYSTEM
                else strings.APPS_TYPE_USER
            )
            rows.append((entry.name or entry.package, entry.package, status, type_))
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    strings.APPS_COL_NAME, strings.APPS_COL_PACKAGE,
                    strings.APPS_COL_STATUS, strings.APPS_COL_TYPE,
                ])
                writer.writerows(rows)
        except OSError as exc:
            _log.error("csv export failed: %s", exc)
            self._status_lbl.setText(str(exc))
            return
        _log.info("apps csv exported to %s", path)
        self._status_lbl.setText(
            strings.APPS_MSG_CSV_EXPORTED.format(path=path)
        )


# ============================================================ Pure parsers

def _parse_pm_list(text: str) -> list[tuple[str, str]]:
    """Parse ``pm list packages -f`` output into ``[(apk_path, package), ...]``.

    Output lines look like::
        package:/data/app/.../base.apk=com.example.app
    """
    out: list[tuple[str, str]] = []
    pat = re.compile(r"^package:(.+\.apk)=(.+?)\s*$")
    for line in text.splitlines():
        m = pat.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def _parse_pm_dump(text: str) -> tuple[str, Optional[bool]]:
    """Extract ``(label, disabled)`` from ``pm dump <pkg>`` (grep'd) output.

    ``disabled`` is ``None`` if the package-level ``enabled=`` line was
    not found (meaning treat as Active per spec default).
    """
    label = ""
    disabled: Optional[bool] = None
    label_pat = re.compile(r"nonLocalizedLabel=(.+?)(?:\s|$)")
    enabled_pat = re.compile(r"^\s*enabled=(\d+)\s*$")
    for raw in text.splitlines():
        if not label:
            m = label_pat.search(raw)
            if m:
                label = m.group(1).strip()
        if disabled is None:
            m = enabled_pat.match(raw)
            if m:
                disabled = m.group(1) in _DISABLED_ENABLED_CODES
    return label, disabled


def _parse_meminfo(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s+(\d+)\s+kB", line)
        if m:
            result[m.group(1)] = int(m.group(2))
    return result


def _parse_df(text: str) -> tuple[int, int]:
    """Return ``(total_kib, used_kib)`` from ``df /data`` output."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0, 0

    # Old Android single-line: "/data: 52.0G total, 46.5G used, 5.5G available"
    if "," in lines[0] and "total" in lines[0]:
        tm = re.search(r"([\d.]+)\s*([KMGT]?)B?\s+total", lines[0], re.IGNORECASE)
        um = re.search(r"([\d.]+)\s*([KMGT]?)B?\s+used", lines[0], re.IGNORECASE)
        total_kib = _to_kib(tm.group(1), tm.group(2)) if tm else 0
        used_kib = _to_kib(um.group(1), um.group(2)) if um else 0
        return total_kib, used_kib

    header = lines[0]
    data_line = next((ln for ln in lines[1:] if "/data" in ln), None)
    if data_line is None and len(lines) > 1:
        data_line = lines[1]
    if not data_line:
        return 0, 0
    parts = data_line.split()
    if len(parts) < 4:
        return 0, 0
    # Human-readable columns: total=parts[1], used=parts[2]
    if re.match(r"^[\d.]+[KMGTkmgt]", parts[1]):
        total_kib = _human_to_kib(parts[1])
        used_kib = _human_to_kib(parts[2]) if len(parts) > 2 else 0
        return total_kib, used_kib
    try:
        is_512 = "512" in header
        total = int(parts[1])
        used = int(parts[2])
        total_kib = total // 2 if is_512 else total
        used_kib = used // 2 if is_512 else used
        return total_kib, used_kib
    except (ValueError, IndexError):
        return 0, 0


_UNIT_MUL = {"K": 1, "M": 1024, "G": 1024 * 1024, "T": 1024 * 1024 * 1024}


def _to_kib(num_str: str, unit: str) -> int:
    try:
        val = float(num_str)
    except ValueError:
        return 0
    return int(val * _UNIT_MUL.get(unit.upper(), 1))


def _human_to_kib(token: str) -> int:
    m = re.match(r"^([\d.]+)([KMGTkmgt])", token)
    if not m:
        return 0
    return _to_kib(m.group(1), m.group(2))


__all__ = ["AppsModule"]
