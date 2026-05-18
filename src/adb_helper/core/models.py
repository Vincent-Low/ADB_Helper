"""Core data models shared across the ADB service and the UI.

``DeviceContext`` lives in :mod:`adb_helper.core.device_context`; re-exported
here so legacy imports ``from ..core.models import DeviceContext`` keep working.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .device_context import ConnectionType, DeviceContext, DeviceStatus

__all__ = [
    "ConnectionType",
    "DeviceContext",
    "DeviceStatus",
    "CommandPriority",
    "CommandStatus",
    "CommandResult",
]


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
