"""Module: Scrcpy (Spec §3.4).

Launches scrcpy as a SEPARATE top-level process window — never embedded in
the Qt main window. Auto-downloads binaries on first launch (GitHub API,
6-hour response cache, SHA-256 verification).
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class ScrcpyModule(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def on_device_changed(self, ctx: DeviceContext) -> None:
        pass

    def on_device_disconnected(self) -> None:
        pass
