"""IModule contract — every sidebar screen implements this.

Spec §8 / CLAUDE.md invariant 2. ``QWidget`` is a real Qt metaclass so we
can't compose it with ``abc.ABCMeta``; instead the four lifecycle methods
raise ``NotImplementedError`` unless overridden. Subclasses MUST override
all four.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from .device_context import DeviceContext


class IModule(QWidget):
    """Abstract lifecycle interface for sidebar modules."""

    def on_activate(self) -> None:
        raise NotImplementedError

    def on_deactivate(self) -> None:
        raise NotImplementedError

    def on_device_changed(self, ctx: DeviceContext | None) -> None:
        raise NotImplementedError

    def on_device_disconnected(self) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class ModuleDescriptor:
    """Sidebar entry: stable id, label, icon, and widget class."""

    id: str
    label: str
    icon_name: str
    widget_class: type[IModule]
