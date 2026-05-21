"""InstallerBridge — drag-and-drop APK paths + sequential per-device install.

Spec §3.3: sequential — one `adb install` per device at a time. Multiple
devices may install in parallel (one job each).  The same file may not
install on the same device twice concurrently.

State machine:
- _queue : list of pending (file, serial, timeout) tuples
- _in_flight : { serial: cmd_id } — at most one job per device
- _watchdogs : { cmd_id: QTimer } — kills runaway jobs (5× timeout)
"""
from __future__ import annotations

from functools import partial
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from ...core import strings
from ...core.adb_service import AdbService
from ...core.logger import get_logger
from ..util import top_level_window
from .base import BridgeBase, to_jsonable

_log = get_logger(__name__)


class InstallerBridge(BridgeBase):
    filesDropped = Signal("QVariant")          # list[str]
    installStarted = Signal("QVariant")        # {cmd_id, file, serial}
    installFinished = Signal(str, "QVariant")  # cmd_id, AdbResult
    installFailed = Signal(str, "QVariant")
    queueDrained = Signal()

    def __init__(self, adb: AdbService) -> None:
        super().__init__()
        self._adb = adb
        # (file, serial, timeout) waiting to dispatch.
        self._queue: List[Tuple[str, str, int]] = []
        # serial -> cmd_id currently running on that device.
        self._in_flight: Dict[str, str] = {}
        # cmd_id -> {"file","serial","timeout"}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        # cmd_id -> watchdog QTimer
        self._watchdogs: Dict[str, QTimer] = {}

        adb.commands.commandStarted.connect(self._on_started)
        adb.commands.commandFinished.connect(self._on_finished)
        adb.commands.commandFailed.connect(self._on_failed)

    # invoked from AdbWebView.filesDropped via WebMainWindow.
    def on_files_dropped(self, paths: List[str]) -> None:
        if paths:
            self.filesDropped.emit(list(paths))

    @Slot(result="QVariant")
    def pickFiles(self) -> List[str]:
        files, _ = QFileDialog.getOpenFileNames(
            top_level_window(),
            strings.INSTALLER_TITLE_ADD,
            "",
            strings.INSTALLER_FILTER_PACKAGES,
        )
        return list(files)

    @Slot("QVariant", "QVariant", "QVariant", result="QVariant")
    def installFiles(
        self,
        files: List[str],
        serials: List[str],
        timeout: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Queue file × device pairs, sequential per device. Returns the
        intended job plan (UI uses it to seed the table before cmd_ids are
        known).  Unknown serials are silently dropped — saves the user a
        30 s timeout per bogus device."""
        t = int(timeout) if timeout else 180
        known = {d.serial for d in self._adb.devices.known_devices()}
        valid_serials = [s for s in serials if s in known]
        if not valid_serials:
            _log.warning(
                "installFiles called with no known serials (received %s)", serials,
            )
            return []
        plan: List[Dict[str, Any]] = []
        for f in files:
            for serial in valid_serials:
                self._queue.append((f, serial, t))
                plan.append({"file": f, "serial": serial})
        self._dispatch()
        return plan

    @Slot(str)
    def cancel(self, cmd_id: str) -> None:
        self._adb.commands.cancel(cmd_id)

    @Slot()
    def cancelAll(self) -> None:
        self._queue.clear()
        for cid in list(self._in_flight.values()):
            self._adb.commands.cancel(cid)

    # --- dispatcher ----------------------------------------------------
    def _dispatch(self) -> None:
        """Pick one queued job per idle device and submit it."""
        if not self._queue:
            if not self._in_flight:
                self.queueDrained.emit()
            return
        remaining: List[Tuple[str, str, int]] = []
        for entry in self._queue:
            f, serial, t = entry
            if serial in self._in_flight:
                remaining.append(entry)
                continue
            cid = self._adb.run_command(serial, ["install", "-r", f], timeout=t)
            self._in_flight[serial] = cid
            self._jobs[cid] = {"file": f, "serial": serial, "timeout": t}
            self._arm_watchdog(cid, t)
        self._queue = remaining

    def _arm_watchdog(self, cmd_id: str, timeout_s: int) -> None:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(max(timeout_s * 5, 60) * 1000)
        # Bound method via partial — no lambda closure over self.
        timer.timeout.connect(partial(self._on_watchdog, cmd_id))
        timer.start()
        self._watchdogs[cmd_id] = timer

    def _disarm_watchdog(self, cmd_id: str) -> None:
        t = self._watchdogs.pop(cmd_id, None)
        if t is not None:
            t.stop()
            t.deleteLater()

    def _on_watchdog(self, cmd_id: str) -> None:
        if cmd_id not in self._jobs:
            return
        _log.warning("installer watchdog fired for cmd_id=%s — forcing cancel", cmd_id)
        self._adb.commands.cancel(cmd_id)

    # --- service signal relays ----------------------------------------
    def _on_started(self, cid: str) -> None:
        job = self._jobs.get(cid)
        if job is not None:
            self.installStarted.emit({
                "cmd_id": cid,
                "file": job["file"],
                "serial": job["serial"],
            })

    def _on_finished(self, cid: str, result: Any) -> None:
        if cid not in self._jobs:
            return
        self._release(cid)
        self.installFinished.emit(cid, to_jsonable(result))
        self._dispatch()

    def _on_failed(self, cid: str, result: Any) -> None:
        if cid not in self._jobs:
            return
        self._release(cid)
        self.installFailed.emit(cid, to_jsonable(result))
        self._dispatch()

    def _release(self, cid: str) -> None:
        self._disarm_watchdog(cid)
        job = self._jobs.pop(cid, None)
        if job is not None:
            serial = job.get("serial")
            if serial and self._in_flight.get(serial) == cid:
                self._in_flight.pop(serial, None)


__all__ = ["InstallerBridge"]
