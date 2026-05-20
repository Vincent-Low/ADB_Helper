"""ThemeManager — tokens-driven palette + QSS application.

Replaces the prior file-loader implementation. Same public API
(``Theme``, ``ThemeManager``, ``get_theme_manager``) so the rest of the
app keeps compiling while modules migrate to the new package.

System-theme follow on Linux is still best-effort via ``darkdetect``
polled every 30 s (Spec §6.2). Windows native colour-scheme change
events arrive automatically through Qt's StyleHints if the user later
wants to switch — for now the manager only polls on Linux.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from ...core.logger import get_logger
from ...core.platform import IS_LINUX
from .. import terminal_palette
from .palette import build_palette
from .qss import render_qss
from .tokens import DARK_TOKENS, LIGHT_TOKENS, Tokens

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
    """Apply palette + QSS to a QApplication; optionally track OS theme."""

    theme_changed = Signal(object)  # Theme enum (effective: LIGHT or DARK)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        global _tm_instance
        _tm_instance = self
        self._app: Optional[QApplication] = None
        self._theme: Theme = Theme.SYSTEM
        self._effective: Theme = Theme.DARK
        self._tokens: Tokens = DARK_TOKENS
        self._timer: Optional[QTimer] = None

    # ---- public API ----------------------------------------------------
    def apply(self, app: QApplication, theme: Theme) -> None:
        """Apply ``theme`` to ``app``. Starts/stops the system-poll timer."""
        self._app = app
        self._theme = theme
        self._stop_polling()
        if theme == Theme.SYSTEM:
            effective = self._detect_system_theme()
            self._start_polling()
        else:
            effective = theme
        changed = effective != self._effective
        self._effective = effective
        self._tokens = DARK_TOKENS if effective == Theme.DARK else LIGHT_TOKENS
        self._apply(effective)
        if changed:
            self.theme_changed.emit(effective)

    def current_theme(self) -> Theme:
        return self._theme

    def effective_theme(self) -> Theme:
        return self._effective

    def current_tokens(self) -> Tokens:
        return self._tokens

    # ---- internals -----------------------------------------------------
    def _apply(self, effective: Theme) -> None:
        if self._app is None:
            return
        tokens = DARK_TOKENS if effective == Theme.DARK else LIGHT_TOKENS
        self._app.setPalette(build_palette(tokens))
        self._app.setStyleSheet(render_qss(tokens))
        refresh_terminal = getattr(terminal_palette, "refresh_for", None)
        if callable(refresh_terminal):
            try:
                refresh_terminal(effective)
            except Exception as e:
                _log.warning("ThemeManager: terminal_palette.refresh_for failed: %s", e)
        _log.info("ThemeManager: applied %s theme", effective.value)

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
            self._tokens = DARK_TOKENS if detected == Theme.DARK else LIGHT_TOKENS
            self._apply(detected)
            self.theme_changed.emit(detected)


__all__ = ["Theme", "ThemeManager", "get_theme_manager"]
