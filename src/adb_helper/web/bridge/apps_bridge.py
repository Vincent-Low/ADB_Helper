"""AppsBridge — install package listing, RAM/storage meters, app actions.

Reuses pure parsers from modules/apps.py so the Vue layer never sees raw
``pm list`` output.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Signal, Slot

from ...core.adb_service import AdbService
from ...core.command_runner import Priority
from ...core.logger import get_logger
from .base import BridgeBase, to_jsonable

from ...core.apps_parsers import (
    parse_df as _parse_df,
    parse_meminfo as _parse_meminfo,
    parse_pm_dump as _parse_pm_dump,
    parse_pm_list as _parse_pm_list,
)

_log = get_logger(__name__)

_LIST_TIMEOUT_S = 30
_DUMP_TIMEOUT_S = 15
_RESOURCE_TIMEOUT_S = 10
_UNINSTALL_TIMEOUT_S = 60
_PULL_TIMEOUT_S = 120
_TOGGLE_TIMEOUT_S = 20


class AppsBridge(BridgeBase):
    listLoaded = Signal("QVariant")    # {serial, apps:[{package,apk_path,type,status}]}
    appUpdated = Signal("QVariant")    # {package, name, status}
    metersUpdated = Signal("QVariant") # {ram:{used,total}, storage:{used,total}}
    actionFinished = Signal("QVariant")  # {action, package, ok, message}

    def __init__(self, adb: AdbService) -> None:
        super().__init__()
        self._adb = adb
        self._serial: str = ""
        self._apps: Dict[str, dict] = {}
        self._pending: dict[str, dict] = {}

        adb.commands.commandFinished.connect(self._on_finished)
        adb.commands.commandFailed.connect(self._on_failed)

    # --- public surface ------------------------------------------------
    @Slot(str)
    def loadAll(self, serial: str) -> None:
        if not serial:
            return
        for cid in list(self._pending):
            self._adb.commands.cancel(cid)
        self._pending.clear()
        self._apps.clear()
        self._serial = serial

        cid = self._adb.commands.submit(serial, ["shell", "pm", "list", "packages", "-f", "-3"],
                                        _LIST_TIMEOUT_S, Priority.NORMAL)
        self._pending[cid] = {"op": "list", "kind": "user"}
        cid = self._adb.commands.submit(serial, ["shell", "pm", "list", "packages", "-f", "-s"],
                                        _LIST_TIMEOUT_S, Priority.NORMAL)
        self._pending[cid] = {"op": "list", "kind": "system"}
        self._refresh_meters(serial)

    @Slot(str)
    def refreshMeters(self, serial: str) -> None:
        self._refresh_meters(serial)

    def _refresh_meters(self, serial: str) -> None:
        cid = self._adb.commands.submit(serial, ["shell", "cat", "/proc/meminfo"],
                                        _RESOURCE_TIMEOUT_S, Priority.NORMAL)
        self._pending[cid] = {"op": "meminfo"}
        cid = self._adb.commands.submit(serial, ["shell", "df", "/data"],
                                        _RESOURCE_TIMEOUT_S, Priority.NORMAL)
        self._pending[cid] = {"op": "df"}

    @Slot(str)
    def uninstall(self, package: str) -> str:
        if not self._serial or not package:
            return ""
        cid = self._adb.commands.submit(self._serial, ["uninstall", package],
                                        _UNINSTALL_TIMEOUT_S, Priority.NORMAL)
        self._pending[cid] = {"op": "uninstall", "package": package}
        return cid

    @Slot(str)
    def disablePackage(self, package: str) -> str:
        if not self._serial or not package:
            return ""
        cid = self._adb.commands.submit(
            self._serial, ["shell", "pm", "disable-user", "--user", "0", package],
            _TOGGLE_TIMEOUT_S, Priority.NORMAL,
        )
        self._pending[cid] = {"op": "disable", "package": package}
        return cid

    @Slot(str)
    def enablePackage(self, package: str) -> str:
        if not self._serial or not package:
            return ""
        cid = self._adb.commands.submit(
            self._serial, ["shell", "pm", "enable", "--user", "0", package],
            _TOGGLE_TIMEOUT_S, Priority.NORMAL,
        )
        self._pending[cid] = {"op": "enable", "package": package}
        return cid

    @Slot(str, str)
    def backupApk(self, package: str, dest: str) -> str:
        entry = self._apps.get(package)
        if not entry or not self._serial:
            return ""
        cid = self._adb.commands.submit(
            self._serial, ["pull", entry["apk_path"], dest],
            _PULL_TIMEOUT_S, Priority.NORMAL,
        )
        self._pending[cid] = {"op": "backup", "package": package, "dest": dest}
        return cid

    # --- service relays -------------------------------------------------
    def _on_finished(self, cid: str, result: Any) -> None:
        entry = self._pending.pop(cid, None)
        if entry is None:
            return
        op = entry.get("op", "")
        if op == "list":
            self._handle_list(entry["kind"], result.stdout)
            return
        if op == "dump":
            pkg = entry["package"]
            label, disabled = _parse_pm_dump(result.stdout)
            row = self._apps.get(pkg)
            if row is not None:
                if label:
                    row["name"] = label
                if disabled is not None:
                    row["status"] = "disabled" if disabled else "active"
                self.appUpdated.emit(dict(row))
            return
        if op == "meminfo":
            kib = _parse_meminfo(result.stdout)
            total = kib.get("MemTotal", 0)
            avail = kib.get("MemAvailable", 0)
            self.metersUpdated.emit({
                "kind": "ram",
                "used_mb": max((total - avail) // 1024, 0),
                "total_mb": total // 1024,
            })
            return
        if op == "df":
            used_kib, total_kib = _parse_df(result.stdout)
            self.metersUpdated.emit({
                "kind": "storage",
                "used_mb": used_kib // 1024,
                "total_mb": total_kib // 1024,
            })
            return
        if op in ("uninstall", "disable", "enable", "backup"):
            self.actionFinished.emit({
                "action": op, "package": entry.get("package", ""),
                "ok": True, "message": (result.stdout or "").strip(),
                "extra": to_jsonable(entry),
            })
            if op == "uninstall":
                self._apps.pop(entry.get("package", ""), None)
            return

    def _on_failed(self, cid: str, result: Any) -> None:
        entry = self._pending.pop(cid, None)
        if entry is None:
            return
        self.actionFinished.emit({
            "action": entry.get("op", ""),
            "package": entry.get("package", ""),
            "ok": False, "message": (result.stderr or result.status or "").strip(),
        })

    # --- list handler ---------------------------------------------------
    def _handle_list(self, kind: str, stdout: str) -> None:
        for apk_path, pkg in _parse_pm_list(stdout):
            if pkg in self._apps:
                continue
            self._apps[pkg] = {
                "package": pkg,
                "name": pkg,
                "apk_path": apk_path,
                "type": kind,
                "status": "active",
            }
        # Both lists done?
        list_pending = any(e.get("op") == "list" for e in self._pending.values())
        if list_pending:
            return
        self.listLoaded.emit({
            "serial": self._serial,
            "apps": [dict(e) for e in self._apps.values()],
        })
        # Queue dumps for label + status.
        for pkg in list(self._apps.keys()):
            cid = self._adb.commands.submit(
                self._serial,
                ["shell", f"pm dump {pkg} 2>/dev/null | grep -E 'enabled|label'"],
                _DUMP_TIMEOUT_S, Priority.NORMAL,
            )
            self._pending[cid] = {"op": "dump", "package": pkg}


__all__ = ["AppsBridge"]
