"""Terminal ANSI palette (Spec §2.2.1).

Hex values are verbatim from the spec table — do NOT replace with the
design-system accent colours from ``DESIGN_TOKENS.md``. These dicts are
consumed exclusively by the Terminal widget's ANSI renderer and MUST NOT
be referenced from QSS (CLAUDE.md invariant 3 is for user-facing strings;
the rule here is invariant 1 + spec §2.2.1: terminal styling lives
separately from app QSS).
"""
from __future__ import annotations

from typing import Dict, Final

LIGHT_PALETTE: Final[Dict[str, str]] = {
    "Background":     "#FFFFFF",
    "Foreground":     "#1E1E1E",
    "Black":          "#000000",
    "BrightBlack":    "#767676",
    "Red":            "#CC0000",
    "BrightRed":      "#E06C75",
    "Green":          "#008000",
    "BrightGreen":    "#98C379",
    "Yellow":         "#B8860B",
    "BrightYellow":   "#E5C07B",
    "Blue":           "#0550AE",
    "BrightBlue":     "#61AFEF",
    "Magenta":        "#8B008B",
    "BrightMagenta":  "#C678DD",
    "Cyan":           "#007070",
    "BrightCyan":     "#56B6C2",
    "White":          "#BBBBBB",
    "BrightWhite":    "#FFFFFF",
}

DARK_PALETTE: Final[Dict[str, str]] = {
    "Background":     "#1E1E1E",
    "Foreground":     "#D4D4D4",
    "Black":          "#3A3A3A",
    "BrightBlack":    "#858585",
    "Red":            "#CC3333",
    "BrightRed":      "#E06C75",
    "Green":          "#3CB371",
    "BrightGreen":    "#98C379",
    "Yellow":         "#D4A017",
    "BrightYellow":   "#E5C07B",
    "Blue":           "#569CD6",
    "BrightBlue":     "#61AFEF",
    "Magenta":        "#9B59B6",
    "BrightMagenta":  "#C678DD",
    "Cyan":           "#2AA198",
    "BrightCyan":     "#56B6C2",
    "White":          "#C0C0C0",
    "BrightWhite":    "#FFFFFF",
}

__all__ = ["LIGHT_PALETTE", "DARK_PALETTE"]
