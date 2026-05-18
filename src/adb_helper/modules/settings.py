"""Module: Settings (Spec §3.9).

About section, bundled-dependency status (ADB / scrcpy / bundletool), and
general settings (theme, screenshots folder, logcat folder, ADB command
timeout, log level). All settings persist immediately to ``settings.json``.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class SettingsModule(QWidget):
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
