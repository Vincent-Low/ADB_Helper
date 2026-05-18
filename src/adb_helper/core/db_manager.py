"""DatabaseManager — SQLite connection + migrations runner.

Spec §1.6: read ``PRAGMA user_version``, apply pending migrations from
``db/migrations/*.sql`` in filename order BEFORE the UI initialises. Each
migration script is responsible for bumping ``user_version`` to its own
version number.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, List, Optional

from .platform import get_app_data_dir

_HISTORY_LIMIT = 50

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
    # Command history (Spec §3.2.2) — last 50 entries kept.
    # ------------------------------------------------------------------
    def get_command_history(self, limit: int = _HISTORY_LIMIT) -> List[str]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT command FROM command_history "
                "ORDER BY id DESC LIMIT ?",
                (int(limit),),
            )
            rows = cur.fetchall()
        return [r[0] for r in rows]

    def add_command_history(self, command: str) -> None:
        cmd = command.strip()
        if not cmd:
            return
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO command_history(command) VALUES(?)", (cmd,)
            )
            self._conn.execute(
                "DELETE FROM command_history WHERE id NOT IN ("
                "SELECT id FROM command_history ORDER BY id DESC LIMIT ?"
                ")",
                (_HISTORY_LIMIT,),
            )

    # ------------------------------------------------------------------
    # Macros (Spec §3.2.3) — commands serialised as JSON list of strings.
    # ------------------------------------------------------------------
    def get_macros(self) -> List[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, name, commands, created_at FROM macros "
                "ORDER BY created_at DESC, id DESC"
            )
            rows = cur.fetchall()
        out: List[dict] = []
        for r in rows:
            try:
                cmds = json.loads(r[2]) if r[2] else []
            except json.JSONDecodeError:
                cmds = []
            if not isinstance(cmds, list):
                cmds = []
            out.append(
                {
                    "id": int(r[0]),
                    "name": r[1] or "",
                    "commands": [str(c) for c in cmds],
                    "created_at": r[3],
                }
            )
        return out

    def save_macro(self, name: str, commands: List[str]) -> int:
        payload = json.dumps(list(commands), ensure_ascii=False)
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO macros(name, commands) VALUES(?, ?)",
                (name, payload),
            )
            return int(cur.lastrowid)

    def rename_macro(self, macro_id: int, name: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE macros SET name=? WHERE id=?",
                (name, int(macro_id)),
            )

    def delete_macro(self, macro_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM macros WHERE id=?", (int(macro_id),)
            )

    def get_paired_devices(self) -> List[Any]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ip, alias, last_connected FROM paired_devices "
                "ORDER BY (last_connected IS NULL), last_connected DESC, ip"
            )
            rows = cur.fetchall()
        return [
            {"ip": r[0], "alias": r[1], "last_connected": r[2]}
            for r in rows
        ]

    def save_paired_device(self, ip: str, alias: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO paired_devices(ip, alias, last_connected) "
                "VALUES(?, ?, NULL) "
                "ON CONFLICT(ip) DO UPDATE SET alias=excluded.alias",
                (ip, alias),
            )

    def delete_paired_device(self, ip: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM paired_devices WHERE ip=?",
                (ip,),
            )

    def update_paired_alias(self, ip: str, alias: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE paired_devices SET alias=? WHERE ip=?",
                (alias, ip),
            )

    def touch_paired_device(self, ip: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE paired_devices SET last_connected=CURRENT_TIMESTAMP "
                "WHERE ip=?",
                (ip,),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
