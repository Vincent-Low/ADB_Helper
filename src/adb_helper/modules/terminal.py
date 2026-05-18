"""Module: Terminal (Spec §3.2).

Always an ``adb shell`` session on the active device — not a host OS shell.
ConPTY on Windows, Python ``pty`` on Linux, driven via ``QProcess``. ANSI
palette from §2.2.1. Command history (last 50) and macro recording of
terminal commands only (GUI-action macros are out of scope — §9).
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class TerminalModule(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def on_device_changed(self, ctx: DeviceContext) -> None:
        pass

    def on_device_disconnected(self) -> None:
        pass
