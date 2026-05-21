"""AdbWebView — QWebEngineView subclass that forwards file drops to Python.

Chromium inside QWebEngineView swallows drag-and-drop on Win/X11/Wayland
unless dragEnterEvent AND dragMoveEvent both accept the action. HTML5 DnD
in the Vue layer can't surface absolute filesystem paths, so paths arrive
here via QDropEvent and are forwarded as a Qt signal to the installer
bridge — see web_main_window.WebMainWindow.__init__.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget


class AdbWebView(QWebEngineView):
    """QWebEngineView that re-emits dropped file paths as a Qt signal."""

    filesDropped = Signal(list)  # list[str] — absolute paths

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, ev: QDragEnterEvent) -> None:  # type: ignore[override]
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()
        else:
            super().dragEnterEvent(ev)

    def dragMoveEvent(self, ev: QDragMoveEvent) -> None:  # type: ignore[override]
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()
        else:
            super().dragMoveEvent(ev)

    def dropEvent(self, ev: QDropEvent) -> None:  # type: ignore[override]
        if not ev.mimeData().hasUrls():
            super().dropEvent(ev)
            return
        paths = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.filesDropped.emit(paths)
            ev.acceptProposedAction()


__all__ = ["AdbWebView"]
