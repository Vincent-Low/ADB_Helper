"""Module: Connections (Spec §3.1).

Default module shown on launch. Manages USB and Wi-Fi (classic + Android 11+
pairing) ADB connections, lists live devices via ``adb track-devices`` (driven
by :class:`DeviceMonitor` signals), and persists paired Wi-Fi devices for
manual reconnection. No auto-reconnect on startup (§9).

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
    QGroupBox,
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
_PCOL_LAST = 2

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


def _status_label(status: str) -> str:
    if status == "online":
        return strings.STATUS_ONLINE
    if status == "unauthorized":
        return f"{strings.STATUS_UNAUTHORIZED} {strings.ICON_UNAUTHORIZED}"
    return strings.STATUS_OFFLINE


class ConnectionsModule(IModule):
    """Connections screen (§3.1)."""

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

        root.addWidget(self._build_live_group())
        root.addWidget(self._build_wifi_classic_group())
        root.addWidget(self._build_wifi_pairing_group())
        root.addWidget(self._build_paired_group(), 1)

    def _build_live_group(self) -> QGroupBox:
        g = QGroupBox(strings.LABEL_CONNECTED_DEVICES, self)
        lay = QVBoxLayout(g)

        self._live_table = QTableWidget(0, 4, g)
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
        lay.addWidget(self._live_table)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._disconnect_btn = QPushButton(strings.BTN_DISCONNECT, g)
        _set_variant(self._disconnect_btn, "destructive")
        self._disconnect_btn.setEnabled(False)
        actions.addWidget(self._disconnect_btn)
        lay.addLayout(actions)
        return g

    def _build_wifi_classic_group(self) -> QGroupBox:
        g = QGroupBox(strings.LABEL_WIFI_CLASSIC, self)
        lay = QVBoxLayout(g)

        row = QHBoxLayout()
        row.addWidget(QLabel(strings.FIELD_IP_ADDRESS, g))
        self._wc_ip = QLineEdit(g)
        self._wc_ip.setPlaceholderText(strings.HINT_IP_ADDRESS)
        self._wc_ip.setValidator(
            QRegularExpressionValidator(QRegularExpression(_IP_RE), self._wc_ip)
        )
        row.addWidget(self._wc_ip, 2)

        row.addWidget(QLabel(strings.FIELD_PORT, g))
        self._wc_port = QSpinBox(g)
        self._wc_port.setRange(1, 65535)
        self._wc_port.setValue(5555)
        row.addWidget(self._wc_port, 0)

        self._wc_connect_btn = QPushButton(strings.BTN_CONNECT, g)
        _set_variant(self._wc_connect_btn, "primary")
        row.addWidget(self._wc_connect_btn, 0)
        lay.addLayout(row)

        self._wc_status = QLabel("", g)
        self._wc_status.setWordWrap(True)
        self._wc_status.setProperty("secondary", "true")
        lay.addWidget(self._wc_status)
        return g

    def _build_wifi_pairing_group(self) -> QGroupBox:
        g = QGroupBox(strings.LABEL_WIFI_PAIRING, self)
        lay = QVBoxLayout(g)

        row = QHBoxLayout()
        row.addWidget(QLabel(strings.FIELD_IP_ADDRESS, g))
        self._wp_ip = QLineEdit(g)
        self._wp_ip.setPlaceholderText(strings.HINT_IP_ADDRESS)
        self._wp_ip.setValidator(
            QRegularExpressionValidator(QRegularExpression(_IP_RE), self._wp_ip)
        )
        row.addWidget(self._wp_ip, 2)

        row.addWidget(QLabel(strings.FIELD_PAIRING_PORT, g))
        self._wp_port = QSpinBox(g)
        self._wp_port.setRange(1, 65535)
        self._wp_port.setValue(37000)
        row.addWidget(self._wp_port, 0)

        row.addWidget(QLabel(strings.FIELD_PIN, g))
        self._wp_pin = QLineEdit(g)
        self._wp_pin.setEchoMode(QLineEdit.Password)
        self._wp_pin.setMaxLength(6)
        self._wp_pin.setPlaceholderText(strings.HINT_PIN)
        self._wp_pin.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^\d{6}$"), self._wp_pin
            )
        )
        row.addWidget(self._wp_pin, 0)

        self._wp_pair_btn = QPushButton(strings.BTN_PAIR, g)
        _set_variant(self._wp_pair_btn, "primary")
        row.addWidget(self._wp_pair_btn, 0)
        lay.addLayout(row)

        self._wp_status = QLabel("", g)
        self._wp_status.setWordWrap(True)
        self._wp_status.setProperty("secondary", "true")
        lay.addWidget(self._wp_status)
        return g

    def _build_paired_group(self) -> QGroupBox:
        g = QGroupBox(strings.LABEL_PAIRED_DEVICES, self)
        lay = QVBoxLayout(g)

        self._paired_table = QTableWidget(0, 3, g)
        self._paired_table.setHorizontalHeaderLabels(
            [strings.COL_ALIAS, strings.COL_IP_ADDRESS, strings.COL_LAST_CONNECTED]
        )
        self._paired_table.verticalHeader().setVisible(False)
        self._paired_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._paired_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._paired_table.horizontalHeader().setStretchLastSection(True)
        self._paired_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        lay.addWidget(self._paired_table)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._paired_connect_btn = QPushButton(strings.BTN_CONNECT, g)
        _set_variant(self._paired_connect_btn, "primary")
        self._paired_connect_btn.setEnabled(False)
        actions.addWidget(self._paired_connect_btn)
        self._paired_forget_btn = QPushButton(strings.BTN_FORGET, g)
        _set_variant(self._paired_forget_btn, "destructive")
        self._paired_forget_btn.setEnabled(False)
        actions.addWidget(self._paired_forget_btn)
        lay.addLayout(actions)
        return g

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
        items = [
            QTableWidgetItem(ctx.serial),
            QTableWidgetItem(ip),
            QTableWidgetItem(ctx.model or ""),
            QTableWidgetItem(_status_label(ctx.status)),
        ]
        items[_COL_SERIAL].setData(Qt.UserRole, ctx.serial)
        items[_COL_STATUS].setData(Qt.UserRole, ctx.status)
        for col, it in enumerate(items):
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self._live_table.setItem(row, col, it)

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
        item = self._live_table.item(row, _COL_STATUS)
        if item is None:
            return
        if item.data(Qt.UserRole) == "unauthorized":
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
        port = int(self._wp_port.value())
        pin = self._wp_pin.text().strip()
        if len(pin) != 6 or not pin.isdigit():
            self._wp_status.setText(strings.MSG_INVALID_PIN)
            return
        target = f"{ip}:{port}"
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
        if self._db is not None:
            try:
                self._db.save_paired_device(ip, strings.ALIAS_DEFAULT)
            except Exception as exc:
                _log.warning("save_paired_device failed: %s", exc)
        self._refresh_paired_table()
        target = f"{ip}:5555"
        cmd_id = self._adb.commands.submit(
            None,
            ["connect", target],
            _CONNECT_TIMEOUT_S,
            Priority.HIGH,
        )
        self._pending[cmd_id] = {
            "kind": "connect_after_pair",
            "ip": ip,
            "target": target,
        }

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
                last_item = QTableWidgetItem(r.get("last_connected") or "")
                last_item.setFlags(last_item.flags() & ~Qt.ItemIsEditable)
                ip_item.setData(Qt.UserRole, r.get("ip") or "")
                self._paired_table.setItem(row, _PCOL_ALIAS, alias_item)
                self._paired_table.setItem(row, _PCOL_IP, ip_item)
                self._paired_table.setItem(row, _PCOL_LAST, last_item)
        finally:
            self._loading_paired = False
        self._on_paired_selection_changed()

    def _on_paired_selection_changed(self) -> None:
        row = self._current_paired_row()
        enabled = row >= 0
        self._paired_connect_btn.setEnabled(enabled)
        self._paired_forget_btn.setEnabled(enabled)

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
        target = f"{ip}:5555"
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
            if success:
                self._wc_status.setText(
                    strings.MSG_CONNECT_OK.format(target=info.get("target", ""))
                )
            else:
                human, raw = parse_error(combined)
                self._wc_status.setText(
                    strings.MSG_CONNECT_FAIL.format(error=human)
                )
                _log.info("classic connect failed raw=%s", raw[:200])

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
                _log.info("pair failed raw=%s", raw[:200])

        elif kind == "connect_after_pair":
            ip = info.get("ip", "")
            if success:
                self._wp_status.setText(
                    strings.MSG_CONNECT_OK.format(target=info.get("target", ""))
                )
                if self._db is not None:
                    try:
                        self._db.touch_paired_device(ip)
                    except Exception as exc:
                        _log.warning("touch_paired_device failed: %s", exc)
                self._refresh_paired_table()
            else:
                human, _ = parse_error(combined)
                self._wp_status.setText(
                    strings.MSG_CONNECT_FAIL.format(error=human)
                )

        elif kind == "connect_paired":
            ip = info.get("ip", "")
            target = info.get("target", "")
            if success:
                if self._db is not None:
                    try:
                        self._db.touch_paired_device(ip)
                    except Exception as exc:
                        _log.warning("touch_paired_device failed: %s", exc)
                self._refresh_paired_table()
                self._show_transient(strings.MSG_CONNECT_OK.format(target=target))
            else:
                human, _ = parse_error(combined)
                self._show_transient(
                    strings.MSG_CONNECT_FAIL.format(error=human)
                )

        elif kind == "disconnect":
            serial = info.get("serial", "")
            if success:
                self._show_transient(
                    strings.MSG_DISCONNECT_OK.format(serial=serial)
                )
            else:
                human, _ = parse_error(combined)
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
