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
LABEL_CONNECTED_DEVICES: Final = "Connected Devices"
LABEL_PAIRED_DEVICES: Final = "Paired Devices"
LABEL_WIFI_CLASSIC: Final = "Wi-Fi Connection (legacy)"
LABEL_WIFI_PAIRING: Final = "Wi-Fi Pairing (Android 11+)"

COL_SERIAL: Final = "Serial"
COL_IP_ADDRESS: Final = "IP Address"
COL_MODEL: Final = "Model"
COL_STATUS: Final = "Status"
COL_ALIAS: Final = "Alias"
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
MSG_PAIR_OK: Final = "Pairing succeeded. Connecting to {ip}…"
MSG_PAIR_FAIL: Final = "Pairing failed: {error}"
MSG_DISCONNECT_OK: Final = "Disconnected {serial}."
MSG_DISCONNECT_FAIL: Final = "Disconnect failed: {error}"
MSG_INVALID_IP: Final = "Enter a valid IP address."
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

# --- Scrcpy module (Spec §3.4) -------------------------------------------
SCRCPY_TITLE: Final = "scrcpy"
SCRCPY_LABEL_BITRATE: Final = "Video bitrate:"
SCRCPY_LABEL_MAX_RES: Final = "Max resolution:"
SCRCPY_LABEL_ORIENTATION: Final = "Orientation lock:"
SCRCPY_LABEL_STAY_AWAKE: Final = "Stay awake"
SCRCPY_LABEL_SHOW_TOUCHES: Final = "Show touches"
SCRCPY_LABEL_TURN_SCREEN_OFF: Final = "Turn screen off"
SCRCPY_LABEL_LAUNCH_OPTIONS: Final = "Launch Options"
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

# --- Device Info module (Spec §3.6) --------------------------------------
DI_BTN_REFRESH: Final = "Refresh"
DI_BTN_EXPORT: Final = "Export to TXT"
DI_TITLE_EXPORT: Final = "Export Device Info"
DI_FILTER_TXT: Final = "Text Files (*.txt)"

DI_SEC_DEVICE: Final = "Device"
DI_SEC_SYSTEM: Final = "System"
DI_SEC_CPU: Final = "CPU"
DI_SEC_GPU: Final = "GPU"
DI_SEC_MEMORY: Final = "Memory"
DI_SEC_STORAGE: Final = "Storage"
DI_SEC_DISPLAY: Final = "Display"
DI_SEC_BATTERY: Final = "Battery"
DI_SEC_NETWORK: Final = "Network"
DI_SEC_LOCALE: Final = "Locale & Time"

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
    "IMEI requires privileged permissions on Android 10+. "
    "This is expected behaviour."
)

# --- Apps module (Spec §3.7) ---------------------------------------------
APPS_BTN_REFRESH: Final = "Refresh"
APPS_BTN_DELETE: Final = "Delete"
APPS_BTN_DISABLE: Final = "Disable"
APPS_BTN_ENABLE: Final = "Enable"
APPS_BTN_EXPORT: Final = "Export to CSV"
APPS_BTN_BACKUP_DELETE: Final = "Back Up and Delete"
APPS_BTN_DELETE_NO_BACKUP: Final = "Delete Without Backup"
APPS_SEARCH_HINT: Final = "Search by name or package…"
APPS_CHK_SHOW_SYSTEM: Final = "Show system apps"
APPS_CHK_SHOW_DISABLED: Final = "Show disabled apps"
APPS_COL_NAME: Final = "App Name"
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
