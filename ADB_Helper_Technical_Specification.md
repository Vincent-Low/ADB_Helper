# ADB_Helper — Technical Specification

## Table of Contents

- [1. General Information](#1-general-information)
  - [1.1 Purpose and Context](#11-purpose-and-context)
  - [1.2 Target Platforms](#12-target-platforms)
  - [1.3 Technology Stack](#13-technology-stack)
  - [1.4 Application Data Storage](#14-application-data-storage)
  - [1.5 Third-Party Dependencies](#15-third-party-dependencies)
  - [1.6 Database Schema Versioning](#16-database-schema-versioning)
  - [1.7 Single-Instance Enforcement](#17-single-instance-enforcement)
- [2. User Interface](#2-user-interface)
  - [2.1 Window Layout](#21-window-layout)
  - [2.2 Theming](#22-theming)
    - [2.2.1 Terminal Colours](#221-terminal-colours)
  - [2.3 Language](#23-language)
  - [2.4 Privilege Elevation](#24-privilege-elevation)
- [3. Modules](#3-modules)
  - [3.1 Module: Connections](#31-module-connections)
  - [3.2 Module: Terminal](#32-module-terminal)
  - [3.3 Module: Installer](#33-module-installer)
  - [3.4 Module: Scrcpy](#34-module-scrcpy)
  - [3.5 Module: Device Buttons](#35-module-device-buttons)
  - [3.6 Module: Device Info](#36-module-device-info)
  - [3.7 Module: Apps](#37-module-apps)
  - [3.8 Module: Logcat](#38-module-logcat)
  - [3.9 Module: Settings](#39-module-settings)
- [4. Logging](#4-logging)
- [5. ADB Service Layer](#5-adb-service-layer)
- [6. Platform-Specific Notes](#6-platform-specific-notes)
- [7. Error Handling — General Rules](#7-error-handling--general-rules)
- [8. Future Extensibility](#8-future-extensibility)
- [9. Out of Scope (Version 1.0)](#9-out-of-scope-version-10)
- [Revision History](#revision-history)

---

## 1. General Information

### 1.1 Purpose and Context

ADB_Helper is a desktop GUI application that provides a user-friendly graphical interface for working with Android devices via ADB (Android Debug Bridge). The application is intended for personal use by a single developer; distribution and retail packaging are not required.

The application runs as a single instance: if a second launch is attempted while it is already running, the second instance exits immediately and brings the existing window to the foreground.

### 1.2 Target Platforms

| Platform | Minimum Version    |
| -------- | ------------------ |
| Windows  | Windows 11         |
| Linux    | Ubuntu 22.04 LTS and later |

The application must be runnable on both platforms from source. Distribution is by copying the unpacked source tree between machines; no installer or packaged executable is required.

### 1.3 Technology Stack

| Component             | Choice                                                                  |
| --------------------- | ----------------------------------------------------------------------- |
| Language              | Python 3.12                                                             |
| UI Framework          | PySide6 (Qt 6)                                                          |
| Database              | SQLite — macros, command history, paired devices, backup records        |
| Configuration storage | JSON files                                                              |
| Terminal emulation    | ConPTY (Windows) / Python `pty` module (Linux), via `QProcess`          |
| Packaging             | PyInstaller single-directory build (primary); Nuitka experimental       |

### 1.4 Application Data Storage

| Platform | Path                          |
| -------- | ----------------------------- |
| Windows  | `%APPDATA%\ADB_Helper\`       |
| Linux    | `~/.config/adb_helper/`       |

Stored data directories:

- `settings.json` — application settings
- `adb_helper.db` — SQLite database (macros, command history, paired devices)
- `logs/` — log files
- `screenshots/` — default screenshot save location (configurable)
- `logcat/` — default logcat export save location
- `platform-tools/` — bundled ADB platform-tools
- `scrcpy/` — bundled scrcpy binaries
- `bundletool/` — bundletool JAR + bundled JRE 17

### 1.5 Third-Party Dependencies

| Component             | Source                                                                  | Update Mechanism                                                                                |
| --------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| ADB (platform-tools)  | `dl.google.com/android/repository/platform-tools-latest-{os}.zip`       | Download ZIP, compare `adb --version`, atomic overwrite with SHA-256 verification               |
| scrcpy                | `github.com/Genymobile/scrcpy/releases`                                 | GitHub API `/releases/latest`, parse asset by OS pattern, SHA-256 verification                  |
| bundletool            | `github.com/google/bundletool/releases`                                 | GitHub API `/releases/latest`, download JAR, SHA-256 verification                               |
| JRE 17 (bundled)      | Adoptium (Eclipse Temurin)                                              | Bundled at first run; updated only with a new application release                               |

> **Note:** JRE 17 is not updated independently. CVE fixes in JRE arrive only with a new application release.

> **Note:** Update downloads are atomic: files are written to a temporary location and replaced only after SHA-256 verification succeeds. If the download fails mid-way, the existing binaries remain intact.

### 1.6 Database Schema Versioning

The SQLite database carries a `user_version` pragma that encodes the schema version as an integer (e.g., 1, 2, 3…). On every application startup the service layer reads the current `user_version` and applies any pending migrations in order before the UI initialises. Each migration is an idempotent SQL script stored in the source tree under `db/migrations/`.

Current schema version: **2**. Migrations applied:

- `0001_initial.sql` — creates `command_history`, `macros`, `paired_devices` tables (schema v1).
- `0002_paired_connect_port.sql` — adds `connect_port INTEGER` column to `paired_devices` (schema v2).

`settings.json` carries a `"schema_version"` integer key. On startup, if the version is lower than expected, the application merges missing keys with their defaults and writes the updated file. Unknown keys from a future version are preserved (forward-compatible read).

### 1.7 Single-Instance Enforcement

On startup the application attempts to acquire a lock file at `<app_data>/adb_helper.lock` (using an OS-level exclusive file lock). If the lock is already held, the running instance is signalled to bring its window to the foreground (via a named pipe on Windows, a Unix domain socket on Linux), and the second instance exits with code 0.

---

## 2. User Interface

### 2.1 Window Layout

Default size: **1280 × 800 px**. Minimum size: **960 × 600 px**. Orientation: landscape. Resizable: yes. Window position and size are saved to `settings.json` on close and restored on next launch.

Layout structure:

- **Left sidebar** (collapsible): navigation between modules. On screens narrower than 1280 px the sidebar collapses to icon-only mode automatically.
- **Main content area** (right of sidebar): displays the active module.
- **Status bar** (bottom): shows the currently selected device (serial + model), connection type (USB / Wi-Fi), and application status messages.

Adaptive behaviour:

- ≥ 1920 px: sidebar expanded with labels; main area uses full available space.
- < 1280 px: sidebar collapses to icons; main area remains fully functional.
- All widgets use relative sizing (stretch factors, minimum sizes) rather than fixed pixel values.
- The layout must accommodate future addition of new modules without redesign.

### 2.2 Theming

| Theme                  | Behaviour                                                                                                                                                |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System theme (default) | Follows the OS light/dark preference; on Windows 11 updated in real time via system events; on Linux polled every 30 seconds via `darkdetect` (best-effort). |
| Light theme            | Always light regardless of OS setting.                                                                                                                   |
| Dark theme             | Always dark regardless of OS setting.                                                                                                                    |

Theme selection is available in Settings and persisted in `settings.json`. Implementation: QSS stylesheets + `darkdetect`.

#### 2.2.1 Terminal Colours

The terminal widget uses a curated 16-colour ANSI palette that is legible on both themes:

| ANSI role                  | Light theme hex     | Dark theme hex      |
| -------------------------- | ------------------- | ------------------- |
| Background                 | `#FFFFFF`           | `#1E1E1E`           |
| Foreground (default text)  | `#1E1E1E`           | `#D4D4D4`           |
| Black / Bright black       | `#000000` / `#767676` | `#3A3A3A` / `#858585` |
| Red / Bright red           | `#CC0000` / `#E06C75` | `#CC3333` / `#E06C75` |
| Green / Bright green       | `#008000` / `#98C379` | `#3CB371` / `#98C379` |
| Yellow / Bright yellow     | `#B8860B` / `#E5C07B` | `#D4A017` / `#E5C07B` |
| Blue / Bright blue         | `#0550AE` / `#61AFEF` | `#569CD6` / `#61AFEF` |
| Magenta / Bright magenta   | `#8B008B` / `#C678DD` | `#9B59B6` / `#C678DD` |
| Cyan / Bright cyan         | `#007070` / `#56B6C2` | `#2AA198` / `#56B6C2` |
| White / Bright white       | `#BBBBBB` / `#FFFFFF` | `#C0C0C0` / `#FFFFFF` |

Monospace font: **Cascadia Code** (Windows 11 built-in); **JetBrains Mono** (bundled fallback for Ubuntu 22.04); system monospace as final fallback. Font size: **13 pt**.

### 2.3 Language

The entire user interface and all log output are in **English only**.

### 2.4 Privilege Elevation

Operations that require elevated privileges prompt the user to run as Administrator (Windows UAC) or with `sudo`/`pkexec` (Linux). The application detects whether it is already running with elevated privileges and shows the prompt only when necessary.

---

## 3. Modules

The application consists of the following modules accessible from the sidebar:

- Connections (default on launch)
- Terminal
- Installer
- Scrcpy
- Device Buttons
- Device Info
- Apps
- Logcat
- Settings

Each module is implemented as a self-contained `QWidget` subclass implementing `IModule` (see §8).

### 3.1 Module: Connections

Default module shown on application launch. **Purpose:** manage ADB device connections — connect, disconnect, and monitor devices.

#### 3.1.1 Device List

Displays all currently connected ADB devices. The list is driven by `adb track-devices` (a persistent ADB server connection that pushes state changes). A polling fallback (`adb devices` every 3 seconds) is used only if `track-devices` fails to initialise.

| Column     | Description                                                       |
| ---------- | ----------------------------------------------------------------- |
| Serial     | ADB serial (e.g., `emulator-5554`, `192.168.1.10:5555`)           |
| IP Address | Shown for Wi-Fi connections; empty for USB                        |
| Model      | Device model name (from `ro.product.model`)                       |
| Status     | Online, Offline, Unauthorized                                     |

**Unauthorized status:** displayed with an information icon (ⓘ). Clicking it opens a dialog: *"Unlock your device, go to Developer Options, and tap Allow on the USB debugging authorization prompt. Then reconnect the device."*

**Device selection:** clicking a device selects it as the active device, shown in the status bar and used by all other modules except Installer. Selection persists until changed by the user or until the device disconnects.

**Device disconnection:** if the active device disconnects while in any module, a modal dialog is shown: *"Device [model] ([serial]) has been disconnected."* After dismissal, the app navigates to Connections and clears the active device.

#### 3.1.2 USB Connection

USB-connected devices appear automatically when ADB detects them. No manual action required.

#### 3.1.3 Wi-Fi — Classic (`adb tcpip` / `adb connect`)

For Android 10 and earlier, or when the new pairing mechanism is unavailable:

- User enters device IP address and port (default: `5555`) and clicks **Connect**.
- The application runs `adb connect <ip>:<port>` and displays the result.
- On success the device appears in the device list.

#### 3.1.4 Wi-Fi — New Pairing (Android 11+)

- User opens **Wireless Debugging** on the device and taps **Pair device with pairing code**.
- User enters IP address, pairing port, and 6-digit PIN in ADB_Helper.
- User clicks **Pair**. Application runs `adb pair <ip>:<pairing_port> <pin>`.
- The PIN is masked in all log output (replaced with `*****`).
- On successful pairing, the paired device record (IP, alias, connection port) is saved to the database and the Paired Devices list refreshes. No automatic post-pair connect is attempted — the user sets the connection port in the Paired Devices list and clicks **Connect** there.
- On failure, the raw ADB error is shown.

#### 3.1.5 Paired Devices List

A persistent list below the live device list shows previously paired Wi-Fi devices (stored in SQLite). Columns: **Alias** (editable inline), **IP Address**, **Connection Port** (editable inline; the port used for `adb connect`, distinct from the pairing port), **Last Connected**. Actions: **Connect** (runs `adb connect <ip>:<connection_port>`; port value is saved back to the database on each connect), **Forget** (removes from DB). The list is informational only — no automatic reconnection on startup.

#### 3.1.6 Disconnect

Select a device and click **Disconnect**. Runs `adb disconnect <serial>`. Device is removed from the live list.

### 3.2 Module: Terminal

**Purpose:** interactive ADB shell terminal for executing commands manually and managing macros. The terminal is always an `adb shell` session on the active device — it is not a general OS shell.

#### 3.2.1 Terminal Emulator

- Full interactive terminal: **ConPTY on Windows**, **`pty` module on Linux**, integrated via `QProcess`.
- Correctly renders ANSI escape codes (colour, cursor movement, title changes).
- Uses the colour palette defined in §2.2.1.
- **Clear** button: clears terminal output. Keyboard shortcut: `Ctrl+L`.

#### 3.2.2 Command History

- The last 50 commands are stored persistently in SQLite across sessions.
- Navigation with `Up`/`Down` arrow keys in the command input field.
- **History** button: opens a modal panel listing all saved commands. Clicking an entry inserts it into the input field.

#### 3.2.3 Macro Recording

A macro is a sequential recording of commands entered and executed in the terminal. Macros record only commands; interactive prompts (stdin during execution) are not supported. Macros are not bound to a specific device — playback runs on the current active device.

**Recording workflow:**

- User clicks **Record Macro**. Button label changes to **Stop Recording**.
- All commands entered during recording are captured in order.
- User clicks **Stop Recording**. A dialog appears with a Macro name field and **Save** / **Cancel** buttons.
- **Save**: macro is saved to the database and appears in the macro list.
- **Cancel**: recording is discarded; button returns to **Record Macro**.

**Macro list:**

- Single click: selects the macro; **Play** button becomes active.
- Double click: immediately starts playback.
- Right-click context menu: **Rename**, **Delete**, **Export**.

**Playback:**

- **Play** button starts playback; label changes to **Stop**.
- Progress shows current command index (e.g., *"Running command 3 of 7"*) and command text.
- On completion, label returns to **Play**.
- Clicking **Stop** halts execution of the current and remaining commands immediately.
- Macros run on a single active device only. Multi-device playback is out of scope.

**Macro export:** exports as `.json` file containing macro name and commands array.

### 3.3 Module: Installer

**Purpose:** install APK files and APK bundles onto one or more connected ADB devices. The Installer module is **independent of the active device selection** — it maintains its own device checklist.

#### 3.3.1 Supported File Formats

| Format   | Installation Method                                                                                                | Notes                                                                                          |
| -------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `.apk`   | `adb install`                                                                                                      | Standard single APK                                                                            |
| `.apks`  | `bundletool install-apks` (requires bundled JRE 17 + bundletool JAR)                                               | Pre-built APK set; `.aab` files are **not** supported (require developer signing key)          |
| `.xapk`  | Unzip → parse `manifest.json` → `adb install-multiple` (split APKs) + `adb push` (OBB files if present)            | Supports split-APK structure with optional OBB payload as described in XApk manifest v2        |
| `.apkm`  | Unzip → `adb install-multiple` (split APKs)                                                                        | APKMirror format; ZIP containing split APK files; no OBB support                               |

> **Note:** `.aab` (Android App Bundle) is not supported because installation requires the developer's signing key.

#### 3.3.2 UI Layout

- **File selection area:** list of selected files. **Add Files** button (multi-select, filters: `*.apk *.apks *.xapk *.apkm`). Files can be removed individually and reordered via drag-and-drop.
- **Device selection area:** checklist of all connected devices (serial + model). No device is pre-checked; the user selects explicitly.
- **Install** button: active when at least one file and one device are selected.
- **Cancel** button: active during installation. Stops after the current file/device operation completes.

#### 3.3.3 Installation Behaviour

- Installation proceeds **sequentially**: file 1 on device 1, file 1 on device 2, …, file 2 on device 1, etc.
- During installation the **Install** button is disabled. Progress shows the current operation.
- If a device disconnects mid-installation, its remaining files are marked as **Failed** and installation continues on other devices.
- If an error occurs on one device, installation continues on remaining devices and files.
- On completion a summary dialog shows successes and failures. Failures include a human-readable error AND the raw ADB/bundletool output.
- The result log is cleared when the user adds new files for the next session.

### 3.4 Module: Scrcpy

**Purpose:** launch scrcpy to mirror and control the active ADB device. scrcpy is launched as a **separate process in its own window** — it is **NOT** embedded in the ADB_Helper window.

#### 3.4.1 Binary Management

| OS              | Asset Pattern                       |
| --------------- | ----------------------------------- |
| Windows 64-bit  | `scrcpy-win64-v*.zip`               |
| Linux x86_64    | `scrcpy-linux-x86_64-v*.tar.gz`     |

- Binaries stored in `<app_data>/scrcpy/`.
- On first launch, if no binary is found, automatic download is attempted via GitHub API.
- GitHub API response is cached for 6 hours to avoid rate limiting.
- If download fails, an instruction panel is shown with manual download steps and a **Retry** button.

#### 3.4.2 Launch Options

| Option                       | Type                | Default   |
| ---------------------------- | ------------------- | --------- |
| Video bitrate                | Dropdown / slider   | 8 Mbps    |
| Max resolution               | Dropdown            | No limit  |
| Display orientation lock     | Dropdown            | Auto      |
| Stay awake                   | Checkbox            | Off       |
| Show touches                 | Checkbox            | Off       |
| Turn screen off              | Checkbox            | Off       |

**Launch** button starts scrcpy with the selected options. Disabled if no active device is selected.

### 3.5 Module: Device Buttons

**Purpose:** simulate hardware and software button presses on the active device via ADB.

| Button         | ADB Command                                                                |
| -------------- | -------------------------------------------------------------------------- |
| Home           | `adb shell input keyevent KEYCODE_HOME`                                    |
| Back           | `adb shell input keyevent KEYCODE_BACK`                                    |
| Recent Apps    | `adb shell input keyevent KEYCODE_APP_SWITCH`                              |
| Volume +       | `adb shell input keyevent KEYCODE_VOLUME_UP`                               |
| Volume −       | `adb shell input keyevent KEYCODE_VOLUME_DOWN`                             |
| Mute           | `adb shell input keyevent KEYCODE_VOLUME_MUTE`                             |
| Camera         | `adb shell input keyevent KEYCODE_CAMERA`                                  |
| Power          | `adb shell input keyevent KEYCODE_POWER`                                   |
| Reboot         | Confirmation dialog → `adb reboot` (normal reboot only)                    |
| Screenshot     | See §3.5.1                                                                 |
| Screen Rotate  | Toggle `accelerometer_rotation` via `adb shell settings`                   |

**Reboot:** confirmation dialog — *"Are you sure you want to reboot the device?"* with **Reboot** / **Cancel** buttons.

#### 3.5.1 Screenshot

Capture method uses `exec-out` to avoid writing to device storage:

```
adb exec-out screencap -p > <screenshots_dir>\adb_helper_screenshot_<timestamp>.png
```

If `exec-out` is unavailable (older devices), fallback:

- `adb shell screencap -p /sdcard/adb_helper_screenshot_<timestamp>.png`
- `adb pull /sdcard/...` to the screenshots folder
- `adb shell rm /sdcard/...` (cleanup)

The file is also retained on the device when `exec-out` fallback is used (matches legacy behaviour). A notification is shown: *"Screenshot saved to: \<path\>"* with an **Open Folder** button. Screenshots folder: configurable in Settings. Default: `<app_data>/screenshots/`.

### 3.6 Module: Device Info

**Purpose:** display all device information available without root access. The view is static — data is fetched once on module activation. A **Refresh** button reloads all fields on demand. An **Export to TXT** button saves all fields to a plain text file (default filename: `device_info_<model>_<date>.txt`).

All field names and values are selectable and copyable (right-click → Copy or `Ctrl+C`). Fields unavailable on a specific device show `N/A`.

#### 3.6.1 Device Section

| Field             | Source                       |
| ----------------- | ---------------------------- |
| Manufacturer      | `ro.product.manufacturer`    |
| Model             | `ro.product.model`           |
| Device codename   | `ro.product.device`          |
| Brand             | `ro.product.brand`           |
| Serial number     | `adb get-serialno`           |

#### 3.6.2 System Section

| Field                  | Source                              |
| ---------------------- | ----------------------------------- |
| Android version        | `ro.build.version.release`          |
| API level              | `ro.build.version.sdk`              |
| Security patch level   | `ro.build.version.security_patch`   |
| Build number           | `ro.build.display.id`               |
| Build fingerprint      | `ro.build.fingerprint`              |
| Build type             | `ro.build.type`                     |
| Build date             | `ro.build.date`                     |
| Bootloader version     | `ro.bootloader`                     |
| Baseband / Radio       | `gsm.version.baseband`              |

#### 3.6.3 CPU Section

| Field                       | Source                                                                            |
| --------------------------- | --------------------------------------------------------------------------------- |
| CPU hardware name           | `/proc/cpuinfo` — `Hardware` field                                                |
| CPU model name              | `/proc/cpuinfo` — `model name` or `Processor` field                               |
| CPU architecture            | `ro.product.cpu.abi`                                                              |
| Number of cores             | `nproc` or count of `processor` entries in `/proc/cpuinfo`                        |
| CPU governor                | `/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`                           |
| Min / Max CPU frequency     | `cpuinfo_min_freq` and `cpuinfo_max_freq` (in MHz)                                |

#### 3.6.4 GPU Section

| Field               | Source                                                  |
| ------------------- | ------------------------------------------------------- |
| GPU vendor          | `dumpsys SurfaceFlinger` — `GLES:` line, vendor part    |
| GPU renderer        | `dumpsys SurfaceFlinger` — `GLES:` line, renderer part  |
| OpenGL ES version   | `dumpsys SurfaceFlinger` — `GLES:` line, version part   |

#### 3.6.5 Memory Section

| Field           | Source                              |
| --------------- | ----------------------------------- |
| Total RAM       | `/proc/meminfo` — `MemTotal`        |
| Available RAM   | `/proc/meminfo` — `MemAvailable`    |
| Total swap      | `/proc/meminfo` — `SwapTotal`       |

#### 3.6.6 Storage Section

| Field                       | Source       |
| --------------------------- | ------------ |
| Total internal storage      | `df /data`   |
| Available internal storage  | `df /data`   |

#### 3.6.7 Display Section

| Field            | Source                              |
| ---------------- | ----------------------------------- |
| Resolution (px)  | `dumpsys display` — physical size   |
| Density (dpi)    | `wm density`                        |
| Refresh rate     | `dumpsys display` — refresh rate    |

#### 3.6.8 Battery Section

| Field             | Source                                                                  |
| ----------------- | ----------------------------------------------------------------------- |
| Level (%)         | `dumpsys battery` — `level`                                             |
| Status            | `dumpsys battery` — `status` (Charging / Discharging / Full / Not charging) |
| Health            | `dumpsys battery` — `health`                                            |
| Temperature (°C)  | `dumpsys battery` — `temperature` ÷ 10                                  |
| Technology        | `dumpsys battery` — `technology`                                        |
| Voltage (mV)      | `dumpsys battery` — `voltage`                                           |

#### 3.6.9 Network Section

| Field                  | Source                                                                  |
| ---------------------- | ----------------------------------------------------------------------- |
| Wi-Fi IP address       | `ip addr show wlan0`                                                    |
| Wi-Fi MAC address      | `ip link show wlan0`                                                    |
| Bluetooth MAC          | `settings get secure bluetooth_address`                                 |
| IMEI (SIM 1 / SIM 2)   | `service call iphonesubinfo` — returns `N/A` on Android 10+ in most cases |

> **Note:** IMEI retrieval via `service call iphonesubinfo` requires privileged permissions on Android 10+. The field will show `N/A` on most modern devices. **This is expected behaviour.**

#### 3.6.10 Locale & Time Section

| Field      | Source                                              |
| ---------- | --------------------------------------------------- |
| Language   | `ro.product.locale` or `persist.sys.locale`         |
| Timezone   | `persist.sys.timezone`                              |

### 3.7 Module: Apps

**Purpose:** view, search, manage (disable/enable/uninstall), and export the list of installed applications. The list loads automatically each time the Apps module becomes active.

#### 3.7.1 App List Columns

| Column         | Description                       |
| -------------- | --------------------------------- |
| (checkbox)     | For multi-selection               |
| App Name       | Human-readable label              |
| Package Name   | e.g., `com.example.app`           |
| Status         | Active, Disabled (greyed row)     |

> **Note:** App icons are not displayed. Extracting icons from APKs on-device without root is unreliable and slow for large app lists.

**Data sources:** `adb shell pm list packages -f -3` (user apps) and `adb shell pm list packages -f -s` (system apps).

#### 3.7.2 Filters and Search

- **Search bar:** filters in real time by App Name or Package Name (case-insensitive substring match).
- **Show/hide system apps** toggle (default: shown).
- **Show/hide disabled apps** toggle (default: shown).

#### 3.7.3 RAM and Storage Progress Bars

Located at the top of the Apps module. **Updated on demand only** — a **Refresh** button triggers an immediate update. No automatic background polling.

- **RAM bar** — label: *"Used: X MB / Total: Y MB"* — source: `/proc/meminfo` (Used = MemTotal − MemAvailable)
- **Storage bar** — label: *"Used: X MB / Total: Y MB"* — source: `df /data`

#### 3.7.4 Delete (Uninstall)

Applies to **user apps only**. System apps cannot be uninstalled — the **Delete** button is disabled for system app selections (tooltip explains this). System apps can only be disabled (see §3.7.5).

- User selects user apps and clicks **Delete**.
- Dialog: *"Do you want to back up the selected apps before deleting?"* Note: Only APK files will be backed up. App data cannot be backed up without root access. Buttons: **Back Up and Delete** / **Delete Without Backup** / **Cancel**.
- **Back Up and Delete**: pulls APK to backup folder for each app, then uninstalls.
- Uninstall command: `adb shell pm uninstall --user 0 <package>` for each, sequentially with progress bar.
- After deletion, the app is immediately removed from the list.

#### 3.7.5 Disable

- User selects active apps and clicks **Disable**.
- Confirmation dialog: *"Are you sure you want to disable the following apps?"* (lists app names). Buttons: **Disable** / **Cancel**.
- Command: `adb shell pm disable-user --user 0 <package>` for each, sequentially with progress bar.
- Disabled apps shown with status **Disabled** and greyed-out row.
- Applies to both user apps and system apps.

#### 3.7.6 Enable

- User selects disabled apps and clicks **Enable**.
- Confirmation dialog: *"Are you sure you want to enable the following apps?"* (lists app names). Buttons: **Enable** / **Cancel**.
- Command: `adb shell pm enable <package>` for each, sequentially with progress bar.
- Re-enabled apps return to **Active** status.

#### 3.7.7 Export App List

**Export to CSV** button: exports the currently visible (filtered) list. Format: UTF-8 with BOM, comma delimiter. Columns: App Name, Package Name, Status, Type (User/System). Default filename: `apps_<device_model>_<date>.csv`.

### 3.8 Module: Logcat

**Purpose:** capture and save the full Android logcat buffer from the active device to a file on the host machine.

#### 3.8.1 Export Logcat

User clicks **Export Logcat**. The application executes:

```
adb -s <serial> logcat -d > <logcat_dir>/<filename>
```

Filename format: `logcat_<DD.MM.YY_HH.mm>_<TZ>.txt` where `TZ` is the host timezone offset (e.g., `GMT+5`, `GMT-3`). The timezone is derived from the host system at the time of export.

Examples:

- `logcat_15.03.25_14.32_GMT+5.txt`
- `logcat_15.03.25_09.17_GMT-3.txt`
- `logcat_15.03.25_12.00_GMT+0.txt`

#### 3.8.2 Save Location

Default save location: `<app_data>/logcat/`. Configurable in Settings (separate from screenshots folder). The directory is created automatically if it does not exist.

#### 3.8.3 Platform Implementation

| Platform | Implementation                                                                                                                                                                                  |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Windows  | Subprocess: `adb -s <serial> logcat -d` with stdout redirected to file. No intermediate `.bat` file is used — the application manages the process directly via Python `subprocess`.             |
| Linux    | Subprocess: `adb -s <serial> logcat -d` with stdout redirected to file. Uses Python `subprocess` with `shell=False`.                                                                            |

> **Note:** The provided `logcat.bat` is the reference implementation for naming conventions and timezone handling. The application replicates equivalent logic in Python without invoking the batch file.

#### 3.8.4 UI Behaviour

- A progress indicator (spinner) is shown while the export is running.
- On completion: notification *"Logcat saved to: \<path\>"* with an **Open Folder** button.
- On failure: error dialog with human-readable message and raw ADB output.
- The **Export Logcat** button is disabled if no active device is selected.
- Export is a one-shot capture (`-d` flag dumps the current buffer and exits); it does not stream continuously.

### 3.9 Module: Settings

**Purpose:** application configuration, dependency management, and version information.

#### 3.9.1 About Section

- Application name: **ADB_Helper**
- Application version (e.g., `1.0.0`)

#### 3.9.2 Installed Dependencies

| Component             | Installed Version    | Latest Version              | Status                                |
| --------------------- | -------------------- | --------------------------- | ------------------------------------- |
| ADB (platform-tools)  | e.g., `35.0.2`       | (fetched on update check)   | Up to date / Update available         |
| scrcpy                | e.g., `4.0`          | (fetched)                   | Up to date / Update available         |
| bundletool            | e.g., `1.17.2`       | (fetched)                   | Up to date / Update available         |

- **Check for Updates** button: queries all sources and updates the status columns.
- **Update** button (per row, active when update available): downloads and installs the update atomically.

#### 3.9.3 General Settings

| Setting              | Type                  | Default                       | Description                                              |
| -------------------- | --------------------- | ----------------------------- | -------------------------------------------------------- |
| Theme                | Dropdown              | System theme                  | System theme / Light theme / Dark theme                  |
| Screenshots folder   | Path picker           | `<app_data>/screenshots/`     | Folder where screenshots are saved                       |
| Logcat folder        | Path picker           | `<app_data>/logcat/`          | Folder where logcat exports are saved                    |
| ADB command timeout  | Number input (seconds)| 30 s                          | Timeout for individual ADB command execution             |
| Log level            | Dropdown              | Error                         | Debug / Info / Warning / Error                           |

All settings are saved immediately on change to `settings.json`.

---

## 4. Logging

### 4.1 Log Format

Each log entry:

```
LEVEL - YYYY-MM-DD HH:MM:SS.mmm TZ±HH:MM - message
```

Example:

```
ERROR - 2025-03-15 14:32:07.441 UTC+05:00 - ADB command failed: device not found
```

All log output is in English only.

### 4.2 Log Storage Policy

- **Location:** `<app_data>/logs/`
- **New log file per session:** each launch creates `adb_helper_<YYYY-MM-DD_HH-MM-SS>.log`
- **Max file size:** 5 MB per file. When the current file reaches 5 MB, a new file is created with an incrementing suffix (e.g., `adb_helper_2025-03-15_14-30-00_2.log`).
- **Max files per session:** 10. When a session would create an 11th file, the oldest file of the current session is deleted. This means early session logs may be lost in very verbose sessions — this is accepted behaviour.
- **Retention period:** log files older than 10 calendar days are deleted automatically on application startup.

### 4.3 Log Levels

| Level             | What is logged                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------- |
| Debug             | All ADB commands issued (with `-s` serial), raw output, internal state changes              |
| Info              | User actions, connection events, installation results                                       |
| Warning           | Non-fatal issues, fallbacks, deprecated operations                                          |
| Error (default)   | Failures, exceptions, ADB errors                                                            |

> **Note:** The default level is **Error**. All device information (serials, model names, IPs) is included in log output; the application is for private use and no PII scrubbing is applied. The only exception is `adb pair` PIN codes, which are always masked as `*****` in logs regardless of log level.

---

## 5. ADB Service Layer

All ADB interactions are routed through a single **ADB Service** component. **No module communicates with ADB directly.** The service exposes Qt signals so UI components can subscribe to events without polling.

### 5.1 CommandRunner

Handles one-shot, fire-and-collect ADB commands (info queries, install, buttons, etc.).

- Thread-pool based (default: 4 workers).
- Each command carries: device serial, command args, timeout (from Settings, default 30 s), priority (Normal / High).
- Commands targeting the active device use **High** priority; background polling uses **Normal**.
- Statuses: `queued` → `running` → `succeeded` / `failed` / `timed_out` / `cancelled`.
- Qt signals: `commandStarted(id)`, `commandFinished(id, result)`, `commandFailed(id, error)`.
- On timeout the subprocess is killed and status is set to `timed_out`.

### 5.2 ProcessManager

Handles long-lived ADB processes: terminal (`adb shell` PTY), scrcpy, logcat export.

- Each managed process has a unique ID, start time, and state (`starting` / `running` / `stopping` / `stopped`).
- Qt signals: `processStarted(id)`, `processStopped(id, exit_code)`, `processOutput(id, data)`.
- On application exit, all managed processes are terminated gracefully.

### 5.3 DeviceMonitor

Monitors the set of connected ADB devices.

- **Primary:** `adb track-devices` (persistent connection, server-push). Preferred because it has zero polling overhead.
- **Fallback:** `adb devices` polled every 3 seconds if `track-devices` fails to initialise.
- Qt signals: `deviceConnected(device)`, `deviceDisconnected(serial)`, `deviceStateChanged(device)`.
- **DeviceContext** object: `{ serial, model, manufacturer, sdk_version, abi, connection_type, status }`.
- Modules receive a `DeviceContext` via `on_device_changed(ctx)`. They must not query ADB for device properties directly.

### 5.4 Error Parsing

The ADB Service translates common ADB error strings into human-readable English messages. Examples:

| Raw ADB error                          | Human-readable message                                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `error: device not found`              | Device is not connected or ADB cannot detect it. Check the USB cable or Wi-Fi connection.               |
| `error: device unauthorized`           | USB debugging authorisation is pending. Unlock the device and tap Allow.                                |
| `INSTALL_FAILED_VERSION_DOWNGRADE`     | The installed version is newer than the one you are trying to install.                                  |
| `INSTALL_FAILED_ALREADY_EXISTS`        | This app is already installed. Use the `-r` flag to reinstall.                                          |

---

## 6. Platform-Specific Notes

### 6.1 Windows 11

- **ConPTY** is used for the terminal emulator (Windows 10 1903+ requirement; satisfied by Windows 11).
- **ADB server autostart:** `adb start-server` is called on application launch.
- **Administrator elevation:** UAC manifest embedded in the executable, or restart-as-admin prompt if elevation is needed mid-session.
- **System theme changes** are received in real time via `WM_SETTINGCHANGE` / `Windows.UI.ViewManagement.UISettings`.
- **Single-instance lock:** a named mutex + named pipe for window focus signal.
- **Terminal font:** Cascadia Code (available by default on Windows 11).

### 6.2 Linux (Ubuntu 22.04+)

- **PTY** via Python `pty` module for the terminal emulator.
- **ADB permissions:** if the ADB server fails to start due to USB permissions, the application shows: *"Run `sudo adb start-server` or add your user to the `plugdev` group and reconnect the device."*
- **Elevation:** `pkexec` or `sudo` prompt as appropriate.
- **System theme:** polled every 30 seconds via `darkdetect`. No real-time signal guaranteed across all desktop environments.
- **Single-instance lock:** a Unix domain socket at `/tmp/adb_helper_<uid>.sock`.
- **Terminal font:** JetBrains Mono (bundled in source tree under `assets/fonts/`).
- **Distribution:** source tree only (no snap, flatpak, or `.deb` package). This avoids USB sandbox restrictions imposed by containerised formats.

---

## 7. Error Handling — General Rules

- All ADB operations show **both** a human-readable explanation in English **AND** the raw technical error from ADB/bundletool output (collapsible or in a scrollable text area).
- Operations that modify device state (Delete, Disable, Enable, Reboot, Uninstall) always show a confirmation dialog before executing.
- Network/download operations show a progress indicator and handle failures gracefully with a retry option.
- If the active device becomes unavailable mid-operation (except Installer), the operation is cancelled, an error is shown, and the user is returned to Connections.
- In the Installer module, device disconnection marks that device's remaining operations as Failed and continues with other devices.

---

## 8. Future Extensibility

The following design principles must be followed to facilitate future module additions:

- Each module is implemented as a self-contained `QWidget` subclass implementing `IModule` with methods: `on_activate()`, `on_deactivate()`, `on_device_changed(ctx: DeviceContext)`, `on_device_disconnected()`.
- Modules are registered in a central **module registry**; adding a new module requires only creating the widget class and registering it — no changes to core navigation code.
- The sidebar navigation is data-driven (reads from the module registry).
- The ADB Service is a singleton accessible to all modules; no module communicates with ADB directly.
- All user-facing strings are defined as constants (i18n-ready structure, English only for now).

---

## 9. Out of Scope (Version 1.0)

The following are explicitly **not** implemented in version 1.0:

- Root-required operations (full app data backup, full system app uninstall, kernel-level access).
- Macro recording of GUI actions (Device Buttons clicks, etc.) — macros record Terminal commands only.
- Live/streaming logcat viewer.
- File manager (push/pull arbitrary files).
- Screen recording via ADB.
- macOS support.
- Multi-device macro playback.
- Android App Bundle (`.aab`) installation.
- App icon extraction in the Apps module.
- Automatic reconnection of paired Wi-Fi devices on startup.

---

## Revision History

| Version | Date       | Changes                                                                                                                                                                                               |
| ------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0.0   | 2026-05-19 | All nine modules fully implemented. DB schema v2 (`connect_port` on paired_devices). §3.1.4 corrected: no auto-connect after pairing. §3.1.5 updated: Paired Devices table has Connection Port column. |
