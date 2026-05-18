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
