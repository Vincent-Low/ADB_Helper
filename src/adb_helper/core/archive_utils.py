"""Archive extraction + SHA-256 verification helpers.

Pulled out of ``modules/scrcpy.py`` so the Vue bridge can use them
without dragging QtWidgets into the import graph.  Behaviour is
preserved exactly — see Spec §3.4 / §6.2.
"""
from __future__ import annotations

import re
import tarfile
import zipfile
from pathlib import Path
from typing import Optional


def parse_sha256sum(path: Path) -> Optional[str]:
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


def extract_archive(archive: Path, dest_root: Path) -> Path:
    """Extract ``archive`` into ``dest_root``; return the extracted top dir.

    Refuses absolute or ``..``-traversing members (Zip Slip).
    """
    if archive.name.endswith(".tar.gz") or archive.name.endswith(".tgz"):
        with tarfile.open(archive, "r:gz") as tf:
            members = tf.getmembers()
            top_names = {_top_segment(m.name) for m in members if m.name}
            top_names.discard("")
            for m in members:
                if _is_unsafe_member(m.name):
                    raise tarfile.TarError(f"unsafe path in archive: {m.name!r}")
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


__all__ = ["parse_sha256sum", "extract_archive"]
