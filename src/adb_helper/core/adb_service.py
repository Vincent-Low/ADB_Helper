"""ADB Service facade.

Spec §5. Singleton owning :class:`CommandRunner`, :class:`ProcessManager`,
and :class:`DeviceMonitor`. CLAUDE.md invariant 1: the only entry point for
ADB I/O. Modules import :func:`get_adb_service` — never instantiate the
sub-components directly.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from .command_runner import AdbCommand, CommandRunner, Priority, resolve_adb_binary
from .device_context import DeviceContext
from .device_monitor import DeviceMonitor
from .logger import get_logger
from .process_manager import ProcessManager

_log = get_logger(__name__)

DEFAULT_TIMEOUT_S = 30


class AdbService(QObject):
    """Singleton façade over the ADB service components."""

    activeDeviceChanged = Signal(object)  # DeviceContext | None

    _instance: Optional["AdbService"] = None

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.commands = CommandRunner(self)
        self.processes = ProcessManager(self)
        self.devices = DeviceMonitor(self.commands, self.processes, self)
        self._active: Optional[DeviceContext] = None
        self._started = False
        self.devices.deviceDisconnected.connect(self._on_device_disconnected)
        self.devices.deviceStateChanged.connect(self._on_device_state_changed)

    # --- lifecycle ------------------------------------------------------
    def start(self) -> None:
        if self._started:
            return
        _log.info("AdbService starting")
        self.devices.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        _log.info("AdbService stopping")
        self.devices.stop()
        self.processes.stop_all()
        self.commands.shutdown(wait=False)
        self._started = False

    # --- command helpers ------------------------------------------------
    def run_command(
        self,
        serial: Optional[str],
        args: list,
        priority: Priority = Priority.NORMAL,
        timeout: int = DEFAULT_TIMEOUT_S,
    ) -> str:
        """Enqueue a one-shot ADB command. Returns the command id."""
        return self.commands.submit(serial, list(args), int(timeout), priority)

    def shell(self, serial: str, cmd_string: str, timeout: int = DEFAULT_TIMEOUT_S) -> str:
        """Run ``adb -s <serial> shell <cmd_string>``. Returns the command id."""
        return self.commands.submit(
            serial,
            ["shell", cmd_string],
            int(timeout),
            Priority.HIGH,
        )

    def spawn_adb(
        self,
        process_id: str,
        serial: Optional[str],
        args: list,
        env: Optional[dict] = None,
    ) -> bool:
        """Spawn a managed ``adb`` subprocess via :class:`ProcessManager`.

        Stdout streams as raw bytes through ``processes.processOutput``;
        completion via ``processes.processStopped``. Use this for commands
        whose output is binary (e.g., ``exec-out screencap -p``) or
        long-lived.
        """
        adb = resolve_adb_binary()
        argv = [adb]
        if serial:
            argv += ["-s", serial]
        argv += list(args)
        return self.processes.start(process_id, argv, env=env)

    def spawn_process(
        self,
        process_id: str,
        argv: list,
        env: Optional[dict] = None,
    ) -> bool:
        """Spawn a managed non-ADB subprocess (e.g., scrcpy) via ProcessManager."""
        return self.processes.start(process_id, list(argv), env=env)

    # --- active device --------------------------------------------------
    @property
    def active_device(self) -> Optional[DeviceContext]:
        return self._active

    def set_active_device(self, ctx: Optional[DeviceContext]) -> None:
        if ctx == self._active:
            return
        self._active = ctx
        _log.info("active device = %s", ctx.serial if ctx else None)
        self.activeDeviceChanged.emit(ctx)

    def _on_device_disconnected(self, serial: str) -> None:
        if self._active is not None and self._active.serial == serial:
            self.set_active_device(None)

    def _on_device_state_changed(self, ctx: DeviceContext) -> None:
        if self._active is not None and self._active.serial == ctx.serial:
            self._active = ctx
            self.activeDeviceChanged.emit(ctx)


def get_adb_service() -> AdbService:
    """Return the process-wide :class:`AdbService` singleton."""
    if AdbService._instance is None:
        AdbService._instance = AdbService()
    return AdbService._instance


def shutdown_adb_service() -> None:
    if AdbService._instance is not None:
        AdbService._instance.stop()
        AdbService._instance = None


__all__ = [
    "AdbService",
    "AdbCommand",
    "Priority",
    "get_adb_service",
    "shutdown_adb_service",
    "DEFAULT_TIMEOUT_S",
]
