"""Platform shims — the ONLY place ``sys.platform`` branches are allowed.

CLAUDE.md invariant 4. Anything that differs between Windows 11 and Ubuntu
22.04+ — paths (handled in :mod:`paths`), PTY backend (ConPTY vs Python
``pty``), single-instance IPC (named pipe vs Unix domain socket), file
locking, theme polling — funnels through this module.

Stub: signatures only. Implementations land alongside the ADB service.
"""
from __future__ import annotations

import sys
from enum import Enum


class HostOS(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"


def host_os() -> HostOS:
    """Return the supported host OS, raising on unsupported platforms (§1.2)."""
    if sys.platform.startswith("win"):
        return HostOS.WINDOWS
    if sys.platform.startswith("linux"):
        return HostOS.LINUX
    raise RuntimeError(
        f"Unsupported platform: {sys.platform!r}. ADB_Helper supports Windows 11 "
        f"and Ubuntu 22.04+ only (§1.2)."
    )


def is_windows() -> bool:
    return host_os() is HostOS.WINDOWS


def is_linux() -> bool:
    return host_os() is HostOS.LINUX


def acquire_single_instance_lock() -> object:
    """Acquire the OS-level exclusive lock on the lockfile (Spec §1.7).

    Windows: named mutex + named pipe handle.
    Linux: ``fcntl.flock`` on ``<app_data>/adb_helper.lock`` + UDS at
    ``/tmp/adb_helper_<uid>.sock``.

    Returns an opaque handle that must outlive the application; raises if a
    running instance already holds the lock (caller signals that instance and
    exits 0).
    """
    raise NotImplementedError


def signal_running_instance_to_focus() -> None:
    """Tell the already-running instance to bring its window forward (§1.7).

    Windows: write to the named pipe.
    Linux: connect to the Unix domain socket and send a focus message.
    """
    raise NotImplementedError


def open_pty_for_adb_shell(serial: str) -> object:
    """Open a PTY suitable for an ``adb shell`` session against ``serial``.

    Windows: ConPTY (Win 10 1903+ — satisfied by Win 11).
    Linux: Python ``pty`` module.

    Both backends are returned wrapped so they can be driven via ``QProcess``
    in the terminal module (Spec §3.2.1 / §6).
    """
    raise NotImplementedError


def start_system_theme_listener(on_change) -> None:
    """Subscribe to OS dark/light theme changes (Spec §2.2 / §6).

    Windows: real-time via ``WM_SETTINGCHANGE`` / ``UISettings``.
    Linux: poll every 30 s via ``darkdetect`` (best-effort).
    """
    raise NotImplementedError
