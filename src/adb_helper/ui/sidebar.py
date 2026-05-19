"""Sidebar widget — data-driven nav from ModuleRegistry (Spec §2.1, §8).

Collapsed ~56 px (icon only) / expanded ~220 px (icon + label). Auto-collapses
when the parent window is narrower than 1280 px. Active item highlighted via
the ``active`` Qt property (styled in QSS).
"""
from __future__ import annotations

import pathlib
from typing import Dict, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QButtonGroup,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ..core.registry import ModuleRegistry

SIDEBAR_W_EXPANDED = 220
SIDEBAR_W_COLLAPSED = 56
COLLAPSE_THRESHOLD = 1280

_ICON_INACTIVE = "#4a525b"
_ICON_ACTIVE = "#2ec5c5"

_ICON_MAP: Dict[str, QStyle.StandardPixmap] = {
    "connections":    QStyle.SP_DriveNetIcon,
    "terminal":       QStyle.SP_ComputerIcon,
    "installer":      QStyle.SP_DialogOpenButton,
    "scrcpy":         QStyle.SP_DesktopIcon,
    "device_buttons": QStyle.SP_MediaPlay,
    "device_info":    QStyle.SP_FileDialogInfoView,
    "apps":           QStyle.SP_DirIcon,
    "logcat":         QStyle.SP_FileDialogContentsView,
    "settings":       QStyle.SP_FileDialogDetailedView,
}


class Sidebar(QWidget):
    """Data-driven sidebar reading from a ``ModuleRegistry``."""

    module_selected = Signal(str)  # module_id

    def __init__(
        self,
        registry: ModuleRegistry,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("appSidebar")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self._collapsed: bool = False
        self._buttons: Dict[str, QPushButton] = {}
        self._icon_names: Dict[str, str] = {}
        self._active_id: Optional[str] = None
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(2)

        for desc in registry.get_all():
            btn = self._build_button(desc.id, desc.label, desc.icon_name)
            self._buttons[desc.id] = btn
            self._icon_names[desc.id] = desc.icon_name
            self._group.addButton(btn)
            layout.addWidget(btn)
            btn.clicked.connect(lambda _checked=False, mid=desc.id: self._on_clicked(mid))

        layout.addStretch(1)
        self._apply_width()

    # --- public API ------------------------------------------------------
    def set_active(self, module_id: str) -> None:
        if module_id not in self._buttons:
            return
        self._active_id = module_id
        for mid, btn in self._buttons.items():
            active = mid == module_id
            btn.setChecked(active)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
            icon_name = self._icon_names.get(mid, "")
            colour = _ICON_ACTIVE if active else _ICON_INACTIVE
            icon = self._load_svg_icon(icon_name, colour)
            if icon is not None:
                btn.setIcon(icon)

    def update_for_window_width(self, width: int) -> None:
        collapsed = width < COLLAPSE_THRESHOLD
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        for mid, btn in self._buttons.items():
            self._apply_button_mode(btn, mid)
        self._apply_width()

    # --- internals -------------------------------------------------------
    def _build_button(self, mid: str, label: str, icon_name: str) -> QPushButton:
        btn = QPushButton(self)
        btn.setObjectName("sidebarItem")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setIconSize(QSize(18, 18))
        svg_icon = self._load_svg_icon(icon_name)
        if svg_icon is not None:
            btn.setIcon(svg_icon)
            btn.setProperty("_svg_icon_name", icon_name)
        else:
            std_icon = _ICON_MAP.get(icon_name, QStyle.SP_FileIcon)
            btn.setIcon(self.style().standardIcon(std_icon))
        btn.setToolTip(label)
        btn.setText(label)
        btn.setProperty("module_id", mid)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return btn

    def _load_svg_icon(self, name: str, colour: Optional[str] = None) -> Optional[QIcon]:
        """Load SVG from assets/icons/ with a single flat colour."""
        root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        svg_path = root / "assets" / "icons" / f"{name}.svg"
        if not svg_path.exists():
            return None
        try:
            svg_text = svg_path.read_text(encoding="utf-8")
        except OSError:
            return None
        fill = colour if colour is not None else _ICON_INACTIVE
        data = svg_text.replace("currentColor", fill).encode("utf-8")
        renderer = QSvgRenderer(data)
        pix = QPixmap(20, 20)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        return QIcon(pix)

    def _apply_button_mode(self, btn: QPushButton, mid: str) -> None:
        if self._collapsed:
            btn.setText("")
        else:
            for desc in (d for d in self._buttons_descriptor_iter() if d[0] == mid):
                btn.setText(desc[1])
                break

    def _buttons_descriptor_iter(self):
        for mid, btn in self._buttons.items():
            yield mid, btn.toolTip()

    def _apply_width(self) -> None:
        w = SIDEBAR_W_COLLAPSED if self._collapsed else SIDEBAR_W_EXPANDED
        self.setFixedWidth(w)

    def _on_clicked(self, module_id: str) -> None:
        self.set_active(module_id)
        self.module_selected.emit(module_id)


__all__ = ["Sidebar", "SIDEBAR_W_EXPANDED", "SIDEBAR_W_COLLAPSED", "COLLAPSE_THRESHOLD"]
