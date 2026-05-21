"""LogcatBridge — one-shot ``adb logcat -d`` export to host file."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Dict, List, Optional

from PySide6.QtCore import Signal, Slot

from ...core import paths
from ...core.adb_service import AdbService
from ...core.logger import get_logger
from ...core.settings_manager import SettingsManager
from .base import BridgeBase

_log = get_logger(__name__)

_RECENT_KEY = "logcat_recent"
_RECENT_MAX = 10


class LogcatBridge(BridgeBase):
    exportStarted = Signal(str)             # absolute path
    exportFinished = Signal("QVariant")     # {ok, path, size_bytes, message}

    def __init__(self, adb: AdbService, settings: SettingsManager) -> None:
        super().__init__()
        self._adb = adb
        self._settings = settings
        self._active_pid: Optional[str] = None
        self._active_path: Optional[Path] = None
        self._file: Optional[IO[bytes]] = None

        adb.processes.processOutput.connect(self._on_output)
        adb.processes.processStopped.connect(self._on_stopped)

    @Slot(result="QVariant")
    def state(self) -> Dict[str, Any]:
        folder = self._settings.get("logcat_folder", str(paths.logcat_dir()))
        return {
            "folder": folder,
            "filename_pattern": "logcat_<date>_<time>_GMT±N.txt",
            "mode": "Single-shot (-d flag)",
            "recent": self._settings.get(_RECENT_KEY, []) or [],
            "in_progress": self._active_pid is not None,
        }

    @Slot(str)
    def setFolder(self, folder: str) -> None:
        self._settings.set("logcat_folder", folder)

    @Slot(str, result="QVariant")
    def export(self, serial: str) -> Dict[str, Any]:
        if self._active_pid is not None:
            return {"ok": False, "message": "export already running"}
        if not serial:
            return {"ok": False, "message": "no serial"}

        now = datetime.now(timezone.utc).astimezone()
        offset = now.utcoffset()
        total_s = int(offset.total_seconds()) if offset else 0
        sign = "+" if total_s >= 0 else "-"
        hh = abs(total_s) // 3600
        tz_str = f"GMT{sign}{hh}"
        filename = f"logcat_{now.strftime('%d.%m.%y_%H.%M')}_{tz_str}.txt"

        folder = Path(self._settings.get("logcat_folder", str(paths.logcat_dir())))
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return {"ok": False, "message": str(exc)}

        path = folder / filename
        try:
            self._file = path.open("wb")
        except OSError as exc:
            return {"ok": False, "message": str(exc)}

        pid = f"logcat-{uuid.uuid4()}"
        ok = self._adb.spawn_adb(pid, serial, ["logcat", "-d"])
        if not ok:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
            return {"ok": False, "message": "spawn failed"}

        self._active_pid = pid
        self._active_path = path
        self.exportStarted.emit(str(path))
        return {"ok": True, "pid": pid, "path": str(path)}

    # --- internal handlers --------------------------------------------
    def _on_output(self, pid: str, data: bytes) -> None:
        if pid != self._active_pid:
            return
        if self._file is None:
            return
        try:
            self._file.write(data)
        except OSError as exc:
            _log.error("logcat write failed: %s", exc)

    def _on_stopped(self, pid: str, rc: int) -> None:
        if pid != self._active_pid:
            return
        self._active_pid = None
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
        path = self._active_path
        self._active_path = None
        if path is None:
            self.exportFinished.emit({"ok": False, "path": "", "size_bytes": 0,
                                      "message": "no path"})
            return
        size = path.stat().st_size if path.exists() else 0
        ok = rc == 0 and size > 0
        if ok:
            self._push_recent(str(path), size)
        elif path.exists():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        self.exportFinished.emit({
            "ok": ok, "path": str(path), "size_bytes": size,
            "message": "" if ok else f"rc={rc}",
        })

    def _push_recent(self, path: str, size: int) -> None:
        recent: List[Dict[str, Any]] = list(self._settings.get(_RECENT_KEY, []) or [])
        recent.insert(0, {
            "path": path, "size": size,
            "saved": datetime.now().isoformat(timespec="seconds"),
        })
        recent = recent[:_RECENT_MAX]
        self._settings.set(_RECENT_KEY, recent)


__all__ = ["LogcatBridge"]
