# ADB_Helper

Desktop GUI for managing Android devices over ADB. Connects, inspects, installs APKs, mirrors screens via scrcpy, tails logcat, and manages apps — all from a single PySide6 window. Designed for daily personal use on Windows 11 and Ubuntu 22.04+. macOS is not supported.

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
adb-helper
```

---

## PyInstaller build (onedir)

```bash
source .venv/bin/activate
pip install -e ".[build]"
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

## Documents

- `ADB_Helper_Technical_Specification.md` — full functional/technical spec (normative).
- `CLAUDE.md` — architecture invariants and contribution rules.
- `adb-helper_handoff_Claude_Design/` — HTML/CSS/JS design prototype (visual reference only).
- `src/adb_helper/ui/DESIGN_TOKENS.md` — extracted design tokens for QSS generation.
