"""ScrcpyBridge — binary discovery / download + launcher.

scrcpy is launched as a separate top-level window via ProcessManager —
never embedded in the QWebEngineView (spec §3.4).
"""
from __future__ import annotations

import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Signal, Slot

from ...core import paths, platform as _platform
from ...core.adb_service import AdbService
from ...core.command_runner import resolve_adb_binary
from ...core.downloader import AtomicDownloader
from ...core.logger import get_logger
from ...core.settings_manager import SettingsManager
from .base import BridgeBase

from ...core.archive_utils import (
    extract_archive as _extract_archive,
    parse_sha256sum as _parse_sha256sum,
)

_log = get_logger(__name__)

_GITHUB_OWNER = "Genymobile"
_GITHUB_REPO = "scrcpy"
_CACHE_FILENAME = "api_cache.json"

_ASSET_RE_LINUX = re.compile(r"^scrcpy-linux-x86_64-v[\d.]+\.tar\.gz$")
_ASSET_RE_WIN = re.compile(r"^scrcpy-win64-v[\d.]+\.zip$")


class ScrcpyBridge(BridgeBase):
    statusChanged = Signal(str)                # human-readable status
    binaryReady = Signal("QVariant")           # {ok, path, version, message}
    launchResult = Signal("QVariant")          # {ok, pid, message}
    processStopped = Signal(str, int)          # pid, rc

    def __init__(self, adb: AdbService, settings: SettingsManager) -> None:
        super().__init__()
        self._adb = adb
        self._settings = settings
        self._binary: Optional[Path] = None
        self._version: str = ""

        adb.processes.processStopped.connect(self._on_process_stopped)

    @Slot(result="QVariant")
    def state(self) -> Dict[str, Any]:
        binary = self._discover_existing()
        if binary is not None:
            self._binary = binary
            self._version = _infer_version(binary)
        return {
            "ready": self._binary is not None,
            "version": self._version,
            "path": str(self._binary) if self._binary else "",
        }

    @Slot()
    def ensureBinary(self) -> None:
        existing = self._discover_existing()
        if existing is not None:
            self._binary = existing
            self._version = _infer_version(existing)
            self.binaryReady.emit({
                "ok": True,
                "path": str(existing),
                "version": self._version,
                "message": "",
            })
            return

        self.statusChanged.emit("Checking scrcpy binary…")
        threading.Thread(
            target=self._fetch_and_install,
            name="scrcpy-bridge-install",
            daemon=True,
        ).start()

    @Slot("QVariant", result="QVariant")
    def launch(self, options: Dict[str, Any]) -> Dict[str, Any]:
        if self._binary is None or not self._binary.exists():
            return {"ok": False, "pid": "", "message": "scrcpy binary not installed"}
        ctx = self._adb.active_device
        if ctx is None or ctx.status != "online":
            return {"ok": False, "pid": "", "message": "no active device"}

        argv: List[str] = [str(self._binary), "-s", ctx.serial]
        bitrate = options.get("bitrate")
        if bitrate:
            argv += ["--video-bit-rate", str(bitrate)]
        max_res = options.get("maxResolution")
        if max_res:
            argv += ["--max-size", str(max_res)]
        orientation = options.get("orientation")
        if orientation is not None and orientation != "":
            argv += [f"--capture-orientation={orientation}"]
        if options.get("stayAwake"):
            argv += ["--stay-awake"]
        if options.get("showTouches"):
            argv += ["--show-touches"]
        if options.get("turnScreenOff"):
            argv += ["--turn-screen-off"]

        env = dict(os.environ)
        for var in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR",
                    "DBUS_SESSION_BUS_ADDRESS"):
            if var in os.environ:
                env[var] = os.environ[var]
        env["ADB"] = resolve_adb_binary()
        adb_dir = str(Path(env["ADB"]).parent)
        env["PATH"] = adb_dir + os.pathsep + env.get("PATH", "")

        pid = f"scrcpy-{uuid.uuid4()}"
        ok = self._adb.spawn_process(pid, argv, env=env)
        return {
            "ok": ok,
            "pid": pid if ok else "",
            "message": "" if ok else "spawn failed",
            "argv": argv,
        }

    # --- internals -----------------------------------------------------
    def _discover_existing(self) -> Optional[Path]:
        scrcpy_root = paths.scrcpy_dir()
        if not scrcpy_root.exists():
            return None
        name = "scrcpy.exe" if _platform.IS_WINDOWS else "scrcpy"
        for candidate in scrcpy_root.rglob(name):
            if candidate.is_file():
                return candidate
        return None

    def _fetch_and_install(self) -> None:
        scrcpy_root = paths.scrcpy_dir()
        scrcpy_root.mkdir(parents=True, exist_ok=True)
        cache_path = scrcpy_root / _CACHE_FILENAME

        release = AtomicDownloader.get_latest_github_release(
            _GITHUB_OWNER, _GITHUB_REPO, cache_path=cache_path
        )
        if release is None:
            self.binaryReady.emit({"ok": False, "path": "", "version": "",
                                   "message": "Failed to fetch scrcpy release info."})
            return
        asset_re = _ASSET_RE_WIN if _platform.IS_WINDOWS else _ASSET_RE_LINUX
        assets = release.get("assets") or []
        asset = next((a for a in assets if asset_re.match(a.get("name", ""))), None)
        if asset is None:
            self.binaryReady.emit({"ok": False, "path": "", "version": "",
                                   "message": "No scrcpy asset for this platform."})
            return

        asset_name = asset["name"]
        asset_url = asset["browser_download_url"]
        sha_asset = next(
            (a for a in assets if a.get("name") == f"{asset_name}.sha256sum"), None
        )
        expected_sha: Optional[str] = None
        if sha_asset is not None:
            sha_dest = scrcpy_root / f"{asset_name}.sha256sum"
            if AtomicDownloader.download(sha_asset["browser_download_url"], sha_dest):
                expected_sha = _parse_sha256sum(sha_dest)

        archive_dest = scrcpy_root / asset_name
        ok = AtomicDownloader.download(asset_url, archive_dest, expected_sha)
        if not ok:
            self.binaryReady.emit({"ok": False, "path": "", "version": "",
                                   "message": "Download failed."})
            return

        try:
            extracted_root = _extract_archive(archive_dest, scrcpy_root)
        except Exception as exc:  # noqa: BLE001 — error surfaced to UI
            _log.error("scrcpy extract failed: %s", exc)
            self.binaryReady.emit({"ok": False, "path": "", "version": "",
                                   "message": "Extract failed."})
            return

        bin_name = "scrcpy.exe" if _platform.IS_WINDOWS else "scrcpy"
        binary = next((p for p in extracted_root.rglob(bin_name) if p.is_file()), None)
        if binary is None:
            self.binaryReady.emit({"ok": False, "path": "", "version": "",
                                   "message": "Binary missing after extract."})
            return
        if not _platform.IS_WINDOWS:
            try:
                os.chmod(binary, 0o755)
            except OSError:
                pass
        version = (release.get("tag_name") or "").lstrip("v")
        self._binary = binary
        self._version = f"v{version}" if version else ""
        self.binaryReady.emit({
            "ok": True,
            "path": str(binary),
            "version": self._version,
            "message": "",
        })

    def _on_process_stopped(self, pid: str, rc: int) -> None:
        if pid.startswith("scrcpy-"):
            self.processStopped.emit(pid, int(rc))


def _infer_version(binary: Path) -> str:
    for part in binary.parts:
        m = re.search(r"v\d+(?:\.\d+)+", part)
        if m:
            return m.group(0)
    return ""


__all__ = ["ScrcpyBridge"]
