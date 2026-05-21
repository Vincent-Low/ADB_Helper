"""WebMainWindow — host for the Vue 3 SPA inside QWebEngineView.

Responsibilities:
- own AdbWebView + QWebChannel
- register all per-module bridges
- forward Qt-side file drops to InstallerBridge
- in dev mode (ADBH_DEV=1): spawn Vite, poll readiness async, then load
- in production: load file://.../frontend_dist/index.html via sys._MEIPASS
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QByteArray, QProcess, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QMainWindow, QMessageBox, QWidget

from ..core.adb_service import AdbService
from ..core.db_manager import DatabaseManager
from ..core.logger import get_logger
from ..core.settings_manager import SettingsManager
from ..ui.theme_manager import ThemeManager
from .bridge.app_bridge import AppBridge
from .bridge.apps_bridge import AppsBridge
from .bridge.base import BridgeBase
from .bridge.buttons_bridge import ButtonsBridge
from .bridge.connections_bridge import ConnectionsBridge
from .bridge.info_bridge import InfoBridge
from .bridge.installer_bridge import InstallerBridge
from .bridge.logcat_bridge import LogcatBridge
from .bridge.scrcpy_bridge import ScrcpyBridge
from .bridge.settings_bridge import SettingsBridge
from .bridge.terminal_bridge import TerminalBridge
from .web_view import AdbWebView

_log = get_logger(__name__)

DEFAULT_W = 1440
DEFAULT_H = 900
MIN_W = 1100
MIN_H = 700

DEV_URL = os.environ.get("ADBH_DEV_URL", "http://127.0.0.1:5173/")
DEV_FLAG = os.environ.get("ADBH_DEV") == "1"


def _frontend_dist_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "frontend_dist"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3] / "frontend_dist"


def _frontend_src_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "frontend"


class WebMainWindow(QMainWindow):
    """Top-level window — replaces the native PySide6 shell."""

    def __init__(
        self,
        adb: AdbService,
        settings: SettingsManager,
        theme_mgr: ThemeManager,
        db: DatabaseManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ADB_Helper")
        self.setMinimumSize(MIN_W, MIN_H)
        self.resize(DEFAULT_W, DEFAULT_H)

        self._adb = adb
        self._settings = settings
        self._theme = theme_mgr
        self._db = db

        self._view = AdbWebView(self)
        self.setCentralWidget(self._view)

        self._channel = QWebChannel(self._view.page())
        self._view.page().setWebChannel(self._channel)

        self._bridges: Dict[str, BridgeBase] = {
            "app":         AppBridge(adb, settings, theme_mgr),
            "connections": ConnectionsBridge(adb, db),
            "terminal":    TerminalBridge(adb, db),
            "installer":   InstallerBridge(adb),
            "scrcpy":      ScrcpyBridge(adb, settings),
            "buttons":     ButtonsBridge(adb, settings),
            "info":        InfoBridge(adb),
            "apps":        AppsBridge(adb),
            "logcat":      LogcatBridge(adb, settings),
            "settings":    SettingsBridge(settings, db),
        }
        for name, obj in self._bridges.items():
            self._channel.registerObject(name, obj)

        self._view.filesDropped.connect(
            self._bridges["installer"].on_files_dropped  # type: ignore[attr-defined]
        )

        self._vite_proc: Optional[QProcess] = None
        self._nam: Optional[QNetworkAccessManager] = None
        self._poll_timer: Optional[QTimer] = None
        self._poll_attempts = 0

        self._restore_geometry()
        self._load_frontend()

    # ------------------------------------------------------------------
    # Frontend loading
    # ------------------------------------------------------------------
    def _load_frontend(self) -> None:
        if DEV_FLAG:
            self._start_vite_then_load()
            return
        index = _frontend_dist_dir() / "index.html"
        if not index.exists():
            QMessageBox.critical(
                self, "ADB_Helper",
                f"frontend_dist/index.html not found at {index}.\n"
                "Run `npm --prefix frontend run build` first."
            )
            self.close()
            return
        self._view.load(QUrl.fromLocalFile(str(index)))

    def _start_vite_then_load(self) -> None:
        # Windows ships npm as a .cmd script — QProcess can't exec it without
        # the extension.
        program = "npm.cmd" if platform.system() == "Windows" else "npm"
        proc = QProcess(self)
        proc.setProgram(program)
        proc.setArguments([
            "run", "dev", "--",
            "--port", "5173", "--strictPort", "--host", "127.0.0.1",
        ])
        proc.setWorkingDirectory(str(_frontend_src_dir()))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.start()
        self._vite_proc = proc

        # Async readiness probe — never blocks the UI thread.
        self._nam = QNetworkAccessManager(self)
        self._poll_attempts = 0
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(300)
        self._poll_timer.timeout.connect(self._poll_dev_server)
        self._poll_timer.start()

    def _poll_dev_server(self) -> None:
        assert self._nam is not None and self._poll_timer is not None
        self._poll_attempts += 1
        if self._poll_attempts > 100:  # ~30 s ceiling
            self._poll_timer.stop()
            QMessageBox.critical(
                self, "ADB_Helper",
                "Vite dev server failed to start on 127.0.0.1:5173.\n"
                "Try `npm --prefix frontend install` and rerun.",
            )
            return
        reply = self._nam.get(QNetworkRequest(QUrl(DEV_URL)))

        def _on_finished() -> None:
            if reply.error() == reply.NetworkError.NoError:
                if self._poll_timer is not None:
                    self._poll_timer.stop()
                self._view.load(QUrl(DEV_URL))
            reply.deleteLater()

        reply.finished.connect(_on_finished)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def focus_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._persist_geometry()
        self._shutdown_vite()
        super().closeEvent(event)

    def _shutdown_vite(self) -> None:
        if self._vite_proc is None:
            return
        if self._vite_proc.state() == QProcess.ProcessState.NotRunning:
            return
        # Windows: `npm run dev` wraps a child node process — terminate() reaches
        # only the wrapper, leaving the server orphaned on :5173.  Hard-kill the
        # tree via taskkill /F /T, then kill() the wrapper for good measure.
        if platform.system() == "Windows":
            try:
                pid = int(self._vite_proc.processId())
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True, timeout=2,
                )
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        self._vite_proc.kill()
        self._vite_proc.waitForFinished(2000)

    # ------------------------------------------------------------------
    # Geometry persistence
    # ------------------------------------------------------------------
    def _restore_geometry(self) -> None:
        geom_b64 = self._settings.get("window_geometry", "")
        if isinstance(geom_b64, str) and geom_b64:
            try:
                ba = QByteArray.fromBase64(geom_b64.encode("ascii"))
                self.restoreGeometry(ba)
            except (ValueError, TypeError):
                pass

    def _persist_geometry(self) -> None:
        try:
            ba = self.saveGeometry()
            self._settings.set("window_geometry",
                               bytes(ba.toBase64()).decode("ascii"))
        except (RuntimeError, ValueError):
            pass


__all__ = ["WebMainWindow"]
