"""Module registry — single source of truth for sidebar navigation.

Spec §8: sidebar order, labels, and routing are data-driven from this
registry. Population happens at import time in ``main.py``; this file
exposes the singleton plus its mutators only.
"""
from __future__ import annotations

from typing import List

from .imodule import ModuleDescriptor


class ModuleRegistry:
    """Ordered, append-only list of ``ModuleDescriptor`` rows."""

    def __init__(self) -> None:
        self._descriptors: List[ModuleDescriptor] = []

    def register(self, descriptor: ModuleDescriptor) -> None:
        if any(d.id == descriptor.id for d in self._descriptors):
            raise ValueError(f"Module id already registered: {descriptor.id!r}")
        self._descriptors.append(descriptor)

    def get_all(self) -> List[ModuleDescriptor]:
        return list(self._descriptors)


registry = ModuleRegistry()
