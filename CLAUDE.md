# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture invariants — NEVER violate these

These rules are load-bearing. Any change that breaks one of them is wrong even if it compiles and passes tests.

1. **ADB I/O isolation.** No module, widget, or helper may call `subprocess`, `QProcess`, or any shell against the `adb` binary directly. All ADB traffic — one-shot commands, long-lived processes, and device monitoring — goes through `src/adb_helper/core/adb_service.py`. The service exposes Qt signals; the UI subscribes. Grep for `"adb"` in any non-core file should return zero command-construction sites.
2. **IModule contract.** Every screen in `src/adb_helper/modules/` is a `QWidget` subclass that also implements `IModule` from `core/imodule.py`: `on_activate()`, `on_deactivate()`, `on_device_changed(ctx: DeviceContext)`, `on_device_disconnected()`. Modules are discovered via `core/registry.py`; sidebar order and labels are read from the registry, never hard-coded.
3. **Strings centralised.** All user-facing strings (button labels, dialog text, status messages, error translations, tooltips) live in `src/adb_helper/core/strings.py`. No string literals in widgets. This keeps the UI i18n-ready even though v1.0 is English-only.
4. **Platform shims only in `core/platform.py`.** Anything that branches on Windows vs Linux — paths, ConPTY vs `pty`, named-pipe vs UDS, lock acquisition, theme polling — lives in `core/platform.py`. Modules and the UI must not contain `if sys.platform == ...` checks.
5. **§9 Out of Scope is binding.** No code, UI element, menu item, setting, or string may exist for: root-required ops, GUI-action macro recording, streaming logcat, file push/pull manager, screen recording, macOS, multi-device macro playback, `.aab` install, app-icon extraction, auto-reconnect of paired Wi-Fi devices. If a feature request leans on any of these, push back before writing code.

## Repository state

The scaffold exists: `src/adb_helper/{core,modules,ui}`, `db/migrations/`, `assets/fonts/`, `tests/`, `main.py`, `pyproject.toml`. Module files are stubs — every module's `QWidget` body is `pass`. No real ADB calls are wired up yet. The technical spec and design handoff (see below) are the source of truth for what each stub becomes.

- `ADB_Helper_Technical_Specification.md` — the full functional/technical spec for the application to be built.
- `adb-helper_handoff_Claude_Design/project/` — an HTML/CSS/JS design prototype exported from Claude Design. It is a visual reference, **not** the target implementation.
- `src/adb_helper/ui/DESIGN_TOKENS.md` — extracted design tokens (colours, spacing, typography) for QSS generation.

There are no build, lint, or test commands wired up yet. Do not invent commands the user has not authorised.

## What is being built

**ADB_Helper** — a single-instance desktop GUI for managing Android devices over ADB. Personal/single-developer tool, no distribution packaging required.

- **Stack:** Python 3.12 + PySide6 (Qt 6), SQLite for persistence, JSON for settings, PyInstaller single-dir build.
- **Target platforms:** Windows 11 and Ubuntu 22.04+. macOS is explicitly out of scope.
- **Terminal emulation:** ConPTY on Windows, Python `pty` module on Linux, both via `QProcess`.
- **Bundled binaries:** `platform-tools` (adb), `scrcpy`, `bundletool` + JRE 17. All auto-update via vendor sources with SHA-256-verified atomic replace.

## Architecture (from the spec — read this before adding modules)

The spec mandates a strict layered design. Future code must respect it:

1. **ADB Service layer is the only thing that talks to `adb`.** No module shells out to ADB directly. The service exposes:
   - `CommandRunner` — thread-pooled one-shot commands with timeout + Normal/High priority.
   - `ProcessManager` — long-lived processes (terminal PTY, scrcpy, logcat export).
   - `DeviceMonitor` — primary: `adb track-devices` (server-push); fallback: `adb devices` polled every 3 s.
   - Qt signals (`commandStarted/Finished/Failed`, `deviceConnected/Disconnected/StateChanged`, `processStarted/Stopped/Output`) drive all UI updates — no polling from the UI.
   - Error parser translates known ADB error strings into English user-facing messages, while still surfacing raw ADB output alongside.

2. **Modules are pluggable `QWidget` subclasses** implementing an `IModule` interface: `on_activate()`, `on_deactivate()`, `on_device_changed(ctx: DeviceContext)`, `on_device_disconnected()`. They are registered in a central registry; sidebar nav is data-driven from that registry. Adding a module = new widget class + registry entry, no core changes.

3. **Active device is global, except in Installer.** The active device (selected in Connections) is shown in the status bar and used by every module — Installer alone keeps its own multi-device checklist because it installs to N devices at once.

4. **Sequential installation semantics.** Installer iterates file × device sequentially. Per-device disconnect mid-run marks remaining files as Failed for that device and continues; per-file errors don't abort the batch.

5. **Persistence boundaries.**
   - `settings.json` — app settings, carries `"schema_version"`; missing keys backfilled with defaults on startup, unknown future keys preserved.
   - `adb_helper.db` (SQLite) — macros, command history (last 50), paired Wi-Fi devices, backup records. Uses `PRAGMA user_version`; migrations under `db/migrations/` applied in order at startup, **before** UI init.
   - App data root: `%APPDATA%\ADB_Helper\` (Windows), `~/.config/adb_helper/` (Linux). Subdirs: `logs/`, `screenshots/`, `logcat/`, `platform-tools/`, `scrcpy/`, `bundletool/`.

6. **Single-instance enforcement.** Lockfile `<app_data>/adb_helper.lock` (OS exclusive lock). Second launch signals the running instance via **named pipe (Windows) / Unix domain socket (Linux)** to raise its window, then exits 0.

7. **Security-sensitive logging.** All ADB I/O is logged (device serials/IPs are not scrubbed — private-use tool). The **only** mandatory redaction: `adb pair` PIN codes are always replaced with `*****` in logs regardless of log level.

## Modules (sidebar order — Connections is the default on launch)

`connections`, `terminal`, `installer`, `scrcpy`, `buttons` (Device Buttons), `info` (Device Info), `apps`, `logcat`, `settings`. The prototype already wires these screens — see `adb-helper_handoff_Claude_Design/project/modules/*.jsx` for the intended UX of each.

Notable per-module rules:

- **Terminal** is always an `adb shell` on the active device, not a host OS shell. Macros record terminal commands only — GUI-button macros and interactive stdin are explicitly out of scope.
- **Scrcpy** launches as a **separate top-level process window** — do **not** embed it inside the Qt main window.
- **Logcat** export is one-shot (`adb logcat -d`), no streaming. Filenames use host TZ offset, e.g. `logcat_15.03.25_14.32_GMT+5.txt`. The reference `logcat.bat` defines naming/TZ logic only — replicate in Python, do **not** invoke the batch file.
- **Apps**: no icon extraction (unreliable without root). System apps cannot be uninstalled — only disabled. `.aab` install is unsupported (requires dev signing key).
- **Device Info** is static-on-activate with a Refresh button — no background polling.

## Out of scope for v1.0

Root-required ops, GUI-action macros, live/streaming logcat, file push/pull manager, screen recording, macOS, multi-device macro playback, `.aab` install, app-icon extraction, auto-reconnect of paired Wi-Fi devices on startup.

## Working with the design prototype

`adb-helper_handoff_Claude_Design/project/` is React-via-Babel-standalone CDN (no build step). It exists to communicate **visual intent and interaction flow** for the future PySide6 port. Notes:

- `index.html` loads all `.jsx` modules in dependency order via `<script type="text/babel">`. There is no bundler.
- `data.jsx` exposes `MOCK_*` constants on `window` — modules read those instead of hitting any real ADB.
- `styles.css` defines design tokens (dark default, light variant, OKLCH accent palette, density modes). Match these visual semantics when translating to QSS, but the prototype's DOM structure is not normative.
- The prototype's `README.md` says: do not render in a browser or screenshot it — read the HTML/CSS directly.

When the user asks to "implement module X", treat the JSX module as the UX spec and the technical spec section (§3.x) as the behavioural spec; defer to the spec when they conflict.
