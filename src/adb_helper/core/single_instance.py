"""Single-instance enforcement (Spec §1.7, §6.2).

Linux implementation: fcntl exclusive lock on ``<app_data>/adb_helper.lock``
plus a Unix domain socket at ``/tmp/adb_helper_<uid>.sock``. Second launch
sends ``focus\\n`` and exits 0. Windows path stubbed — not the target runtime
for v1.0 shell scaffold.
"""
from __future__ import annotations

import os
import socket
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from .logger import get_logger
from .platform import IS_LINUX, get_lock_path, get_socket_path

_log = get_logger(__name__)

_FOCUS_MSG = b"focus\n"


class SingleInstance(QObject):
    """Cross-process single-instance gate (Linux primary)."""

    focus_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._lock_path = get_lock_path()
        self._socket_path = get_socket_path()
        self._lock_fd: Optional[int] = None
        self._server_socket: Optional[socket.socket] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # --- public API ------------------------------------------------------
    def acquire(self) -> bool:
        """Try to acquire single-instance lock.

        Returns True if this is the primary instance. Returns False if
        another instance holds the lock — in that case a focus message
        has already been sent to the running instance.
        """
        if not IS_LINUX:
            return self._acquire_unsupported()

        import fcntl

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self._lock_path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            self._signal_focus()
            return False

        self._lock_fd = fd
        try:
            os.ftruncate(fd, 0)
            os.write(fd, str(os.getpid()).encode("ascii"))
        except OSError:
            pass

        self._start_listener()
        return True

    def release(self) -> None:
        self._stop_event.set()
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None
        try:
            self._socket_path.unlink(missing_ok=True)
        except OSError:
            pass
        if self._lock_fd is not None:
            try:
                import fcntl
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = None

    # --- context manager -------------------------------------------------
    def __enter__(self) -> "SingleInstance":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    # --- internals -------------------------------------------------------
    def _acquire_unsupported(self) -> bool:
        _log.warning("SingleInstance: non-Linux path not wired in v1.0 shell")
        return True

    def _signal_focus(self) -> None:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(str(self._socket_path))
            sock.sendall(_FOCUS_MSG)
            sock.close()
            _log.info("SingleInstance: focus signal sent to running instance")
        except OSError as e:
            _log.warning("SingleInstance: failed to signal running instance: %s", e)

    def _start_listener(self) -> None:
        try:
            self._socket_path.unlink(missing_ok=True)
        except OSError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(self._socket_path))
        srv.listen(1)
        srv.settimeout(0.5)
        self._server_socket = srv

        t = threading.Thread(
            target=self._listener_loop,
            name="single-instance-listener",
            daemon=True,
        )
        self._listener_thread = t
        t.start()

    def _listener_loop(self) -> None:
        srv = self._server_socket
        if srv is None:
            return
        while not self._stop_event.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                conn.settimeout(1.0)
                data = b""
                while b"\n" not in data and len(data) < 64:
                    chunk = conn.recv(64)
                    if not chunk:
                        break
                    data += chunk
                if data.startswith(b"focus"):
                    _log.info("SingleInstance: focus signal received")
                    self.focus_requested.emit()
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
