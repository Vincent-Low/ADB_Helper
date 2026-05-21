"""Pure parsers for the Device Info module (Spec §3.6).

Lives in `core/` (no Qt imports) so both Vue/QWebChannel bridges and any
future test harness can consume them without dragging in PySide6 widgets.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from . import strings

NA = "N/A"

BATTERY_STATUS: Dict[str, str] = {
    "1": "Unknown",
    "2": "Charging",
    "3": "Discharging",
    "4": "Not charging",
    "5": "Full",
}

BATTERY_HEALTH: Dict[str, str] = {
    "1": "Unknown",
    "2": "Good",
    "3": "Overheat",
    "4": "Dead",
    "5": "Over voltage",
    "6": "Unspecified failure",
    "7": "Cold",
}

# role -> adb argv
FETCH_ROLES: Dict[str, List[str]] = {
    "getprop": ["shell", "getprop"],
    "cpuinfo": ["shell", "cat /proc/cpuinfo"],
    "meminfo": ["shell", "cat /proc/meminfo"],
    "df_data": ["shell", "df /data"],
    "wm_density": ["shell", "wm density"],
    "battery": ["shell", "dumpsys battery"],
    "display": ["shell", "dumpsys display"],
    "surfaceflinger": ["shell", "dumpsys SurfaceFlinger"],
    "ip_addr": ["shell", "ip addr show wlan0"],
    "ip_link": ["shell", "ip link show wlan0"],
    "wlan_mac_file": ["shell", "cat /sys/class/net/wlan0/address"],
    "bt_addr": ["shell", "settings get secure bluetooth_address"],
    "cpu_gov": ["shell", "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"],
    "cpu_min": ["shell", "cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq"],
    "cpu_max": ["shell", "cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"],
}

SECTIONS: List[Tuple[str, List[str]]] = [
    (strings.DI_SEC_DEVICE, [
        strings.DI_FIELD_MANUFACTURER, strings.DI_FIELD_MODEL,
        strings.DI_FIELD_CODENAME, strings.DI_FIELD_BRAND,
        strings.DI_FIELD_SERIAL,
    ]),
    (strings.DI_SEC_SYSTEM, [
        strings.DI_FIELD_ANDROID_VERSION, strings.DI_FIELD_API_LEVEL,
        strings.DI_FIELD_SECURITY_PATCH, strings.DI_FIELD_BUILD_NUMBER,
        strings.DI_FIELD_BUILD_FINGERPRINT, strings.DI_FIELD_BUILD_TYPE,
        strings.DI_FIELD_BUILD_DATE, strings.DI_FIELD_BOOTLOADER,
        strings.DI_FIELD_BASEBAND,
    ]),
    (strings.DI_SEC_CPU, [
        strings.DI_FIELD_CPU_HARDWARE, strings.DI_FIELD_CPU_MODEL,
        strings.DI_FIELD_CPU_ARCH, strings.DI_FIELD_CPU_CORES,
        strings.DI_FIELD_CPU_GOVERNOR, strings.DI_FIELD_CPU_FREQ,
    ]),
    (strings.DI_SEC_GPU, [
        strings.DI_FIELD_GPU_VENDOR, strings.DI_FIELD_GPU_RENDERER,
        strings.DI_FIELD_OPENGL_VERSION,
    ]),
    (strings.DI_SEC_MEMORY, [
        strings.DI_FIELD_RAM_TOTAL, strings.DI_FIELD_RAM_AVAILABLE,
        strings.DI_FIELD_SWAP_TOTAL,
    ]),
    (strings.DI_SEC_STORAGE, [
        strings.DI_FIELD_STORAGE_TOTAL, strings.DI_FIELD_STORAGE_AVAILABLE,
    ]),
    (strings.DI_SEC_DISPLAY, [
        strings.DI_FIELD_RESOLUTION, strings.DI_FIELD_DENSITY,
        strings.DI_FIELD_REFRESH_RATE,
    ]),
    (strings.DI_SEC_BATTERY, [
        strings.DI_FIELD_BATTERY_LEVEL, strings.DI_FIELD_BATTERY_STATUS,
        strings.DI_FIELD_BATTERY_HEALTH, strings.DI_FIELD_BATTERY_TEMP,
        strings.DI_FIELD_BATTERY_TECH, strings.DI_FIELD_BATTERY_VOLTAGE,
    ]),
    (strings.DI_SEC_NETWORK, [
        strings.DI_FIELD_WIFI_IP, strings.DI_FIELD_WIFI_MAC,
        strings.DI_FIELD_BT_MAC, strings.DI_FIELD_IMEI,
    ]),
    (strings.DI_SEC_LOCALE, [
        strings.DI_FIELD_LANGUAGE, strings.DI_FIELD_TIMEZONE,
    ]),
]


def kib_to_human(kib: int) -> str:
    if kib >= 1024 * 1024:
        return f"{kib / (1024 * 1024):.1f} GB"
    if kib >= 1024:
        return f"{kib // 1024} MB"
    return f"{kib} KB"


def khz_to_mhz(raw: str) -> str:
    try:
        return f"{int(raw.strip()) // 1000} MHz"
    except (ValueError, AttributeError):
        return NA


def parse_getprop(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\[(.+?)\]:\s*\[(.*?)\]\s*$", line)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def parse_cpuinfo(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    cores = 0
    for line in text.splitlines():
        if re.match(r"^processor\s*:\s*\d+", line, re.IGNORECASE):
            cores += 1
    name = _parse_cpu_name(text)
    if name != NA:
        result["model_name"] = name
    hw = _parse_cpu_hardware(text)
    if hw != NA:
        result["hardware"] = hw
    if cores:
        result["cores"] = str(cores)
    return result


def _parse_cpu_name(cpuinfo: str) -> str:
    for field in ("model name", "Model name", "Processor", "processor"):
        for line in cpuinfo.splitlines():
            stripped = line.strip()
            if (stripped.lower().startswith(field.lower() + ":")
                    or stripped.lower().startswith(field.lower() + "\t")):
                val = line.split(":", 1)[1].strip() if ":" in line else ""
                if val and not val.isdigit():
                    return val
    return NA


def _parse_cpu_hardware(cpuinfo: str) -> str:
    for line in cpuinfo.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("hardware") and ":" in stripped:
            return stripped.split(":", 1)[1].strip()
    return NA


def parse_meminfo(text: str) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s+(\d+)\s+kB", line)
        if m:
            result[m.group(1)] = int(m.group(2))
    return result


def parse_df_human(text: str) -> Dict[str, str]:
    """Return ``{"total": "...", "available": "..."}`` strings for display."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {}

    def _old(ln: str) -> Dict[str, str] | None:
        if re.search(r"\btotal\b", ln) and "," in ln:
            tm = re.search(r"([\d.]+\s*[KMGT]?B?)\s+total", ln, re.IGNORECASE)
            am = re.search(r"([\d.]+\s*[KMGT]?B?)\s+available", ln, re.IGNORECASE)
            return {
                "total":     tm.group(1).strip() if tm else NA,
                "available": am.group(1).strip() if am else NA,
            }
        return None

    if (r := _old(lines[0])):
        return r

    header = lines[0]
    data_line = next((ln for ln in lines[1:] if "/data" in ln), None)
    if data_line is None and len(lines) > 1:
        data_line = lines[1]
    if not data_line:
        return {}
    if (r := _old(data_line)):
        return r

    parts = data_line.split()
    if len(parts) < 4:
        return {}
    if re.match(r"^[\d.]+[KMGTkmgt]", parts[1]):
        return {"total": parts[1], "available": parts[3] if len(parts) > 3 else NA}
    try:
        is_512 = "512" in header
        total_kib = int(parts[1]) // 2 if is_512 else int(parts[1])
        avail_kib = int(parts[3]) // 2 if is_512 else int(parts[3])
        return {"total": kib_to_human(total_kib), "available": kib_to_human(avail_kib)}
    except (ValueError, IndexError):
        return {}


def parse_battery(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([\w ]+?):\s*(.+)", line)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            result[key] = m.group(2).strip()
    return result


def parse_display(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
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


def parse_surfaceflinger(text: str) -> Dict[str, str]:
    m = re.search(r"GLES:\s*(.+)", text)
    if not m:
        return {}
    parts = m.group(1).split(", ", 2)
    return {
        "vendor":   parts[0].strip() if len(parts) > 0 else NA,
        "renderer": parts[1].strip() if len(parts) > 1 else NA,
        "version":  parts[2].strip() if len(parts) > 2 else NA,
    }


def parse_ip_addr(text: str) -> str:
    m = re.search(r"inet\s+([\d.]+)/", text)
    return m.group(1) if m else ""


def parse_ip_link(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("link/ether"):
            parts = stripped.split()
            if len(parts) >= 2 and re.match(r"^[0-9a-fA-F:]{17}$", parts[1]):
                return parts[1]
    return ""


def parse_mac_file(text: str) -> str:
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    return line if re.match(r"^[0-9a-fA-F:]{17}$", line) else ""


__all__ = [
    "NA",
    "BATTERY_STATUS", "BATTERY_HEALTH",
    "FETCH_ROLES", "SECTIONS",
    "kib_to_human", "khz_to_mhz",
    "parse_getprop", "parse_cpuinfo",
    "parse_meminfo", "parse_df_human",
    "parse_battery", "parse_display",
    "parse_surfaceflinger",
    "parse_ip_addr", "parse_ip_link", "parse_mac_file",
]
