"""Core data models shared across the ADB service and the UI.

Stub — fields will be populated as the ADB service is implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ConnectionType(str, Enum):
    USB = "usb"
    WIFI = "wifi"
    UNKNOWN = "unknown"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"


@dataclass(frozen=True)
class DeviceContext:
    """Snapshot of a device passed to modules via ``IModule.on_device_changed``.

    Spec §5.3.
    """

    serial: str
    model: str = ""
    manufacturer: str = ""
    sdk_version: int = 0
    abi: str = ""
    connection_type: ConnectionType = ConnectionType.UNKNOWN
    status: DeviceStatus = DeviceStatus.OFFLINE
    ip_address: Optional[str] = None


class CommandPriority(str, Enum):
    NORMAL = "normal"
    HIGH = "high"


class CommandStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class CommandResult:
    """Outcome of a one-shot ADB command (Spec §5.1)."""

    command_id: str
    status: CommandStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: int = 0
