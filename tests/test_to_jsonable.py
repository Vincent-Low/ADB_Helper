"""Unit tests for adb_helper.web.bridge.base.to_jsonable.

No Qt event loop required — to_jsonable is pure.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pytest

from adb_helper.web.bridge.base import to_jsonable


def test_primitives_pass_through():
    assert to_jsonable(None) is None
    assert to_jsonable(True) is True
    assert to_jsonable(42) == 42
    assert to_jsonable(3.14) == 3.14
    assert to_jsonable("hi") == "hi"


def test_bytes_become_base64():
    raw = b"\x89PNG\r\n\x1a\n"
    out = to_jsonable(raw)
    assert isinstance(out, str)
    assert base64.b64decode(out) == raw


def test_bytearray_and_memoryview():
    assert base64.b64decode(to_jsonable(bytearray(b"abc"))) == b"abc"
    assert base64.b64decode(to_jsonable(memoryview(b"xyz"))) == b"xyz"


def test_enum_returns_value():
    class Mode(str, Enum):
        DARK = "dark"
        LIGHT = "light"

    assert to_jsonable(Mode.DARK) == "dark"


def test_path_becomes_str():
    p = Path("/tmp/foo.txt")
    assert to_jsonable(p) == "/tmp/foo.txt"


def test_dataclass_is_flattened():
    @dataclass
    class Box:
        a: int
        b: str

    assert to_jsonable(Box(1, "x")) == {"a": 1, "b": "x"}


def test_nested_collections():
    payload = {"k": [1, (2, 3), {"deep": b"\x00"}]}
    out = to_jsonable(payload)
    assert out["k"][0] == 1
    assert out["k"][1] == [2, 3]
    assert isinstance(out["k"][2]["deep"], str)


def test_cycle_returns_none_not_recursion_error():
    a: dict = {}
    a["self"] = a
    out = to_jsonable(a)
    # Outer dict is fine, inner ref to itself becomes None.
    assert out["self"] is None


def test_unknown_type_falls_back_to_str():
    class Opaque:
        def __str__(self) -> str:
            return "opaque-repr"

    assert to_jsonable(Opaque()) == "opaque-repr"


def test_dict_keys_coerced_to_str():
    out = to_jsonable({1: "one", 2: "two"})
    assert out == {"1": "one", "2": "two"}
