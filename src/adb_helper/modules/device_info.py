"""Module: Device Info (Spec §3.6; Redesign §5.6).

Static-on-activate snapshot of all device info available without root.
Refresh reloads on demand. Export to TXT supported.

Layout (Redesign §5.6): 10 section cards repacked into a 2-column
``QGridLayout`` (cards flow left → right, top → bottom) inside a
``QScrollArea``. Each card body is a ``QFormLayout`` with label width 180,
label text in ``text_2`` via ``role="hint"``, and value labels set as
selectable. Technical fields (fingerprint, MAC, IP, serials) use a
monospace font.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core import strings
from ..core.adb_service import get_adb_service
from ..core.command_runner import AdbResult, Priority
from ..core.device_context import DeviceContext
from ..core.imodule import IModule
from ..core.logger import get_logger
from ..ui.style_utils import page_header
from ..ui.style_utils import set_variant as _set_variant

_log = get_logger(__name__)

_NA = "N/A"
_DASH = "—"
_TIMEOUT = 30

_SEL = (
    Qt.TextInteractionFlag.TextSelectableByMouse
    | Qt.TextInteractionFlag.TextSelectableByKeyboard
)

_BATTERY_STATUS: dict[str, str] = {
    "1": "Unknown",
    "2": "Charging",
    "3": "Discharging",
    "4": "Not charging",
    "5": "Full",
}

_BATTERY_HEALTH: dict[str, str] = {
    "1": "Unknown",
    "2": "Good",
    "3": "Overheat",
    "4": "Dead",
    "5": "Over voltage",
    "6": "Unspecified failure",
    "7": "Cold",
}

# Fields that should render in a monospace font (fingerprints, MACs, IPs, …).
_MONO_FIELDS = frozenset({
    strings.DI_FIELD_SERIAL,
    strings.DI_FIELD_BUILD_FINGERPRINT,
    strings.DI_FIELD_BUILD_NUMBER,
    strings.DI_FIELD_BASEBAND,
    strings.DI_FIELD_WIFI_IP,
    strings.DI_FIELD_WIFI_MAC,
    strings.DI_FIELD_BT_MAC,
})

# role -> adb args
_FETCH_ROLES: dict[str, list[str]] = {
    "getprop":       ["shell", "getprop"],
    "cpuinfo":       ["shell", "cat /proc/cpuinfo"],
    "meminfo":       ["shell", "cat /proc/meminfo"],
    "df_data":       ["shell", "df /data"],
    "wm_density":    ["shell", "wm density"],
    "battery":       ["shell", "dumpsys battery"],
    "display":       ["shell", "dumpsys display"],
    "surfaceflinger":["shell", "dumpsys SurfaceFlinger"],
    "ip_addr":       ["shell", "ip addr show wlan0"],
    "ip_link":       ["shell", "ip link show wlan0"],
    "wlan_mac_file": ["shell", "cat /sys/class/net/wlan0/address"],
    "bt_addr":       ["shell", "settings get secure bluetooth_address"],
    "cpu_gov":       ["shell", "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"],
    "cpu_min":       ["shell", "cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq"],
    "cpu_max":       ["shell", "cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"],
}

# Ordered section definitions used by both UI builder and TXT exporter.
_SECTIONS: list[tuple[str, list[str]]] = [
    (strings.DI_SEC_DEVICE, [
        strings.DI_FIELD_MANUFACTURER,
        strings.DI_FIELD_MODEL,
        strings.DI_FIELD_CODENAME,
        strings.DI_FIELD_BRAND,
        strings.DI_FIELD_SERIAL,
    ]),
    (strings.DI_SEC_SYSTEM, [
        strings.DI_FIELD_ANDROID_VERSION,
        strings.DI_FIELD_API_LEVEL,
        strings.DI_FIELD_SECURITY_PATCH,
        strings.DI_FIELD_BUILD_NUMBER,
        strings.DI_FIELD_BUILD_FINGERPRINT,
        strings.DI_FIELD_BUILD_TYPE,
        strings.DI_FIELD_BUILD_DATE,
        strings.DI_FIELD_BOOTLOADER,
        strings.DI_FIELD_BASEBAND,
    ]),
    (strings.DI_SEC_CPU, [
        strings.DI_FIELD_CPU_HARDWARE,
        strings.DI_FIELD_CPU_MODEL,
        strings.DI_FIELD_CPU_ARCH,
        strings.DI_FIELD_CPU_CORES,
        strings.DI_FIELD_CPU_GOVERNOR,
        strings.DI_FIELD_CPU_FREQ,
    ]),
    (strings.DI_SEC_GPU, [
        strings.DI_FIELD_GPU_VENDOR,
        strings.DI_FIELD_GPU_RENDERER,
        strings.DI_FIELD_OPENGL_VERSION,
    ]),
    (strings.DI_SEC_MEMORY, [
        strings.DI_FIELD_RAM_TOTAL,
        strings.DI_FIELD_RAM_AVAILABLE,
        strings.DI_FIELD_SWAP_TOTAL,
    ]),
    (strings.DI_SEC_STORAGE, [
        strings.DI_FIELD_STORAGE_TOTAL,
        strings.DI_FIELD_STORAGE_AVAILABLE,
    ]),
    (strings.DI_SEC_DISPLAY, [
        strings.DI_FIELD_RESOLUTION,
        strings.DI_FIELD_DENSITY,
        strings.DI_FIELD_REFRESH_RATE,
    ]),
    (strings.DI_SEC_BATTERY, [
        strings.DI_FIELD_BATTERY_LEVEL,
        strings.DI_FIELD_BATTERY_STATUS,
        strings.DI_FIELD_BATTERY_HEALTH,
        strings.DI_FIELD_BATTERY_TEMP,
        strings.DI_FIELD_BATTERY_TECH,
        strings.DI_FIELD_BATTERY_VOLTAGE,
    ]),
    (strings.DI_SEC_NETWORK, [
        strings.DI_FIELD_WIFI_IP,
        strings.DI_FIELD_WIFI_MAC,
        strings.DI_FIELD_BT_MAC,
        strings.DI_FIELD_IMEI,
    ]),
    (strings.DI_SEC_LOCALE, [
        strings.DI_FIELD_LANGUAGE,
        strings.DI_FIELD_TIMEZONE,
    ]),
]


def _kib_to_human(kib: int) -> str:
    if kib >= 1024 * 1024:
        return f"{kib / (1024 * 1024):.1f} GB"
    if kib >= 1024:
        return f"{kib // 1024} MB"
    return f"{kib} KB"


def _khz_to_mhz(raw: str) -> str:
    try:
        return f"{int(raw.strip()) // 1000} MHz"
    except (ValueError, AttributeError):
        return _NA


def _mono_font_for(widget: QWidget) -> QFont:
    font = widget.font()
    font.setFamily("JetBrains Mono")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


class DeviceInfoModule(IModule):
    """Device Info screen (§3.6; Redesign §5.6). Static snapshot, Refresh + Export to TXT."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        self._serial: Optional[str] = None
        self._model: str = "device"
        self._pending: dict[str, str] = {}   # cmd_id -> role
        self._results: dict[str, str] = {}   # role  -> stdout
        self._labels: dict[str, QLabel] = {} # field -> QLabel
        self._build_ui()
        self._wire_signals()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        # --- page header with dynamic subtitle ---
        self._refresh_btn = QPushButton(strings.DI_BTN_REFRESH, self)
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.clicked.connect(self._on_refresh)
        _set_variant(self._refresh_btn, "primary")

        self._export_btn = QPushButton(strings.DI_BTN_EXPORT, self)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)

        # Build header inline so we can hold a ref to the subtitle label.
        hdr_host = QWidget(self)
        hdr_row = QHBoxLayout(hdr_host)
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(10)
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        title_lbl = QLabel(strings.LABEL_DEVICE_INFO, hdr_host)
        title_lbl.setProperty("role", "page-title")
        self._subtitle_lbl = QLabel(self._make_subtitle(), hdr_host)
        self._subtitle_lbl.setProperty("role", "hint")
        text_col.addWidget(title_lbl)
        text_col.addWidget(self._subtitle_lbl)
        hdr_row.addLayout(text_col, 1)
        hdr_row.addWidget(self._refresh_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        hdr_row.addWidget(self._export_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(hdr_host)

        # Loading progress bar (indeterminate while fetching).
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # --- 2-column card grid inside a scroll area ---
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget(scroll)
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        for idx, (title, fields) in enumerate(_SECTIONS):
            row, col = divmod(idx, 2)
            grid.addWidget(self._build_section_card(title, fields, content), row, col)

        grid.setRowStretch(len(_SECTIONS) // 2, 1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _build_section_card(
        self, title: str, fields: list[str], parent: QWidget
    ) -> QFrame:
        """Build a QFrame[role="card"] with a QFormLayout for one info section."""
        frame = QFrame(parent)
        frame.setProperty("role", "card")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Card header
        hdr = QFrame(frame)
        hdr.setProperty("role", "card-h")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(14, 10, 14, 10)
        sec_lbl = QLabel(title, hdr)
        sec_lbl.setProperty("role", "section-label")
        hdr_lay.addWidget(sec_lbl)
        outer.addWidget(hdr)

        # Card body — QFormLayout
        body = QWidget(frame)
        form = QFormLayout(body)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        for field in fields:
            # Row label: fixed width 180, hint color via role="hint".
            row_lbl = QLabel(field + ":", body)
            row_lbl.setProperty("role", "hint")
            row_lbl.setFixedWidth(180)
            row_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if field == strings.DI_FIELD_IMEI:
                row_lbl.setToolTip(strings.DI_TOOLTIP_IMEI)

            val_lbl = _make_value_label(_DASH, body)
            if field in _MONO_FIELDS:
                val_lbl.setFont(_mono_font_for(val_lbl))

            form.addRow(row_lbl, val_lbl)
            self._labels[field] = val_lbl

        outer.addWidget(body)
        outer.addStretch(1)
        return frame

    def _wire_signals(self) -> None:
        self._adb.commands.commandFinished.connect(self._on_cmd_finished)
        self._adb.commands.commandFailed.connect(self._on_cmd_failed)

    # ---------------------------------------------------------- Fetch

    def _fetch(self) -> None:
        for cid in list(self._pending):
            self._adb.commands.cancel(cid)
        self._pending.clear()
        self._results.clear()
        self._set_loading(True)
        for role, args in _FETCH_ROLES.items():
            cid = self._adb.commands.submit(
                self._serial, args, _TIMEOUT, Priority.NORMAL
            )
            self._pending[cid] = role

    def _set_loading(self, loading: bool) -> None:
        self._progress.setVisible(loading)
        active = self._serial is not None
        self._refresh_btn.setEnabled(active and not loading)
        self._export_btn.setEnabled(active and not loading and bool(self._results))

    @Slot(str, object)
    def _on_cmd_finished(self, cid: str, result: AdbResult) -> None:
        if cid not in self._pending:
            return
        role = self._pending.pop(cid)
        self._results[role] = result.stdout
        if not self._pending:
            self._update_ui()

    @Slot(str, object)
    def _on_cmd_failed(self, cid: str, result: AdbResult) -> None:
        if cid not in self._pending:
            return
        self._pending.pop(cid)
        if not self._pending:
            self._update_ui()

    def _update_ui(self) -> None:
        self._populate_all()
        self._set_loading(False)

    # ------------------------------------------------------- Populate UI

    def _populate_all(self) -> None:
        props = _parse_getprop(self._results.get("getprop", ""))
        S = strings
        s = self._set_label

        # §3.6.1 Device
        s(S.DI_FIELD_MANUFACTURER, props.get("ro.product.manufacturer", _NA))
        s(S.DI_FIELD_MODEL,        props.get("ro.product.model",        _NA))
        s(S.DI_FIELD_CODENAME,     props.get("ro.product.device",       _NA))
        s(S.DI_FIELD_BRAND,        props.get("ro.product.brand",        _NA))
        s(S.DI_FIELD_SERIAL,       self._serial or _NA)

        # §3.6.2 System
        s(S.DI_FIELD_ANDROID_VERSION,   props.get("ro.build.version.release",        _NA))
        s(S.DI_FIELD_API_LEVEL,         props.get("ro.build.version.sdk",            _NA))
        s(S.DI_FIELD_SECURITY_PATCH,    props.get("ro.build.version.security_patch", _NA))
        s(S.DI_FIELD_BUILD_NUMBER,      props.get("ro.build.display.id",             _NA))
        s(S.DI_FIELD_BUILD_FINGERPRINT, props.get("ro.build.fingerprint",            _NA))
        s(S.DI_FIELD_BUILD_TYPE,        props.get("ro.build.type",                   _NA))
        s(S.DI_FIELD_BUILD_DATE,        props.get("ro.build.date",                   _NA))
        s(S.DI_FIELD_BOOTLOADER,        props.get("ro.bootloader",                   _NA))
        s(S.DI_FIELD_BASEBAND,          props.get("gsm.version.baseband") or _NA)

        # §3.6.3 CPU
        cpu = _parse_cpuinfo(self._results.get("cpuinfo", ""))
        s(S.DI_FIELD_CPU_HARDWARE,  cpu.get("hardware",    _NA))
        s(S.DI_FIELD_CPU_MODEL,     cpu.get("model_name",  _NA))
        s(S.DI_FIELD_CPU_ARCH,      props.get("ro.product.cpu.abi", _NA))
        s(S.DI_FIELD_CPU_CORES,     cpu.get("cores",       _NA))
        s(S.DI_FIELD_CPU_GOVERNOR,  self._results.get("cpu_gov", "").strip() or _NA)
        cpu_min = _khz_to_mhz(self._results.get("cpu_min", ""))
        cpu_max = _khz_to_mhz(self._results.get("cpu_max", ""))
        freq = f"{cpu_min} / {cpu_max}" if cpu_min != _NA and cpu_max != _NA else _NA
        s(S.DI_FIELD_CPU_FREQ, freq)

        # §3.6.4 GPU
        gpu = _parse_surfaceflinger(self._results.get("surfaceflinger", ""))
        s(S.DI_FIELD_GPU_VENDOR,     gpu.get("vendor",   _NA))
        s(S.DI_FIELD_GPU_RENDERER,   gpu.get("renderer", _NA))
        s(S.DI_FIELD_OPENGL_VERSION, gpu.get("version",  _NA))

        # §3.6.5 Memory
        mem = _parse_meminfo(self._results.get("meminfo", ""))
        s(S.DI_FIELD_RAM_TOTAL,     _kib_to_human(mem["MemTotal"])     if "MemTotal"     in mem else _NA)
        s(S.DI_FIELD_RAM_AVAILABLE, _kib_to_human(mem["MemAvailable"]) if "MemAvailable" in mem else _NA)
        s(S.DI_FIELD_SWAP_TOTAL,    _kib_to_human(mem["SwapTotal"])    if "SwapTotal"    in mem else _NA)

        # §3.6.6 Storage
        stor = _parse_df(self._results.get("df_data", ""))
        s(S.DI_FIELD_STORAGE_TOTAL,     stor.get("total",     _NA))
        s(S.DI_FIELD_STORAGE_AVAILABLE, stor.get("available", _NA))

        # §3.6.7 Display
        disp = _parse_display(self._results.get("display", ""))
        s(S.DI_FIELD_RESOLUTION,   disp.get("resolution",   _NA))
        dm = re.search(r"density[:\s]+(\d+)", self._results.get("wm_density", ""))
        s(S.DI_FIELD_DENSITY,      dm.group(1) if dm else _NA)
        s(S.DI_FIELD_REFRESH_RATE, disp.get("refresh_rate", _NA))

        # §3.6.8 Battery
        bat = _parse_battery(self._results.get("battery", ""))
        level = bat.get("level", "")
        s(S.DI_FIELD_BATTERY_LEVEL,   f"{level}%" if level else _NA)
        s(S.DI_FIELD_BATTERY_STATUS,
          _BATTERY_STATUS.get(bat.get("status", ""), bat.get("status") or _NA))
        s(S.DI_FIELD_BATTERY_HEALTH,
          _BATTERY_HEALTH.get(bat.get("health", ""), bat.get("health") or _NA))
        temp_raw = bat.get("temperature", "")
        try:
            s(S.DI_FIELD_BATTERY_TEMP, f"{int(temp_raw) / 10:.1f}°C" if temp_raw else _NA)
        except ValueError:
            s(S.DI_FIELD_BATTERY_TEMP, _NA)
        s(S.DI_FIELD_BATTERY_TECH,    bat.get("technology") or _NA)
        voltage = bat.get("voltage", "")
        s(S.DI_FIELD_BATTERY_VOLTAGE, f"{voltage} mV" if voltage else _NA)

        # §3.6.9 Network
        s(S.DI_FIELD_WIFI_IP,  _parse_ip_addr(self._results.get("ip_addr", "")) or _NA)
        wifi_mac = (
            _parse_ip_link(self._results.get("ip_link", ""))
            or _parse_mac_file(self._results.get("wlan_mac_file", ""))
        )
        s(S.DI_FIELD_WIFI_MAC, wifi_mac or _NA)
        bt_raw = self._results.get("bt_addr", "").strip()
        s(S.DI_FIELD_BT_MAC,   bt_raw if bt_raw and bt_raw != "null" else _NA)
        s(S.DI_FIELD_IMEI,     strings.DI_VALUE_IMEI_NA)

        # §3.6.10 Locale & Time
        lang = (
            props.get("ro.product.locale")
            or props.get("persist.sys.locale")
            or _NA
        )
        s(S.DI_FIELD_LANGUAGE, lang)
        s(S.DI_FIELD_TIMEZONE, props.get("persist.sys.timezone") or _NA)

    def _set_label(self, field: str, value: str) -> None:
        lbl = self._labels.get(field)
        if lbl is not None:
            lbl.setText(value or _NA)

    def _clear_fields(self) -> None:
        for lbl in self._labels.values():
            lbl.setText(_DASH)

    def _make_subtitle(self) -> str:
        serial = self._serial or "—"
        return strings.PAGE_SUBTITLE_DEVICE_INFO.format(serial=serial)

    def _update_subtitle(self) -> None:
        self._subtitle_lbl.setText(self._make_subtitle())

    # --------------------------------------------------------- Export

    def _on_export(self) -> None:
        safe_model = re.sub(r"[^\w\-]", "_", self._model)
        today = date.today().strftime("%Y-%m-%d")
        default_name = f"device_info_{safe_model}_{today}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self,
            strings.DI_TITLE_EXPORT,
            default_name,
            strings.DI_FILTER_TXT,
        )
        if not path:
            return
        lines: list[str] = [
            f"Device Info — {self._model} — {today}",
            "",
        ]
        for title, fields in _SECTIONS:
            lines.append(f"=== {title} ===")
            for field in fields:
                lbl = self._labels.get(field)
                lines.append(f"{field}: {lbl.text() if lbl else _NA}")
            lines.append("")
        try:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            _log.info("device info exported to %s", path)
        except OSError as exc:
            _log.error("export failed: %s", exc)

    def _on_refresh(self) -> None:
        self._fetch()

    # -------------------------------------------------- IModule lifecycle

    def on_activate(self) -> None:
        ctx = self._adb.active_device
        if ctx is not None:
            self._serial = ctx.serial
            self._model = ctx.model
            self._update_subtitle()
            self._fetch()

    def on_deactivate(self) -> None:
        for cid in list(self._pending):
            self._adb.commands.cancel(cid)
        self._pending.clear()

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        if ctx is not None:
            self._serial = ctx.serial
            self._model = ctx.model
            self._update_subtitle()
            self._fetch()
        else:
            self._serial = None
            self._update_subtitle()
            for cid in list(self._pending):
                self._adb.commands.cancel(cid)
            self._pending.clear()
            self._set_loading(False)
            self._clear_fields()

    def on_device_disconnected(self) -> None:
        self._serial = None
        self._update_subtitle()
        for cid in list(self._pending):
            self._adb.commands.cancel(cid)
        self._pending.clear()
        self._set_loading(False)
        self._clear_fields()


# ------------------------------------------------------------ Pure parsers

def _parse_getprop(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\[(.+?)\]:\s*\[(.*?)\]\s*$", line)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def _parse_cpuinfo(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    cores = 0
    for line in text.splitlines():
        if re.match(r"^processor\s*:\s*\d+", line, re.IGNORECASE):
            cores += 1
    name = _parse_cpu_name(text)
    if name != _NA:
        result["model_name"] = name
    hw = _parse_cpu_hardware(text)
    if hw != _NA:
        result["hardware"] = hw
    if cores:
        result["cores"] = str(cores)
    return result


def _parse_cpu_name(cpuinfo: str) -> str:
    for field in ("model name", "Model name", "Processor", "processor"):
        for line in cpuinfo.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith(field.lower() + ":") \
               or stripped.lower().startswith(field.lower() + "\t"):
                val = line.split(":", 1)[1].strip() if ":" in line else ""
                if val and not val.isdigit():
                    return val
    return _NA


def _parse_cpu_hardware(cpuinfo: str) -> str:
    for line in cpuinfo.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("hardware") and ":" in stripped:
            return stripped.split(":", 1)[1].strip()
    return _NA


def _parse_meminfo(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s+(\d+)\s+kB", line)
        if m:
            result[m.group(1)] = int(m.group(2))
    return result


def _parse_df(text: str) -> dict[str, str]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {}

    def _old_style(ln: str) -> dict[str, str] | None:
        if re.search(r"\btotal\b", ln) and "," in ln:
            tm = re.search(r"([\d.]+\s*[KMGT]?B?)\s+total", ln, re.IGNORECASE)
            am = re.search(r"([\d.]+\s*[KMGT]?B?)\s+available", ln, re.IGNORECASE)
            return {
                "total":     tm.group(1).strip() if tm else _NA,
                "available": am.group(1).strip() if am else _NA,
            }
        return None

    if r := _old_style(lines[0]):
        return r

    header = lines[0]
    data_line = next((ln for ln in lines[1:] if "/data" in ln), None)
    if data_line is None:
        data_line = lines[1] if len(lines) > 1 else ""
    if not data_line:
        return {}

    if r := _old_style(data_line):
        return r

    parts = data_line.split()
    if len(parts) < 4:
        return {}

    if re.match(r"^[\d.]+[KMGTkmgt]", parts[1]):
        return {
            "total":     parts[1],
            "available": parts[3] if len(parts) > 3 else _NA,
        }

    try:
        is_512 = "512" in header
        total_kib = int(parts[1]) // 2 if is_512 else int(parts[1])
        avail_kib = int(parts[3]) // 2 if is_512 else int(parts[3])
        return {"total": _kib_to_human(total_kib), "available": _kib_to_human(avail_kib)}
    except (ValueError, IndexError):
        return {}


def _parse_battery(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([\w ]+?):\s*(.+)", line)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            result[key] = m.group(2).strip()
    return result


def _parse_display(text: str) -> dict[str, str]:
    result: dict[str, str] = {}

    m = re.search(r"\breal\s+(\d+)\s+x\s+(\d+)", text)
    if m:
        result["resolution"] = f"{m.group(1)} x {m.group(2)}"
    else:
        wm = re.search(r"\bwidth=(\d+)", text)
        hm = re.search(r"\bheight=(\d+)", text)
        if wm and hm:
            result["resolution"] = f"{wm.group(1)} x {hm.group(1)}"
        else:
            m2 = re.search(r"\b(\d{3,4})\s+x\s+(\d{3,5})\b", text)
            if m2:
                result["resolution"] = f"{m2.group(1)} x {m2.group(2)}"

    for pat in (
        r"refreshRate=([\d.]+)",
        r"\bfps=([\d.]+)",
        r"refresh rate[:\s]+([\d.]+)",
    ):
        rm = re.search(pat, text, re.IGNORECASE)
        if rm:
            try:
                result["refresh_rate"] = f"{float(rm.group(1)):.0f} Hz"
            except ValueError:
                pass
            break

    return result


def _parse_surfaceflinger(text: str) -> dict[str, str]:
    m = re.search(r"GLES:\s*(.+)", text)
    if not m:
        return {}
    parts = m.group(1).split(", ", 2)
    return {
        "vendor":   parts[0].strip() if len(parts) > 0 else _NA,
        "renderer": parts[1].strip() if len(parts) > 1 else _NA,
        "version":  parts[2].strip() if len(parts) > 2 else _NA,
    }


def _parse_ip_addr(text: str) -> str:
    m = re.search(r"inet\s+([\d.]+)/", text)
    return m.group(1) if m else ""


def _parse_ip_link(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("link/ether"):
            parts = stripped.split()
            if len(parts) >= 2 and re.match(r"^[0-9a-fA-F:]{17}$", parts[1]):
                return parts[1]
    return ""


def _parse_mac_file(text: str) -> str:
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    return line if re.match(r"^[0-9a-fA-F:]{17}$", line) else ""


def _make_value_label(text: str = _DASH, parent: Optional[QWidget] = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setTextInteractionFlags(_SEL)
    lbl.setWordWrap(True)
    lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return lbl
