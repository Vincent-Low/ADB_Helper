"""MainWindow — shell that hosts Sidebar + module stack + status bar.

Spec §2.1: default 1280×800, minimum 960×600; geometry persisted via
SettingsManager. Sidebar auto-collapses below 1100 px width (Redesign v1.0).
Active device mid-operation disconnect → modal + nav to Connections (Spec §7).
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.adb_service import AdbService
from ..core.device_context import DeviceContext
from ..core.logger import get_logger
from ..core.registry import ModuleRegistry
from ..core.settings_manager import SettingsManager
from ..core import strings
from .sidebar import Sidebar
from .status_bar import AppStatusBar
from .theming import Theme, ThemeManager

_log = get_logger(__name__)

DEFAULT_W = 1280
DEFAULT_H = 800
MIN_W = 960
MIN_H = 600

DEFAULT_MODULE_ID = "connections"


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(
        self,
        registry: ModuleRegistry,
        adb_service: AdbService,
        settings: SettingsManager,
        theme_manager: ThemeManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(strings.APP_NAME)
        self.setMinimumSize(QSize(MIN_W, MIN_H))
        self.resize(DEFAULT_W, DEFAULT_H)

        self._registry = registry
        self._adb = adb_service
        self._settings = settings
        self._theme = theme_manager
        self._modules: Dict[str, QWidget] = {}
        self._active_module_id: Optional[str] = None

        self._build_ui()
        self._wire_signals()
        self._restore_geometry()

        if self._registry.get_all():
            initial = DEFAULT_MODULE_ID
            if not any(d.id == initial for d in self._registry.get_all()):
                initial = self._registry.get_all()[0].id
            self.navigate_to(initial)

    # --- construction ----------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("appCentral")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QWidget(central)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._sidebar = Sidebar(self._registry, body)
        self._stack = QStackedWidget(body)

        body_layout.addWidget(self._sidebar)
        body_layout.addWidget(self._stack, 1)

        for desc in self._registry.get_all():
            widget = desc.widget_class()
            self._modules[desc.id] = widget
            self._stack.addWidget(widget)

        root.addWidget(body, 1)

        self._status = AppStatusBar(self)
        self.setStatusBar(self._status)
        self.setCentralWidget(central)

    def _wire_signals(self) -> None:
        self._sidebar.module_selected.connect(self.navigate_to)
        self._adb.activeDeviceChanged.connect(self._on_active_device_changed)
        self._adb.devices.deviceDisconnected.connect(self._on_device_disconnected)
        self._theme.theme_changed.connect(self._on_theme_changed)
        # TODO: wire status bar battery / ADB-daemon segments once
        # AdbService exposes batteryChanged / daemonStateChanged signals.
        # Until then the bar stays on its safe defaults (battery hidden,
        # ADB shown as running).

    # --- public API ------------------------------------------------------
    def navigate_to(self, module_id: str) -> None:
        if module_id not in self._modules:
            _log.warning("MainWindow: unknown module_id=%r", module_id)
            return
        if module_id == self._active_module_id:
            return

        if self._active_module_id is not None:
            prev = self._modules[self._active_module_id]
            self._safe_call(prev, "on_deactivate")

        widget = self._modules[module_id]
        self._stack.setCurrentWidget(widget)
        self._sidebar.set_active(module_id)
        self._active_module_id = module_id
        self._safe_call(widget, "on_activate")
        ctx = self._adb.active_device
        if ctx is not None:
            self._safe_call(widget, "on_device_changed", ctx)

    def focus_window(self) -> None:
        """Handle SingleInstance focus_requested."""
        self.show()
        self.raise_()
        self.activateWindow()

    # --- event handlers --------------------------------------------------
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sidebar.update_for_window_width(event.size().width())

    def closeEvent(self, event) -> None:
        self._persist_geometry()
        super().closeEvent(event)

    def _on_active_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._status.update_device(ctx)
        if self._active_module_id is None:
            return
        widget = self._modules[self._active_module_id]
        if ctx is None:
            self._safe_call(widget, "on_device_disconnected")
        else:
            self._safe_call(widget, "on_device_changed", ctx)

    def _on_device_disconnected(self, serial: str) -> None:
        active = self._adb.active_device
        if active is None or active.serial != serial:
            return
        if self._active_module_id == "installer":
            return
        model = active.model or "device"
        QMessageBox.warning(
            self,
            strings.APP_NAME,
            strings.MSG_DEVICE_DISCONNECTED.format(model=model, serial=serial),
        )
        self._adb.set_active_device(None)
        self.navigate_to("connections")

    def _on_theme_changed(self, theme: Theme) -> None:
        _log.info("MainWindow: theme changed -> %s", theme.value)
        app = QApplication.instance()
        if app is not None:
            for w in app.allWidgets():
                style = w.style()
                style.unpolish(w)
                style.polish(w)
                w.update()
        # Sidebar self-subscribes to theme_changed and re-renders its SVG
        # icons against the new tokens — no extra call needed here.

    # --- geometry --------------------------------------------------------
    def _restore_geometry(self) -> None:
        geom_b64 = self._settings.get("window_geometry", "")
        if isinstance(geom_b64, str) and geom_b64:
            try:
                ba = QByteArray.fromBase64(geom_b64.encode("ascii"))
                if not self.restoreGeometry(ba):
                    self.resize(DEFAULT_W, DEFAULT_H)
            except Exception:
                self.resize(DEFAULT_W, DEFAULT_H)

    def _persist_geometry(self) -> None:
        try:
            ba = self.saveGeometry()
            b64 = bytes(ba.toBase64()).decode("ascii")
            self._settings.set("window_geometry", b64)
        except Exception as e:
            _log.warning("MainWindow: failed to persist geometry: %s", e)

    # --- helpers ---------------------------------------------------------
    @staticmethod
    def _safe_call(widget: QWidget, method: str, *args) -> None:
        fn = getattr(widget, method, None)
        if fn is None:
            return
        try:
            fn(*args)
        except NotImplementedError:
            pass
        except Exception as e:
            _log.warning("module %s.%s raised: %s", type(widget).__name__, method, e)


__all__ = ["MainWindow", "DEFAULT_W", "DEFAULT_H", "MIN_W", "MIN_H"]
