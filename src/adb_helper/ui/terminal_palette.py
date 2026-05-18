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
    "background":     "#FFFFFF",
    "foreground":     "#1E1E1E",
    "black":          "#000000",
    "bright_black":   "#767676",
    "red":            "#CC0000",
    "bright_red":     "#E06C75",
    "green":          "#008000",
    "bright_green":   "#98C379",
    "yellow":         "#B8860B",
    "bright_yellow":  "#E5C07B",
    "blue":           "#0550AE",
    "bright_blue":    "#61AFEF",
    "magenta":        "#8B008B",
    "bright_magenta": "#C678DD",
    "cyan":           "#007070",
    "bright_cyan":    "#56B6C2",
    "white":          "#BBBBBB",
    "bright_white":   "#FFFFFF",
}

DARK_PALETTE: Final[Dict[str, str]] = {
    "background":     "#1E1E1E",
    "foreground":     "#D4D4D4",
    "black":          "#3A3A3A",
    "bright_black":   "#858585",
    "red":            "#CC3333",
    "bright_red":     "#E06C75",
    "green":          "#3CB371",
    "bright_green":   "#98C379",
    "yellow":         "#D4A017",
    "bright_yellow":  "#E5C07B",
    "blue":           "#569CD6",
    "bright_blue":    "#61AFEF",
    "magenta":        "#9B59B6",
    "bright_magenta": "#C678DD",
    "cyan":           "#2AA198",
    "bright_cyan":    "#56B6C2",
    "white":          "#C0C0C0",
    "bright_white":   "#FFFFFF",
}

__all__ = ["LIGHT_PALETTE", "DARK_PALETTE"]
