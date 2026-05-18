# ADB_Helper

Desktop GUI for managing Android devices over ADB. Single-developer tool — Windows 11 and Ubuntu 22.04+ only. macOS not supported.

## Status

Scaffolding stage. Module bodies are stubs. No ADB logic is wired up yet.

## Documents

- `ADB_Helper_Technical_Specification.md` — full functional/technical spec (normative).
- `CLAUDE.md` — architecture invariants for AI-assisted contributors.
- `adb-helper_handoff_Claude_Design/` — HTML/CSS/JS design prototype (visual reference only).
- `src/adb_helper/ui/DESIGN_TOKENS.md` — extracted design tokens for QSS generation.

## Layout

```text
src/adb_helper/
  core/        ADB service, models, IModule, registry, paths, strings, platform shims
  modules/     One QWidget per sidebar entry (§3.x of the spec)
  ui/          QSS, theme manager, common widgets, DESIGN_TOKENS.md
db/migrations/ SQL schema migrations applied at startup before UI init
assets/fonts/  JetBrains Mono (bundled Linux fallback; Cascadia Code is built-in on Win 11)
tests/         pytest suite
main.py        Entry point
```

## Dependencies

- Python 3.12
- PySide6 >= 6.7 (Qt 6)
- darkdetect >= 0.8
- pyinstaller >= 6.0 (build only)

All other imports are stdlib: `sqlite3`, `subprocess`, `json`, `pathlib`, `threading`, `socket`, `fcntl`.

## Running

Not runnable yet. Once implementation lands:

```bash
python -m venv .venv
. .venv/bin/activate            # Linux
.venv\Scripts\activate          # Windows
pip install -e .
python main.py
```
