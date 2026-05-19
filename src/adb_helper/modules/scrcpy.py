"""Module: Scrcpy (Spec §3.4).

Launches scrcpy in its OWN top-level window as a separate process — never
embedded. On first activation, if no scrcpy binary is present under
``<app_data>/scrcpy/``, the module fetches the latest release from the
GitHub API (response cached for 6 hours), downloads the platform-matching
asset with SHA-256 verification, and extracts it.

Process spawning goes through :meth:`AdbService.spawn_process` (which uses
:class:`ProcessManager`) so scrcpy is terminated on app exit alongside any
other managed children.
"""
from __future__ import annotations

import os
import re
import tarfile
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import paths, strings
from ..core.adb_service import get_adb_service
from ..core.command_runner import resolve_adb_binary
from ..core.device_context import DeviceContext
from ..core.downloader import AtomicDownloader
from ..core.imodule import IModule
from ..core.logger import get_logger
from ..ui.style_utils import set_variant as _set_variant
from ..core import platform as _platform

_log = get_logger(__name__)

_CACHE_FILENAME = "api_cache.json"
_GITHUB_OWNER = "Genymobile"
_GITHUB_REPO = "scrcpy"

_ASSET_RE_LINUX = re.compile(r"^scrcpy-linux-x86_64-v[\d.]+\.tar\.gz$")
_ASSET_RE_WIN = re.compile(r"^scrcpy-win64-v[\d.]+\.zip$")


# --- background worker signals -------------------------------------------
class _BinaryWorkerSignals(QObject):
    finished = Signal(bool, str, str)  # ok, binary_path, message


class ScrcpyModule(IModule):
    """Scrcpy launch screen (§3.4)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._adb = get_adb_service()
        self._binary: Optional[Path] = None
        self._version_label: str = ""
        self._signals = _BinaryWorkerSignals()
        self._signals.finished.connect(self._on_binary_ready)
        self._build_ui()
        self._adb.activeDeviceChanged.connect(self._on_active_device_changed)
        self._refresh_state(self._adb.active_device)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        self._status = QLabel("", self)
        self._status.setWordWrap(True)
        self._status.setProperty("secondary", "true")
        root.addWidget(self._status)

        self._stack = QStackedWidget(self)
        root.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_launch_page())
        self._stack.addWidget(self._build_install_page())

    def _build_launch_page(self) -> QWidget:
        page = QWidget(self)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        opts = QGroupBox(strings.SCRCPY_LABEL_LAUNCH_OPTIONS, page)
        form = QFormLayout(opts)

        self._bitrate = QComboBox(opts)
        for label, value in (
            (strings.SCRCPY_BITRATE_2, "2M"),
            (strings.SCRCPY_BITRATE_4, "4M"),
            (strings.SCRCPY_BITRATE_8, "8M"),
            (strings.SCRCPY_BITRATE_16, "16M"),
            (strings.SCRCPY_BITRATE_32, "32M"),
        ):
            self._bitrate.addItem(label, value)
        self._bitrate.setCurrentIndex(2)  # 8M default
        form.addRow(strings.SCRCPY_LABEL_BITRATE, self._bitrate)

        self._max_res = QComboBox(opts)
        self._max_res.addItem(strings.SCRCPY_RES_NONE, 0)
        for label, value in (
            (strings.SCRCPY_RES_1920, 1920),
            (strings.SCRCPY_RES_1280, 1280),
            (strings.SCRCPY_RES_1024, 1024),
            (strings.SCRCPY_RES_800, 800),
        ):
            self._max_res.addItem(label, value)
        form.addRow(strings.SCRCPY_LABEL_MAX_RES, self._max_res)

        self._orientation = QComboBox(opts)
        self._orientation.addItem(strings.SCRCPY_ORIENT_AUTO, None)
        for label, value in (
            (strings.SCRCPY_ORIENT_0, 0),
            (strings.SCRCPY_ORIENT_90, 90),
            (strings.SCRCPY_ORIENT_180, 180),
            (strings.SCRCPY_ORIENT_270, 270),
        ):
            self._orientation.addItem(label, value)
        form.addRow(strings.SCRCPY_LABEL_ORIENTATION, self._orientation)

        self._stay_awake = QCheckBox(strings.SCRCPY_LABEL_STAY_AWAKE, opts)
        form.addRow("", self._stay_awake)
        self._show_touches = QCheckBox(strings.SCRCPY_LABEL_SHOW_TOUCHES, opts)
        form.addRow("", self._show_touches)
        self._turn_screen_off = QCheckBox(strings.SCRCPY_LABEL_TURN_SCREEN_OFF, opts)
        form.addRow("", self._turn_screen_off)

        lay.addWidget(opts)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._launch_btn = QPushButton(strings.SCRCPY_BTN_LAUNCH, page)
        _set_variant(self._launch_btn, "primary")
        self._launch_btn.setEnabled(False)
        self._launch_btn.clicked.connect(self._on_launch_clicked)
        actions.addWidget(self._launch_btn)
        lay.addLayout(actions)
        lay.addStretch(1)
        return page

    def _build_install_page(self) -> QWidget:
        page = QWidget(self)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        self._install_msg = QLabel("", page)
        self._install_msg.setWordWrap(True)
        lay.addWidget(self._install_msg)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._retry_btn = QPushButton(strings.SCRCPY_BTN_RETRY, page)
        self._retry_btn.clicked.connect(self._start_binary_check)
        actions.addWidget(self._retry_btn)
        lay.addLayout(actions)
        lay.addStretch(1)
        return page

    # ----------------------------------------------------- IModule lifecycle
    def on_activate(self) -> None:
        if self._binary is None or not self._binary.exists():
            self._start_binary_check()
        else:
            self._refresh_state(self._adb.active_device)

    def on_deactivate(self) -> None:
        return None

    def on_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._refresh_state(ctx)

    def on_device_disconnected(self) -> None:
        self._launch_btn.setEnabled(False)
        self._status.setText(strings.SCRCPY_MSG_NO_DEVICE)

    # ------------------------------------------------------- State refresh
    @Slot(object)
    def _on_active_device_changed(self, ctx: Optional[DeviceContext]) -> None:
        self._refresh_state(ctx)

    def _refresh_state(self, ctx: Optional[DeviceContext]) -> None:
        ready = self._binary is not None and self._binary.exists()
        online = ctx is not None and ctx.status == "online"
        self._launch_btn.setEnabled(ready and online)
        if not ready:
            return
        if not online:
            self._status.setText(strings.SCRCPY_MSG_NO_DEVICE)
        else:
            self._status.setText(
                strings.SCRCPY_MSG_READY.format(version=self._version_label or "")
            )

    # --------------------------------------------------- Binary management
    def _start_binary_check(self) -> None:
        existing = self._find_existing_binary()
        if existing is not None:
            self._binary = existing
            self._version_label = self._infer_version_from_path(existing)
            self._stack.setCurrentIndex(0)
            self._refresh_state(self._adb.active_device)
            return

        self._stack.setCurrentIndex(1)
        self._install_msg.setText(strings.SCRCPY_MSG_CHECKING)
        self._retry_btn.setEnabled(False)
        threading.Thread(
            target=self._fetch_and_install,
            name="scrcpy-install",
            daemon=True,
        ).start()

    def _find_existing_binary(self) -> Optional[Path]:
        scrcpy_root = paths.scrcpy_dir()
        if not scrcpy_root.exists():
            return None
        name = "scrcpy.exe" if _platform.IS_WINDOWS else "scrcpy"
        for candidate in scrcpy_root.rglob(name):
            if candidate.is_file():
                return candidate
        return None

    def _infer_version_from_path(self, binary: Path) -> str:
        for part in binary.parts:
            m = re.search(r"v\d+(?:\.\d+)+", part)
            if m:
                return m.group(0)
        return ""

    def _fetch_and_install(self) -> None:
        scrcpy_root = paths.scrcpy_dir()
        scrcpy_root.mkdir(parents=True, exist_ok=True)
        cache_path = scrcpy_root / _CACHE_FILENAME

        release = AtomicDownloader.get_latest_github_release(
            _GITHUB_OWNER, _GITHUB_REPO, cache_path=cache_path
        )
        if release is None:
            self._signals.finished.emit(
                False, "", strings.SCRCPY_MSG_DOWNLOAD_FAILED.format(path=str(scrcpy_root))
            )
            return

        asset_re = _ASSET_RE_WIN if _platform.IS_WINDOWS else _ASSET_RE_LINUX
        assets = release.get("assets") or []
        asset = next(
            (a for a in assets if asset_re.match(a.get("name", ""))), None
        )
        if asset is None:
            self._signals.finished.emit(
                False, "", strings.SCRCPY_MSG_NO_ASSET.format(path=str(scrcpy_root))
            )
            return

        asset_name = asset["name"]
        asset_url = asset["browser_download_url"]
        sha_asset = next(
            (a for a in assets if a.get("name") == f"{asset_name}.sha256sum"),
            None,
        )
        expected_sha: Optional[str] = None
        if sha_asset is not None:
            sha_dest = scrcpy_root / f"{asset_name}.sha256sum"
            if AtomicDownloader.download(sha_asset["browser_download_url"], sha_dest):
                expected_sha = _parse_sha256sum(sha_dest)

        archive_dest = scrcpy_root / asset_name
        ok = AtomicDownloader.download(asset_url, archive_dest, expected_sha)
        if not ok:
            self._signals.finished.emit(
                False, "", strings.SCRCPY_MSG_DOWNLOAD_FAILED.format(path=str(scrcpy_root))
            )
            return

        try:
            extracted_root = _extract_archive(archive_dest, scrcpy_root)
        except (tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
            _log.error("scrcpy extract failed: %s", exc)
            self._signals.finished.emit(
                False, "", strings.SCRCPY_MSG_DOWNLOAD_FAILED.format(path=str(scrcpy_root))
            )
            return

        bin_name = "scrcpy.exe" if _platform.IS_WINDOWS else "scrcpy"
        binary = next(
            (p for p in extracted_root.rglob(bin_name) if p.is_file()), None
        )
        if binary is None:
            self._signals.finished.emit(
                False, "", strings.SCRCPY_MSG_DOWNLOAD_FAILED.format(path=str(scrcpy_root))
            )
            return

        if not _platform.IS_WINDOWS:
            try:
                os.chmod(binary, 0o755)
            except OSError:
                pass

        version = (release.get("tag_name") or "").lstrip("v")
        self._signals.finished.emit(True, str(binary), version)

    @Slot(bool, str, str)
    def _on_binary_ready(self, ok: bool, binary_path: str, message: str) -> None:
        if ok:
            self._binary = Path(binary_path)
            self._version_label = f"v{message}" if message else ""
            self._stack.setCurrentIndex(0)
            self._refresh_state(self._adb.active_device)
        else:
            self._install_msg.setText(message)
            self._retry_btn.setEnabled(True)
            self._launch_btn.setEnabled(False)

    # ----------------------------------------------------------- Launching
    def _on_launch_clicked(self) -> None:
        if self._binary is None or not self._binary.exists():
            self._start_binary_check()
            return
        ctx = self._adb.active_device
        if ctx is None or ctx.status != "online":
            return

        argv = [str(self._binary), "-s", ctx.serial]
        bitrate = self._bitrate.currentData()
        if bitrate:
            argv += ["--video-bit-rate", bitrate]
        max_res = self._max_res.currentData()
        if max_res:
            argv += ["--max-size", str(max_res)]
        orientation = self._orientation.currentData()
        if orientation is not None:
            argv += [f"--capture-orientation={orientation}"]
        if self._stay_awake.isChecked():
            argv += ["--stay-awake"]
        if self._show_touches.isChecked():
            argv += ["--show-touches"]
        if self._turn_screen_off.isChecked():
            argv += ["--turn-screen-off"]

        env = dict(os.environ)
        env["ADB"] = resolve_adb_binary()
        # Bundled adb directory on PATH so any helper scrcpy spawns finds it.
        adb_dir = str(Path(env["ADB"]).parent)
        env["PATH"] = adb_dir + os.pathsep + env.get("PATH", "")

        pid = f"scrcpy-{uuid.uuid4()}"
        self._status.setText(
            strings.SCRCPY_MSG_LAUNCHING.format(serial=ctx.serial)
        )
        ok = self._adb.spawn_process(pid, argv, env=env)
        if ok:
            self._status.setText(strings.SCRCPY_MSG_LAUNCHED)
        else:
            self._status.setText(strings.SCRCPY_MSG_LAUNCH_FAILED)


# --- helpers -------------------------------------------------------------
def _parse_sha256sum(path: Path) -> Optional[str]:
    """Return the hex digest from a ``sha256sum``-format file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        token = line.split()[0]
        if re.fullmatch(r"[0-9a-fA-F]{64}", token):
            return token
    return None


def _extract_archive(archive: Path, dest_root: Path) -> Path:
    """Extract ``archive`` into ``dest_root``; return the extracted top dir."""
    if archive.name.endswith(".tar.gz") or archive.name.endswith(".tgz"):
        with tarfile.open(archive, "r:gz") as tf:
            members = tf.getmembers()
            top_names = {_top_segment(m.name) for m in members if m.name}
            top_names.discard("")
            for m in members:
                if _is_unsafe_member(m.name):
                    raise tarfile.TarError(f"unsafe path in archive: {m.name!r}")
            # Python 3.12+ recommends an explicit filter for tarfile.extractall.
            tf.extractall(dest_root, filter="data")
    elif archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            top_names = {_top_segment(n) for n in names if n}
            top_names.discard("")
            for n in names:
                if _is_unsafe_member(n):
                    raise zipfile.BadZipFile(f"unsafe path in archive: {n!r}")
            zf.extractall(dest_root)
    else:
        raise OSError(f"unknown archive format: {archive.name}")

    try:
        archive.unlink(missing_ok=True)
    except OSError:
        pass

    if len(top_names) == 1:
        return dest_root / next(iter(top_names))
    return dest_root


def _top_segment(name: str) -> str:
    name = name.replace("\\", "/")
    return name.split("/", 1)[0]


def _is_unsafe_member(name: str) -> bool:
    name = name.replace("\\", "/")
    if name.startswith("/"):
        return True
    parts = name.split("/")
    return ".." in parts


__all__ = ["ScrcpyModule"]
