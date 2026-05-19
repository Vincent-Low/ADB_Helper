"""Centralised user-facing strings.

CLAUDE.md invariant 3: no string literals in widgets. Add new entries here
and reference them by name. v1.0 is English-only (Spec §2.3) but this
structure keeps i18n possible later.
"""
from __future__ import annotations

from typing import Final

APP_NAME: Final = "ADB_Helper"

# Sidebar labels — sidebar order is defined in the module registry,
# not by the constant order here.
LABEL_CONNECTIONS: Final = "Connections"
LABEL_TERMINAL: Final = "Terminal"
LABEL_INSTALLER: Final = "Installer"
LABEL_SCRCPY: Final = "Scrcpy"
LABEL_DEVICE_BUTTONS: Final = "Device Buttons"
LABEL_DEVICE_INFO: Final = "Device Info"
LABEL_APPS: Final = "Apps"
LABEL_LOGCAT: Final = "Logcat"
LABEL_SETTINGS: Final = "Settings"

# Device status pills (Spec §3.1 / §5.4).
STATUS_ONLINE: Final = "Online"
STATUS_OFFLINE: Final = "Offline"
STATUS_UNAUTHORIZED: Final = "Unauthorized"
STATUS_CONNECTING: Final = "Connecting"
STATUS_DISCONNECTED: Final = "Disconnected"

# Error translations (Spec §5.4 error parser).
ERROR_DEVICE_NOT_FOUND: Final = (
    "Device is not connected or ADB cannot detect it. "
    "Check the USB cable or Wi-Fi connection."
)
ERROR_DEVICE_UNAUTHORIZED: Final = (
    "USB debugging authorisation is pending. Unlock the device and tap Allow."
)
ERROR_INSTALL_VERSION_DOWNGRADE: Final = (
    "The installed version is newer than the one you are trying to install."
)
ERROR_INSTALL_ALREADY_EXISTS: Final = (
    "This app is already installed. Use the reinstall option to overwrite."
)
ERROR_ADB_TIMEOUT: Final = "ADB command timed out."

# Status / informational messages. ``.format(...)`` is used at call site.
MSG_DEVICE_CONNECTED: Final = "Device connected: {model} ({serial})."
MSG_DEVICE_DISCONNECTED: Final = "Device {model} ({serial}) has been disconnected."
MSG_SCREENSHOT_SAVED: Final = "Screenshot saved to: {path}"
MSG_LOGCAT_SAVED: Final = "Logcat saved to: {path}"
MSG_APK_BACKED_UP: Final = "APK backed up to: {path}"

# Confirmation prompts.
CONFIRM_REBOOT: Final = "Are you sure you want to reboot the device?"
CONFIRM_REBOOT_BOOTLOADER: Final = (
    "Are you sure you want to reboot the device into bootloader mode?"
)
CONFIRM_REBOOT_RECOVERY: Final = (
    "Are you sure you want to reboot the device into recovery mode?"
)
CONFIRM_DISABLE: Final = "Are you sure you want to disable the following apps?"
CONFIRM_ENABLE: Final = "Are you sure you want to enable the following apps?"
CONFIRM_DELETE: Final = "Are you sure you want to delete the selected items?"
CONFIRM_UNINSTALL: Final = "Are you sure you want to uninstall the following apps?"

# Help / contextual hints.
UNAUTHORIZED_HELP: Final = (
    "Unlock your device, go to Developer Options, and tap Allow on the USB "
    "debugging authorization prompt. Then reconnect the device."
)
LINUX_ADB_PERMISSION_HINT: Final = (
    "Run `sudo adb start-server` or add your user to the `plugdev` group "
    "and reconnect the device."
)
INSTALL_BACKUP_PROMPT: Final = (
    "Do you want to back up the selected apps before deleting? Only APK "
    "files will be backed up. App data cannot be backed up without root "
    "access."
)
IMEI_UNAVAILABLE_NOTE: Final = (
    "IMEI retrieval via `service call iphonesubinfo` requires privileged "
    "permissions on Android 10+. The field will show N/A on most modern "
    "devices. This is expected behaviour."
)

# Redaction placeholder for `adb pair` PIN codes (CLAUDE.md §7).
PIN_REDACTED: Final = "*****"

# --- Connections module (Spec §3.1) ---------------------------------------
LABEL_CONNECTED_DEVICES: Final = "CONNECTED DEVICES"
LABEL_PAIRED_DEVICES: Final = "PAIRED DEVICES"
LABEL_WIFI_CLASSIC: Final = "WI-FI CONNECTION (LEGACY)"
LABEL_WIFI_PAIRING: Final = "WI-FI PAIRING (ANDROID 11+)"

COL_SERIAL: Final = "Serial"
COL_IP_ADDRESS: Final = "IP Address"
COL_MODEL: Final = "Model"
COL_STATUS: Final = "Status"
COL_ALIAS: Final = "Alias"
COL_CONNECTION_PORT: Final = "Connection Port"
COL_LAST_CONNECTED: Final = "Last Connected"

FIELD_IP_ADDRESS: Final = "IP Address:"
FIELD_PORT: Final = "Port:"
FIELD_PAIRING_PORT: Final = "Pairing Port:"
FIELD_PIN: Final = "PIN:"

HINT_IP_ADDRESS: Final = "192.168.1.10"
HINT_PIN: Final = "6-digit code"

BTN_CONNECT: Final = "Connect"
BTN_DISCONNECT: Final = "Disconnect"
BTN_PAIR: Final = "Pair"
BTN_FORGET: Final = "Forget"

TITLE_UNAUTHORIZED_DIALOG: Final = "Unauthorized Device"
ICON_UNAUTHORIZED: Final = "ⓘ"

MSG_CONNECTING: Final = "Connecting…"
MSG_PAIRING: Final = "Pairing…"
MSG_CONNECT_OK: Final = "Connected to {target}."
MSG_CONNECT_FAIL: Final = "Connect failed: {error}"
MSG_PAIR_OK: Final = "Paired with {ip}. Enter connection port in the table below."
MSG_PAIR_FAIL: Final = "Pairing failed: {error}"
MSG_DISCONNECT_OK: Final = "Disconnected {serial}."
MSG_DISCONNECT_FAIL: Final = "Disconnect failed: {error}"
MSG_INVALID_IP: Final = "Enter a valid IP address."
MSG_INVALID_PORT: Final = "Enter a valid port number (1–65535)."
MSG_INVALID_PIN: Final = "Enter the 6-digit pairing code."
ALIAS_DEFAULT: Final = "Wi-Fi Device"

# --- Terminal module (Spec §3.2) ------------------------------------------
TERM_BTN_CLEAR: Final = "Clear"
TERM_BTN_HISTORY: Final = "History"
TERM_BTN_RECORD: Final = "Record Macro"
TERM_BTN_STOP_RECORDING: Final = "Stop Recording"
TERM_BTN_PLAY: Final = "Play"
TERM_BTN_STOP_PLAYBACK: Final = "Stop"
TERM_LABEL_MACROS: Final = "Macros"
TERM_LABEL_HISTORY_TITLE: Final = "Command History"
TERM_LABEL_SAVE_MACRO_TITLE: Final = "Save Macro"
TERM_LABEL_RENAME_MACRO_TITLE: Final = "Rename Macro"
TERM_LABEL_EXPORT_MACRO_TITLE: Final = "Export Macro"
TERM_LABEL_DELETE_MACRO_TITLE: Final = "Delete Macro"
TERM_FIELD_NAME: Final = "Name:"
TERM_BTN_SAVE: Final = "Save"
TERM_BTN_CANCEL: Final = "Cancel"
TERM_MENU_RENAME: Final = "Rename"
TERM_MENU_DELETE: Final = "Delete"
TERM_MENU_EXPORT: Final = "Export"
TERM_FILTER_JSON: Final = "Macro Files (*.json)"
TERM_PROMPT_TEMPLATE: Final = "{serial}:/ $ "
TERM_MSG_NO_DEVICE: Final = (
    "No active device. Connect a device in the Connections module."
)
TERM_MSG_DEVICE_DISCONNECTED: Final = "Device disconnected."
TERM_MSG_SESSION_STARTING: Final = "Starting adb shell on {serial}…"
TERM_MSG_SESSION_EXITED: Final = "Shell session exited (rc={rc})."
TERM_MSG_RUNNING: Final = "Running command {n} of {m}: {cmd}"
TERM_MSG_PLAYBACK_DONE: Final = "Macro complete."
TERM_MSG_PLAYBACK_STOPPED: Final = "Macro stopped."
TERM_MSG_RECORDING: Final = "Recording macro…"
TERM_MSG_RECORDING_DISCARDED: Final = "Recording discarded."
TERM_MSG_RECORDING_EMPTY: Final = "No commands were recorded."
TERM_MSG_NAME_REQUIRED: Final = "Macro name cannot be empty."
TERM_MSG_MACRO_SAVED: Final = "Macro '{name}' saved ({count} commands)."
TERM_MSG_MACRO_EXPORTED: Final = "Macro exported to {path}."
TERM_CONFIRM_DELETE_MACRO: Final = "Delete macro '{name}'? This cannot be undone."

# --- Device Buttons module (Spec §3.5) -----------------------------------
DB_LABEL_HOME: Final = "Home"
DB_LABEL_BACK: Final = "Back"
DB_LABEL_RECENT: Final = "Recent Apps"
DB_LABEL_VOLUME_UP: Final = "Volume +"
DB_LABEL_VOLUME_DOWN: Final = "Volume −"
DB_LABEL_MUTE: Final = "Mute"
DB_LABEL_CAMERA: Final = "Camera"
DB_LABEL_POWER: Final = "Power"
DB_LABEL_REBOOT: Final = "Reboot"
DB_LABEL_SCREENSHOT: Final = "Screenshot"
DB_LABEL_SCREEN_ROTATE: Final = "Screen Rotate"
DB_TITLE_REBOOT_CONFIRM: Final = "Confirm Reboot"
DB_TITLE_SCREENSHOT: Final = "Screenshot"
DB_BTN_REBOOT: Final = "Reboot"
DB_BTN_OPEN_FOLDER: Final = "Open Folder"
DB_MSG_NO_DEVICE: Final = "No active device. Select a device in Connections."
DB_MSG_SCREENSHOT_FAILED: Final = "Screenshot failed: {error}"
DB_MSG_ROTATION_TOGGLED: Final = "Auto-rotate set to {value}."
DB_MSG_ROTATION_FAILED: Final = "Failed to toggle auto-rotate: {error}"
DB_RECENT_TITLE: Final = "RECENT ACTIONS"
DB_RECENT_COL_TIME: Final = "Time"
DB_RECENT_COL_ACTION: Final = "Action"
DB_RECENT_COL_DEVICE: Final = "Device"
DB_RECENT_COL_RESULT: Final = "Result"
DB_RECENT_RESULT_OK: Final = "OK"
DB_RECENT_RESULT_FAIL: Final = "Failed"
DB_RECENT_EMPTY: Final = "No actions yet."

# --- Scrcpy module (Spec §3.4) -------------------------------------------
SCRCPY_TITLE: Final = "scrcpy"
SCRCPY_LABEL_BITRATE: Final = "Video bitrate:"
SCRCPY_LABEL_MAX_RES: Final = "Max resolution:"
SCRCPY_LABEL_ORIENTATION: Final = "Orientation lock:"
SCRCPY_LABEL_STAY_AWAKE: Final = "Stay awake"
SCRCPY_LABEL_SHOW_TOUCHES: Final = "Show touches"
SCRCPY_LABEL_TURN_SCREEN_OFF: Final = "Turn screen off"
SCRCPY_LABEL_LAUNCH_OPTIONS: Final = "LAUNCH OPTIONS"
SCRCPY_LABEL_NO_LIMIT: Final = "No limit"
SCRCPY_LABEL_AUTO: Final = "Auto"
SCRCPY_BTN_LAUNCH: Final = "Launch"
SCRCPY_BTN_RETRY: Final = "Retry"
SCRCPY_BTN_DOWNLOAD: Final = "Download"
SCRCPY_MSG_NO_DEVICE: Final = "No active device. Select a device in Connections."
SCRCPY_MSG_CHECKING: Final = "Checking scrcpy binary…"
SCRCPY_MSG_DOWNLOADING: Final = "Downloading scrcpy {version}…"
SCRCPY_MSG_READY: Final = "scrcpy {version} ready."
SCRCPY_MSG_LAUNCHING: Final = "Launching scrcpy on {serial}…"
SCRCPY_MSG_LAUNCHED: Final = "scrcpy launched."
SCRCPY_MSG_LAUNCH_FAILED: Final = "Failed to launch scrcpy."
SCRCPY_MSG_DOWNLOAD_FAILED: Final = (
    "Failed to download scrcpy automatically. Download manually from "
    "https://github.com/Genymobile/scrcpy/releases/latest, extract into "
    "{path}, and click Retry."
)
SCRCPY_MSG_NO_ASSET: Final = (
    "No scrcpy release asset found for this platform. Download manually from "
    "https://github.com/Genymobile/scrcpy/releases/latest and extract into {path}."
)
SCRCPY_BITRATE_2: Final = "2 Mbps"
SCRCPY_BITRATE_4: Final = "4 Mbps"
SCRCPY_BITRATE_8: Final = "8 Mbps"
SCRCPY_BITRATE_16: Final = "16 Mbps"
SCRCPY_BITRATE_32: Final = "32 Mbps"
SCRCPY_RES_NONE: Final = "No limit"
SCRCPY_RES_1920: Final = "1920"
SCRCPY_RES_1280: Final = "1280"
SCRCPY_RES_1024: Final = "1024"
SCRCPY_RES_800: Final = "800"
SCRCPY_ORIENT_AUTO: Final = "Auto"
SCRCPY_ORIENT_0: Final = "0°"
SCRCPY_ORIENT_90: Final = "90°"
SCRCPY_ORIENT_180: Final = "180°"
SCRCPY_ORIENT_270: Final = "270°"
SCRCPY_RECENT_TITLE: Final = "RECENT LAUNCHES"
SCRCPY_RECENT_COL_TIME: Final = "Time"
SCRCPY_RECENT_COL_DEVICE: Final = "Device"
SCRCPY_RECENT_COL_FLAGS: Final = "Flags"
SCRCPY_RECENT_COL_STATUS: Final = "Status"
SCRCPY_RECENT_STATUS_RUNNING: Final = "Running"
SCRCPY_RECENT_STATUS_OK: Final = "Launched"
SCRCPY_RECENT_STATUS_FAIL: Final = "Failed"
SCRCPY_RECENT_EMPTY: Final = "No launches yet."

# --- Device Info module (Spec §3.6) --------------------------------------
DI_BTN_REFRESH: Final = "Refresh"
DI_BTN_EXPORT: Final = "Export to TXT"
DI_TITLE_EXPORT: Final = "Export Device Info"
DI_FILTER_TXT: Final = "Text Files (*.txt)"

DI_SEC_DEVICE: Final = "DEVICE"
DI_SEC_SYSTEM: Final = "SYSTEM"
DI_SEC_CPU: Final = "CPU"
DI_SEC_GPU: Final = "GPU"
DI_SEC_MEMORY: Final = "MEMORY"
DI_SEC_STORAGE: Final = "STORAGE"
DI_SEC_DISPLAY: Final = "DISPLAY"
DI_SEC_BATTERY: Final = "BATTERY"
DI_SEC_NETWORK: Final = "NETWORK"
DI_SEC_LOCALE: Final = "LOCALE & TIME"

DI_FIELD_MANUFACTURER: Final = "Manufacturer"
DI_FIELD_MODEL: Final = "Model"
DI_FIELD_CODENAME: Final = "Device codename"
DI_FIELD_BRAND: Final = "Brand"
DI_FIELD_SERIAL: Final = "Serial number"

DI_FIELD_ANDROID_VERSION: Final = "Android version"
DI_FIELD_API_LEVEL: Final = "API level"
DI_FIELD_SECURITY_PATCH: Final = "Security patch level"
DI_FIELD_BUILD_NUMBER: Final = "Build number"
DI_FIELD_BUILD_FINGERPRINT: Final = "Build fingerprint"
DI_FIELD_BUILD_TYPE: Final = "Build type"
DI_FIELD_BUILD_DATE: Final = "Build date"
DI_FIELD_BOOTLOADER: Final = "Bootloader version"
DI_FIELD_BASEBAND: Final = "Baseband / Radio"

DI_FIELD_CPU_HARDWARE: Final = "CPU hardware name"
DI_FIELD_CPU_MODEL: Final = "CPU model name"
DI_FIELD_CPU_ARCH: Final = "CPU architecture"
DI_FIELD_CPU_CORES: Final = "Number of cores"
DI_FIELD_CPU_GOVERNOR: Final = "CPU governor"
DI_FIELD_CPU_FREQ: Final = "Min / Max CPU frequency"

DI_FIELD_GPU_VENDOR: Final = "GPU vendor"
DI_FIELD_GPU_RENDERER: Final = "GPU renderer"
DI_FIELD_OPENGL_VERSION: Final = "OpenGL ES version"

DI_FIELD_RAM_TOTAL: Final = "Total RAM"
DI_FIELD_RAM_AVAILABLE: Final = "Available RAM"
DI_FIELD_SWAP_TOTAL: Final = "Total swap"

DI_FIELD_STORAGE_TOTAL: Final = "Total internal storage"
DI_FIELD_STORAGE_AVAILABLE: Final = "Available internal storage"

DI_FIELD_RESOLUTION: Final = "Resolution (px)"
DI_FIELD_DENSITY: Final = "Density (dpi)"
DI_FIELD_REFRESH_RATE: Final = "Refresh rate"

DI_FIELD_BATTERY_LEVEL: Final = "Level (%)"
DI_FIELD_BATTERY_STATUS: Final = "Status"
DI_FIELD_BATTERY_HEALTH: Final = "Health"
DI_FIELD_BATTERY_TEMP: Final = "Temperature (°C)"
DI_FIELD_BATTERY_TECH: Final = "Technology"
DI_FIELD_BATTERY_VOLTAGE: Final = "Voltage (mV)"

DI_FIELD_WIFI_IP: Final = "Wi-Fi IP address"
DI_FIELD_WIFI_MAC: Final = "Wi-Fi MAC address"
DI_FIELD_BT_MAC: Final = "Bluetooth MAC"
DI_FIELD_IMEI: Final = "IMEI (SIM 1 / SIM 2)"

DI_FIELD_LANGUAGE: Final = "Language"
DI_FIELD_TIMEZONE: Final = "Timezone"

DI_TOOLTIP_IMEI: Final = (
    "IMEI is not accessible without root on Android 10+. "
    "This is expected behaviour."
)
DI_VALUE_IMEI_NA: Final = "N/A (requires privileged access on Android 10+)"

# --- Apps module (Spec §3.7) ---------------------------------------------
APPS_BTN_REFRESH: Final = "Refresh"
APPS_BTN_DELETE: Final = "Delete"
APPS_BTN_DISABLE: Final = "Disable"
APPS_BTN_ENABLE: Final = "Enable"
APPS_BTN_EXPORT: Final = "Export to CSV"
APPS_BTN_BACKUP_DELETE: Final = "Back Up and Delete"
APPS_BTN_DELETE_NO_BACKUP: Final = "Delete Without Backup"
APPS_SEARCH_HINT: Final = "Search by package…"
APPS_CHK_SHOW_SYSTEM: Final = "Show system apps"
APPS_CHK_SHOW_DISABLED: Final = "Show disabled apps"
APPS_COL_PACKAGE: Final = "Package Name"
APPS_COL_STATUS: Final = "Status"
APPS_COL_TYPE: Final = "Type"
APPS_STATUS_ACTIVE: Final = "Active"
APPS_STATUS_DISABLED: Final = "Disabled"
APPS_TYPE_USER: Final = "User"
APPS_TYPE_SYSTEM: Final = "System"
APPS_LABEL_RAM: Final = "RAM"
APPS_LABEL_STORAGE: Final = "Storage"
APPS_LABEL_USED_TOTAL: Final = "Used: {used} MB / Total: {total} MB"
APPS_MSG_NO_DEVICE: Final = "No active device. Select a device in Connections."
APPS_MSG_LOADING: Final = "Loading apps…"
APPS_MSG_LOADED: Final = "{count} apps loaded."
APPS_MSG_NOTHING_SELECTED: Final = "No apps selected."
APPS_MSG_NO_USER_APPS_SELECTED: Final = "Selection contains no user apps."
APPS_MSG_NO_ACTIVE_SELECTED: Final = "Selection contains no active apps."
APPS_MSG_NO_DISABLED_SELECTED: Final = "Selection contains no disabled apps."
APPS_MSG_BACKUP_OK: Final = "APK backed up: {pkg}"
APPS_MSG_BACKUP_FAILED: Final = "Backup failed for {pkg}: {error}"
APPS_MSG_UNINSTALL_FAILED: Final = "Uninstall failed for {pkg}: {error}"
APPS_MSG_DISABLE_FAILED: Final = "Disable failed for {pkg}: {error}"
APPS_MSG_ENABLE_FAILED: Final = "Enable failed for {pkg}: {error}"
APPS_MSG_CSV_EXPORTED: Final = "App list exported to {path}."
APPS_MSG_OP_DONE: Final = "Done. {ok} succeeded, {fail} failed."
APPS_TOOLTIP_SYSTEM_DELETE: Final = "System apps cannot be uninstalled — only disabled."
APPS_TITLE_DELETE: Final = "Delete Apps"
APPS_TITLE_DISABLE: Final = "Disable Apps"
APPS_TITLE_ENABLE: Final = "Enable Apps"
APPS_TITLE_EXPORT: Final = "Export App List"
APPS_FILTER_CSV: Final = "CSV Files (*.csv)"

# --- Logcat module (Spec §3.8) -------------------------------------------
LOG_BTN_EXPORT: Final = "Export Logcat"
LOG_TITLE_EXPORT: Final = "Logcat"
LOG_MSG_EXPORTING: Final = "Exporting…"
LOG_MSG_NO_DEVICE: Final = "No active device. Select a device in Connections."
LOG_TITLE_ERROR: Final = "Export Failed"
LOG_MSG_ERROR: Final = "Failed to capture logcat from the device."
LOG_BTN_SHOW_DETAILS: Final = "Show Details"
LOG_BTN_HIDE_DETAILS: Final = "Hide Details"
LOG_BTN_CLOSE: Final = "Close"
LOG_HINT_DESC: Final = (
    "Capture the current device log (one-shot adb logcat -d) and save it "
    "to the configured logcat folder."
)
LOG_TITLE_BUFFER: Final = "EXPORT LOGCAT BUFFER"
LOG_TITLE_CONFIG: Final = "CONFIGURATION"
LOG_TITLE_RECENT: Final = "RECENT EXPORTS"
LOG_LABEL_SAVE_FOLDER: Final = "Save folder:"
LOG_LABEL_FILENAME: Final = "Filename:"
LOG_LABEL_MODE: Final = "Mode:"
LOG_LABEL_TIMEZONE: Final = "Timezone:"
LOG_VAL_MODE: Final = "Single-shot (-d flag)"
LOG_VAL_FILENAME_PATTERN: Final = "logcat_<date>_<time>_GMT±N.txt"
LOG_BTN_BROWSE: Final = "Browse…"
LOG_BTN_OPEN_FILE: Final = "Open"
LOG_BTN_REMOVE: Final = "Remove"
LOG_FILE_COUNT: Final = "{n} files"
LOG_RECENT_EMPTY: Final = "No exports yet."

# --- Installer module (Spec §3.3) ----------------------------------------
INSTALLER_LABEL_FILES: Final = "FILES TO INSTALL"
INSTALLER_LABEL_DEVICES: Final = "TARGET DEVICES"
INSTALLER_LABEL_INSTALLATION: Final = "INSTALLATION"
INSTALLER_LABEL_RESULTS: Final = "RESULTS"
INSTALLER_BTN_ADD_FILES: Final = "Add Files"
INSTALLER_BTN_REMOVE: Final = "Remove"
INSTALLER_BTN_CLEAR: Final = "Clear"
INSTALLER_BTN_INSTALL: Final = "Install"
INSTALLER_BTN_CANCEL: Final = "Cancel"
INSTALLER_BTN_SHOW_DETAILS: Final = "Show Details"
INSTALLER_BTN_HIDE_DETAILS: Final = "Hide Details"
INSTALLER_BTN_CLOSE: Final = "Close"
INSTALLER_FILTER_PACKAGES: Final = (
    "Android Packages (*.apk *.apks *.xapk *.apkm);;All Files (*)"
)
INSTALLER_TITLE_ADD: Final = "Select files to install"
INSTALLER_TITLE_SUMMARY: Final = "Installation Summary"
INSTALLER_COL_FILE: Final = "File"
INSTALLER_COL_TYPE: Final = "Type"
INSTALLER_COL_SIZE: Final = "Size"
INSTALLER_COL_SERIAL: Final = "Serial"
INSTALLER_COL_MODEL: Final = "Model"
INSTALLER_COL_RESULT: Final = "Result"
INSTALLER_RESULT_OK: Final = "Success"
INSTALLER_RESULT_FAIL: Final = "Failed"
INSTALLER_RESULT_SKIPPED: Final = "Skipped (device disconnected)"
INSTALLER_RESULT_PENDING: Final = "Pending"
INSTALLER_RESULT_RUNNING: Final = "Installing…"
INSTALLER_MSG_NO_FILES: Final = "Add at least one file to install."
INSTALLER_MSG_NO_DEVICES: Final = "Select at least one device."
INSTALLER_MSG_NO_CONNECTED: Final = "No connected devices."
INSTALLER_MSG_RUNNING: Final = "Installing {file} on {device}…"
INSTALLER_MSG_DONE: Final = "Done. {ok} succeeded, {fail} failed."
INSTALLER_MSG_AAB_UNSUPPORTED: Final = (
    "Android App Bundle (.aab) is not supported — requires the developer "
    "signing key."
)
INSTALLER_MSG_BUNDLETOOL_MISSING: Final = (
    "bundletool.jar is not installed. Open Settings → Installed "
    "Dependencies and download bundletool."
)
INSTALLER_MSG_JRE_MISSING: Final = (
    "Java runtime not found on PATH. Install JRE 17 to install .apks files."
)
INSTALLER_MSG_UNSUPPORTED_FORMAT: Final = "Unsupported file format: {ext}"

# --- Status bar ------------------------------------------------------------
STATUS_NO_DEVICE: Final = "No device selected"

# --- Settings module (Spec §3.9) -------------------------------------------
APP_VERSION: Final = "1.0.0"
SETT_SEC_ABOUT: Final = "ABOUT"
SETT_SEC_DEPS: Final = "INSTALLED DEPENDENCIES"
SETT_SEC_GENERAL: Final = "GENERAL SETTINGS"
SETT_BTN_CHECK_UPDATES: Final = "Check for Updates"
SETT_BTN_UPDATE: Final = "Update"
SETT_BTN_DOWNLOAD: Final = "Download"
SETT_COL_COMPONENT: Final = "Component"
SETT_COL_INSTALLED: Final = "Installed"
SETT_COL_LATEST: Final = "Latest"
SETT_COL_STATUS: Final = "Status"
SETT_COL_ACTION: Final = "Action"
SETT_DEP_ADB: Final = "ADB (platform-tools)"
SETT_DEP_SCRCPY: Final = "scrcpy"
SETT_DEP_BUNDLETOOL: Final = "bundletool"
SETT_STATUS_UP_TO_DATE: Final = "Up to date"
SETT_STATUS_UPDATE_AVAILABLE: Final = "Update available"
SETT_STATUS_NOT_INSTALLED: Final = "Not installed"
SETT_STATUS_CHECKING: Final = "Checking…"
SETT_STATUS_UNKNOWN: Final = "Unknown"
SETT_LABEL_THEME: Final = "Theme:"
SETT_THEME_SYSTEM: Final = "System"
SETT_THEME_LIGHT: Final = "Light"
SETT_THEME_DARK: Final = "Dark"
SETT_LABEL_SCREENSHOTS_FOLDER: Final = "Screenshots folder:"
SETT_LABEL_LOGCAT_FOLDER: Final = "Logcat folder:"
SETT_LABEL_ADB_TIMEOUT: Final = "ADB command timeout (s):"
SETT_LABEL_LOG_LEVEL: Final = "Log level:"
SETT_LOG_DEBUG: Final = "Debug"
SETT_LOG_INFO: Final = "Info"
SETT_LOG_WARNING: Final = "Warning"
SETT_LOG_ERROR: Final = "Error"
SETT_BTN_BROWSE: Final = "Browse"
SETT_TITLE_BROWSE_SCREENSHOTS: Final = "Select Screenshots Folder"
SETT_TITLE_BROWSE_LOGCAT: Final = "Select Logcat Folder"
SETT_MSG_UPDATING: Final = "Updating {component}…"
SETT_MSG_UPDATE_DONE: Final = "Updated {component} to {version}."
SETT_MSG_UPDATE_FAILED: Final = "Update failed for {component}."
SETT_MSG_CHECKING: Final = "Checking for updates…"
SETT_MSG_CHECK_DONE: Final = "Update check complete."
