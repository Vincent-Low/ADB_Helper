"""SettingsBridge — app settings + dependency status."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QFileDialog

from ...core import paths, strings
from ...core.db_manager import DatabaseManager
from ...core.settings_manager import SettingsManager
from ..util import top_level_window
from .base import BridgeBase


def _exists(p: Path) -> bool:
    return p.exists()


def _adb_installed() -> bool:
    candidate = paths.platform_tools_dir() / ("adb.exe" if _is_win() else "adb")
    return candidate.exists() or shutil.which("adb") is not None


def _is_win() -> bool:
    import sys
    return sys.platform.startswith("win")


def _scrcpy_installed() -> bool:
    root = paths.scrcpy_dir()
    if not root.exists():
        return False
    name = "scrcpy.exe" if _is_win() else "scrcpy"
    for p in root.rglob(name):
        if p.is_file():
            return True
    return False


def _bundletool_installed() -> bool:
    root = paths.bundletool_dir()
    return root.exists() and any(p.suffix == ".jar" for p in root.glob("*"))


class SettingsBridge(BridgeBase):
    settingsChanged = Signal("QVariant")
    depsChecked = Signal("QVariant")

    def __init__(self, settings: SettingsManager, db: DatabaseManager) -> None:
        super().__init__()
        self._settings = settings
        self._db = db

    @Slot(result="QVariant")
    def all(self) -> Dict[str, Any]:
        return self._settings.as_dict()

    @Slot(str, "QVariant")
    def set(self, key: str, value: Any) -> None:
        self._settings.set(key, value)
        self.settingsChanged.emit({key: value})

    @Slot(str, result="QVariant")
    def get(self, key: str) -> Any:
        return self._settings.get(key)

    @Slot(str, str, result=str)
    def pickFolder(self, title: str, current: str) -> str:
        """Open a native folder dialog. Returns absolute path or empty string."""
        chosen = QFileDialog.getExistingDirectory(
            top_level_window(), title, current,
        )
        return chosen or ""

    @Slot(result="QVariant")
    def dependencies(self) -> List[Dict[str, Any]]:
        deps = [
            {
                "component": strings.SETT_DEP_ADB,
                "installed": _adb_installed(),
                "version": "",       # filled by frontend if cached
                "latest": "",
                "status": "installed" if _adb_installed() else "missing",
            },
            {
                "component": strings.SETT_DEP_SCRCPY,
                "installed": _scrcpy_installed(),
                "version": "",
                "latest": "",
                "status": "installed" if _scrcpy_installed() else "missing",
            },
            {
                "component": strings.SETT_DEP_BUNDLETOOL,
                "installed": _bundletool_installed(),
                "version": "",
                "latest": "",
                "status": "installed" if _bundletool_installed() else "missing",
            },
        ]
        self.depsChecked.emit(deps)
        return deps


__all__ = ["SettingsBridge"]
