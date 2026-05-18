"""Application data paths.

Spec §1.4:
- Windows: ``%APPDATA%\\ADB_Helper\\``
- Linux:   ``~/.config/adb_helper/``

Subdirectories: ``logs/``, ``screenshots/``, ``logcat/``, ``platform-tools/``,
``scrcpy/``, ``bundletool/``.

Only Linux is the target runtime for now, but the Windows branch is kept so the
module imports cleanly on either platform.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME_WINDOWS = "ADB_Helper"
APP_DIR_NAME_LINUX = "adb_helper"

SUBDIRS = (
    "logs",
    "screenshots",
    "logcat",
    "platform-tools",
    "scrcpy",
    "bundletool",
)


def app_data_root() -> Path:
    """Return the platform-appropriate application data root.

    Raises:
        RuntimeError: on unsupported platforms (e.g., macOS — see §1.2 / §9).
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if not base:
            raise RuntimeError("APPDATA environment variable is not set.")
        return Path(base) / APP_DIR_NAME_WINDOWS

    if sys.platform.startswith("linux"):
        return Path.home() / ".config" / APP_DIR_NAME_LINUX

    raise RuntimeError(
        f"Unsupported platform: {sys.platform!r}. ADB_Helper supports Windows 11 "
        f"and Ubuntu 22.04+ only (§1.2)."
    )


def settings_path() -> Path:
    return app_data_root() / "settings.json"


def database_path() -> Path:
    return app_data_root() / "adb_helper.db"


def lockfile_path() -> Path:
    return app_data_root() / "adb_helper.lock"


def logs_dir() -> Path:
    return app_data_root() / "logs"


def screenshots_dir() -> Path:
    return app_data_root() / "screenshots"


def logcat_dir() -> Path:
    return app_data_root() / "logcat"


def platform_tools_dir() -> Path:
    return app_data_root() / "platform-tools"


def scrcpy_dir() -> Path:
    return app_data_root() / "scrcpy"


def bundletool_dir() -> Path:
    return app_data_root() / "bundletool"


def ensure_app_dirs() -> Path:
    """Create the app data root and all required subdirectories.

    Idempotent: safe to call on every startup.
    Returns the app data root path.
    """
    root = app_data_root()
    root.mkdir(parents=True, exist_ok=True)
    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root
