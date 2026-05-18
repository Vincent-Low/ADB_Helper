"""ADB error string translator.

Spec §5.4 / §7. Translates known raw ADB/bundletool error strings to English
user-facing messages. Raw output is always surfaced alongside the translation.
"""
from __future__ import annotations

from typing import Tuple

_FALLBACK_MESSAGE = "An unexpected ADB error occurred."

# Order matters: more specific patterns first. Match is case-insensitive
# substring on the raw output.
_RULES: tuple[tuple[str, str], ...] = (
    (
        "error: device not found",
        "Device is not connected or ADB cannot detect it. "
        "Check the USB cable or Wi-Fi connection.",
    ),
    (
        "error: device unauthorized",
        "USB debugging authorisation is pending. "
        "Unlock the device and tap Allow.",
    ),
    (
        "device unauthorized",
        "USB debugging authorisation is pending. "
        "Unlock the device and tap Allow.",
    ),
    (
        "more than one device/emulator",
        "More than one device or emulator is connected. "
        "Select a specific device before retrying.",
    ),
    (
        "more than one device",
        "More than one device or emulator is connected. "
        "Select a specific device before retrying.",
    ),
    (
        "failed to read response",
        "ADB server lost contact with the device. "
        "Reconnect the device and retry.",
    ),
    (
        "INSTALL_FAILED_VERSION_DOWNGRADE",
        "The installed version is newer than the one you are trying to install.",
    ),
    (
        "INSTALL_FAILED_ALREADY_EXISTS",
        "This app is already installed. Use the reinstall option to overwrite.",
    ),
    (
        "INSTALL_FAILED_INSUFFICIENT_STORAGE",
        "Not enough storage on the device to install this app.",
    ),
    (
        "INSTALL_FAILED_INVALID_APK",
        "The APK file is invalid or corrupted.",
    ),
    (
        "INSTALL_PARSE_FAILED_NO_CERTIFICATES",
        "The APK is not signed. Signed APKs are required for installation.",
    ),
)


def parse(raw: str) -> Tuple[str, str]:
    """Translate raw ADB/bundletool output.

    Returns ``(human_message, raw_output)``. ``raw_output`` is the original
    string unchanged. ``human_message`` is the English translation or a
    generic fallback when no rule matches.
    """
    if raw is None:
        return _FALLBACK_MESSAGE, ""
    text = raw or ""
    haystack = text.lower()
    for needle, message in _RULES:
        if needle.lower() in haystack:
            return message, text
    return _FALLBACK_MESSAGE, text
