"""Bridge base class + JSON-safe conversion helper.

QWebChannel transports only QVariant-compatible primitives.  Dataclasses
(DeviceContext, AdbResult, …) must be flattened before they cross the
bridge — ``to_jsonable()`` is the single point of truth for that.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import PurePath
from typing import Any

from PySide6.QtCore import QObject


def to_jsonable(obj: Any, _seen: set[int] | None = None) -> Any:
    """Recursively convert any value into a JSON-/QVariant-safe form.

    - bytes / bytearray → base64-encoded ASCII string
    - Enum → underlying ``.value``
    - dataclass → flat dict
    - Path-like → str
    - cycles → ``None`` (instead of RecursionError)
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(obj)).decode("ascii")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, PurePath):
        return str(obj)

    seen = _seen if _seen is not None else set()
    oid = id(obj)
    if oid in seen:
        return None  # cycle break
    seen.add(oid)

    if is_dataclass(obj):
        return {k: to_jsonable(v, seen) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v, seen) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_jsonable(x, seen) for x in obj]
    return str(obj)


class BridgeBase(QObject):
    """Marker base for all QWebChannel bridges.

    Subclasses register slots/signals and own the Python-side translation
    of Qt service signals into Vue-facing payloads.
    """


__all__ = ["BridgeBase", "to_jsonable"]
