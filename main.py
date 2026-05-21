"""ADB_Helper entry point (Spec §1.7, §2.1, §8).

UI shell is a single QWebEngineView hosting a Vue 3 + Tailwind SPA; all
Vue ↔ Python traffic flows through QWebChannel bridges in
``adb_helper.web``.  Backend (``core/``) is unchanged.
"""
from __future__ import annotations

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

# QtWebEngine must be imported before QApplication is constructed so the
# WebEngine platform plugin is registered.
import PySide6.QtWebEngineCore  # noqa: F401  — side effect: registers plugin
import PySide6.QtWebEngineWidgets  # noqa: F401

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

if hasattr(Qt, "AA_EnableHighDpiScaling"):
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, "AA_UseHighDpiPixmaps"):
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from adb_helper.core import strings
from adb_helper.core.adb_service import get_adb_service, shutdown_adb_service
from adb_helper.core.db_manager import DatabaseManager
from adb_helper.core.logger import get_logger, init_logging
from adb_helper.core.paths import ensure_app_dirs
from adb_helper.core.settings_manager import SettingsManager
from adb_helper.core.single_instance import SingleInstance
from adb_helper.ui.theme_manager import Theme, ThemeManager
from adb_helper.web.web_main_window import WebMainWindow


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

    window = WebMainWindow(adb, settings, theme_mgr, db)
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
