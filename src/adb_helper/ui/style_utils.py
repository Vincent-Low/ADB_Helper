"""QSS variant helper."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget


def set_variant(widget: QWidget, variant: str) -> None:
    widget.setProperty("variant", variant)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


__all__ = ["set_variant"]
