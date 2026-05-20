"""Shared layout / styling helpers for the per-module redesign (plan §5).

The helpers below cover the three primitives every page uses:

* ``page_header(title, subtitle, actions)`` — top row of a module page with
  the role="page-title" label, an optional role="hint" subtitle, a stretch
  spacer, and right-aligned action widgets.
* ``card(label, body, actions)`` — wraps a body widget in a
  ``QFrame[role="card"]`` with a header (role="section-label") and an
  optional ``card-f`` footer carrying action buttons.
* ``set_variant(btn, variant)`` — kept from before; toggles the QSS
  ``variant`` property and re-polishes.

All helpers stay token-agnostic; the QSS template owns colours.
"""
from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


def set_variant(widget: QWidget, variant: str) -> None:
    widget.setProperty("variant", variant)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def page_header(
    title: str,
    subtitle: str = "",
    actions: Iterable[QWidget] = (),
    parent: Optional[QWidget] = None,
) -> QWidget:
    """Build a page-header row (title + subtitle on left, actions on right)."""
    host = QWidget(parent)
    host.setObjectName("pageHeader")
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)

    text_col = QVBoxLayout()
    text_col.setContentsMargins(0, 0, 0, 0)
    text_col.setSpacing(2)

    title_lbl = QLabel(title, host)
    title_lbl.setProperty("role", "page-title")
    text_col.addWidget(title_lbl)

    if subtitle:
        sub_lbl = QLabel(subtitle, host)
        sub_lbl.setProperty("role", "hint")
        sub_lbl.setWordWrap(True)
        text_col.addWidget(sub_lbl)

    row.addLayout(text_col, 1)

    for action in actions:
        row.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)

    return host


def card(
    label: str,
    body: QWidget,
    actions: Iterable[QWidget] = (),
    parent: Optional[QWidget] = None,
) -> QFrame:
    """Build ``QFrame[role="card"]`` with header + body (+ optional footer)."""
    frame = QFrame(parent)
    frame.setProperty("role", "card")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    header = QFrame(frame)
    header.setProperty("role", "card-h")
    h_row = QHBoxLayout(header)
    h_row.setContentsMargins(14, 10, 14, 10)
    h_row.setSpacing(8)
    lbl = QLabel(label, header)
    lbl.setProperty("role", "section-label")
    h_row.addWidget(lbl, 1)
    outer.addWidget(header)

    body_host = QFrame(frame)
    body_host.setProperty("role", "card-b")
    b_row = QVBoxLayout(body_host)
    b_row.setContentsMargins(14, 14, 14, 14)
    b_row.setSpacing(10)
    b_row.addWidget(body)
    outer.addWidget(body_host, 1)

    actions = list(actions)
    if actions:
        footer = QFrame(frame)
        footer.setProperty("role", "card-f")
        f_row = QHBoxLayout(footer)
        f_row.setContentsMargins(14, 10, 14, 10)
        f_row.setSpacing(8)
        f_row.addStretch(1)
        for a in actions:
            f_row.addWidget(a, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(footer)

    return frame


def card_with_header_actions(
    label: str,
    body: QWidget,
    header_actions: Iterable[QWidget] = (),
    parent: Optional[QWidget] = None,
) -> QFrame:
    """Variant of ``card`` with actions in the header row (right-aligned)."""
    frame = QFrame(parent)
    frame.setProperty("role", "card")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    header = QFrame(frame)
    header.setProperty("role", "card-h")
    h_row = QHBoxLayout(header)
    h_row.setContentsMargins(14, 10, 14, 10)
    h_row.setSpacing(8)
    lbl = QLabel(label, header)
    lbl.setProperty("role", "section-label")
    h_row.addWidget(lbl, 1)
    for a in header_actions:
        h_row.addWidget(a, 0, Qt.AlignmentFlag.AlignVCenter)
    outer.addWidget(header)

    body_host = QFrame(frame)
    body_host.setProperty("role", "card-b")
    b_row = QVBoxLayout(body_host)
    b_row.setContentsMargins(14, 14, 14, 14)
    b_row.setSpacing(10)
    b_row.addWidget(body)
    outer.addWidget(body_host, 1)

    return frame


__all__ = [
    "set_variant",
    "page_header",
    "card",
    "card_with_header_actions",
]
