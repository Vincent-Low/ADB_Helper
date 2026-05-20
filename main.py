"""ADB_Helper entry point (Spec §1.7, §2.1, §8)."""
from __future__ import annotations

import os
import sys
from typing import List

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

if hasattr(Qt, "AA_EnableHighDpiScaling"):
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, "AA_UseHighDpiPixmaps"):
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from adb_helper.core import strings
from adb_helper.core.adb_service import get_adb_service, shutdown_adb_service
from adb_helper.core.db_manager import DatabaseManager
from adb_helper.core.imodule import ModuleDescriptor
from adb_helper.core.logger import get_logger, init_logging
from adb_helper.core.paths import ensure_app_dirs
from adb_helper.core.registry import registry
from adb_helper.core.settings_manager import SettingsManager
from adb_helper.core.single_instance import SingleInstance
from adb_helper.modules.apps import AppsModule
from adb_helper.modules.connections import ConnectionsModule
from adb_helper.modules.device_buttons import DeviceButtonsModule
from adb_helper.modules.device_info import DeviceInfoModule
from adb_helper.modules.installer import InstallerModule
from adb_helper.modules.logcat import LogcatModule
from adb_helper.modules.scrcpy import ScrcpyModule
from adb_helper.modules.settings import SettingsModule
from adb_helper.modules.terminal import TerminalModule
from adb_helper.ui.main_window import MainWindow
from adb_helper.ui.theming import Theme, ThemeManager


def _module_descriptors() -> List[ModuleDescriptor]:
    """Sidebar order — Connections is default (Spec §3 module ordering)."""
    return [
        ModuleDescriptor("connections",    strings.LABEL_CONNECTIONS,    "connections",    ConnectionsModule),
        ModuleDescriptor("terminal",       strings.LABEL_TERMINAL,       "terminal",       TerminalModule),
        ModuleDescriptor("installer",      strings.LABEL_INSTALLER,      "installer",      InstallerModule),
        ModuleDescriptor("scrcpy",         strings.LABEL_SCRCPY,         "scrcpy",         ScrcpyModule),
        ModuleDescriptor("device_buttons", strings.LABEL_DEVICE_BUTTONS, "device_buttons", DeviceButtonsModule),
        ModuleDescriptor("device_info",    strings.LABEL_DEVICE_INFO,    "device_info",    DeviceInfoModule),
        ModuleDescriptor("apps",           strings.LABEL_APPS,           "apps",           AppsModule),
        ModuleDescriptor("logcat",         strings.LABEL_LOGCAT,         "logcat",         LogcatModule),
        ModuleDescriptor("settings",       strings.LABEL_SETTINGS,       "settings",       SettingsModule),
    ]


def main() -> int:
    ensure_app_dirs()
    init_logging()
    log = get_logger("main")

    app = QApplication(sys.argv)
    app.setApplicationName(strings.APP_NAME)
    app.setQuitOnLastWindowClosed(True)
    app.setStyle("Fusion")
    _base_font = app.font()
    _base_font.setPointSize(10)
    app.setFont(_base_font)

    single = SingleInstance()
    if not single.acquire():
        log.info("Another instance is running; focus signal sent. Exiting.")
        return 0

    settings = SettingsManager.instance()
    db = DatabaseManager.instance()
    adb = get_adb_service()

    theme_mgr = ThemeManager()
    theme_value = settings.get("theme", Theme.SYSTEM.value)
    try:
        theme = Theme(theme_value)
    except ValueError:
        theme = Theme.SYSTEM
    theme_mgr.apply(app, theme)

    for desc in _module_descriptors():
        try:
            registry.register(desc)
        except ValueError:
            pass

    window = MainWindow(registry, adb, settings, theme_mgr)
    single.focus_requested.connect(window.focus_window)
    window.show()

    adb.start()

    try:
        exit_code = app.exec()
    finally:
        try:
            shutdown_adb_service()
        finally:
            try:
                db.close()
            except Exception:
                pass
            single.release()
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
