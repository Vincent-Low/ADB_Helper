"""IModule interface — every sidebar screen implements this.

Spec §8. Module widgets are ``QWidget`` subclasses that also implement these
four methods. Concrete imports of ``QWidget`` are deferred so this module can
be imported without PySide6 in lightweight contexts (tests, doc tooling).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import DeviceContext


@runtime_checkable
class IModule(Protocol):
    """Lifecycle hooks invoked by the module host (main window)."""

    def on_activate(self) -> None:
        """Called when the module becomes visible in the main content area."""
        ...

    def on_deactivate(self) -> None:
        """Called when another module is about to take over."""
        ...

    def on_device_changed(self, ctx: DeviceContext) -> None:
        """Called when the global active device changes.

        Installer ignores this and maintains its own multi-device checklist
        (§3.3 / CLAUDE.md invariant 3).
        """
        ...

    def on_device_disconnected(self) -> None:
        """Called when the global active device disconnects (§3.1.1)."""
        ...
