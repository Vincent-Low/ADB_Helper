"""Pure parsers for the Apps module (Spec §3.7).

Lives in `core/` so the QWebChannel bridge can consume them without
pulling in PySide6.QtWidgets via the legacy `modules/` package.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

# `pm get-packages-property` enable codes treated as "disabled" — see
# AOSP PackageManager.COMPONENT_ENABLED_STATE_DISABLED constants.
_DISABLED_ENABLED_CODES = {"2", "3", "4"}


def parse_pm_list(text: str) -> List[Tuple[str, str]]:
    """Parse ``pm list packages -f`` into ``[(apk_path, package), ...]``."""
    out: List[Tuple[str, str]] = []
    pat = re.compile(r"^package:(.+\.apk)=(.+?)\s*$")
    for line in text.splitlines():
        m = pat.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def parse_pm_dump(text: str) -> Tuple[str, Optional[bool]]:
    """Extract ``(label, disabled)`` from grep'd ``pm dump`` output."""
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


def parse_meminfo(text: str) -> dict[str, int]:
    """``/proc/meminfo`` → {key: KiB}."""
    result: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s+(\d+)\s+kB", line)
        if m:
            result[m.group(1)] = int(m.group(2))
    return result


def parse_df(text: str) -> Tuple[int, int]:
    """Return ``(used_kib, total_kib)``.

    NOTE order is `(used, total)` — convenient for the storage meter
    which displays "used / total".  The legacy module had this swapped
    relative to its caller; we fix it here permanently.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0, 0

    # Old Android single-line: "/data: 52.0G total, 46.5G used, 5.5G available"
    if "," in lines[0] and "total" in lines[0]:
        tm = re.search(r"([\d.]+)\s*([KMGT]?)B?\s+total", lines[0], re.IGNORECASE)
        um = re.search(r"([\d.]+)\s*([KMGT]?)B?\s+used",  lines[0], re.IGNORECASE)
        total_kib = _to_kib(tm.group(1), tm.group(2)) if tm else 0
        used_kib  = _to_kib(um.group(1), um.group(2)) if um else 0
        return used_kib, total_kib

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
        used_kib  = _human_to_kib(parts[2]) if len(parts) > 2 else 0
        return used_kib, total_kib
    try:
        is_512 = "512" in header
        total = int(parts[1])
        used  = int(parts[2])
        total_kib = total // 2 if is_512 else total
        used_kib  = used  // 2 if is_512 else used
        return used_kib, total_kib
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


__all__ = ["parse_pm_list", "parse_pm_dump", "parse_meminfo", "parse_df"]
