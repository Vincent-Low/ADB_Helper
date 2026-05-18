"""Platform shims — the ONLY place ``sys.platform`` branches are allowed.

CLAUDE.md invariant 4. Path resolution, PTY backend, single-instance IPC
(named pipe vs Unix domain socket), and theme polling funnel through here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

IS_LINUX: bool = sys.platform.startswith("linux")
IS_WINDOWS: bool = sys.platform.startswith("win")

if not (IS_LINUX or IS_WINDOWS):
    raise RuntimeError(
        f"Unsupported platform: {sys.platform!r}. ADB_Helper supports "
        f"Windows 11 and Ubuntu 22.04+ only (Spec §1.2)."
    )

_APP_DIR_NAME_WINDOWS = "ADB_Helper"
_APP_DIR_NAME_LINUX = "adb_helper"


def get_app_data_dir() -> Path:
    """Return the app data root, creating it on first call (Spec §1.4)."""
    if IS_WINDOWS:
        base = os.environ.get("APPDATA")
        if not base:
            raise RuntimeError("APPDATA environment variable is not set.")
        path = Path(base) / _APP_DIR_NAME_WINDOWS
    else:
        path = Path.home() / ".config" / _APP_DIR_NAME_LINUX
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_lock_path() -> Path:
    """Single-instance lockfile path (Spec §1.7)."""
    return get_app_data_dir() / "adb_helper.lock"


def get_socket_path() -> Path:
    """IPC endpoint used by a second launch to focus the running instance.

    Linux: ``/tmp/adb_helper_<uid>.sock`` (Unix domain socket).
    Windows: a placeholder ``Path`` whose ``name`` is the named-pipe name;
    callers on Windows pass ``str(get_socket_path())`` after stripping the
    directory.
    """
    if IS_LINUX:
        return Path("/tmp") / f"adb_helper_{os.getuid()}.sock"
    return Path(r"\\.\pipe") / "ADB_Helper"


def get_monospace_font() -> str:
    """Preferred monospace font family for the terminal (Spec §2.2.1)."""
    return "Cascadia Code" if IS_WINDOWS else "JetBrains Mono"
