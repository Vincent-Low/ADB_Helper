"""Module: Connections (Spec §3.1).

Default module shown on launch. Manages USB and Wi-Fi (classic + Android 11+
pairing) ADB connections, lists live devices via ``adb track-devices``, and
persists paired Wi-Fi devices for manual reconnection (no auto-reconnect — §9).

Stub: widget body is ``pass``; no logic yet.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class ConnectionsModule(QWidget):
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
