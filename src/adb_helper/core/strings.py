"""Centralised user-facing strings.

CLAUDE.md invariant 3: no string literals in widgets. Add new entries here and
reference them by name. v1.0 is English-only (Spec §2.3) but this structure
keeps i18n possible later.
"""
from __future__ import annotations

from typing import Final

APP_NAME: Final = "ADB_Helper"

SIDEBAR_CONNECTIONS: Final = "Connections"
SIDEBAR_TERMINAL: Final = "Terminal"
SIDEBAR_INSTALLER: Final = "Installer"
SIDEBAR_SCRCPY: Final = "Scrcpy"
SIDEBAR_DEVICE_BUTTONS: Final = "Device Buttons"
SIDEBAR_DEVICE_INFO: Final = "Device Info"
SIDEBAR_APPS: Final = "Apps"
SIDEBAR_LOGCAT: Final = "Logcat"
SIDEBAR_SETTINGS: Final = "Settings"

UNAUTHORIZED_HELP: Final = (
    "Unlock your device, go to Developer Options, and tap Allow on the USB "
    "debugging authorization prompt. Then reconnect the device."
)

DEVICE_DISCONNECTED_TEMPLATE: Final = (
    "Device {model} ({serial}) has been disconnected."
)

REBOOT_CONFIRM: Final = "Are you sure you want to reboot the device?"

SCREENSHOT_SAVED_TEMPLATE: Final = "Screenshot saved to: {path}"
LOGCAT_SAVED_TEMPLATE: Final = "Logcat saved to: {path}"

INSTALL_BACKUP_PROMPT: Final = (
    "Do you want to back up the selected apps before deleting? "
    "Only APK files will be backed up. App data cannot be backed up without "
    "root access."
)

DISABLE_CONFIRM: Final = "Are you sure you want to disable the following apps?"
ENABLE_CONFIRM: Final = "Are you sure you want to enable the following apps?"

LINUX_ADB_PERMISSION_HINT: Final = (
    "Run `sudo adb start-server` or add your user to the `plugdev` group and "
    "reconnect the device."
)

ERR_DEVICE_NOT_FOUND: Final = (
    "Device is not connected or ADB cannot detect it. Check the USB cable or "
    "Wi-Fi connection."
)
ERR_DEVICE_UNAUTHORIZED: Final = (
    "USB debugging authorisation is pending. Unlock the device and tap Allow."
)
ERR_INSTALL_VERSION_DOWNGRADE: Final = (
    "The installed version is newer than the one you are trying to install."
)
ERR_INSTALL_ALREADY_EXISTS: Final = (
    "This app is already installed. Use the `-r` flag to reinstall."
)

IMEI_UNAVAILABLE_NOTE: Final = (
    "IMEI retrieval via `service call iphonesubinfo` requires privileged "
    "permissions on Android 10+. The field will show N/A on most modern "
    "devices. This is expected behaviour."
)

PIN_REDACTED: Final = "*****"
