"""Application status bar (Spec §2.1).

Left widget: persistent device indicator. Right widget: transient messages
auto-cleared after 4 seconds. Strings come from ``core.strings`` — no
literals here.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QStatusBar, QWidget

from ..core.device_context import DeviceContext

NO_DEVICE_TEXT = "No device selected"
MESSAGE_TIMEOUT_MS = 4000


class AppStatusBar(QStatusBar):
    """Status bar with persistent device indicator + transient message."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSizeGripEnabled(False)

        self._device_label = QLabel(NO_DEVICE_TEXT, self)
        self._device_label.setObjectName("statusDevice")
        self._device_label.setProperty("secondary", "true")
        self.addWidget(self._device_label, 1)

        self._message_label = QLabel("", self)
        self._message_label.setObjectName("statusMessage")
        self._message_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.addPermanentWidget(self._message_label, 0)

        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_message)

    def update_device(self, ctx: Optional[DeviceContext]) -> None:
        if ctx is None:
            self._device_label.setText(NO_DEVICE_TEXT)
            return
        conn = "USB" if ctx.connection_type == "usb" else "Wi-Fi"
        self._device_label.setText(f"{ctx.model} ({ctx.serial}) · {conn}")

    def show_message(self, text: str) -> None:
        self._message_label.setText(text)
        self._clear_timer.start(MESSAGE_TIMEOUT_MS)

    def _clear_message(self) -> None:
        self._message_label.setText("")


__all__ = ["AppStatusBar", "NO_DEVICE_TEXT", "MESSAGE_TIMEOUT_MS"]
