"""Long-lived ADB-related processes.

Spec §5.2. Terminal PTY, scrcpy, logcat export. SIGTERM-then-SIGKILL stop
(3 s grace). Stdout streamed to listeners via Qt signal.
"""
from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, Signal

from .logger import get_logger

_log = get_logger(__name__)

_TERM_GRACE_S = 3.0
_READ_CHUNK = 4096


class ProcessState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ManagedProcess:
    id: str
    process: subprocess.Popen
    start_time: float
    state: ProcessState


class ProcessManager(QObject):
    """Owns long-lived child processes (§5.2)."""

    processStarted = Signal(str)
    processStopped = Signal(str, int)
    processOutput = Signal(str, bytes)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._procs: dict[str, ManagedProcess] = {}
        self._lock = threading.Lock()
        self._reader_threads: dict[str, threading.Thread] = {}

    def start(
        self,
        id: str,
        args: list,
        env: Optional[dict] = None,
    ) -> bool:
        """Spawn a managed process. Returns False if ``id`` already exists or
        spawn fails."""
        with self._lock:
            if id in self._procs:
                _log.warning("process id collision: %s", id)
                return False
        try:
            popen = subprocess.Popen(
                list(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                env=env,
                bufsize=0,
            )
        except OSError as exc:
            _log.error("process spawn failed id=%s err=%s", id, exc)
            return False

        managed = ManagedProcess(
            id=id, process=popen, start_time=time.time(), state=ProcessState.RUNNING
        )
        with self._lock:
            self._procs[id] = managed

        reader = threading.Thread(
            target=self._read_loop, args=(id,), name=f"proc-read-{id}", daemon=True
        )
        self._reader_threads[id] = reader
        reader.start()

        _log.info("process started id=%s argv=%s", id, args)
        self.processStarted.emit(id)
        return True

    def write(self, id: str, data: bytes) -> bool:
        """Forward ``data`` to the process stdin. Returns False if not running."""
        with self._lock:
            managed = self._procs.get(id)
        if managed is None or managed.process.stdin is None:
            return False
        try:
            managed.process.stdin.write(data)
            managed.process.stdin.flush()
            return True
        except OSError:
            return False

    def stop(self, id: str) -> None:
        """SIGTERM then SIGKILL after 3 s grace."""
        with self._lock:
            managed = self._procs.get(id)
        if managed is None:
            return
        managed.state = ProcessState.STOPPING
        proc = managed.process
        if proc.poll() is not None:
            self._finalize(id, proc.returncode if proc.returncode is not None else 0)
            return
        try:
            proc.terminate()
        except OSError:
            pass

        def _kill_after_grace() -> None:
            time.sleep(_TERM_GRACE_S)
            if proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass

        threading.Thread(
            target=_kill_after_grace, name=f"proc-kill-{id}", daemon=True
        ).start()

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self._procs.keys())
        for pid in ids:
            self.stop(pid)

    def is_running(self, id: str) -> bool:
        with self._lock:
            managed = self._procs.get(id)
        if managed is None:
            return False
        return managed.process.poll() is None

    def _read_loop(self, id: str) -> None:
        with self._lock:
            managed = self._procs.get(id)
        if managed is None:
            return
        proc = managed.process
        stdout = proc.stdout
        if stdout is None:
            proc.wait()
            self._finalize(id, proc.returncode if proc.returncode is not None else 0)
            return
        try:
            while True:
                chunk = stdout.read(_READ_CHUNK)
                if not chunk:
                    break
                self.processOutput.emit(id, chunk)
        except (OSError, ValueError):
            pass
        rc = proc.wait()
        self._finalize(id, rc if rc is not None else 0)

    def _finalize(self, id: str, returncode: int) -> None:
        with self._lock:
            managed = self._procs.pop(id, None)
            self._reader_threads.pop(id, None)
        if managed is not None:
            managed.state = ProcessState.STOPPED
        _log.info("process stopped id=%s rc=%s", id, returncode)
        self.processStopped.emit(id, returncode)
