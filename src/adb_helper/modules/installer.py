"""Module: Installer (Spec §3.3).

Independent of the global active device — maintains its own multi-device
checklist. Installs ``.apk``, ``.apks``, ``.xapk``, and ``.apkm`` sequentially
across N devices. ``.aab`` is unsupported (developer signing key required — §9).
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..core.models import DeviceContext


class InstallerModule(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def on_device_changed(self, ctx: DeviceContext) -> None:
        # Installer ignores the global active device by design (§3.3).
        pass

    def on_device_disconnected(self) -> None:
        pass
