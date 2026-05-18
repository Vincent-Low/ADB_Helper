"""Module: Device Buttons (Spec §3.5).

Simulates hardware/software button presses on the active device via
``adb shell input keyevent``. Includes screenshot capture via ``exec-out``
with fallback to ``screencap`` + ``pull`` + ``rm`` for older devices.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class DeviceButtonsModule(QWidget):
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
