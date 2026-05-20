"""Module: Connections (Spec §3.1; Redesign §5.1).

Default module shown on launch. Manages USB and Wi-Fi (classic + Android 11+
pairing) ADB connections, lists live devices via ``adb track-devices`` (driven
by :class:`DeviceMonitor` signals), and persists paired Wi-Fi devices for
manual reconnection. No auto-reconnect on startup (§9).

Layout (Redesign §5.1): 2×2 ``QGridLayout`` of role="card" cards —
    (0,0) Wi-Fi Pairing    | (0,1) Wi-Fi Connection (Legacy)
    (1,0) Connected Devices| (1,1) Paired Devices

All ADB traffic flows through :class:`AdbService`; no direct ``subprocess`` or
``QProcess`` use here (CLAUDE.md invariant 1). All user-facing strings come
from :mod:`adb_helper.core.strings` (invariant 3).
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRegularExpression, Qt, Slot
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import strings
from ..core.adb_service import get_adb_service
from ..core.command_runner import Priority
from ..core.db_manager import DatabaseManager
from ..core.device_context import DeviceContext
from ..core.error_parser import parse as parse_error
from ..core.imodule import IModule
from ..core.logger import get_logger
from ..ui.style_utils import card, card_with_header_actions, page_header
from ..ui.style_utils import set_variant as _set_variant

_log = get_logger(__name__)

# Live device table columns.
_COL_SERIAL = 0
_COL_IP = 1
_COL_MODEL = 2
_COL_STATUS = 3

# Paired device table columns.
_PCOL_ALIAS = 0
_PCOL_IP = 1
_PCOL_PORT = 2
_PCOL_LAST = 3

_CONNECT_TIMEOUT_S = 15
_PAIR_TIMEOUT_S = 20
_DISCONNECT_TIMEOUT_S = 10

_IP_RE = r"^(25[0-5]|2[0-4]\d|1\d\d|\d{1,2})(\.(25[0-5]|2[0-4]\d|1\d\d|\d{1,2})){3}$"


def _split_ip_port(serial: str) -> tuple[str, str]:
    """Return ``(ip, port)`` for a Wi-Fi serial; ``("", "")`` for USB."""
    if ":" in serial and serial.count(".") >= 3:
        ip, _, port = serial.partition(":")
        return ip, port
    return "", ""


def _pill_kind_for_status(status: str) -> str:
    if status == "online":
        return "online"
    if status == "unauthorized":
        return "warn"
    return "offline"


def _status_pill_text(status: str) -> str:
    if status == "online":
        return strings.STATUS_ONLINE
    if status == "unauthorized":
        return strings.STATUS_UNAUTHORIZED
    return strings.STATUS_OFFLINE


def _make_pill(text: str, kind: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("pill", kind)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class ConnectionsModule(IModule):
    """Connections screen (§3.1; Redesign §5.1)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        try:
            self._db: Optional[DatabaseManager] = DatabaseManager.instance()
        except Exception as exc:  # pragma: no cover - defensive
            _log.warning("DatabaseManager unavailable: %s", exc)
            self._db = None

        # cmd_id -> {"kind": str, **payload}
        self._pending: dict[str, dict] = {}
        # Flag set while we mutate live table programmatically.
        self._syncing_live = False
        # Flag set while we populate the paired table.
        self._loading_paired = False

        self._build_ui()
        self._wire_signals()
        self._refresh_live_table()
        self._refresh_paired_table()
        self._sync_active_selection(self._adb.active_device)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        # --- page header --------------------------------------------------
        self._refresh_btn = QPushButton(strings.BTN_REFRESH, self)
        _set_variant(self._refresh_btn, "primary")
        self._scan_btn = QPushButton(strings.BTN_SCAN_NETWORK, self)
        self._scan_btn.setEnabled(False)
        self._scan_btn.setToolTip(strings.TOOLTIP_NOT_IMPLEMENTED)
        header = page_header(
            strings.LABEL_CONNECTIONS,
            strings.PAGE_SUBTITLE_CONNECTIONS,
            actions=[self._scan_btn, self._refresh_btn],
            parent=self,
        )
        root.addWidget(header)

        # --- 2×2 card grid ------------------------------------------------
        grid_host = QWidget(self)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        grid.addWidget(self._build_wifi_pairing_card(), 0, 0)
        grid.addWidget(self._build_wifi_classic_card(), 0, 1)
        grid.addWidget(self._build_live_card(), 1, 0)
        grid.addWidget(self._build_paired_card(), 1, 1)

        root.addWidget(grid_host, 1)

    # --- card builders ---------------------------------------------------
    def _build_wifi_pairing_card(self) -> QFrame:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        # Row 1: IP address.
        ip_row = QHBoxLayout()
        ip_row.setSpacing(10)
        ip_row.addWidget(QLabel(strings.FIELD_IP_ADDRESS))
        self._wp_ip = QLineEdit()
        self._wp_ip.setPlaceholderText(strings.HINT_IP_ADDRESS)
        self._wp_ip.setValidator(
            QRegularExpressionValidator(QRegularExpression(_IP_RE), self._wp_ip)
        )
        ip_row.addWidget(self._wp_ip, 1)
        body_lay.addLayout(ip_row)

        # Row 2: Pairing Port + PIN + Pair button (single line, per plan §5.1).
        pp_row = QHBoxLayout()
        pp_row.setSpacing(10)
        pp_row.addWidget(QLabel(strings.FIELD_PAIRING_PORT))
        self._wp_port = QLineEdit()
        self._wp_port.setFixedWidth(130)
        self._wp_port.setPlaceholderText("44331")
        self._wp_port.setMaxLength(5)
        self._wp_port.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^\d{1,5}$"), self._wp_port
            )
        )
        pp_row.addWidget(self._wp_port)

        pp_row.addWidget(QLabel(strings.FIELD_PIN))
        self._wp_pin = QLineEdit()
        self._wp_pin.setFixedWidth(130)
        self._wp_pin.setEchoMode(QLineEdit.Normal)
        self._wp_pin.setMaxLength(6)
        self._wp_pin.setPlaceholderText("123456")
        self._wp_pin.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^\d{0,6}$"), self._wp_pin
            )
        )
        pp_row.addWidget(self._wp_pin)

        pp_row.addStretch(1)

        self._wp_pair_btn = QPushButton(strings.BTN_PAIR)
        _set_variant(self._wp_pair_btn, "primary")
        pp_row.addWidget(self._wp_pair_btn)
        body_lay.addLayout(pp_row)

        # Status line.
        self._wp_status = QLabel("")
        self._wp_status.setWordWrap(True)
        self._wp_status.setProperty("role", "hint")
        body_lay.addWidget(self._wp_status)
        body_lay.addStretch(1)

        return card(strings.CARD_WIFI_PAIRING, body, parent=self)

    def _build_wifi_classic_card(self) -> QFrame:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(QLabel(strings.FIELD_IP_ADDRESS))
        self._wc_ip = QLineEdit()
        self._wc_ip.setPlaceholderText(strings.HINT_IP_ADDRESS)
        self._wc_ip.setValidator(
            QRegularExpressionValidator(QRegularExpression(_IP_RE), self._wc_ip)
        )
        row.addWidget(self._wc_ip, 1)

        row.addWidget(QLabel(strings.FIELD_PORT))
        self._wc_port = QSpinBox()
        self._wc_port.setRange(1, 65535)
        self._wc_port.setValue(5555)
        self._wc_port.setFixedWidth(110)
        row.addWidget(self._wc_port)

        body_lay.addLayout(row)

        connect_row = QHBoxLayout()
        connect_row.setSpacing(10)
        connect_row.addStretch(1)
        self._wc_connect_btn = QPushButton(strings.BTN_CONNECT)
        _set_variant(self._wc_connect_btn, "primary")
        connect_row.addWidget(self._wc_connect_btn)
        body_lay.addLayout(connect_row)

        self._wc_status = QLabel("")
        self._wc_status.setWordWrap(True)
        self._wc_status.setProperty("role", "hint")
        body_lay.addWidget(self._wc_status)
        body_lay.addStretch(1)

        return card(strings.CARD_WIFI_CLASSIC, body, parent=self)

    def _build_live_card(self) -> QFrame:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        self._live_table = QTableWidget(0, 4)
        self._live_table.setHorizontalHeaderLabels(
            [
                strings.COL_SERIAL,
                strings.COL_IP_ADDRESS,
                strings.COL_MODEL,
                strings.COL_STATUS,
            ]
        )
        self._live_table.verticalHeader().setVisible(False)
        self._live_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._live_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._live_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._live_table.horizontalHeader().setStretchLastSection(True)
        self._live_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        body_lay.addWidget(self._live_table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._disconnect_btn = QPushButton(strings.BTN_DISCONNECT)
        _set_variant(self._disconnect_btn, "destructive")
        self._disconnect_btn.setEnabled(False)
        actions.addWidget(self._disconnect_btn)
        body_lay.addLayout(actions)

        return card(strings.CARD_CONNECTED_DEVICES, body, parent=self)

    def _build_paired_card(self) -> QFrame:
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(10)

        self._paired_table = QTableWidget(0, 4)
        self._paired_table.setHorizontalHeaderLabels(
            [
                strings.COL_ALIAS,
                strings.COL_IP_ADDRESS,
                strings.COL_CONNECTION_PORT,
                strings.COL_LAST_CONNECTED,
            ]
        )
        self._paired_table.verticalHeader().setVisible(False)
        self._paired_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._paired_table.setSelectionMode(QAbstractItemView.SingleSelection)
        # Row height 40 keeps the size="sm" QLineEdit (28 px) fully visible
        # — fixes handoff §6.1.
        self._paired_table.verticalHeader().setDefaultSectionSize(40)
        hdr = self._paired_table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(_PCOL_PORT, QHeaderView.Interactive)
        hdr.resizeSection(_PCOL_PORT, 140)
        self._paired_table.setColumnWidth(_PCOL_PORT, 140)
        body_lay.addWidget(self._paired_table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._paired_connect_btn = QPushButton(strings.BTN_CONNECT)
        _set_variant(self._paired_connect_btn, "primary")
        self._paired_connect_btn.setEnabled(False)
        actions.addWidget(self._paired_connect_btn)
        self._paired_forget_btn = QPushButton(strings.BTN_FORGET)
        _set_variant(self._paired_forget_btn, "destructive")
        self._paired_forget_btn.setEnabled(False)
        actions.addWidget(self._paired_forget_btn)
        body_lay.addLayout(actions)

        return card(strings.CARD_PAIRED_DEVICES, body, parent=self)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------
    def _wire_signals(self) -> None:
        mon = self._adb.devices
        mon.deviceConnected.connect(self._on_device_connected_signal)
        mon.deviceDisconnected.connect(self._on_device_disconnected_signal)
        mon.deviceStateChanged.connect(self._on_device_state_changed_signal)

        self._adb.commands.commandFinished.connect(self._on_cmd_finished)
        self._adb.commands.commandFailed.connect(self._on_cmd_failed)
        self._adb.activeDeviceChanged.connect(self._sync_active_selection)

        self._live_table.itemSelectionChanged.connect(self._on_live_selection_changed)
        self._live_table.cellClicked.connect(self._on_live_cell_clicked)
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)

        self._wc_connect_btn.clicked.connect(self._on_wifi_classic_connect)
        self._wp_pair_btn.clicked.connect(self._on_wifi_pair)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)

        self._paired_table.itemSelectionChanged.connect(
            self._on_paired_selection_changed
        )
        self._paired_table.itemChanged.connect(self._on_paired_item_changed)
        self._paired_connect_btn.clicked.connect(self._on_paired_connect_clicked)
        self._paired_forget_btn.clicked.connect(self._on_paired_forget_clicked)

    # ------------------------------------------------------------------
    # IModule lifecycle
    # ------------------------------------------------------------------
    def on_activate(self) -> None:
        self._refresh_paired_table()
        self._refresh_live_table()
        self._sync_active_selection(self._adb.active_device)

    def on_deactivate(self) -> None:
        return None

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._sync_active_selection(ctx)

    def on_device_disconnected(self) -> None:
        self._syncing_live = True
        try:
            self._live_table.clearSelection()
        finally:
            self._syncing_live = False
        self._disconnect_btn.setEnabled(False)

    def _on_refresh_clicked(self) -> None:
        self._refresh_live_table()
        self._refresh_paired_table()

    # ------------------------------------------------------------------
    # Live device table
    # ------------------------------------------------------------------
    def _refresh_live_table(self) -> None:
        self._syncing_live = True
        try:
            self._live_table.setRowCount(0)
            for ctx in self._adb.devices.known_devices():
                self._append_live_row(ctx)
        finally:
            self._syncing_live = False

    def _append_live_row(self, ctx: DeviceContext) -> None:
        row = self._live_table.rowCount()
        self._live_table.insertRow(row)
        self._set_live_row(row, ctx)

    def _set_live_row(self, row: int, ctx: DeviceContext) -> None:
        ip, _ = _split_ip_port(ctx.serial)
        serial_item = QTableWidgetItem(ctx.serial)
        serial_item.setData(Qt.UserRole, ctx.serial)
        ip_item = QTableWidgetItem(ip)
        model_item = QTableWidgetItem(ctx.model or "")
        for it in (serial_item, ip_item, model_item):
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self._live_table.setItem(row, _COL_SERIAL, serial_item)
        self._live_table.setItem(row, _COL_IP, ip_item)
        self._live_table.setItem(row, _COL_MODEL, model_item)

        kind = _pill_kind_for_status(ctx.status)
        text = _status_pill_text(ctx.status)
        pill = _make_pill(text, kind)
        # Stash the raw status for unauthorized-click detection.
        pill.setProperty("_status", ctx.status)
        self._live_table.setCellWidget(row, _COL_STATUS, pill)

    def _find_live_row(self, serial: str) -> int:
        for row in range(self._live_table.rowCount()):
            item = self._live_table.item(row, _COL_SERIAL)
            if item is not None and item.data(Qt.UserRole) == serial:
                return row
        return -1

    @Slot(object)
    def _on_device_connected_signal(self, ctx: DeviceContext) -> None:
        if self._find_live_row(ctx.serial) >= 0:
            return
        self._syncing_live = True
        try:
            self._append_live_row(ctx)
        finally:
            self._syncing_live = False

    @Slot(str)
    def _on_device_disconnected_signal(self, serial: str) -> None:
        row = self._find_live_row(serial)
        if row < 0:
            return
        self._syncing_live = True
        try:
            self._live_table.removeRow(row)
        finally:
            self._syncing_live = False

    @Slot(object)
    def _on_device_state_changed_signal(self, ctx: DeviceContext) -> None:
        row = self._find_live_row(ctx.serial)
        if row < 0:
            self._on_device_connected_signal(ctx)
            return
        self._syncing_live = True
        try:
            self._set_live_row(row, ctx)
        finally:
            self._syncing_live = False
        active = self._adb.active_device
        if active is not None and active.serial == ctx.serial:
            self._select_live_row(row)

    def _on_live_selection_changed(self) -> None:
        if self._syncing_live:
            return
        row = self._current_live_row()
        if row < 0:
            self._disconnect_btn.setEnabled(False)
            return
        serial = self._live_table.item(row, _COL_SERIAL).data(Qt.UserRole)
        self._disconnect_btn.setEnabled(True)
        ctx = self._find_known_ctx(serial)
        if ctx is not None and self._adb.active_device != ctx:
            self._adb.set_active_device(ctx)

    def _on_live_cell_clicked(self, row: int, col: int) -> None:
        if col != _COL_STATUS:
            return
        w = self._live_table.cellWidget(row, _COL_STATUS)
        if w is None:
            return
        if w.property("_status") == "unauthorized":
            QMessageBox.information(
                self,
                strings.TITLE_UNAUTHORIZED_DIALOG,
                strings.UNAUTHORIZED_HELP,
            )

    def _current_live_row(self) -> int:
        sel = self._live_table.selectionModel()
        if sel is None:
            return -1
        rows = sel.selectedRows()
        return rows[0].row() if rows else -1

    def _select_live_row(self, row: int) -> None:
        if row < 0 or row >= self._live_table.rowCount():
            return
        self._syncing_live = True
        try:
            self._live_table.selectRow(row)
        finally:
            self._syncing_live = False
        self._disconnect_btn.setEnabled(True)

    def _find_known_ctx(self, serial: str) -> Optional[DeviceContext]:
        for ctx in self._adb.devices.known_devices():
            if ctx.serial == serial:
                return ctx
        return None

    def _sync_active_selection(self, ctx: Optional[DeviceContext]) -> None:
        if ctx is None:
            self._syncing_live = True
            try:
                self._live_table.clearSelection()
            finally:
                self._syncing_live = False
            self._disconnect_btn.setEnabled(False)
            return
        row = self._find_live_row(ctx.serial)
        if row >= 0:
            self._select_live_row(row)

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------
    def _on_disconnect_clicked(self) -> None:
        row = self._current_live_row()
        if row < 0:
            return
        serial = self._live_table.item(row, _COL_SERIAL).data(Qt.UserRole)
        cmd_id = self._adb.commands.submit(
            None,
            ["disconnect", serial],
            _DISCONNECT_TIMEOUT_S,
            Priority.HIGH,
        )
        self._pending[cmd_id] = {"kind": "disconnect", "serial": serial}

    # ------------------------------------------------------------------
    # Wi-Fi Classic
    # ------------------------------------------------------------------
    def _on_wifi_classic_connect(self) -> None:
        ip = self._wc_ip.text().strip()
        if not _valid_ip(ip):
            self._wc_status.setText(strings.MSG_INVALID_IP)
            return
        port = int(self._wc_port.value())
        target = f"{ip}:{port}"
        self._wc_status.setText(strings.MSG_CONNECTING)
        self._wc_connect_btn.setEnabled(False)
        cmd_id = self._adb.commands.submit(
            None,
            ["connect", target],
            _CONNECT_TIMEOUT_S,
            Priority.NORMAL,
        )
        self._pending[cmd_id] = {
            "kind": "connect_classic",
            "target": target,
        }

    # ------------------------------------------------------------------
    # Wi-Fi Pairing
    # ------------------------------------------------------------------
    def _on_wifi_pair(self) -> None:
        ip = self._wp_ip.text().strip()
        if not _valid_ip(ip):
            self._wp_status.setText(strings.MSG_INVALID_IP)
            return
        port_text = self._wp_port.text().strip()
        if not port_text.isdigit() or not (1 <= int(port_text) <= 65535):
            self._wp_status.setText(strings.MSG_INVALID_PORT)
            return
        port = int(port_text)
        pin = self._wp_pin.text().strip()
        if len(pin) != 6 or not pin.isdigit():
            self._wp_status.setText(strings.MSG_INVALID_PIN)
            return
        target = f"{ip}:{port}"
        _log.info("pairing device target=%s", target)
        self._wp_status.setText(strings.MSG_PAIRING)
        self._wp_pair_btn.setEnabled(False)
        # Logger filter masks the 6-digit PIN because the command argv contains
        # "pair" — see _PinMaskingFilter in core/logger.py (CLAUDE.md §7).
        cmd_id = self._adb.commands.submit(
            None,
            ["pair", target, pin],
            _PAIR_TIMEOUT_S,
            Priority.NORMAL,
        )
        self._pending[cmd_id] = {
            "kind": "pair",
            "ip": ip,
            "pair_target": target,
        }
        self._wp_pin.clear()

    def _after_pair_success(self, ip: str) -> None:
        _log.info("pair succeeded ip=%s, saving to paired devices", ip)
        if self._db is not None:
            try:
                self._db.save_paired_device(ip, strings.ALIAS_DEFAULT)
            except Exception as exc:
                _log.warning("save_paired_device failed: %s", exc)
        self._refresh_paired_table()

    # ------------------------------------------------------------------
    # Paired devices table
    # ------------------------------------------------------------------
    def _refresh_paired_table(self) -> None:
        rows = []
        if self._db is not None:
            try:
                rows = self._db.get_paired_devices()
            except Exception as exc:
                _log.warning("get_paired_devices failed: %s", exc)
                rows = []
        self._loading_paired = True
        try:
            self._paired_table.setRowCount(0)
            for r in rows:
                row = self._paired_table.rowCount()
                self._paired_table.insertRow(row)

                alias_item = QTableWidgetItem(r.get("alias") or "")
                alias_item.setFlags(alias_item.flags() | Qt.ItemIsEditable)

                ip_item = QTableWidgetItem(r.get("ip") or "")
                ip_item.setFlags(ip_item.flags() & ~Qt.ItemIsEditable)
                ip_item.setData(Qt.UserRole, r.get("ip") or "")

                last_item = QTableWidgetItem(r.get("last_connected") or "")
                last_item.setFlags(last_item.flags() & ~Qt.ItemIsEditable)

                self._paired_table.setItem(row, _PCOL_ALIAS, alias_item)
                self._paired_table.setItem(row, _PCOL_IP, ip_item)
                self._paired_table.setItem(row, _PCOL_LAST, last_item)

                port_edit = QLineEdit()
                port_edit.setProperty("size", "sm")
                port_edit.setPlaceholderText("40787")
                port_edit.setMaxLength(5)
                port_edit.setValidator(
                    QRegularExpressionValidator(
                        QRegularExpression(r"^\d{0,5}$"), port_edit
                    )
                )
                stored_port = r.get("connect_port")
                if stored_port is not None:
                    port_edit.setText(str(stored_port))
                port_edit.textChanged.connect(self._update_connect_btn_state)
                self._paired_table.setCellWidget(row, _PCOL_PORT, port_edit)
        finally:
            self._loading_paired = False
        self._update_connect_btn_state()

    def _on_paired_selection_changed(self) -> None:
        row = self._current_paired_row()
        self._paired_forget_btn.setEnabled(row >= 0)
        self._update_connect_btn_state()

    def _update_connect_btn_state(self) -> None:
        row = self._current_paired_row()
        if row < 0:
            self._paired_connect_btn.setEnabled(False)
            return
        edit = self._port_edit_for_row(row)
        port_text = edit.text().strip() if edit is not None else ""
        self._paired_connect_btn.setEnabled(
            len(port_text) == 5 and port_text.isdigit()
        )

    def _current_paired_row(self) -> int:
        sel = self._paired_table.selectionModel()
        if sel is None:
            return -1
        rows = sel.selectedRows()
        return rows[0].row() if rows else -1

    def _paired_ip_for_row(self, row: int) -> str:
        item = self._paired_table.item(row, _PCOL_IP)
        if item is None:
            return ""
        ip = item.data(Qt.UserRole)
        return str(ip) if ip else ""

    def _port_edit_for_row(self, row: int) -> Optional[QLineEdit]:
        w = self._paired_table.cellWidget(row, _PCOL_PORT)
        return w if isinstance(w, QLineEdit) else None

    def _on_paired_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_paired:
            return
        if item.column() != _PCOL_ALIAS:
            return
        ip = self._paired_ip_for_row(item.row())
        if not ip or self._db is None:
            return
        new_alias = item.text().strip() or strings.ALIAS_DEFAULT
        try:
            self._db.update_paired_alias(ip, new_alias)
        except Exception as exc:
            _log.warning("update_paired_alias failed: %s", exc)

    def _on_paired_connect_clicked(self) -> None:
        row = self._current_paired_row()
        if row < 0:
            return
        ip = self._paired_ip_for_row(row)
        if not ip:
            return
        edit = self._port_edit_for_row(row)
        port_text = edit.text().strip() if edit is not None else ""
        if len(port_text) != 5 or not port_text.isdigit():
            return
        target = f"{ip}:{port_text}"
        _log.info("connecting paired device target=%s", target)
        cmd_id = self._adb.commands.submit(
            None,
            ["connect", target],
            _CONNECT_TIMEOUT_S,
            Priority.NORMAL,
        )
        self._pending[cmd_id] = {
            "kind": "connect_paired",
            "ip": ip,
            "target": target,
            "connect_port": int(port_text),
        }

    def _on_paired_forget_clicked(self) -> None:
        row = self._current_paired_row()
        if row < 0:
            return
        ip = self._paired_ip_for_row(row)
        if not ip or self._db is None:
            return
        try:
            self._db.delete_paired_device(ip)
        except Exception as exc:
            _log.warning("delete_paired_device failed: %s", exc)
        self._refresh_paired_table()

    # ------------------------------------------------------------------
    # Command completion
    # ------------------------------------------------------------------
    @Slot(str, object)
    def _on_cmd_finished(self, cmd_id: str, result: object) -> None:
        info = self._pending.pop(cmd_id, None)
        if info is None:
            return
        self._handle_result(info, result, success=True)

    @Slot(str, object)
    def _on_cmd_failed(self, cmd_id: str, result: object) -> None:
        info = self._pending.pop(cmd_id, None)
        if info is None:
            return
        self._handle_result(info, result, success=False)

    def _handle_result(self, info: dict, result: object, success: bool) -> None:
        stdout = getattr(result, "stdout", "") or ""
        stderr = getattr(result, "stderr", "") or ""
        combined = (stderr + "\n" + stdout).strip()
        # adb-connect sometimes returns rc=0 but prints "failed to connect…".
        if success and combined.lower().startswith("failed to connect"):
            success = False

        kind = info.get("kind")

        if kind == "connect_classic":
            self._wc_connect_btn.setEnabled(True)
            target = info.get("target", "")
            if success:
                _log.info("connect_classic succeeded target=%s", target)
                self._wc_status.setText(
                    strings.MSG_CONNECT_OK.format(target=target)
                )
            else:
                human, raw = parse_error(combined)
                self._wc_status.setText(
                    strings.MSG_CONNECT_FAIL.format(error=human)
                )
                _log.warning(
                    "connect_classic failed target=%s raw=%s", target, raw[:200]
                )

        elif kind == "pair":
            self._wp_pair_btn.setEnabled(True)
            if success:
                ip = info.get("ip", "")
                self._wp_status.setText(strings.MSG_PAIR_OK.format(ip=ip))
                self._after_pair_success(ip)
            else:
                human, raw = parse_error(combined)
                self._wp_status.setText(
                    strings.MSG_PAIR_FAIL.format(error=human)
                )
                _log.warning(
                    "pair failed target=%s raw=%s",
                    info.get("pair_target", ""),
                    raw[:200],
                )

        elif kind == "connect_paired":
            ip = info.get("ip", "")
            target = info.get("target", "")
            connect_port = info.get("connect_port")
            if success:
                _log.info("connect_paired succeeded target=%s", target)
                if self._db is not None:
                    try:
                        self._db.save_paired_device(
                            ip, strings.ALIAS_DEFAULT, connect_port
                        )
                        self._db.touch_paired_device(ip)
                    except Exception as exc:
                        _log.warning("db update failed after connect: %s", exc)
                self._refresh_paired_table()
                self._show_transient(strings.MSG_CONNECT_OK.format(target=target))
            else:
                human, raw = parse_error(combined)
                _log.warning(
                    "connect_paired failed target=%s raw=%s", target, raw[:200]
                )
                self._show_transient(
                    strings.MSG_CONNECT_FAIL.format(error=human)
                )

        elif kind == "disconnect":
            serial = info.get("serial", "")
            if success:
                _log.info("disconnect succeeded serial=%s", serial)
                self._show_transient(
                    strings.MSG_DISCONNECT_OK.format(serial=serial)
                )
            else:
                human, raw = parse_error(combined)
                _log.warning(
                    "disconnect failed serial=%s raw=%s", serial, raw[:200]
                )
                self._show_transient(
                    strings.MSG_DISCONNECT_FAIL.format(error=human)
                )

    def _show_transient(self, text: str) -> None:
        """Push a transient status to the main window's status bar if reachable."""
        w = self.window()
        status = getattr(w, "statusBar", None)
        if status is None:
            return
        try:
            bar = status()
        except TypeError:
            return
        show = getattr(bar, "show_message", None) or getattr(bar, "showMessage", None)
        if show is not None:
            try:
                show(text)
            except Exception:
                pass


def _valid_ip(text: str) -> bool:
    parts = text.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit():
            return False
        n = int(p)
        if n < 0 or n > 255:
            return False
    return True


__all__ = ["ConnectionsModule"]
