"""Session logger.

Spec §4. Per-session rotating log files under ``<app_data>/logs/`` with
PIN-masking filter applied at every level (CLAUDE.md §7).
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from . import paths

_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 9  # current + 9 backups = 10 files per session (§4.2)
_RETENTION_DAYS = 10
_SESSION_PREFIX = "adb_helper_"

_session_file: Optional[Path] = None
_handler: Optional[RotatingFileHandler] = None
_root_configured = False


class _PinMaskingFilter(logging.Filter):
    """Mask 6-digit PIN codes in messages that mention 'pair' or 'PIN' (§4.3)."""

    _trigger = re.compile(r"\b(pair|pin)\b", re.IGNORECASE)
    _digits = re.compile(r"\b\d{6}\b")

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if self._trigger.search(msg):
            masked = self._digits.sub("*****", msg)
            record.msg = masked
            record.args = ()
        return True


class _TzFormatter(logging.Formatter):
    """Format: ``LEVEL - YYYY-MM-DD HH:MM:SS.mmm UTC±HH:MM - message`` (§4.1)."""

    def format(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone()
        offset = dt.utcoffset() or _zero_delta()
        total = int(offset.total_seconds())
        sign = "+" if total >= 0 else "-"
        hh = abs(total) // 3600
        mm = (abs(total) % 3600) // 60
        ms = int(record.msecs)
        ts = f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{ms:03d} UTC{sign}{hh:02d}:{mm:02d}"
        return f"{record.levelname} - {ts} - {record.getMessage()}"


def _zero_delta():
    from datetime import timedelta
    return timedelta(0)


def _prune_old_logs(logs_dir: Path) -> None:
    cutoff = time.time() - _RETENTION_DAYS * 86400
    for entry in logs_dir.glob(f"{_SESSION_PREFIX}*.log*"):
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            continue


def _build_session_path(logs_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return logs_dir / f"{_SESSION_PREFIX}{ts}.log"


def init_logging(level: int = logging.ERROR) -> Path:
    """Initialise the session logger. Idempotent. Returns active log file path."""
    global _session_file, _handler, _root_configured

    logs_dir = paths.logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    _prune_old_logs(logs_dir)

    if _root_configured and _handler is not None and _session_file is not None:
        logging.getLogger().setLevel(level)
        return _session_file

    _session_file = _build_session_path(logs_dir)
    _handler = RotatingFileHandler(
        _session_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    _handler.setFormatter(_TzFormatter())
    _handler.addFilter(_PinMaskingFilter())

    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        if isinstance(existing, RotatingFileHandler) and getattr(
            existing, "_adb_helper_session", False
        ):
            root.removeHandler(existing)
    setattr(_handler, "_adb_helper_session", True)
    root.addHandler(_handler)
    _root_configured = True
    return _session_file


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Calls :func:`init_logging` on first use."""
    if not _root_configured:
        init_logging()
    return logging.getLogger(name)


def set_level(level: int) -> None:
    logging.getLogger().setLevel(level)


def session_log_file() -> Optional[Path]:
    return _session_file
