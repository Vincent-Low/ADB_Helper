"""Installer sequential-queue tests.

Exercises InstallerBridge against a mock AdbService that captures
``run_command`` calls without actually running anything.  Verifies that:
  - file × device pairs are queued
  - at most ONE job runs per device at any time
  - finishing a job dequeues the next for that device
  - unknown serials are filtered
"""
from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from typing import Any, Callable, List

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QObject, Signal, QCoreApplication

from adb_helper.web.bridge.installer_bridge import InstallerBridge
from adb_helper.core.device_context import DeviceContext


@dataclass
class FakeResult:
    id: str
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    status: str = "succeeded"


class _FakeCommands(QObject):
    commandStarted = Signal(str)
    commandFinished = Signal(str, object)
    commandFailed = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self.calls: List[dict] = []

    def submit(self, serial, args, timeout, priority):
        # Match real CommandRunner shape — InstallerBridge calls run_command
        # which forwards to commands.submit.  But our InstallerBridge calls
        # adb.run_command directly; we intercept there instead.
        raise AssertionError("FakeCommands.submit should not be called")

    def cancel(self, cmd_id):
        self.calls.append({"op": "cancel", "id": cmd_id})


class _FakeDevices:
    def __init__(self, ctxs):
        self._ctxs = ctxs

    def known_devices(self):
        return list(self._ctxs)


class _FakeAdb(QObject):
    def __init__(self, known_serials: List[str]) -> None:
        super().__init__()
        self.commands = _FakeCommands()
        ctxs = [
            DeviceContext(s, "Pixel", "Google", "33", "arm64-v8a", "usb", "online")
            for s in known_serials
        ]
        self.devices = _FakeDevices(ctxs)
        self.run_calls: List[dict] = []

    def run_command(self, serial, args, timeout=30):
        cid = f"cmd-{len(self.run_calls)}-{uuid.uuid4().hex[:6]}"
        self.run_calls.append({"cmd_id": cid, "serial": serial, "args": list(args)})
        return cid


@pytest.fixture
def qapp():
    # InstallerBridge uses QTimer (watchdog) — needs a QCoreApplication.
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    yield app


def test_sequential_one_per_device(qapp):
    adb = _FakeAdb(known_serials=["A", "B"])
    bridge = InstallerBridge(adb)

    # 2 files × 2 devices = 4 pairs, but only 2 should run concurrently
    # (one per device).  After install on A finishes, the next A-file
    # should dispatch.
    plan = bridge.installFiles(["f1.apk", "f2.apk"], ["A", "B"])
    assert len(plan) == 4

    # Initially 2 in-flight (one per device).
    assert len(adb.run_calls) == 2
    serials_in_flight = {c["serial"] for c in adb.run_calls}
    assert serials_in_flight == {"A", "B"}

    # Finish A's first job — second A-file should now dispatch.
    first_a = next(c for c in adb.run_calls if c["serial"] == "A")
    adb.commands.commandFinished.emit(
        first_a["cmd_id"], FakeResult(id=first_a["cmd_id"]),
    )
    assert len(adb.run_calls) == 3
    assert adb.run_calls[-1]["serial"] == "A"


def test_unknown_serials_filtered(qapp):
    adb = _FakeAdb(known_serials=["A"])
    bridge = InstallerBridge(adb)

    plan = bridge.installFiles(["f.apk"], ["A", "GHOST"])
    assert len(plan) == 1
    assert plan[0]["serial"] == "A"
    assert len(adb.run_calls) == 1


def test_empty_when_no_known(qapp):
    adb = _FakeAdb(known_serials=["A"])
    bridge = InstallerBridge(adb)
    plan = bridge.installFiles(["f.apk"], ["GHOST"])
    assert plan == []
    assert adb.run_calls == []
