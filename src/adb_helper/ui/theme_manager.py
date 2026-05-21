"""ThemeManager — track system theme, expose effective theme to bridges.

Vue SPA owns all styling (Tailwind + CSS vars in ``frontend/src/style.css``).
ThemeManager no longer loads QSS; it only resolves the effective theme so
the AppBridge can push ``themeChanged`` to the Vue side. System-theme follow
on Linux is best-effort via ``darkdetect`` polled every 30 s.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from ..core.logger import get_logger
from ..core.platform import IS_LINUX

_log = get_logger(__name__)

_POLL_MS = 30_000

_tm_instance: Optional["ThemeManager"] = None


def get_theme_manager() -> Optional["ThemeManager"]:
    """Return the application-wide ThemeManager (registered on first construction)."""
    return _tm_instance


class Theme(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    """Resolve effective theme; emit ``theme_changed`` for the Vue bridge."""

    theme_changed = Signal(object)  # Theme enum

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        global _tm_instance
        _tm_instance = self
        self._app: Optional[QApplication] = None
        self._theme: Theme = Theme.SYSTEM
        self._effective: Theme = Theme.DARK
        self._timer: Optional[QTimer] = None

    def apply(self, app: QApplication, theme: Theme) -> None:
        self._app = app
        self._theme = theme
        self._stop_polling()
        if theme == Theme.SYSTEM:
            effective = self._detect_system_theme()
            self._start_polling()
        else:
            effective = theme
        if effective != self._effective:
            self._effective = effective
            self.theme_changed.emit(effective)
        else:
            self._effective = effective

    def current_theme(self) -> Theme:
        return self._theme

    def effective_theme(self) -> Theme:
        return self._effective

    # --- internals -------------------------------------------------------
    def _detect_system_theme(self) -> Theme:
        try:
            import darkdetect
            value = darkdetect.theme()
        except Exception as e:
            _log.warning("darkdetect unavailable (%s); defaulting to dark", e)
            return Theme.DARK
        if isinstance(value, str) and value.lower() == "light":
            return Theme.LIGHT
        return Theme.DARK

    def _start_polling(self) -> None:
        if not IS_LINUX:
            return
        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_MS)
        self._timer.timeout.connect(self._poll_system_theme)
        self._timer.start()

    def _stop_polling(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None

    def _poll_system_theme(self) -> None:
        if self._theme != Theme.SYSTEM:
            return
        detected = self._detect_system_theme()
        if detected != self._effective:
            self._effective = detected
            self.theme_changed.emit(detected)


__all__ = ["Theme", "ThemeManager", "get_theme_manager"]
