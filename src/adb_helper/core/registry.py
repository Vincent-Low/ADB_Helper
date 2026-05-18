"""Module registry — single source of truth for sidebar navigation.

Spec §8: sidebar order, labels, and routing are data-driven from this registry.
Adding a module means appending an entry here plus a new file in
``adb_helper.modules`` — no edits to the main window or sidebar widget required.

The registry stores factory callables rather than constructed widgets so the
UI layer can instantiate modules lazily after Qt is up.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional


@dataclass(frozen=True)
class ModuleEntry:
    """One row in the sidebar."""

    key: str
    """Stable identifier (e.g., ``"connections"``). Used in settings.json."""

    title: str
    """User-facing label shown in the sidebar."""

    icon: str
    """Icon identifier resolved by the UI layer."""

    factory: Callable[[], object]
    """Callable returning a fresh ``QWidget`` that implements ``IModule``."""

    default: bool = False
    """Selected on first launch when True (only Connections should be true)."""


@dataclass
class ModuleRegistry:
    """Append-only ordered collection of ``ModuleEntry`` rows."""

    _entries: List[ModuleEntry] = field(default_factory=list)

    def register(self, entry: ModuleEntry) -> None:
        if any(e.key == entry.key for e in self._entries):
            raise ValueError(f"Module key already registered: {entry.key!r}")
        self._entries.append(entry)

    def entries(self) -> Iterable[ModuleEntry]:
        return tuple(self._entries)

    def get(self, key: str) -> Optional[ModuleEntry]:
        for e in self._entries:
            if e.key == key:
                return e
        return None

    def default_key(self) -> Optional[str]:
        for e in self._entries:
            if e.default:
                return e.key
        return None
