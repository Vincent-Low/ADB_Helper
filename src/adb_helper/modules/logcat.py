"""Module: Logcat (Spec §3.8).

One-shot export of ``adb logcat -d`` to a host file. Filename format
``logcat_<DD.MM.YY_HH.mm>_<TZ>.txt`` using the host timezone offset.
Streaming/live logcat is out of scope (§9).
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class LogcatModule(QWidget):
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
