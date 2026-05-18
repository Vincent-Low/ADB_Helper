"""DatabaseManager — SQLite connection + migrations runner.

Spec §1.6: read ``PRAGMA user_version``, apply pending migrations from
``db/migrations/*.sql`` in filename order BEFORE the UI initialises. Each
migration script is responsible for bumping ``user_version`` to its own
version number.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, List, Optional

from .platform import get_app_data_dir

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "db" / "migrations"
_MIGRATION_VERSION_RE = re.compile(r"^(\d+)_")


class DatabaseManager:
    """Process-wide singleton (access via :func:`DatabaseManager.instance`)."""

    _instance: Optional["DatabaseManager"] = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        db_path: Optional[Path] = None,
        migrations_dir: Optional[Path] = None,
    ) -> None:
        self._db_path: Path = db_path or (get_app_data_dir() / "adb_helper.db")
        self._migrations_dir: Path = migrations_dir or MIGRATIONS_DIR
        self._lock = threading.RLock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(self._db_path), check_same_thread=False
        )
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._apply_migrations()

    @classmethod
    def instance(cls) -> "DatabaseManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def _current_user_version(self) -> int:
        cur = self._conn.execute("PRAGMA user_version")
        return int(cur.fetchone()[0])

    def _discover_migrations(self) -> List[Path]:
        if not self._migrations_dir.exists():
            return []
        files = sorted(
            p for p in self._migrations_dir.iterdir()
            if p.is_file() and p.suffix == ".sql"
        )
        return files

    def _apply_migrations(self) -> None:
        with self._lock:
            for path in self._discover_migrations():
                match = _MIGRATION_VERSION_RE.match(path.name)
                if not match:
                    continue
                target = int(match.group(1))
                current = self._current_user_version()
                if current >= target:
                    continue
                sql = path.read_text(encoding="utf-8")
                with self._conn:
                    self._conn.executescript(sql)

    # ------------------------------------------------------------------
    # Stub methods — filled in Stage 11. Signatures fixed so callers can
    # be wired up against the interface ahead of implementation.
    # ------------------------------------------------------------------
    def get_command_history(self, limit: int = 50) -> List[Any]:
        raise NotImplementedError

    def add_command_history(self, command: str) -> None:
        raise NotImplementedError

    def get_macros(self) -> List[Any]:
        raise NotImplementedError

    def save_macro(self, name: str, commands: List[str]) -> int:
        raise NotImplementedError

    def delete_macro(self, macro_id: int) -> None:
        raise NotImplementedError

    def get_paired_devices(self) -> List[Any]:
        raise NotImplementedError

    def save_paired_device(self, ip: str, alias: str) -> None:
        raise NotImplementedError

    def delete_paired_device(self, ip: str) -> None:
        raise NotImplementedError

    def close(self) -> None:
        with self._lock:
            self._conn.close()
