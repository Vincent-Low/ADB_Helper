"""Pytest configuration — make src/ importable without -e install."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Skip Qt platform plugin probing in headless CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
