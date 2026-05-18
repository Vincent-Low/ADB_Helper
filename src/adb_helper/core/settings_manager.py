"""SettingsManager — JSON-backed settings with forward-compatible reads.

Spec §1.6 / §3.9.3:
- Carries ``"schema_version"``.
- Missing keys are backfilled with defaults on load.
- Unknown future keys are preserved on save.
- Atomic write: ``.tmp`` then ``os.replace``.
- ``set()`` saves immediately.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from .platform import get_app_data_dir

SCHEMA_VERSION = 1


def _default_settings() -> Dict[str, Any]:
    root = get_app_data_dir()
    return {
        "schema_version": SCHEMA_VERSION,
        "theme": "system",
        "screenshots_folder": str(root / "screenshots"),
        "logcat_folder": str(root / "logcat"),
        "adb_timeout": 30,
        "log_level": "error",
    }


class SettingsManager:
    """Process-wide singleton (access via :func:`SettingsManager.instance`)."""

    _instance: Optional["SettingsManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path: Path = path or (get_app_data_dir() / "settings.json")
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = _default_settings()

    @classmethod
    def instance(cls) -> "SettingsManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance.load()
            return cls._instance

    def load(self) -> None:
        defaults = _default_settings()
        with self._lock:
            if not self._path.exists():
                self._data = defaults
                self._save_locked()
                return
            try:
                with self._path.open("r", encoding="utf-8") as fh:
                    on_disk = json.load(fh)
            except (json.JSONDecodeError, OSError):
                self._data = defaults
                self._save_locked()
                return
            if not isinstance(on_disk, dict):
                self._data = defaults
                self._save_locked()
                return
            merged: Dict[str, Any] = dict(on_disk)
            for key, value in defaults.items():
                merged.setdefault(key, value)
            merged["schema_version"] = SCHEMA_VERSION
            self._data = merged
            self._save_locked()

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._path)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._save_locked()

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)
