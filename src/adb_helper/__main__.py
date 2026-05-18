"""Allow `python -m adb_helper` and `adb-helper` console script."""
from __future__ import annotations

import sys


def main() -> int:
    import os
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    import main as _entry
    return _entry.main()


if __name__ == "__main__":
    sys.exit(main())
