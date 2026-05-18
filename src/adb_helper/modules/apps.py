"""Module: Apps (Spec §3.7).

Lists installed apps via ``pm list packages``. No icon extraction (§9). System
apps can be disabled but not uninstalled. RAM and Storage bars refresh on
demand only — no background polling.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class AppsModule(QWidget):
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
