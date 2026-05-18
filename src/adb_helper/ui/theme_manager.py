"""ThemeManager — load + apply QSS, follow system theme on Linux (Spec §2.2).

QSS lives in ``ui/qss/{light,dark}.qss``. Terminal palette is NEVER touched
from QSS — see ``ui/terminal_palette.py``. System-theme follow on Linux is
best-effort: ``darkdetect`` polled every 30 s via ``QTimer`` (Spec §6.2).
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from ..core.logger import get_logger
from ..core.platform import IS_LINUX

_log = get_logger(__name__)

_QSS_DIR = Path(__file__).resolve().parent / "qss"
_POLL_MS = 30_000


class Theme(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    """Apply QSS to the QApplication; optionally track OS theme."""

    theme_changed = Signal(object)  # Theme enum

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._app: Optional[QApplication] = None
        self._theme: Theme = Theme.SYSTEM
        self._effective: Theme = Theme.DARK
        self._timer: Optional[QTimer] = None

    def apply(self, app: QApplication, theme: Theme) -> None:
        """Apply theme to ``app``. Starts/stops the system-poll timer."""
        self._app = app
        self._theme = theme
        self._stop_polling()
        if theme == Theme.SYSTEM:
            effective = self._detect_system_theme()
            self._start_polling()
        else:
            effective = theme
        self._apply_qss(effective)
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
    def _apply_qss(self, effective: Theme) -> None:
        if self._app is None:
            return
        qss_file = _QSS_DIR / f"{effective.value}.qss"
        try:
            qss = qss_file.read_text(encoding="utf-8")
        except OSError as e:
            _log.error("ThemeManager: failed to load %s: %s", qss_file, e)
            return
        self._app.setStyleSheet(qss)
        _log.info("ThemeManager: applied %s.qss", effective.value)

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
            self._apply_qss(detected)
            self.theme_changed.emit(detected)


__all__ = ["Theme", "ThemeManager"]
