"""DeviceContext — immutable snapshot of an ADB-connected device.

Spec §5.3 / §8. Passed to modules via ``IModule.on_device_changed``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConnectionType = Literal["usb", "wifi"]
DeviceStatus = Literal["online", "offline", "unauthorized"]


@dataclass(frozen=True)
class DeviceContext:
    serial: str
    model: str
    manufacturer: str
    sdk_version: str
    abi: str
    connection_type: ConnectionType
    status: DeviceStatus

    @property
    def human_label(self) -> str:
        return f"{self.model} ({self.serial})"
