"""Design tokens — surfaces, borders, text, accent, semantics, geometry.

Values copied 1:1 from ``design.html`` (:root + [data-theme="light"]).
See handoff.md §2. Do NOT add per-widget colours here — this is the single
source of truth for the QSS template and the QPalette.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tokens:
    # ---- Surfaces ----
    bg_app: str
    bg_content: str
    bg_card: str
    bg_card_2: str
    bg_elevated: str
    bg_input: str
    bg_row_alt: str
    bg_row_selected: str
    bg_row_hover: str

    # ---- Borders ----
    border: str
    border_strong: str
    border_input: str

    # ---- Text ----
    text_1: str
    text_2: str
    text_3: str
    text_disabled: str

    # ---- Accent ----
    accent: str
    accent_strong: str
    accent_soft: str
    accent_fg: str

    # ---- Semantics ----
    success: str
    warning: str
    danger: str

    # ---- Geometry (defaults shared across themes) ----
    r_sm: int = 4
    r_md: int = 6
    r_lg: int = 8
    sp_2: int = 8
    sp_3: int = 12
    sp_4: int = 16
    input_h: int = 32
    btn_h: int = 32
    row_h: int = 36


DARK_TOKENS = Tokens(
    bg_app="#0d1015",
    bg_content="#121620",
    bg_card="#171c26",
    bg_card_2="#1d2330",
    bg_elevated="#232a39",
    bg_input="#131822",
    bg_row_alt="rgba(255,255,255,0.025)",
    bg_row_selected="rgba(45,212,191,0.12)",
    bg_row_hover="rgba(255,255,255,0.05)",
    border="#262d3c",
    border_strong="#344055",
    border_input="#2a3243",
    text_1="#e6eaf0",
    text_2="#a5acba",
    text_3="#6b7280",
    text_disabled="#4b5260",
    accent="#2dd4bf",
    accent_strong="#14b8a6",
    accent_soft="rgba(45,212,191,0.14)",
    accent_fg="#08201d",
    success="#34d399",
    warning="#fbbf24",
    danger="#f87171",
)


LIGHT_TOKENS = Tokens(
    bg_app="#eef0f3",
    bg_content="#f4f6f8",
    bg_card="#ffffff",
    bg_card_2="#fafbfc",
    bg_elevated="#f0f2f5",
    bg_input="#ffffff",
    bg_row_alt="rgba(0,0,0,0.025)",
    bg_row_selected="rgba(13,148,136,0.10)",
    bg_row_hover="rgba(0,0,0,0.04)",
    border="#e2e5ea",
    border_strong="#cbd1d9",
    border_input="#d4d9e1",
    text_1="#1a1d23",
    text_2="#5b6371",
    text_3="#868d99",
    text_disabled="#b6bcc6",
    accent="#0d9488",
    accent_strong="#0f766e",
    accent_soft="rgba(13,148,136,0.10)",
    accent_fg="#ffffff",
    success="#10b981",
    warning="#d97706",
    danger="#dc2626",
)


__all__ = ["Tokens", "DARK_TOKENS", "LIGHT_TOKENS"]
