"""Theming package — tokens, palette, QSS template, ThemeManager.

Public API:
    Theme           — enum (SYSTEM / LIGHT / DARK).
    ThemeManager    — apply theme to a QApplication; emits ``theme_changed``.
    get_theme_manager — module-level accessor for the app-wide manager.
    Tokens          — frozen dataclass with all design tokens.
    DARK_TOKENS / LIGHT_TOKENS — built-in palettes (handoff §2).
    build_palette   — Tokens → QPalette.
    render_qss      — Tokens → QSS string.
"""
from __future__ import annotations

from .palette import build_palette
from .qss import render_qss
from .theme_manager import Theme, ThemeManager, get_theme_manager
from .tokens import DARK_TOKENS, LIGHT_TOKENS, Tokens

__all__ = [
    "Theme",
    "ThemeManager",
    "get_theme_manager",
    "Tokens",
    "DARK_TOKENS",
    "LIGHT_TOKENS",
    "build_palette",
    "render_qss",
]
