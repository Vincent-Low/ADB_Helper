"""ADB Service layer — the ONLY module that talks to ``adb``.

CLAUDE.md invariant 1. Spec §5.

Three responsibilities live here:

* :class:`CommandRunner` — thread-pooled one-shot commands with timeout and
  Normal/High priority (§5.1).
* :class:`ProcessManager` — long-lived processes: terminal PTY, scrcpy,
  logcat export (§5.2).
* :class:`DeviceMonitor` — primary ``adb track-devices``, fallback ``adb
  devices`` polled every 3 s (§5.3).

All three expose Qt signals so the UI subscribes instead of polling. A single
:class:`AdbService` singleton wires them together and is the only object
modules import. The error parser that translates known ADB strings into
English user-facing messages also lives here.

Stub: class skeletons and signatures only.
"""
from __future__ import annotations

from typing import Optional

from .models import CommandPriority, CommandResult, DeviceContext


class CommandRunner:
    """Thread-pooled one-shot ADB commands (§5.1)."""

    def submit(
        self,
        serial: Optional[str],
        args: tuple[str, ...],
        timeout_s: int,
        priority: CommandPriority = CommandPriority.NORMAL,
    ) -> str:
        """Queue a command. Returns a command id used in Qt signals."""
        raise NotImplementedError

    def cancel(self, command_id: str) -> None:
        raise NotImplementedError


class ProcessManager:
    """Long-lived ADB processes — terminal PTY, scrcpy, logcat export (§5.2)."""

    def start(self, args: tuple[str, ...]) -> str:
        """Start a managed process. Returns a process id used in Qt signals."""
        raise NotImplementedError

    def stop(self, process_id: str) -> None:
        raise NotImplementedError

    def stop_all(self) -> None:
        """Called on application exit to terminate all managed processes."""
        raise NotImplementedError


class DeviceMonitor:
    """Tracks the set of connected ADB devices (§5.3)."""

    def start(self) -> None:
        """Begin monitoring. Prefers ``adb track-devices``; falls back to a
        3-second poll of ``adb devices`` if the persistent stream fails."""
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


def translate_adb_error(raw: str) -> str:
    """Map a known raw ADB/bundletool error string to an English message.

    Falls back to ``raw`` when no mapping is known. The raw output is always
    surfaced to the UI alongside the translation (§5.4 / §7).
    """
    raise NotImplementedError


class AdbService:
    """Facade owning :class:`CommandRunner`, :class:`ProcessManager`, and
    :class:`DeviceMonitor`. Modules see this singleton only."""

    def __init__(self) -> None:
        self.commands = CommandRunner()
        self.processes = ProcessManager()
        self.devices = DeviceMonitor()

    def start(self) -> None:
        raise NotImplementedError

    def shutdown(self) -> None:
        raise NotImplementedError

    def active_device(self) -> Optional[DeviceContext]:
        raise NotImplementedError

    def set_active_device(self, ctx: Optional[DeviceContext]) -> None:
        raise NotImplementedError

    def last_command_result(self, command_id: str) -> Optional[CommandResult]:
        raise NotImplementedError
