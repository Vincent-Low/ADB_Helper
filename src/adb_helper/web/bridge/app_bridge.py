"""AppBridge — global state: theme, settings snapshot, active device, strings."""
from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import Signal, Slot

from ...core import strings as strings_module
from ...core.adb_service import AdbService
from ...core.settings_manager import SettingsManager
from ...ui.theme_manager import Theme, ThemeManager
from .base import BridgeBase, to_jsonable


def _strings_snapshot() -> Dict[str, str]:
    """Snapshot of every exported str/Final from core.strings."""
    out: Dict[str, str] = {}
    for name in dir(strings_module):
        if name.startswith("_"):
            continue
        val = getattr(strings_module, name)
        if isinstance(val, str):
            out[name] = val
    return out


class AppBridge(BridgeBase):
    """Global bridge — theme switching, settings access, strings, active device."""

    themeChanged = Signal(str)            # resolved theme: "dark" | "light"
    activeDeviceChanged = Signal("QVariant")
    settingsChanged = Signal("QVariant")

    def __init__(
        self,
        adb: AdbService,
        settings: SettingsManager,
        theme_mgr: ThemeManager,
    ) -> None:
        super().__init__()
        self._adb = adb
        self._settings = settings
        self._theme = theme_mgr

        adb.activeDeviceChanged.connect(
            lambda ctx: self.activeDeviceChanged.emit(to_jsonable(ctx))
        )
        theme_mgr.theme_changed.connect(
            lambda t: self.themeChanged.emit(getattr(t, "value", str(t)))
        )

    @Slot(result="QVariant")
    def getInitialState(self) -> Dict[str, Any]:
        return {
            "theme": self._settings.get("theme", "system"),
            "effectiveTheme": self._theme.effective_theme().value,
            "settings": self._settings.as_dict(),
            "activeDevice": to_jsonable(self._adb.active_device),
            "strings": _strings_snapshot(),
            "appVersion": strings_module.APP_VERSION,
        }

    @Slot(str)
    def setTheme(self, mode: str) -> None:
        """Persist + apply theme. ``mode`` ∈ {"system","light","dark"}."""
        try:
            theme = Theme(mode)
        except ValueError:
            theme = Theme.SYSTEM
        self._settings.set("theme", theme.value)
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            self._theme.apply(app, theme)

    @Slot(result="QVariant")
    def effectiveTheme(self) -> str:
        return self._theme.effective_theme().value


__all__ = ["AppBridge"]
