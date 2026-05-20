"""Build a QPalette from Tokens.

Needed because QSS does NOT cover every native widget — QFileDialog,
QMessageBox, Win11 scrollbars, and some Fusion-rendered controls read from
QPalette before QSS overrides hit. See handoff §2.1.
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

from .tokens import Tokens


def build_palette(t: Tokens) -> QPalette:
    """Translate token colours into a fully populated QPalette."""
    p = QPalette()

    # Active group
    p.setColor(QPalette.ColorRole.Window, QColor(t.bg_app))
    p.setColor(QPalette.ColorRole.WindowText, QColor(t.text_1))
    p.setColor(QPalette.ColorRole.Base, QColor(t.bg_input))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(t.bg_card_2))
    p.setColor(QPalette.ColorRole.Text, QColor(t.text_1))
    p.setColor(QPalette.ColorRole.Button, QColor(t.bg_card_2))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(t.text_1))
    p.setColor(QPalette.ColorRole.Highlight, QColor(t.accent))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(t.accent_fg))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(t.bg_card))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(t.text_1))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.text_3))
    p.setColor(QPalette.ColorRole.Link, QColor(t.accent))
    p.setColor(QPalette.ColorRole.LinkVisited, QColor(t.accent_strong))

    # Disabled group
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t.text_disabled))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t.text_disabled))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(t.text_disabled))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(t.bg_elevated))
    p.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.HighlightedText,
        QColor(t.text_disabled),
    )

    return p


__all__ = ["build_palette"]
