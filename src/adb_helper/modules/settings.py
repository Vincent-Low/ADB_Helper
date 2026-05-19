"""Module: Settings (Spec §3.9).

About section, bundled-dependency status (ADB / scrcpy / bundletool), and
general settings (theme, screenshots folder, logcat folder, ADB command
timeout, log level). All settings persist immediately to ``settings.json``.
"""
from __future__ import annotations

import logging
import os
import re
import tarfile
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import paths, strings
from ..core.device_context import DeviceContext
from ..core.downloader import AtomicDownloader
from ..core.imodule import IModule
from ..core.logger import get_logger, set_level
from ..core.settings_manager import SettingsManager
from ..core import platform as _platform

_log = get_logger(__name__)

_GITHUB_SCRCPY_OWNER = "Genymobile"
_GITHUB_SCRCPY_REPO = "scrcpy"
_GITHUB_BT_OWNER = "google"
_GITHUB_BT_REPO = "bundletool"
_ASSET_RE_SCRCPY_LINUX = re.compile(r"^scrcpy-linux-x86_64-v[\d.]+\.tar\.gz$")
_ASSET_RE_SCRCPY_WIN = re.compile(r"^scrcpy-win64-v[\d.]+\.zip$")
_ASSET_RE_BT = re.compile(r"^bundletool-all-([\d.]+)\.jar$")
_BT_VERSION_FILE = "bundletool.version"
_BT_JAR_NAME = "bundletool.jar"
_SCRCPY_CACHE = "settings_api_cache_scrcpy.json"
_BT_CACHE = "settings_api_cache_bt.json"

_DEP_KEYS = ["adb", "scrcpy", "bundletool"]
_DEP_LABELS = {
    "adb": strings.SETT_DEP_ADB,
    "scrcpy": strings.SETT_DEP_SCRCPY,
    "bundletool": strings.SETT_DEP_BUNDLETOOL,
}

_COL_COMPONENT = 0
_COL_INSTALLED = 1
_COL_LATEST = 2
_COL_STATUS = 3
_COL_ACTION = 4

_LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


# ====================================================== Background workers

class _CheckSignals(QObject):
    dep_result = Signal(str, str, str, str, str, str, str)
    # key, installed, latest, status, action_label, asset_url, sha256
    done = Signal()


class _InstalledSignals(QObject):
    installed_result = Signal(str, str)  # key, installed_version (empty = not installed)


class _UpdateSignals(QObject):
    progress = Signal(str, str)   # key, message
    finished = Signal(str, bool, str)   # key, ok, version_or_error


class _CheckWorker:
    def __init__(self, signals: _CheckSignals) -> None:
        self._sig = signals

    def run(self) -> None:
        try:
            self._check_adb()
            self._check_scrcpy()
            self._check_bundletool()
        except Exception as exc:
            _log.error("dep check worker crashed: %s", exc)
        self._sig.done.emit()

    def _check_adb(self) -> None:
        installed = _adb_installed_version()
        latest, dl_url = _adb_latest_version()
        if not installed:
            self._sig.dep_result.emit(
                "adb", strings.SETT_STATUS_NOT_INSTALLED,
                latest or "—", strings.SETT_STATUS_NOT_INSTALLED,
                strings.SETT_BTN_DOWNLOAD, dl_url, "",
            )
            return
        if latest and latest != installed:
            status = strings.SETT_STATUS_UPDATE_AVAILABLE
            action = strings.SETT_BTN_UPDATE
        elif latest:
            status = strings.SETT_STATUS_UP_TO_DATE
            action = ""
        else:
            status = strings.SETT_STATUS_UNKNOWN
            action = strings.SETT_BTN_UPDATE
        self._sig.dep_result.emit(
            "adb", installed, latest or "—", status, action, dl_url, "",
        )

    def _check_scrcpy(self) -> None:
        installed = _scrcpy_installed_version()
        cache_path = paths.scrcpy_dir() / _SCRCPY_CACHE
        release = AtomicDownloader.get_latest_github_release(
            _GITHUB_SCRCPY_OWNER, _GITHUB_SCRCPY_REPO, cache_path=cache_path
        )
        latest = ""
        asset_url = ""
        sha256 = ""
        if release:
            latest = (release.get("tag_name") or "").lstrip("v")
            asset_re = _ASSET_RE_SCRCPY_WIN if _platform.IS_WINDOWS else _ASSET_RE_SCRCPY_LINUX
            assets = release.get("assets") or []
            asset = next(
                (a for a in assets if asset_re.match(a.get("name", ""))), None
            )
            if asset:
                asset_url = asset.get("browser_download_url", "")
                sha_name = asset["name"] + ".sha256sum"
                sha_asset = next(
                    (a for a in assets if a.get("name") == sha_name), None
                )
                if sha_asset:
                    sha256 = sha_asset.get("browser_download_url", "")

        if not installed:
            self._sig.dep_result.emit(
                "scrcpy", strings.SETT_STATUS_NOT_INSTALLED,
                latest or "—", strings.SETT_STATUS_NOT_INSTALLED,
                strings.SETT_BTN_DOWNLOAD if asset_url else "",
                asset_url, sha256,
            )
            return
        if latest and _version_gt(latest, installed):
            status = strings.SETT_STATUS_UPDATE_AVAILABLE
            action = strings.SETT_BTN_UPDATE if asset_url else ""
        else:
            status = strings.SETT_STATUS_UP_TO_DATE
            action = ""
        self._sig.dep_result.emit(
            "scrcpy", installed, latest or "—", status, action, asset_url, sha256,
        )

    def _check_bundletool(self) -> None:
        installed = _bundletool_installed_version()
        cache_path = paths.bundletool_dir() / _BT_CACHE
        release = AtomicDownloader.get_latest_github_release(
            _GITHUB_BT_OWNER, _GITHUB_BT_REPO, cache_path=cache_path
        )
        latest = ""
        asset_url = ""
        if release:
            latest = (release.get("tag_name") or "").lstrip("v")
            assets = release.get("assets") or []
            asset = next(
                (a for a in assets if _ASSET_RE_BT.match(a.get("name", ""))), None
            )
            if asset:
                asset_url = asset.get("browser_download_url", "")

        if not installed:
            self._sig.dep_result.emit(
                "bundletool", strings.SETT_STATUS_NOT_INSTALLED,
                latest or "—", strings.SETT_STATUS_NOT_INSTALLED,
                strings.SETT_BTN_DOWNLOAD if asset_url else "",
                asset_url, "",
            )
            return
        if latest and _version_gt(latest, installed):
            status = strings.SETT_STATUS_UPDATE_AVAILABLE
            action = strings.SETT_BTN_UPDATE if asset_url else ""
        else:
            status = strings.SETT_STATUS_UP_TO_DATE
            action = ""
        self._sig.dep_result.emit(
            "bundletool", installed, latest or "—", status, action, asset_url, "",
        )


class _UpdateWorker:
    def __init__(
        self,
        key: str,
        asset_url: str,
        sha256_asset_url: str,
        signals: _UpdateSignals,
    ) -> None:
        self._key = key
        self._asset_url = asset_url
        self._sha256_asset_url = sha256_asset_url
        self._sig = signals

    def run(self) -> None:
        try:
            if self._key == "adb":
                ok, msg = self._update_adb()
            elif self._key == "scrcpy":
                ok, msg = self._update_scrcpy()
            elif self._key == "bundletool":
                ok, msg = self._update_bundletool()
            else:
                ok, msg = False, "Unknown component"
        except Exception as exc:
            _log.error("update worker crashed key=%s err=%s", self._key, exc)
            ok, msg = False, str(exc)
        self._sig.finished.emit(self._key, ok, msg)

    def _update_adb(self) -> tuple[bool, str]:
        dest_dir = paths.platform_tools_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        os_suffix = "windows" if _platform.IS_WINDOWS else "linux"
        url = self._asset_url or (
            f"https://dl.google.com/android/repository/"
            f"platform-tools-latest-{os_suffix}.zip"
        )
        archive = dest_dir / "platform-tools-latest.zip.tmp"
        self._sig.progress.emit(self._key, strings.SETT_MSG_UPDATING.format(component=strings.SETT_DEP_ADB))
        if not AtomicDownloader.download(url, archive):
            return False, strings.SETT_MSG_UPDATE_FAILED.format(component=strings.SETT_DEP_ADB)
        # Linux refuses to overwrite a running executable ("Text file busy").
        # Stop adb server + monitoring before extraction; restart after.
        _stop_adb_server_before_update()
        try:
            with zipfile.ZipFile(archive) as zf:
                for member in zf.namelist():
                    parts = Path(member).parts
                    if len(parts) > 1:
                        rel = Path(*parts[1:])
                    else:
                        continue
                    target = dest_dir / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    data = zf.read(member)
                    target.write_bytes(data)
        except (zipfile.BadZipFile, OSError) as exc:
            _log.error("adb archive extract failed: %s", exc)
            return False, strings.SETT_MSG_UPDATE_FAILED.format(component=strings.SETT_DEP_ADB)
        finally:
            try:
                archive.unlink(missing_ok=True)
            except OSError:
                pass
        version = _adb_installed_version()
        _restart_adb_server_after_update()
        return True, version

    def _update_scrcpy(self) -> tuple[bool, str]:
        if not self._asset_url:
            return False, strings.SETT_MSG_UPDATE_FAILED.format(component=strings.SETT_DEP_SCRCPY)
        dest_dir = paths.scrcpy_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        asset_name = self._asset_url.rsplit("/", 1)[-1]
        archive_dest = dest_dir / asset_name
        self._sig.progress.emit(
            self._key,
            strings.SETT_MSG_UPDATING.format(component=strings.SETT_DEP_SCRCPY),
        )
        expected_sha: Optional[str] = None
        if self._sha256_asset_url:
            sha_dest = dest_dir / (asset_name + ".sha256sum")
            if AtomicDownloader.download(self._sha256_asset_url, sha_dest):
                expected_sha = _parse_sha256sum(sha_dest)
        if not AtomicDownloader.download(self._asset_url, archive_dest, expected_sha):
            return False, strings.SETT_MSG_UPDATE_FAILED.format(component=strings.SETT_DEP_SCRCPY)
        try:
            _extract_archive(archive_dest, dest_dir)
        except (tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
            _log.error("scrcpy extract failed: %s", exc)
            return False, strings.SETT_MSG_UPDATE_FAILED.format(component=strings.SETT_DEP_SCRCPY)
        version = _scrcpy_installed_version()
        return True, version

    def _update_bundletool(self) -> tuple[bool, str]:
        if not self._asset_url:
            return False, strings.SETT_MSG_UPDATE_FAILED.format(component=strings.SETT_DEP_BUNDLETOOL)
        dest_dir = paths.bundletool_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        jar_dest = dest_dir / _BT_JAR_NAME
        self._sig.progress.emit(
            self._key,
            strings.SETT_MSG_UPDATING.format(component=strings.SETT_DEP_BUNDLETOOL),
        )
        if not AtomicDownloader.download(self._asset_url, jar_dest):
            return False, strings.SETT_MSG_UPDATE_FAILED.format(component=strings.SETT_DEP_BUNDLETOOL)
        m = _ASSET_RE_BT.match(self._asset_url.rsplit("/", 1)[-1])
        version = m.group(1) if m else ""
        if version:
            try:
                (dest_dir / _BT_VERSION_FILE).write_text(version, encoding="utf-8")
            except OSError:
                pass
        return True, version


# ============================================================ SettingsModule

class SettingsModule(IModule):
    """Settings screen (§3.9)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._check_sigs = _CheckSignals()
        self._update_sigs = _UpdateSignals()
        self._installed_sigs = _InstalledSignals()
        # dep key -> {asset_url, sha256, action}
        self._dep_state: dict[str, dict] = {k: {} for k in _DEP_KEYS}
        self._updating: Optional[str] = None
        self._installed_loaded = False
        self._build_ui()
        self._wire_signals()
        self._load_settings()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        # --- About ---------------------------------------------------------
        about_box = QGroupBox(strings.SETT_SEC_ABOUT, self)
        about_layout = QHBoxLayout(about_box)
        about_layout.setContentsMargins(12, 8, 12, 8)
        app_lbl = QLabel(strings.APP_NAME, self)
        ver_lbl = QLabel(f"v{strings.APP_VERSION}", self)
        ver_lbl.setProperty("secondary", "true")
        about_layout.addWidget(app_lbl)
        about_layout.addWidget(ver_lbl)
        about_layout.addStretch(1)
        root.addWidget(about_box)

        # --- Dependencies --------------------------------------------------
        deps_box = QGroupBox(strings.SETT_SEC_DEPS, self)
        deps_layout = QVBoxLayout(deps_box)
        deps_layout.setContentsMargins(12, 8, 12, 8)
        deps_layout.setSpacing(8)

        self._deps_table = QTableWidget(len(_DEP_KEYS), 5, self)
        self._deps_table.setHorizontalHeaderLabels([
            strings.SETT_COL_COMPONENT,
            strings.SETT_COL_INSTALLED,
            strings.SETT_COL_LATEST,
            strings.SETT_COL_STATUS,
            strings.SETT_COL_ACTION,
        ])
        self._deps_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._deps_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._deps_table.verticalHeader().setVisible(False)
        self._deps_table.verticalHeader().setDefaultSectionSize(40)
        self._deps_table.verticalHeader().setMinimumSectionSize(40)
        hdr = self._deps_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_ACTION, QHeaderView.ResizeMode.Fixed)
        self._deps_table.setColumnWidth(_COL_ACTION, 100)
        self._deps_table.setFixedHeight(
            self._deps_table.horizontalHeader().height()
            + 40 * len(_DEP_KEYS)
            + 4
        )

        for row, key in enumerate(_DEP_KEYS):
            comp_item = QTableWidgetItem(_DEP_LABELS[key])
            comp_item.setFlags(comp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._deps_table.setItem(row, _COL_COMPONENT, comp_item)
            for col in (_COL_INSTALLED, _COL_LATEST, _COL_STATUS):
                item = QTableWidgetItem("—")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._deps_table.setItem(row, col, item)
            action_btn = QPushButton("", self)
            action_btn.setEnabled(False)
            action_btn.setProperty("dep_key", key)
            action_btn.setMinimumWidth(80)
            action_btn.setMinimumHeight(28)
            action_btn.clicked.connect(
                lambda _checked=False, k=key: self._on_dep_action(k)
            )
            self._deps_table.setCellWidget(row, _COL_ACTION, action_btn)

        deps_layout.addWidget(self._deps_table)

        check_row = QHBoxLayout()
        self._check_btn = QPushButton(strings.SETT_BTN_CHECK_UPDATES, self)
        self._check_btn.clicked.connect(self._on_check_updates)
        check_row.addWidget(self._check_btn)
        check_row.addStretch(1)
        self._deps_status_lbl = QLabel("", self)
        self._deps_status_lbl.setProperty("secondary", "true")
        check_row.addWidget(self._deps_status_lbl)
        deps_layout.addLayout(check_row)
        root.addWidget(deps_box)

        # --- General Settings ----------------------------------------------
        gen_box = QGroupBox(strings.SETT_SEC_GENERAL, self)
        gen_form = QFormLayout(gen_box)
        gen_form.setContentsMargins(12, 12, 12, 12)
        gen_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        gen_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        # Theme
        self._theme_combo = QComboBox(self)
        for label, val in [
            (strings.SETT_THEME_SYSTEM, "system"),
            (strings.SETT_THEME_LIGHT, "light"),
            (strings.SETT_THEME_DARK, "dark"),
        ]:
            self._theme_combo.addItem(label, val)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        gen_form.addRow(strings.SETT_LABEL_THEME, self._theme_combo)

        # Screenshots folder
        ss_row = QHBoxLayout()
        self._ss_path = QLineEdit(self)
        self._ss_path.editingFinished.connect(self._on_ss_path_changed)
        ss_browse = QPushButton(strings.SETT_BTN_BROWSE, self)
        ss_browse.clicked.connect(self._on_ss_browse)
        ss_row.addWidget(self._ss_path, 1)
        ss_row.addWidget(ss_browse)
        gen_form.addRow(strings.SETT_LABEL_SCREENSHOTS_FOLDER, ss_row)

        # Logcat folder
        lc_row = QHBoxLayout()
        self._lc_path = QLineEdit(self)
        self._lc_path.editingFinished.connect(self._on_lc_path_changed)
        lc_browse = QPushButton(strings.SETT_BTN_BROWSE, self)
        lc_browse.clicked.connect(self._on_lc_browse)
        lc_row.addWidget(self._lc_path, 1)
        lc_row.addWidget(lc_browse)
        gen_form.addRow(strings.SETT_LABEL_LOGCAT_FOLDER, lc_row)

        # ADB timeout
        self._timeout_spin = QSpinBox(self)
        self._timeout_spin.setRange(5, 300)
        self._timeout_spin.setSuffix(" s")
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        gen_form.addRow(strings.SETT_LABEL_ADB_TIMEOUT, self._timeout_spin)

        # Log level
        self._log_level_combo = QComboBox(self)
        for label, val in [
            (strings.SETT_LOG_DEBUG, "debug"),
            (strings.SETT_LOG_INFO, "info"),
            (strings.SETT_LOG_WARNING, "warning"),
            (strings.SETT_LOG_ERROR, "error"),
        ]:
            self._log_level_combo.addItem(label, val)
        self._log_level_combo.currentIndexChanged.connect(self._on_log_level_changed)
        gen_form.addRow(strings.SETT_LABEL_LOG_LEVEL, self._log_level_combo)

        root.addWidget(gen_box)
        root.addStretch(1)

    def _wire_signals(self) -> None:
        self._check_sigs.dep_result.connect(self._on_dep_result)
        self._check_sigs.done.connect(self._on_check_done)
        self._update_sigs.progress.connect(self._on_update_progress)
        self._update_sigs.finished.connect(self._on_update_finished)
        self._installed_sigs.installed_result.connect(self._on_installed_result)

    # --------------------------------------------- Settings load / persist
    def _load_settings(self) -> None:
        sm = SettingsManager.instance()

        self._theme_combo.blockSignals(True)
        theme_val = sm.get("theme", "system")
        idx = self._theme_combo.findData(theme_val)
        self._theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._theme_combo.blockSignals(False)

        self._ss_path.blockSignals(True)
        self._ss_path.setText(sm.get("screenshots_folder", str(paths.screenshots_dir())))
        self._ss_path.blockSignals(False)

        self._lc_path.blockSignals(True)
        self._lc_path.setText(sm.get("logcat_folder", str(paths.logcat_dir())))
        self._lc_path.blockSignals(False)

        self._timeout_spin.blockSignals(True)
        self._timeout_spin.setValue(int(sm.get("adb_timeout", 30)))
        self._timeout_spin.blockSignals(False)

        self._log_level_combo.blockSignals(True)
        level_val = sm.get("log_level", "error")
        idx = self._log_level_combo.findData(level_val)
        self._log_level_combo.setCurrentIndex(idx if idx >= 0 else 3)
        self._log_level_combo.blockSignals(False)

    # ----------------------------------------------------- IModule lifecycle
    def on_activate(self) -> None:
        self._load_settings()
        self._refresh_installed_versions()

    def _refresh_installed_versions(self) -> None:
        """Populate INSTALLED column from disk only. No network."""
        if self._updating is not None:
            return
        sigs = self._installed_sigs

        def _work() -> None:
            try:
                for key in _DEP_KEYS:
                    if key == "adb":
                        v = _adb_installed_version()
                    elif key == "scrcpy":
                        v = _scrcpy_installed_version()
                    elif key == "bundletool":
                        v = _bundletool_installed_version()
                    else:
                        v = ""
                    sigs.installed_result.emit(key, v)
            except Exception as exc:
                _log.error("installed version probe failed: %s", exc)

        threading.Thread(target=_work, name="installed-probe", daemon=True).start()

    @Slot(str, str)
    def _on_installed_result(self, key: str, installed: str) -> None:
        if key not in _DEP_KEYS:
            return
        row = _DEP_KEYS.index(key)
        item = self._deps_table.item(row, _COL_INSTALLED)
        if item is None:
            return
        # Don't clobber values already populated by Check for Updates.
        if item.text() not in ("", "—"):
            return
        item.setText(installed if installed else strings.SETT_STATUS_NOT_INSTALLED)

    def on_deactivate(self) -> None:
        pass

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        pass

    def on_device_disconnected(self) -> None:
        pass

    # ---------------------------------------------------- Dep check actions
    def _on_check_updates(self) -> None:
        self._check_btn.setEnabled(False)
        self._deps_status_lbl.setText(strings.SETT_MSG_CHECKING)
        for row in range(len(_DEP_KEYS)):
            item = self._deps_table.item(row, _COL_STATUS)
            if item:
                item.setText(strings.SETT_STATUS_CHECKING)
            btn = self._deps_table.cellWidget(row, _COL_ACTION)
            if btn:
                btn.setEnabled(False)
                btn.setText("")
        worker = _CheckWorker(self._check_sigs)
        t = threading.Thread(target=worker.run, name="dep-check", daemon=True)
        t.start()

    @Slot(str, str, str, str, str, str, str)
    def _on_dep_result(
        self,
        key: str,
        installed: str,
        latest: str,
        status: str,
        action_label: str,
        asset_url: str,
        sha256_url: str,
    ) -> None:
        row = _DEP_KEYS.index(key) if key in _DEP_KEYS else -1
        if row < 0:
            return
        self._dep_state[key] = {
            "action": action_label,
            "asset_url": asset_url,
            "sha256_url": sha256_url,
        }
        def _set(col: int, text: str) -> None:
            item = self._deps_table.item(row, col)
            if item:
                item.setText(text)

        _set(_COL_INSTALLED, installed)
        _set(_COL_LATEST, latest)
        _set(_COL_STATUS, status)

        btn = self._deps_table.cellWidget(row, _COL_ACTION)
        if btn:
            btn.setText(action_label)
            btn.setEnabled(bool(action_label) and self._updating is None)

    @Slot()
    def _on_check_done(self) -> None:
        self._check_btn.setEnabled(True)
        self._deps_status_lbl.setText(strings.SETT_MSG_CHECK_DONE)

    def _on_dep_action(self, key: str) -> None:
        if self._updating is not None:
            return
        state = self._dep_state.get(key, {})
        asset_url = state.get("asset_url", "")
        sha256_url = state.get("sha256_url", "")
        if not asset_url and key != "adb":
            return
        self._updating = key
        self._check_btn.setEnabled(False)
        for row in range(len(_DEP_KEYS)):
            btn = self._deps_table.cellWidget(row, _COL_ACTION)
            if btn:
                btn.setEnabled(False)
        label = _DEP_LABELS.get(key, key)
        self._deps_status_lbl.setText(strings.SETT_MSG_UPDATING.format(component=label))
        worker = _UpdateWorker(key, asset_url, sha256_url, self._update_sigs)
        t = threading.Thread(target=worker.run, name=f"dep-update-{key}", daemon=True)
        t.start()

    @Slot(str, str)
    def _on_update_progress(self, key: str, message: str) -> None:
        self._deps_status_lbl.setText(message)

    @Slot(str, bool, str)
    def _on_update_finished(self, key: str, ok: bool, version_or_error: str) -> None:
        self._updating = None
        label = _DEP_LABELS.get(key, key)
        if ok:
            self._deps_status_lbl.setText(
                strings.SETT_MSG_UPDATE_DONE.format(
                    component=label, version=version_or_error
                )
            )
            _log.info("dep updated key=%s version=%s", key, version_or_error)
        else:
            self._deps_status_lbl.setText(
                strings.SETT_MSG_UPDATE_FAILED.format(component=label)
            )
            _log.error("dep update failed key=%s err=%s", key, version_or_error)
        # Re-enable buttons based on cached state.
        for k, state in self._dep_state.items():
            row = _DEP_KEYS.index(k)
            btn = self._deps_table.cellWidget(row, _COL_ACTION)
            if btn:
                btn.setEnabled(bool(state.get("action")))
        self._check_btn.setEnabled(True)
        # Refresh the updated row.
        self._on_check_updates()

    # -------------------------------------------------- General Settings
    def _on_theme_changed(self, _idx: int) -> None:
        val = self._theme_combo.currentData()
        if not val:
            return
        SettingsManager.instance().set("theme", val)
        from ..ui.theme_manager import Theme, get_theme_manager
        tm = get_theme_manager()
        app = QApplication.instance()
        if tm is not None and app is not None:
            try:
                theme = Theme(val)
                tm.apply(app, theme)  # type: ignore[arg-type]
            except Exception as exc:
                _log.error("theme apply failed: %s", exc)

    def _on_ss_path_changed(self) -> None:
        val = self._ss_path.text().strip()
        if val:
            SettingsManager.instance().set("screenshots_folder", val)

    def _on_lc_path_changed(self) -> None:
        val = self._lc_path.text().strip()
        if val:
            SettingsManager.instance().set("logcat_folder", val)

    def _on_ss_browse(self) -> None:
        current = self._ss_path.text() or str(paths.screenshots_dir())
        chosen = QFileDialog.getExistingDirectory(
            self, strings.SETT_TITLE_BROWSE_SCREENSHOTS, current
        )
        if chosen:
            self._ss_path.setText(chosen)
            SettingsManager.instance().set("screenshots_folder", chosen)

    def _on_lc_browse(self) -> None:
        current = self._lc_path.text() or str(paths.logcat_dir())
        chosen = QFileDialog.getExistingDirectory(
            self, strings.SETT_TITLE_BROWSE_LOGCAT, current
        )
        if chosen:
            self._lc_path.setText(chosen)
            SettingsManager.instance().set("logcat_folder", chosen)

    def _on_timeout_changed(self, value: int) -> None:
        SettingsManager.instance().set("adb_timeout", value)

    def _on_log_level_changed(self, _idx: int) -> None:
        val = self._log_level_combo.currentData()
        if not val:
            return
        SettingsManager.instance().set("log_level", val)
        level = _LOG_LEVEL_MAP.get(val, logging.ERROR)
        set_level(level)


# ===================================================== Pure helper functions

def _stop_adb_server_before_update() -> None:
    """Kill the ADB server so its binary is not busy during replacement.

    Subprocess call only — safe to invoke from a worker thread. The running
    track-devices process inside DeviceMonitor dies as a side-effect; its
    ProcessManager handler then switches to the poll fallback on the main
    thread.
    """
    import subprocess
    import time
    from ..core.command_runner import resolve_adb_binary

    try:
        adb_path = resolve_adb_binary()
        subprocess.run(
            [str(adb_path), "kill-server"],
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.5)
    except Exception as exc:
        _log.warning("adb kill-server failed (continuing): %s", exc)


def _restart_adb_server_after_update() -> None:
    """Start the new adb server. Monitor reconnects via its poll fallback."""
    import subprocess
    from ..core.command_runner import resolve_adb_binary

    try:
        adb_path = resolve_adb_binary()
        subprocess.run(
            [str(adb_path), "start-server"],
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        _log.warning("adb start-server failed: %s", exc)


def _adb_installed_version() -> str:
    props = paths.platform_tools_dir() / "source.properties"
    if not props.exists():
        return ""
    try:
        text = props.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.startswith("Pkg.Revision="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _adb_latest_version() -> tuple[str, str]:
    os_suffix = "windows" if _platform.IS_WINDOWS else "linux"
    dl_url = (
        f"https://dl.google.com/android/repository/"
        f"platform-tools-latest-{os_suffix}.zip"
    )

    class _CapRedirect(urllib.request.HTTPRedirectHandler):
        redirect_url: str = ""

        def http_error_302(self, req, fp, code, msg, headers):
            type(self).redirect_url = headers.get("Location", "")
            raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

        http_error_301 = http_error_302
        http_error_307 = http_error_302
        http_error_308 = http_error_302

    _CapRedirect.redirect_url = ""
    opener = urllib.request.build_opener(_CapRedirect)
    try:
        with opener.open(
            urllib.request.Request(dl_url, headers={"User-Agent": "ADB_Helper/1.0"}),
            timeout=10,
        ):
            pass
    except urllib.error.HTTPError:
        pass
    except Exception:
        return "", dl_url

    location = _CapRedirect.redirect_url
    if location:
        m = re.search(r"platform-tools_r([\d.]+)", location)
        if m:
            return m.group(1), dl_url
    return "", dl_url


def _scrcpy_installed_version() -> str:
    scrcpy_root = paths.scrcpy_dir()
    if not scrcpy_root.exists():
        return ""
    bin_name = "scrcpy.exe" if _platform.IS_WINDOWS else "scrcpy"
    binary = next((p for p in scrcpy_root.rglob(bin_name) if p.is_file()), None)
    if binary is None:
        return ""
    for part in binary.parts:
        m = re.search(r"v?(\d+(?:\.\d+)+)", part)
        if m:
            return m.group(1)
    return "installed"


def _bundletool_installed_version() -> str:
    jar = paths.bundletool_dir() / _BT_JAR_NAME
    if not jar.exists():
        return ""
    ver_file = paths.bundletool_dir() / _BT_VERSION_FILE
    if ver_file.exists():
        try:
            return ver_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return "installed"


def _version_gt(a: str, b: str) -> bool:
    """Return True if version string ``a`` is strictly greater than ``b``."""
    def _parts(s: str) -> list[int]:
        return [int(x) for x in re.findall(r"\d+", s)]
    try:
        return _parts(a) > _parts(b)
    except (ValueError, TypeError):
        return False


def _parse_sha256sum(path: Path) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"([0-9a-fA-F]{64})", text.strip())
        if m:
            return m.group(1)
    except OSError:
        pass
    return None


def _extract_archive(archive: Path, dest: Path) -> Path:
    """Extract tar.gz or zip archive; return the extracted root directory."""
    name = archive.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(dest)
            top = next(
                (m.name for m in tf.getmembers() if m.isdir() and "/" not in m.name),
                None,
            )
    elif name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
            top = next(
                (
                    info.filename.rstrip("/")
                    for info in zf.infolist()
                    if info.is_dir() and "/" not in info.filename.rstrip("/")
                ),
                None,
            )
    else:
        raise ValueError(f"Unknown archive format: {archive.name}")
    return dest / top if top else dest


__all__ = ["SettingsModule"]
