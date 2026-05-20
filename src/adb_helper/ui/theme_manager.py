"""Backwards-compat shim — re-exports from ``adb_helper.ui.theming``.

The real implementation moved to the ``theming`` package (plan §1).
This module exists so existing importers (``ui.theme_manager``) keep
working while module-side imports migrate to ``ui.theming``.

Slated for removal once every importer references the package directly.
"""
from __future__ import annotations

from .theming import Theme, ThemeManager, get_theme_manager

__all__ = ["Theme", "ThemeManager", "get_theme_manager"]
