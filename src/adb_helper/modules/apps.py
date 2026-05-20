"""Module: Apps (Spec §3.7; Redesign §5.7).

Lists installed apps via ``pm list packages``. No icon extraction (§9). System
apps can be disabled but not uninstalled. RAM and Storage bars refresh on
demand only — no background polling.

Layout (Redesign §5.7):
    Page header
    QFrame#ResourceStats — RAM | Storage | spacer | Refresh
    QSplitter(Horizontal):
        QFrame#AppsList   (stretchFactor 1.4)
            card-h: PACKAGES + count hint
            QFrame#AppsToolbar (search + 2 checkboxes)
            QTableView (checkbox column + Package + Status)
            card-f: Delete | Disable | Enable | Export CSV | counter
        QFrame#AppDetails (stretchFactor 1)
            card-h: APP DETAILS + ↗
            empty state OR (meta row + QFormLayout 8 rows + footer)
            footer: Open | Force-stop | Clear data | Uninstall
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
from PySide6.QtGui import QBrush, QColor, QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
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
from ..ui.style_utils import page_header
from ..ui.style_utils import set_variant as _set_variant

_log = get_logger(__name__)

_LIST_TIMEOUT_S = 30
_DUMP_TIMEOUT_S = 15
_RESOURCE_TIMEOUT_S = 10
_UNINSTALL_TIMEOUT_S = 60
_PULL_TIMEOUT_S = 120
_TOGGLE_TIMEOUT_S = 20
_SINGLE_OP_TIMEOUT_S = 15

_COL_CHECK = 0
_COL_PACKAGE = 1
_COL_STATUS = 2
_COL_TYPE = 3

_ROLE_PACKAGE = Qt.ItemDataRole.UserRole + 1
_ROLE_APK_PATH = Qt.ItemDataRole.UserRole + 2
_ROLE_TYPE_RAW = Qt.ItemDataRole.UserRole + 3
_ROLE_STATUS_RAW = Qt.ItemDataRole.UserRole + 4

_TYPE_USER = "user"
_TYPE_SYSTEM = "system"
_STATUS_ACTIVE = "active"
_STATUS_DISABLED = "disabled"

_DISABLED_ENABLED_CODES = {"2", "3", "4"}

_DASH = "—"


@dataclass
class AppEntry:
    package: str
    apk_path: str
    app_type: str          # "user" | "system"
    name: str = ""         # display label (defaults to package)
    status: str = _STATUS_ACTIVE
    version_name: str = ""
    version_code: str = ""
    uid: str = ""


@dataclass
class _PendingOp:
    kind: str
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
            pkg = (src.item(row, _COL_PACKAGE).text()
                   if src.item(row, _COL_PACKAGE) else "").lower()
            if self._needle not in pkg:
                return False
        return True


def _mono_font(widget: QWidget) -> QFont:
    f = widget.font()
    f.setFamily("JetBrains Mono")
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


class AppsModule(IModule):
    """Apps screen (§3.7; Redesign §5.7)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        self._serial: Optional[str] = None
        self._model_name: str = "device"
        self._apps: dict[str, AppEntry] = {}
        self._pending: dict[str, _PendingOp] = {}
        # Sequential bulk-op state.
        self._op_kind: Optional[str] = None
        self._op_queue: list[dict] = []
        self._op_total: int = 0
        self._op_ok: int = 0
        self._op_fail: int = 0
        self._backup_dir: Optional[Path] = None
        # Detail-panel currently selected package, if any.
        self._detail_pkg: Optional[str] = None
        # Meta-row labels (field key -> QLabel).
        self._meta_labels: dict[str, QLabel] = {}
        self._build_ui()
        self._wire_signals()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        root.addWidget(
            page_header(
                strings.LABEL_APPS,
                strings.PAGE_SUBTITLE_APPS,
                parent=self,
            )
        )

        root.addWidget(self._build_resource_stats())

        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(8)
        self._splitter.addWidget(self._build_apps_list_card())
        self._splitter.addWidget(self._build_app_details_card())
        # Plan §5.7: list stretchFactor 1.4, details 1 → 14 : 10.
        self._splitter.setStretchFactor(0, 14)
        self._splitter.setStretchFactor(1, 10)
        root.addWidget(self._splitter, 1)

        self._set_controls_enabled(False)
        # TODO (deferred): narrow-screen (<800 width) collapse —
        # `setChildrenCollapsible(False)` keeps both panes visible; respond to
        # resizeEvent by toggling `splitter.widget(1).setVisible(False)` once
        # a back-button is implemented to return from details to list.

    # --- top stats card ----------------------------------------------
    def _build_resource_stats(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("ResourceStats")
        row = QHBoxLayout(frame)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(16)

        # RAM block
        ram_col = QVBoxLayout()
        ram_col.setSpacing(2)
        self._ram_title = QLabel(strings.APPS_LABEL_RAM, frame)
        self._ram_title.setProperty("role", "section-label")
        self._ram_bar = QProgressBar(frame)
        self._ram_bar.setRange(0, 1)
        self._ram_bar.setValue(0)
        self._ram_bar.setTextVisible(False)
        self._ram_bar.setFixedHeight(6)
        self._ram_label = QLabel(_DASH, frame)
        self._ram_label.setProperty("role", "hint")
        ram_col.addWidget(self._ram_title)
        ram_col.addWidget(self._ram_bar)
        ram_col.addWidget(self._ram_label)
        row.addLayout(ram_col, 1)

        # Storage block
        sto_col = QVBoxLayout()
        sto_col.setSpacing(2)
        self._sto_title = QLabel(strings.APPS_LABEL_STORAGE, frame)
        self._sto_title.setProperty("role", "section-label")
        self._sto_bar = QProgressBar(frame)
        self._sto_bar.setRange(0, 1)
        self._sto_bar.setValue(0)
        self._sto_bar.setTextVisible(False)
        self._sto_bar.setFixedHeight(6)
        self._sto_label = QLabel(_DASH, frame)
        self._sto_label.setProperty("role", "hint")
        sto_col.addWidget(self._sto_title)
        sto_col.addWidget(self._sto_bar)
        sto_col.addWidget(self._sto_label)
        row.addLayout(sto_col, 1)

        row.addStretch(1)
        self._refresh_btn = QPushButton(strings.APPS_BTN_REFRESH, frame)
        self._refresh_btn.clicked.connect(self._on_refresh)
        row.addWidget(self._refresh_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        return frame

    # --- left card: apps list ---------------------------------------
    def _build_apps_list_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("AppsList")
        card.setProperty("role", "card")
        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Card header
        hdr = QFrame(card)
        hdr.setProperty("role", "card-h")
        hdr_row = QHBoxLayout(hdr)
        hdr_row.setContentsMargins(14, 10, 14, 10)
        hdr_row.setSpacing(8)
        title = QLabel(strings.APPS_CARD_PACKAGES, hdr)
        title.setProperty("role", "section-label")
        self._count_hint = QLabel(
            strings.APPS_COUNTER_FMT.format(count=0), hdr
        )
        self._count_hint.setProperty("role", "hint")
        hdr_row.addWidget(title)
        hdr_row.addStretch(1)
        hdr_row.addWidget(self._count_hint)
        v.addWidget(hdr)

        # Toolbar — search + 2 checkboxes (separate frame below header)
        toolbar = QFrame(card)
        toolbar.setObjectName("AppsToolbar")
        tb_row = QHBoxLayout(toolbar)
        tb_row.setContentsMargins(14, 10, 14, 10)
        tb_row.setSpacing(10)
        self._search = QLineEdit(toolbar)
        self._search.setPlaceholderText(strings.APPS_SEARCH_HINT)
        self._search.textChanged.connect(self._on_search)
        tb_row.addWidget(self._search, 1)
        self._chk_system = QCheckBox(strings.APPS_CHK_SHOW_SYSTEM, toolbar)
        self._chk_system.setChecked(True)
        self._chk_system.toggled.connect(self._on_show_system)
        tb_row.addWidget(self._chk_system)
        self._chk_disabled = QCheckBox(strings.APPS_CHK_SHOW_DISABLED, toolbar)
        self._chk_disabled.setChecked(True)
        self._chk_disabled.toggled.connect(self._on_show_disabled)
        tb_row.addWidget(self._chk_disabled)
        v.addWidget(toolbar)

        # Table
        self._table_model = QStandardItemModel(0, 4, card)
        self._table_model.setHorizontalHeaderLabels([
            "",
            strings.APPS_COL_PACKAGE,
            strings.APPS_COL_STATUS,
            strings.APPS_COL_TYPE,
        ])
        self._table_model.itemChanged.connect(self._on_item_changed)
        self._proxy = _AppsProxyModel(self)
        self._proxy.setSourceModel(self._table_model)

        self._table = QTableView(card)
        self._table.setModel(self._proxy)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnHidden(_COL_TYPE, True)
        hdr_view = self._table.horizontalHeader()
        hdr_view.setSectionResizeMode(_COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        hdr_view.setSectionResizeMode(_COL_PACKAGE, QHeaderView.ResizeMode.Stretch)
        hdr_view.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        v.addWidget(self._table, 1)

        # Footer: bulk actions + counter (right)
        footer = QFrame(card)
        footer.setProperty("role", "card-f")
        f_row = QHBoxLayout(footer)
        f_row.setContentsMargins(14, 10, 14, 10)
        f_row.setSpacing(8)
        self._delete_btn = QPushButton(strings.APPS_BTN_DELETE, footer)
        _set_variant(self._delete_btn, "destructive")
        self._delete_btn.clicked.connect(self._on_delete)
        self._disable_btn = QPushButton(strings.APPS_BTN_DISABLE, footer)
        self._disable_btn.clicked.connect(self._on_disable)
        self._enable_btn = QPushButton(strings.APPS_BTN_ENABLE, footer)
        self._enable_btn.clicked.connect(self._on_enable)
        self._export_btn = QPushButton(strings.APPS_BTN_EXPORT, footer)
        self._export_btn.clicked.connect(self._on_export)
        for b in (self._delete_btn, self._disable_btn,
                  self._enable_btn, self._export_btn):
            f_row.addWidget(b)
        f_row.addStretch(1)
        self._status_lbl = QLabel("", footer)
        self._status_lbl.setProperty("role", "hint")
        f_row.addWidget(self._status_lbl)
        self._progress = QProgressBar(footer)
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(120)
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        f_row.addWidget(self._progress)
        v.addWidget(footer)

        return card

    # --- right card: app details -------------------------------------
    def _build_app_details_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("AppDetails")
        card.setProperty("role", "card")
        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header: section label + ↗ button
        hdr = QFrame(card)
        hdr.setProperty("role", "card-h")
        hdr_row = QHBoxLayout(hdr)
        hdr_row.setContentsMargins(14, 10, 14, 10)
        title = QLabel(strings.APPS_CARD_DETAILS, hdr)
        title.setProperty("role", "section-label")
        hdr_row.addWidget(title)
        hdr_row.addStretch(1)
        self._detail_expand_btn = QPushButton("↗", hdr)
        _set_variant(self._detail_expand_btn, "ghost")
        self._detail_expand_btn.setFixedWidth(28)
        self._detail_expand_btn.setEnabled(False)
        self._detail_expand_btn.setToolTip(strings.TOOLTIP_NOT_IMPLEMENTED)
        hdr_row.addWidget(self._detail_expand_btn)
        v.addWidget(hdr)

        # Body host (stack-like: empty label OR meta/form/footer)
        self._detail_body = QWidget(card)
        body_lay = QVBoxLayout(self._detail_body)
        body_lay.setContentsMargins(14, 14, 14, 14)
        body_lay.setSpacing(12)

        # Empty state — centred hint label.
        self._detail_empty = QLabel(strings.APPS_DETAIL_EMPTY, self._detail_body)
        self._detail_empty.setProperty("role", "hint")
        self._detail_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_empty.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        body_lay.addWidget(self._detail_empty)

        # Meta row (icon block + pkg name + badges).
        self._detail_meta = QWidget(self._detail_body)
        meta_row = QHBoxLayout(self._detail_meta)
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(10)
        self._detail_icon = QLabel("·", self._detail_meta)
        self._detail_icon.setFixedSize(40, 40)
        self._detail_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_icon.setProperty("role", "section-label")
        meta_row.addWidget(self._detail_icon)
        meta_text_col = QVBoxLayout()
        meta_text_col.setContentsMargins(0, 0, 0, 0)
        meta_text_col.setSpacing(2)
        self._detail_pkg_lbl = QLabel("", self._detail_meta)
        self._detail_pkg_lbl.setFont(_mono_font(self._detail_pkg_lbl))
        self._detail_pkg_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._detail_badges = QLabel("", self._detail_meta)
        self._detail_badges.setProperty("role", "hint")
        meta_text_col.addWidget(self._detail_pkg_lbl)
        meta_text_col.addWidget(self._detail_badges)
        meta_row.addLayout(meta_text_col, 1)
        body_lay.addWidget(self._detail_meta)

        # Form: 8 meta rows.
        self._detail_form_host = QWidget(self._detail_body)
        form = QFormLayout(self._detail_form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        mono_fields = {
            strings.APPS_META_PACKAGE,
            strings.APPS_META_VERSION,
            strings.APPS_META_VERSION_CODE,
            strings.APPS_META_UID,
            strings.APPS_META_APK_PATH,
        }
        for key in (
            strings.APPS_META_PACKAGE,
            strings.APPS_META_LABEL,
            strings.APPS_META_TYPE,
            strings.APPS_META_STATUS,
            strings.APPS_META_VERSION,
            strings.APPS_META_VERSION_CODE,
            strings.APPS_META_UID,
            strings.APPS_META_APK_PATH,
        ):
            row_lbl = QLabel(key + ":", self._detail_form_host)
            row_lbl.setProperty("role", "hint")
            row_lbl.setFixedWidth(140)
            val_lbl = QLabel(_DASH, self._detail_form_host)
            val_lbl.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            val_lbl.setWordWrap(True)
            if key in mono_fields:
                val_lbl.setFont(_mono_font(val_lbl))
            form.addRow(row_lbl, val_lbl)
            self._meta_labels[key] = val_lbl
        body_lay.addWidget(self._detail_form_host)

        body_lay.addStretch(1)
        v.addWidget(self._detail_body, 1)

        # Footer (single-app actions).
        self._detail_footer = QFrame(card)
        self._detail_footer.setProperty("role", "card-f")
        d_row = QHBoxLayout(self._detail_footer)
        d_row.setContentsMargins(14, 10, 14, 10)
        d_row.setSpacing(8)
        self._open_btn = QPushButton(strings.APPS_BTN_OPEN, self._detail_footer)
        self._open_btn.clicked.connect(self._on_detail_open)
        self._force_stop_btn = QPushButton(
            strings.APPS_BTN_FORCE_STOP, self._detail_footer
        )
        self._force_stop_btn.clicked.connect(self._on_detail_force_stop)
        self._clear_data_btn = QPushButton(
            strings.APPS_BTN_CLEAR_DATA, self._detail_footer
        )
        self._clear_data_btn.clicked.connect(self._on_detail_clear_data)
        self._detail_uninstall_btn = QPushButton(
            strings.APPS_BTN_UNINSTALL, self._detail_footer
        )
        _set_variant(self._detail_uninstall_btn, "destructive")
        self._detail_uninstall_btn.clicked.connect(self._on_detail_uninstall)
        for b in (self._open_btn, self._force_stop_btn,
                  self._clear_data_btn, self._detail_uninstall_btn):
            d_row.addWidget(b)
        d_row.addStretch(1)
        v.addWidget(self._detail_footer)

        self._apply_detail_visibility(selected=False)
        return card

    def _apply_detail_visibility(self, selected: bool) -> None:
        self._detail_empty.setVisible(not selected)
        self._detail_meta.setVisible(selected)
        self._detail_form_host.setVisible(selected)
        self._detail_footer.setVisible(selected)
        for b in (self._open_btn, self._force_stop_btn,
                  self._clear_data_btn, self._detail_uninstall_btn,
                  self._detail_expand_btn):
            b.setEnabled(selected and self._serial is not None and self._op_kind is None)
        # Expand button stays disabled (not implemented yet).
        self._detail_expand_btn.setEnabled(False)

    def _wire_signals(self) -> None:
        self._adb.commands.commandFinished.connect(self._on_cmd_finished)
        self._adb.commands.commandFailed.connect(self._on_cmd_failed)
        sel = self._table.selectionModel()
        if sel is not None:
            sel.currentRowChanged.connect(self._on_current_row_changed)

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
        self._update_counter()
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
        self._ram_label.setText(_DASH)
        self._sto_bar.setRange(0, 1)
        self._sto_bar.setValue(0)
        self._sto_label.setText(_DASH)
        self._status_lbl.setText(strings.APPS_MSG_NO_DEVICE)
        self._update_counter()
        self._detail_pkg = None
        self._apply_detail_visibility(selected=False)
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
        elif op.kind == "open_app":
            self._handle_single(op, result, success,
                                strings.APPS_MSG_OPEN_FAILED)
        elif op.kind == "force_stop":
            self._handle_single(op, result, success,
                                strings.APPS_MSG_FORCE_STOP_FAILED)
        elif op.kind == "clear_data":
            self._handle_single(op, result, success,
                                strings.APPS_MSG_CLEAR_DATA_FAILED)

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
        list_pending = any(
            o.kind in ("list_user", "list_system")
            for o in self._pending.values()
        )
        if list_pending:
            return
        self._populate_table()
        self._update_counter()
        # Queue per-package dump for label + status + version + uid.
        for pkg in list(self._apps.keys()):
            cmd = (
                f"pm dump {pkg} 2>/dev/null | "
                f"grep -E 'enabled|nonLocalizedLabel|versionName|versionCode|userId'"
            )
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
        self._table_model.appendRow([chk, pkg_item, status_item, type_item])
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
        info = _parse_pm_dump(result.stdout)
        label = info["label"]
        disabled = info["disabled"]
        if label:
            entry.name = label
        if disabled is not None:
            entry.status = _STATUS_DISABLED if disabled else _STATUS_ACTIVE
        if info["version_name"]:
            entry.version_name = info["version_name"]
        if info["version_code"]:
            entry.version_code = info["version_code"]
        if info["uid"]:
            entry.uid = info["uid"]
        self._refresh_row(op.package)
        if op.package == self._detail_pkg:
            self._update_detail_panel()

    def _refresh_row(self, package: str) -> None:
        entry = self._apps.get(package)
        row = self._find_row(package)
        if entry is None or row < 0:
            return
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
        for col in (_COL_PACKAGE, _COL_STATUS, _COL_TYPE):
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
        self._update_counter()

    def _on_show_system(self, checked: bool) -> None:
        self._proxy.set_show_system(checked)
        self._update_counter()

    def _on_show_disabled(self, checked: bool) -> None:
        self._proxy.set_show_disabled(checked)
        self._update_counter()

    def _update_counter(self) -> None:
        visible = self._proxy.rowCount() if self._proxy is not None else 0
        total = len(self._apps)
        if visible == total:
            self._count_hint.setText(strings.APPS_COUNTER_FMT.format(count=total))
        else:
            self._count_hint.setText(f"{visible} / {total}")

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

    @Slot(QModelIndex, QModelIndex)
    def _on_current_row_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            self._detail_pkg = None
            self._apply_detail_visibility(selected=False)
            return
        src = self._proxy.mapToSource(current)
        row = src.row()
        chk = self._table_model.item(row, _COL_CHECK)
        pkg = chk.data(_ROLE_PACKAGE) if chk is not None else None
        if not pkg:
            self._detail_pkg = None
            self._apply_detail_visibility(selected=False)
            return
        self._detail_pkg = str(pkg)
        self._apply_detail_visibility(selected=True)
        self._update_detail_panel()

    def _update_detail_panel(self) -> None:
        pkg = self._detail_pkg
        if pkg is None:
            return
        entry = self._apps.get(pkg)
        if entry is None:
            return
        # Icon placeholder: first two letters of package (after last '.').
        last = pkg.rsplit(".", 1)[-1] or pkg
        self._detail_icon.setText(last[:2].upper())
        self._detail_pkg_lbl.setText(entry.name or pkg)
        badge_parts: list[str] = []
        badge_parts.append(
            strings.APPS_TYPE_SYSTEM if entry.app_type == _TYPE_SYSTEM
            else strings.APPS_TYPE_USER
        )
        badge_parts.append(
            strings.APPS_STATUS_DISABLED if entry.status == _STATUS_DISABLED
            else strings.APPS_STATUS_ACTIVE
        )
        self._detail_badges.setText(" · ".join(badge_parts))
        S = strings
        self._meta_labels[S.APPS_META_PACKAGE].setText(entry.package or _DASH)
        self._meta_labels[S.APPS_META_LABEL].setText(entry.name or _DASH)
        self._meta_labels[S.APPS_META_TYPE].setText(
            S.APPS_TYPE_SYSTEM if entry.app_type == _TYPE_SYSTEM else S.APPS_TYPE_USER
        )
        self._meta_labels[S.APPS_META_STATUS].setText(
            S.APPS_STATUS_DISABLED if entry.status == _STATUS_DISABLED
            else S.APPS_STATUS_ACTIVE
        )
        self._meta_labels[S.APPS_META_VERSION].setText(entry.version_name or _DASH)
        self._meta_labels[S.APPS_META_VERSION_CODE].setText(entry.version_code or _DASH)
        self._meta_labels[S.APPS_META_UID].setText(entry.uid or _DASH)
        self._meta_labels[S.APPS_META_APK_PATH].setText(entry.apk_path or _DASH)
        # Footer buttons: tune by app_type/status.
        is_user = entry.app_type == _TYPE_USER
        self._detail_uninstall_btn.setEnabled(
            is_user and self._serial is not None and self._op_kind is None
        )
        self._detail_uninstall_btn.setToolTip(
            "" if is_user else strings.APPS_TOOLTIP_SYSTEM_DELETE
        )

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
        if not on:
            self._delete_btn.setEnabled(False)
        else:
            self._on_item_changed(QStandardItem())
        # Detail-panel buttons piggyback on visibility helper.
        self._apply_detail_visibility(self._detail_pkg is not None)

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
        listing = "\n".join(f"• {e.package}" for e in users)
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
            if self._detail_pkg == op.package:
                self._detail_pkg = None
                self._apply_detail_visibility(selected=False)
            self._update_counter()
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
        self._submit(
            "uninstall",
            ["shell", f"pm uninstall --user 0 {op.package}"],
            _UNINSTALL_TIMEOUT_S, Priority.HIGH,
            _PendingOp(kind="uninstall", package=op.package),
        )

    def _handle_toggle(
        self, op: _PendingOp, result: AdbResult, success: bool
    ) -> None:
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
                if op.package == self._detail_pkg:
                    self._update_detail_panel()
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

    def _handle_single(
        self, op: _PendingOp, result: AdbResult, success: bool,
        fail_msg_fmt: str,
    ) -> None:
        if success:
            _log.info("apps single op %s pkg=%s ok", op.kind, op.package)
            return
        err = (result.stderr or result.stdout or "rc!=0").strip()[:200]
        _log.warning("%s failed pkg=%s err=%s", op.kind, op.package, err)
        self._status_lbl.setText(
            fail_msg_fmt.format(pkg=op.package, error=err)
        )

    # ------------------------------------ Detail-panel single actions
    def _on_detail_open(self) -> None:
        pkg = self._detail_pkg
        if not pkg or not self._serial:
            return
        cmd = (
            "monkey -p " + pkg
            + " -c android.intent.category.LAUNCHER 1"
        )
        self._submit(
            "shell", ["shell", cmd], _SINGLE_OP_TIMEOUT_S, Priority.HIGH,
            _PendingOp(kind="open_app", package=pkg),
        )

    def _on_detail_force_stop(self) -> None:
        pkg = self._detail_pkg
        if not pkg or not self._serial:
            return
        ans = QMessageBox.question(
            self, strings.APPS_TITLE_FORCE_STOP,
            strings.APPS_CONFIRM_FORCE_STOP.format(pkg=pkg),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._submit(
            "shell", ["shell", f"am force-stop {pkg}"],
            _SINGLE_OP_TIMEOUT_S, Priority.HIGH,
            _PendingOp(kind="force_stop", package=pkg),
        )

    def _on_detail_clear_data(self) -> None:
        pkg = self._detail_pkg
        if not pkg or not self._serial:
            return
        ans = QMessageBox.question(
            self, strings.APPS_TITLE_CLEAR_DATA,
            strings.APPS_CONFIRM_CLEAR_DATA.format(pkg=pkg),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._submit(
            "shell", ["shell", f"pm clear {pkg}"],
            _SINGLE_OP_TIMEOUT_S, Priority.HIGH,
            _PendingOp(kind="clear_data", package=pkg),
        )

    def _on_detail_uninstall(self) -> None:
        pkg = self._detail_pkg
        if not pkg or not self._serial or self._op_kind is not None:
            return
        entry = self._apps.get(pkg)
        if entry is None or entry.app_type != _TYPE_USER:
            return
        # Reuse bulk uninstall pipeline for single-item.
        box = QMessageBox(self)
        box.setWindowTitle(strings.APPS_TITLE_DELETE)
        box.setText(strings.INSTALL_BACKUP_PROMPT + "\n\n• " + pkg)
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
            [{"package": pkg, "apk_path": entry.apk_path,
              "do_backup": do_backup}],
        )

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
            rows.append((entry.package, status, type_))
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    strings.APPS_COL_PACKAGE,
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
    """Parse ``pm list packages -f`` output → ``[(apk_path, package), ...]``."""
    out: list[tuple[str, str]] = []
    pat = re.compile(r"^package:(.+\.apk)=(.+?)\s*$")
    for line in text.splitlines():
        m = pat.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def _parse_pm_dump(text: str) -> dict:
    """Extract label, enabled, version, uid from grep'd ``pm dump`` output."""
    info = {
        "label": "",
        "disabled": None,  # type: ignore[var-annotated]
        "version_name": "",
        "version_code": "",
        "uid": "",
    }
    label_pat = re.compile(r"nonLocalizedLabel=(.+?)(?:\s|$)")
    enabled_pat = re.compile(r"^\s*enabled=(\d+)\s*$")
    version_name_pat = re.compile(r"versionName=(\S+)")
    version_code_pat = re.compile(r"versionCode=(\d+)")
    user_id_pat = re.compile(r"userId=(\d+)")
    for raw in text.splitlines():
        if not info["label"]:
            m = label_pat.search(raw)
            if m:
                info["label"] = m.group(1).strip()
        if info["disabled"] is None:
            m = enabled_pat.match(raw)
            if m:
                info["disabled"] = m.group(1) in _DISABLED_ENABLED_CODES
        if not info["version_name"]:
            m = version_name_pat.search(raw)
            if m:
                info["version_name"] = m.group(1).strip()
        if not info["version_code"]:
            m = version_code_pat.search(raw)
            if m:
                info["version_code"] = m.group(1).strip()
        if not info["uid"]:
            m = user_id_pat.search(raw)
            if m:
                info["uid"] = m.group(1).strip()
    return info


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
