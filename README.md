# ADB_Helper

**v1.0.0** — Desktop GUI for managing Android devices over ADB. Connects, inspects, installs APKs, mirrors screens via scrcpy, exports logcat, and manages apps. UI is a Vue 3 + Tailwind SPA hosted inside a single `QWebEngineView`; all Vue ↔ Python traffic flows through `QWebChannel`. Backend (`src/adb_helper/core/`) is pure Python — no Qt widgets in module logic. Designed for daily personal use on Windows 11 and Ubuntu 22.04+. macOS is not supported.

## Architecture at a glance

```
PySide6 QMainWindow
  └── QWebEngineView  ← QWebChannel ──→  Vue 3 SPA (frontend/)
       host-side bridges live in src/adb_helper/web/bridge/*
       backend services unchanged in src/adb_helper/core/
```

---

## Ubuntu 22.04+ prerequisites

```bash
# Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev

# Android udev rules (run once, then replug device)
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="*", MODE="0664", GROUP="plugdev"' \
    | sudo tee /etc/udev/rules.d/51-android.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# Add yourself to plugdev
sudo usermod -aG plugdev "$USER"
# Log out and back in for group change to take effect.
```

---

## Install from source

```bash
git clone <repo-url> ADB_Helper
cd ADB_Helper

python3.12 -m venv .venv
source .venv/bin/activate

pip install -e .

# Build the Vue frontend (required — Python loads it from frontend_dist/).
cd frontend && npm ci && npm run build && cd ..

adb-helper
```

### Dev mode (HMR)

Set `ADBH_DEV=1` and the Python host will spawn Vite as a child process
and load `http://127.0.0.1:5173/` once it's ready.

```bash
ADBH_DEV=1 python main.py
# OR override the dev URL if Vite runs elsewhere:
ADBH_DEV=1 ADBH_DEV_URL=http://127.0.0.1:5174/ python main.py
```

Frontend stack: Vue 3 + Vite 6 + Pinia + Tailwind 3 + TypeScript + xterm.js.

---

## PyInstaller build (onedir)

```bash
source .venv/bin/activate
pip install -e ".[build]"

# Vue bundle is bundled INSIDE the Python binary — build it first.
cd frontend && npm ci && npm run build && cd ..

pyinstaller adb_helper.spec
# Output: dist/adb_helper/
```

Run the resulting binary:

```bash
dist/adb_helper/adb_helper          # Linux
dist\adb_helper\adb_helper.exe      # Windows
```

---

## Windows 11 quick-start

1. Install Python 3.12 from python.org (check "Add to PATH").
2. Open PowerShell in the project folder:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e .
   adb-helper
   ```

3. Enable USB debugging on the device (Settings → Developer options → USB debugging).
4. Accept the RSA key prompt on the device when first connected.

No udev rules needed on Windows; ADB uses WinUSB drivers automatically.

---

## Out of scope (v1.0)

Root-required operations, GUI-action macro recording, streaming/live logcat, file push/pull manager, screen recording, macOS, multi-device macro playback, `.aab` install, app-icon extraction, auto-reconnect of paired Wi-Fi devices on startup.

---

## Tests

```bash
.venv/bin/python -m pytest -q
```

Pure-function unit tests live in `tests/`. No Qt event loop is started by
default (`QT_QPA_PLATFORM=offscreen` is set in `tests/conftest.py`); the
installer-queue suite spins up a minimal `QCoreApplication`.

---

## Documents

- `ADB_Helper_Technical_Specification.md` — full functional/technical spec (normative).
- `CLAUDE.md` — architecture invariants and contribution rules.
- `design.html` — visual reference (dark/light tokens, layout intent).
- `frontend/src/style.css` — design tokens applied to Tailwind.
