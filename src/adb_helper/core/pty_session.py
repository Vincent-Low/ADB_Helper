"""PtySession — Linux PTY-backed ``adb shell`` session (Spec §3.2.1, §6.2).

Spawns ``adb -s <serial> shell`` via ``os.fork() + pty.openpty()`` so the
child inherits a controlling terminal — required so ``adb shell`` runs in
interactive mode and emits ANSI sequences. The PTY master fd is read in a
``QThread``; bytes are emitted via the ``output_ready`` signal so the UI
can render them on the GUI thread.

CLAUDE.md invariant 1: this module is in ``core/`` and is the ADB I/O
boundary for the terminal — modules under ``ui/`` and ``modules/`` route
through it instead of touching ``pty``/``subprocess`` directly. CLAUDE.md
invariant 4: platform branching lives in :mod:`core.platform`; this module
consumes ``IS_LINUX`` rather than re-checking ``sys.platform``.

Windows note: ConPTY is not implemented here. ``start()`` raises on
non-Linux hosts. The full Windows path lives outside the v1.0 scope of
this file.
"""
from __future__ import annotations

import errno
import os
import signal
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from . import platform as _platform
from .command_runner import resolve_adb_binary
from .logger import get_logger

if _platform.IS_LINUX:
    import fcntl
    import pty
    import select
    import termios

_log = get_logger(__name__)

_READ_CHUNK = 4096
_SELECT_TIMEOUT_S = 0.5
_TERM_GRACE_S = 3


class _ReaderThread(QThread):
    """Reads the PTY master fd and emits chunks on the GUI thread."""

    chunk = Signal(bytes)
    finished_with_rc = Signal(int)

    def __init__(self, master_fd: int, pid: int, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._master_fd = master_fd
        self._pid = pid
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        master = self._master_fd
        try:
            while not self._stop:
                try:
                    r, _, _ = select.select([master], [], [], _SELECT_TIMEOUT_S)
                except (OSError, ValueError):
                    break
                if master not in r:
                    continue
                try:
                    data = os.read(master, _READ_CHUNK)
                except OSError as exc:
                    if exc.errno in (errno.EIO, errno.EBADF):
                        break
                    continue
                if not data:
                    break
                self.chunk.emit(data)
        finally:
            rc = self._reap()
            self.finished_with_rc.emit(rc)

    def _reap(self) -> int:
        try:
            pid, status = os.waitpid(self._pid, os.WNOHANG)
        except OSError:
            return -1
        if pid == 0:
            # Child still alive — give it a moment, then SIGTERM.
            try:
                os.kill(self._pid, signal.SIGTERM)
            except OSError:
                pass
            try:
                pid, status = os.waitpid(self._pid, 0)
            except OSError:
                return -1
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        if os.WIFSIGNALED(status):
            return -os.WTERMSIG(status)
        return -1


class PtySession(QObject):
    """Owns one ``adb shell`` PTY session for a single device serial."""

    output_ready = Signal(bytes)
    process_exited = Signal(int)

    def __init__(self, serial: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._serial = serial
        self._master_fd: Optional[int] = None
        self._pid: Optional[int] = None
        self._reader: Optional[_ReaderThread] = None
        self._closing = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> bool:
        """Fork, set up PTY, exec ``adb shell``. Returns False on failure."""
        if not _platform.IS_LINUX:
            raise RuntimeError(
                "PtySession requires Linux. Use ConPTY on Windows (not in v1.0)."
            )
        if self._pid is not None:
            return False

        adb_bin = resolve_adb_binary()
        argv: List[str] = [adb_bin, "-s", self._serial, "shell"]

        try:
            master, slave = pty.openpty()
        except OSError as exc:
            _log.error("pty.openpty failed: %s", exc)
            return False

        try:
            pid = os.fork()
        except OSError as exc:
            _log.error("os.fork failed: %s", exc)
            os.close(master)
            os.close(slave)
            return False

        if pid == 0:
            # Child: become session leader, attach slave as controlling TTY,
            # wire stdin/stdout/stderr to it, then exec adb.
            try:
                os.setsid()
                try:
                    fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
                except OSError:
                    pass
                os.dup2(slave, 0)
                os.dup2(slave, 1)
                os.dup2(slave, 2)
                if slave > 2:
                    os.close(slave)
                os.close(master)
                os.execvp(argv[0], argv)
            except Exception:  # pragma: no cover — exec failure path
                os._exit(127)
            os._exit(127)

        # Parent.
        os.close(slave)
        self._master_fd = master
        self._pid = pid
        _log.info(
            "pty session started serial=%s pid=%s argv=%s",
            self._serial, pid, argv,
        )

        reader = _ReaderThread(master, pid, self)
        reader.chunk.connect(self.output_ready)
        reader.finished_with_rc.connect(self._on_reader_finished)
        self._reader = reader
        reader.start()
        return True

    def write(self, data: bytes) -> bool:
        """Write ``data`` to the PTY master. Returns False if not running."""
        fd = self._master_fd
        if fd is None:
            return False
        try:
            os.write(fd, data)
            return True
        except OSError:
            return False

    def close(self) -> None:
        """Send EOF and terminate the child. Idempotent."""
        if self._closing:
            return
        self._closing = True
        fd = self._master_fd
        pid = self._pid
        if fd is not None:
            try:
                os.write(fd, b"\x04")  # Ctrl+D — EOF on cooked PTY.
            except OSError:
                pass
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        if self._reader is not None:
            self._reader.request_stop()
            self._reader.wait(_TERM_GRACE_S * 1000)
            if self._reader.isRunning() and pid is not None:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                self._reader.wait(2000)
        self._cleanup_fd()

    def is_running(self) -> bool:
        return self._pid is not None and self._reader is not None and self._reader.isRunning()

    @property
    def serial(self) -> str:
        return self._serial

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _on_reader_finished(self, rc: int) -> None:
        _log.info(
            "pty session exited serial=%s pid=%s rc=%s",
            self._serial, self._pid, rc,
        )
        self._cleanup_fd()
        self._pid = None
        self._reader = None
        self.process_exited.emit(int(rc))

    def _cleanup_fd(self) -> None:
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None


__all__ = ["PtySession"]
