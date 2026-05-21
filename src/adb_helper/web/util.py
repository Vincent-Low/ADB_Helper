"""Shared helpers for the web/ package."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget


def top_level_window() -> Optional[QWidget]:
    """Return the topmost visible application window, or None.

    Used as the parent for native dialogs (QFileDialog, QMessageBox)
    so they appear modal to the main shell.  Excludes the dialog
    itself by checking visibility — a QFileDialog spawned inside a
    QMessageBox is rare but possible.
    """
    app = QApplication.instance()
    if app is None:
        return None
    for w in app.topLevelWidgets():
        if w.isVisible():
            return w
    return None


__all__ = ["top_level_window"]
