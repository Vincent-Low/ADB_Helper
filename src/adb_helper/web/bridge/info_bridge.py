"""InfoBridge — Device Info (Spec §3.6) fetch + parse.

Reuses parsers from modules/device_info.py so we don't duplicate the
regex zoo. Bridge fans out 14 shell commands in parallel and emits one
``finished`` signal carrying the flat field map keyed by canonical
field name (the strings.* constants).
"""
from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Signal, Slot

from ...core import strings
from ...core.adb_service import AdbService
from ...core.command_runner import Priority
from .base import BridgeBase

from ...core.device_info_parsers import (
    BATTERY_HEALTH as _BATTERY_HEALTH,
    BATTERY_STATUS as _BATTERY_STATUS,
    FETCH_ROLES as _FETCH_ROLES,
    NA as _NA,
    SECTIONS as _SECTIONS,
    khz_to_mhz as _khz_to_mhz,
    kib_to_human as _kib_to_human,
    parse_battery as _parse_battery,
    parse_cpuinfo as _parse_cpuinfo,
    parse_df_human as _parse_df,
    parse_display as _parse_display,
    parse_getprop as _parse_getprop,
    parse_ip_addr as _parse_ip_addr,
    parse_ip_link as _parse_ip_link,
    parse_mac_file as _parse_mac_file,
    parse_meminfo as _parse_meminfo,
    parse_surfaceflinger as _parse_surfaceflinger,
)

_TIMEOUT = 30


def _build_fields(serial: str, results: Dict[str, str]) -> Dict[str, str]:
    """Apply the same population logic as DeviceInfoModule._populate_all."""
    import re
    S = strings
    props = _parse_getprop(results.get("getprop", ""))
    out: Dict[str, str] = {}

    out[S.DI_FIELD_MANUFACTURER] = props.get("ro.product.manufacturer", _NA)
    out[S.DI_FIELD_MODEL]        = props.get("ro.product.model", _NA)
    out[S.DI_FIELD_CODENAME]     = props.get("ro.product.device", _NA)
    out[S.DI_FIELD_BRAND]        = props.get("ro.product.brand", _NA)
    out[S.DI_FIELD_SERIAL]       = serial or _NA

    out[S.DI_FIELD_ANDROID_VERSION]   = props.get("ro.build.version.release", _NA)
    out[S.DI_FIELD_API_LEVEL]         = props.get("ro.build.version.sdk", _NA)
    out[S.DI_FIELD_SECURITY_PATCH]    = props.get("ro.build.version.security_patch", _NA)
    out[S.DI_FIELD_BUILD_NUMBER]      = props.get("ro.build.display.id", _NA)
    out[S.DI_FIELD_BUILD_FINGERPRINT] = props.get("ro.build.fingerprint", _NA)
    out[S.DI_FIELD_BUILD_TYPE]        = props.get("ro.build.type", _NA)
    out[S.DI_FIELD_BUILD_DATE]        = props.get("ro.build.date", _NA)
    out[S.DI_FIELD_BOOTLOADER]        = props.get("ro.bootloader", _NA)
    out[S.DI_FIELD_BASEBAND]          = props.get("gsm.version.baseband") or _NA

    cpu = _parse_cpuinfo(results.get("cpuinfo", ""))
    out[S.DI_FIELD_CPU_HARDWARE] = cpu.get("hardware", _NA)
    out[S.DI_FIELD_CPU_MODEL]    = cpu.get("model_name", _NA)
    out[S.DI_FIELD_CPU_ARCH]     = props.get("ro.product.cpu.abi", _NA)
    out[S.DI_FIELD_CPU_CORES]    = cpu.get("cores", _NA)
    out[S.DI_FIELD_CPU_GOVERNOR] = results.get("cpu_gov", "").strip() or _NA
    cpu_min = _khz_to_mhz(results.get("cpu_min", ""))
    cpu_max = _khz_to_mhz(results.get("cpu_max", ""))
    out[S.DI_FIELD_CPU_FREQ] = (f"{cpu_min} / {cpu_max}"
                                if cpu_min != _NA and cpu_max != _NA else _NA)

    gpu = _parse_surfaceflinger(results.get("surfaceflinger", ""))
    out[S.DI_FIELD_GPU_VENDOR]     = gpu.get("vendor", _NA)
    out[S.DI_FIELD_GPU_RENDERER]   = gpu.get("renderer", _NA)
    out[S.DI_FIELD_OPENGL_VERSION] = gpu.get("version", _NA)

    mem = _parse_meminfo(results.get("meminfo", ""))
    out[S.DI_FIELD_RAM_TOTAL]     = _kib_to_human(mem["MemTotal"])     if "MemTotal"     in mem else _NA
    out[S.DI_FIELD_RAM_AVAILABLE] = _kib_to_human(mem["MemAvailable"]) if "MemAvailable" in mem else _NA
    out[S.DI_FIELD_SWAP_TOTAL]    = _kib_to_human(mem["SwapTotal"])    if "SwapTotal"    in mem else _NA

    stor = _parse_df(results.get("df_data", ""))
    out[S.DI_FIELD_STORAGE_TOTAL]     = stor.get("total", _NA)
    out[S.DI_FIELD_STORAGE_AVAILABLE] = stor.get("available", _NA)

    disp = _parse_display(results.get("display", ""))
    out[S.DI_FIELD_RESOLUTION] = disp.get("resolution", _NA)
    dm = re.search(r"density[:\s]+(\d+)", results.get("wm_density", ""))
    out[S.DI_FIELD_DENSITY] = dm.group(1) if dm else _NA
    out[S.DI_FIELD_REFRESH_RATE] = disp.get("refresh_rate", _NA)

    bat = _parse_battery(results.get("battery", ""))
    level = bat.get("level", "")
    out[S.DI_FIELD_BATTERY_LEVEL]   = f"{level}%" if level else _NA
    out[S.DI_FIELD_BATTERY_STATUS]  = _BATTERY_STATUS.get(bat.get("status", ""),
                                                         bat.get("status") or _NA)
    out[S.DI_FIELD_BATTERY_HEALTH]  = _BATTERY_HEALTH.get(bat.get("health", ""),
                                                         bat.get("health") or _NA)
    temp_raw = bat.get("temperature", "")
    try:
        out[S.DI_FIELD_BATTERY_TEMP] = f"{int(temp_raw) / 10:.1f}°C" if temp_raw else _NA
    except ValueError:
        out[S.DI_FIELD_BATTERY_TEMP] = _NA
    out[S.DI_FIELD_BATTERY_TECH] = bat.get("technology") or _NA
    voltage = bat.get("voltage", "")
    out[S.DI_FIELD_BATTERY_VOLTAGE] = f"{voltage} mV" if voltage else _NA

    out[S.DI_FIELD_WIFI_IP] = _parse_ip_addr(results.get("ip_addr", "")) or _NA
    wifi_mac = (_parse_ip_link(results.get("ip_link", ""))
                or _parse_mac_file(results.get("wlan_mac_file", "")))
    out[S.DI_FIELD_WIFI_MAC] = wifi_mac or _NA
    bt_raw = results.get("bt_addr", "").strip()
    out[S.DI_FIELD_BT_MAC] = bt_raw if bt_raw and bt_raw != "null" else _NA
    out[S.DI_FIELD_IMEI] = strings.DI_VALUE_IMEI_NA

    lang = (props.get("ro.product.locale") or props.get("persist.sys.locale") or _NA)
    out[S.DI_FIELD_LANGUAGE] = lang
    out[S.DI_FIELD_TIMEZONE] = props.get("persist.sys.timezone") or _NA
    return out


def _sections_layout() -> List[Dict[str, Any]]:
    return [{"title": title, "fields": list(fields)} for title, fields in _SECTIONS]


class InfoBridge(BridgeBase):
    fetchStarted = Signal()
    fetchFinished = Signal("QVariant")  # {serial, fields, sections}
    fetchProgress = Signal(int, int)    # done, total

    def __init__(self, adb: AdbService) -> None:
        super().__init__()
        self._adb = adb
        self._pending: dict[str, str] = {}   # cmd_id → role
        self._results: dict[str, str] = {}
        self._target_serial: str = ""
        self._total: int = 0

        adb.commands.commandFinished.connect(self._on_finished)
        adb.commands.commandFailed.connect(self._on_failed)

    @Slot(result="QVariant")
    def sections(self) -> List[Dict[str, Any]]:
        return _sections_layout()

    @Slot(str)
    def fetch(self, serial: str) -> None:
        if not serial:
            return
        # Cancel anything in-flight.
        for cid in list(self._pending):
            self._adb.commands.cancel(cid)
        self._pending.clear()
        self._results.clear()
        self._target_serial = serial
        self._total = len(_FETCH_ROLES)
        self.fetchStarted.emit()
        for role, args in _FETCH_ROLES.items():
            cid = self._adb.commands.submit(serial, args, _TIMEOUT, Priority.NORMAL)
            self._pending[cid] = role
        self.fetchProgress.emit(0, self._total)

    def _on_finished(self, cmd_id: str, result: Any) -> None:
        role = self._pending.pop(cmd_id, None)
        if role is None:
            return
        self._results[role] = result.stdout
        self.fetchProgress.emit(self._total - len(self._pending), self._total)
        if not self._pending:
            self._emit_done()

    def _on_failed(self, cmd_id: str, result: Any) -> None:
        if self._pending.pop(cmd_id, None) is None:
            return
        self.fetchProgress.emit(self._total - len(self._pending), self._total)
        if not self._pending:
            self._emit_done()

    def _emit_done(self) -> None:
        fields = _build_fields(self._target_serial, self._results)
        self.fetchFinished.emit({
            "serial": self._target_serial,
            "fields": fields,
            "sections": _sections_layout(),
        })


__all__ = ["InfoBridge"]
