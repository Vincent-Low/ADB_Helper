"""ConnectionsBridge — device discovery, Wi-Fi pair/connect, paired-device DB."""
from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import Signal, Slot

from ...core.adb_service import AdbService
from ...core.db_manager import DatabaseManager
from .base import BridgeBase, to_jsonable


class ConnectionsBridge(BridgeBase):
    deviceConnected = Signal("QVariant")
    deviceDisconnected = Signal(str)
    deviceStateChanged = Signal("QVariant")
    activeDeviceChanged = Signal("QVariant")
    commandFinished = Signal(str, "QVariant")
    commandFailed = Signal(str, "QVariant")

    def __init__(self, adb: AdbService, db: DatabaseManager) -> None:
        super().__init__()
        self._adb = adb
        self._db = db
        # Track ONLY our own pair/connect/disconnect cmd_ids so we don't
        # spam Vue with every install / screenshot / getprop result.
        self._owned_cmd_ids: set[str] = set()

        adb.devices.deviceConnected.connect(
            lambda ctx: self.deviceConnected.emit(to_jsonable(ctx))
        )
        adb.devices.deviceDisconnected.connect(self.deviceDisconnected.emit)
        adb.devices.deviceStateChanged.connect(
            lambda ctx: self.deviceStateChanged.emit(to_jsonable(ctx))
        )
        adb.activeDeviceChanged.connect(
            lambda ctx: self.activeDeviceChanged.emit(to_jsonable(ctx))
        )
        adb.commands.commandFinished.connect(self._on_cmd_finished)
        adb.commands.commandFailed.connect(self._on_cmd_failed)

    def _track(self, cmd_id: str) -> str:
        self._owned_cmd_ids.add(cmd_id)
        return cmd_id

    def _on_cmd_finished(self, cid: str, result) -> None:
        if cid in self._owned_cmd_ids:
            self._owned_cmd_ids.discard(cid)
            self.commandFinished.emit(cid, to_jsonable(result))

    def _on_cmd_failed(self, cid: str, result) -> None:
        if cid in self._owned_cmd_ids:
            self._owned_cmd_ids.discard(cid)
            self.commandFailed.emit(cid, to_jsonable(result))

    # --- devices --------------------------------------------------------
    @Slot(result="QVariant")
    def listDevices(self) -> List[Any]:
        return [to_jsonable(d) for d in self._adb.devices.known_devices()]

    @Slot(result="QVariant")
    def activeDevice(self) -> Any:
        return to_jsonable(self._adb.active_device)

    @Slot(str)
    def setActiveDevice(self, serial: str) -> None:
        for d in self._adb.devices.known_devices():
            if d.serial == serial:
                self._adb.set_active_device(d)
                return
        self._adb.set_active_device(None)

    @Slot()
    def clearActiveDevice(self) -> None:
        self._adb.set_active_device(None)

    # --- connect/pair/disconnect ---------------------------------------
    @Slot(str, int, str, result=str)
    def pair(self, ip: str, port: int, pin: str) -> str:
        return self._track(
            self._adb.run_command(None, ["pair", f"{ip}:{int(port)}", pin], timeout=60)
        )

    @Slot(str, int, result=str)
    def connect(self, ip: str, port: int) -> str:
        return self._track(
            self._adb.run_command(None, ["connect", f"{ip}:{int(port)}"], timeout=30)
        )

    @Slot(str, result=str)
    def disconnect(self, target: str) -> str:
        return self._track(
            self._adb.run_command(None, ["disconnect", target], timeout=15)
        )

    # --- paired devices DB ---------------------------------------------
    @Slot(result="QVariant")
    def listPaired(self) -> List[Any]:
        return self._db.get_paired_devices()

    @Slot(str, str, "QVariant")
    def savePaired(self, ip: str, alias: str, connect_port: Optional[int]) -> None:
        port = int(connect_port) if connect_port not in (None, "", 0) else None
        self._db.save_paired_device(ip, alias, port)

    @Slot(str)
    def forgetPaired(self, ip: str) -> None:
        self._db.delete_paired_device(ip)

    @Slot(str, str)
    def renamePaired(self, ip: str, alias: str) -> None:
        self._db.update_paired_alias(ip, alias)

    @Slot(str)
    def touchPaired(self, ip: str) -> None:
        self._db.touch_paired_device(ip)


__all__ = ["ConnectionsBridge"]
