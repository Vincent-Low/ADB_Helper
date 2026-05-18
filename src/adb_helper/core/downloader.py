"""Atomic downloader (Spec §1.5).

SHA-256 verified downloads written to ``<dest>.tmp`` and ``os.replace``-d
into place. GitHub ``/releases/latest`` fetcher with a 6-hour on-disk cache
(Spec §3.4.1) to avoid API rate limiting.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from .logger import get_logger

_log = get_logger(__name__)

_DEFAULT_CACHE_TTL_S = 6 * 3600
_CHUNK = 64 * 1024
_USER_AGENT = "ADB_Helper/1.0"


class AtomicDownloader:
    """Atomic, SHA-256-verified file downloader + GitHub release fetcher."""

    @staticmethod
    def download(
        url: str,
        dest: Path,
        expected_sha256: Optional[str] = None,
        timeout: int = 60,
    ) -> bool:
        """Stream ``url`` to ``dest`` atomically, verifying SHA-256 if given.

        Writes to ``dest.tmp`` and renames on success. Removes the partial on
        any failure. Returns True on success, False otherwise.
        """
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        hasher = hashlib.sha256()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as fh:
                while True:
                    chunk = resp.read(_CHUNK)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    fh.write(chunk)
                fh.flush()
                os.fsync(fh.fileno())
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            _log.error("download failed url=%s err=%s", url, exc)
            _unlink_silent(tmp)
            return False

        actual = hasher.hexdigest()
        if expected_sha256 is not None and actual.lower() != expected_sha256.lower():
            _log.error(
                "sha mismatch url=%s expected=%s actual=%s",
                url, expected_sha256, actual,
            )
            _unlink_silent(tmp)
            return False

        try:
            os.replace(tmp, dest)
        except OSError as exc:
            _log.error("atomic replace failed dest=%s err=%s", dest, exc)
            _unlink_silent(tmp)
            return False

        _log.info("download ok url=%s dest=%s sha=%s", url, dest, actual)
        return True

    @staticmethod
    def get_latest_github_release(
        owner: str,
        repo: str,
        cache_path: Optional[Path] = None,
        ttl_seconds: int = _DEFAULT_CACHE_TTL_S,
        timeout: int = 30,
    ) -> Optional[dict]:
        """Fetch ``/repos/{owner}/{repo}/releases/latest`` with on-disk caching."""
        now = time.time()
        if cache_path is not None:
            cached = _read_cache(cache_path)
            if cached is not None and now - float(cached.get("_fetched_at", 0)) < ttl_seconds:
                data = cached.get("data")
                if isinstance(data, dict):
                    return data

        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            _log.error("github release fetch failed %s/%s err=%s", owner, repo, exc)
            return None

        if not isinstance(data, dict):
            return None

        if cache_path is not None:
            _write_cache(cache_path, {"_fetched_at": now, "data": data})
        return data


def _unlink_silent(p: Path) -> None:
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def _read_cache(path: Path) -> Optional[dict]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _write_cache(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        _log.warning("release cache write failed path=%s err=%s", path, exc)


__all__ = ["AtomicDownloader"]
