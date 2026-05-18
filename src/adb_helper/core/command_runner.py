"""One-shot ADB commands.

Spec §5.1. PriorityQueue-fed worker pool (4 threads). HIGH dequeues before
NORMAL. Subprocess kill on timeout. PIN-mask logging via logger filter.
"""
from __future__ import annotations

import itertools
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from queue import Empty, PriorityQueue
from typing import Optional, Tuple

from PySide6.QtCore import QObject, Signal

from . import paths, platform as _platform
from .logger import get_logger

_WORKERS = 4
_DISPATCH_POLL_S = 0.1

_log = get_logger(__name__)


class Priority(IntEnum):
    HIGH = 0
    NORMAL = 1


@dataclass(frozen=True)
class AdbCommand:
    id: str
    serial: Optional[str]
    args: list
    timeout: int
    priority: Priority


@dataclass(frozen=True)
class AdbResult:
    id: str
    stdout: str
    stderr: str
    returncode: int
    status: str  # "succeeded" | "failed" | "timed_out" | "cancelled"


def resolve_adb_binary() -> str:
    """Return adb binary path. Bundled platform-tools wins; falls back to PATH."""
    name = "adb.exe" if _platform.IS_WINDOWS else "adb"
    bundled = paths.platform_tools_dir() / name
    if bundled.exists():
        return str(bundled)
    found = shutil.which("adb")
    return found if found else "adb"


class CommandRunner(QObject):
    """Thread-pooled one-shot ADB command runner (§5.1).

    Internal queue is a :class:`queue.PriorityQueue` so HIGH-priority items
    always dequeue before NORMAL. Four worker threads pull commands and run
    them via :mod:`subprocess`. On timeout the child process is killed and
    the command is reported as ``timed_out``.
    """

    commandStarted = Signal(str)
    commandFinished = Signal(str, object)
    commandFailed = Signal(str, object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._queue: "PriorityQueue[Tuple[int, int, AdbCommand]]" = PriorityQueue()
        self._counter = itertools.count()
        self._cancelled: set[str] = set()
        self._running: dict[str, subprocess.Popen] = {}
        self._running_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(
            max_workers=_WORKERS, thread_name_prefix="adb-cmd"
        )
        self._workers: list = []
        for _ in range(_WORKERS):
            fut = self._executor.submit(self._worker_loop)
            self._workers.append(fut)

    # --- public API ------------------------------------------------------
    def run(self, command: AdbCommand) -> str:
        """Enqueue ``command``. Returns the command id."""
        seq = next(self._counter)
        self._queue.put((int(command.priority), seq, command))
        _log.debug(
            "queued command id=%s serial=%s priority=%s args=%s",
            command.id, command.serial, command.priority.name, command.args,
        )
        return command.id

    def submit(
        self,
        serial: Optional[str],
        args: list,
        timeout: int,
        priority: Priority = Priority.NORMAL,
    ) -> str:
        """Convenience: build an :class:`AdbCommand` and enqueue."""
        cmd = AdbCommand(
            id=str(uuid.uuid4()),
            serial=serial,
            args=list(args),
            timeout=int(timeout),
            priority=priority,
        )
        return self.run(cmd)

    def cancel(self, command_id: str) -> None:
        """Cancel a queued or running command."""
        self._cancelled.add(command_id)
        with self._running_lock:
            proc = self._running.get(command_id)
        if proc is not None:
            try:
                proc.kill()
            except OSError:
                pass

    def shutdown(self, wait: bool = True) -> None:
        self._stop_event.set()
        with self._running_lock:
            procs = list(self._running.values())
        for p in procs:
            try:
                p.kill()
            except OSError:
                pass
        self._executor.shutdown(wait=wait)

    # --- worker ----------------------------------------------------------
    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                _prio, _seq, cmd = self._queue.get(timeout=_DISPATCH_POLL_S)
            except Empty:
                continue
            if cmd.id in self._cancelled:
                self._cancelled.discard(cmd.id)
                self.commandFailed.emit(
                    cmd.id,
                    AdbResult(cmd.id, "", "", -1, "cancelled"),
                )
                self._queue.task_done()
                continue
            self._execute(cmd)
            self._queue.task_done()

    def _execute(self, cmd: AdbCommand) -> None:
        adb = resolve_adb_binary()
        argv = [adb]
        if cmd.serial:
            argv += ["-s", cmd.serial]
        argv += list(cmd.args)

        self.commandStarted.emit(cmd.id)
        _log.debug("running command id=%s argv=%s", cmd.id, argv)
        start = time.monotonic()
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
        except OSError as exc:
            _log.error("failed to spawn adb id=%s err=%s", cmd.id, exc)
            self.commandFailed.emit(
                cmd.id, AdbResult(cmd.id, "", str(exc), -1, "failed")
            )
            return

        with self._running_lock:
            self._running[cmd.id] = proc

        try:
            stdout_b, stderr_b = proc.communicate(timeout=cmd.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                stdout_b, stderr_b = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                stdout_b, stderr_b = b"", b""
            result = AdbResult(
                cmd.id,
                _safe_decode(stdout_b),
                _safe_decode(stderr_b),
                -1,
                "timed_out",
            )
            _log.warning(
                "command timed out id=%s timeout=%ss elapsed=%.2fs",
                cmd.id, cmd.timeout, time.monotonic() - start,
            )
            with self._running_lock:
                self._running.pop(cmd.id, None)
            self.commandFailed.emit(cmd.id, result)
            return
        finally:
            with self._running_lock:
                self._running.pop(cmd.id, None)

        if cmd.id in self._cancelled:
            self._cancelled.discard(cmd.id)
            result = AdbResult(
                cmd.id,
                _safe_decode(stdout_b),
                _safe_decode(stderr_b),
                proc.returncode or -1,
                "cancelled",
            )
            self.commandFailed.emit(cmd.id, result)
            return

        status = "succeeded" if proc.returncode == 0 else "failed"
        result = AdbResult(
            cmd.id,
            _safe_decode(stdout_b),
            _safe_decode(stderr_b),
            proc.returncode if proc.returncode is not None else -1,
            status,
        )
        if status == "succeeded":
            self.commandFinished.emit(cmd.id, result)
        else:
            _log.info(
                "command failed id=%s rc=%s stderr=%s",
                cmd.id, proc.returncode, result.stderr.strip()[:200],
            )
            self.commandFailed.emit(cmd.id, result)


def _safe_decode(buf: bytes) -> str:
    try:
        return buf.decode("utf-8", errors="replace")
    except Exception:
        return ""
