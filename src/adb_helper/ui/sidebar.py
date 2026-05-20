"""Sidebar widget — data-driven nav from ModuleRegistry (Spec §2.1, §8).

Three width modes driven by parent-window width (Redesign v1.0 + Plan §2.2):
    width < 1100   → 64 px  (icon-only, brand row hidden)
    1100..1699     → 220 px (default expanded)
    width >= 1700  → 256 px (wide screens, e.g. 4K)

Active item is styled via the ``active`` Qt property (matched by the QSS
template in ``ui/theming/qss.py``). Icon colours come from the current
token set — re-rendered when ``ThemeManager.theme_changed`` fires.
"""
from __future__ import annotations

import pathlib
from typing import Dict, Optional

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ..core import strings
from ..core.registry import ModuleRegistry
from .theming import DARK_TOKENS, Tokens, get_theme_manager

SIDEBAR_W_COLLAPSED = 64
SIDEBAR_W_EXPANDED = 220
SIDEBAR_W_WIDE = 256
COLLAPSE_THRESHOLD = 1100
WIDE_THRESHOLD = 1700

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


class _BrandLogo(QWidget):
    """26×26 rounded-square gradient tile with a centred capital letter."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarLogo")
        self.setFixedSize(26, 26)
        self._letter: str = "A"
        self._bg_start: QColor = QColor(DARK_TOKENS.accent)
        self._bg_end: QColor = QColor(DARK_TOKENS.accent_strong)
        self._fg: QColor = QColor(DARK_TOKENS.accent_fg)

    def set_letter(self, letter: str) -> None:
        self._letter = (letter or "A")[:1].upper()
        self.update()

    def set_tokens(self, tokens: Tokens) -> None:
        self._bg_start = QColor(tokens.accent)
        self._bg_end = QColor(tokens.accent_strong)
        self._fg = QColor(tokens.accent_fg)
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: D401 — Qt callback
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, self._bg_start)
        gradient.setColorAt(1.0, self._bg_end)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(rect, 6.0, 6.0)
        font = QFont()
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(self._fg)
        p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self._letter)
        p.end()


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
        self._wide: bool = False
        self._buttons: Dict[str, QPushButton] = {}
        self._icon_names: Dict[str, str] = {}
        self._labels: Dict[str, str] = {}
        self._active_id: Optional[str] = None
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(2)

        self._brand = self._build_brand()
        layout.addWidget(self._brand)

        for desc in registry.get_all():
            btn = self._build_button(desc.id, desc.label, desc.icon_name)
            self._buttons[desc.id] = btn
            self._icon_names[desc.id] = desc.icon_name
            self._labels[desc.id] = desc.label
            self._group.addButton(btn)
            layout.addWidget(btn)
            btn.clicked.connect(lambda _checked=False, mid=desc.id: self._on_clicked(mid))

        layout.addStretch(1)
        self._apply_tokens(self._current_tokens())
        self._apply_width()

        tm = get_theme_manager()
        if tm is not None:
            tm.theme_changed.connect(self._on_theme_changed)

    # --- public API ------------------------------------------------------
    def set_active(self, module_id: str) -> None:
        if module_id not in self._buttons:
            return
        self._active_id = module_id
        active_clr, inactive_clr = self._icon_colours()
        for mid, btn in self._buttons.items():
            active = mid == module_id
            btn.setChecked(active)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
            icon_name = self._icon_names.get(mid, "")
            colour = active_clr if active else inactive_clr
            icon = self._load_svg_icon(icon_name, colour)
            if icon is not None:
                btn.setIcon(icon)

    def update_for_window_width(self, width: int) -> None:
        collapsed = width < COLLAPSE_THRESHOLD
        wide = width >= WIDE_THRESHOLD and not collapsed
        if collapsed == self._collapsed and wide == self._wide:
            return
        self._collapsed = collapsed
        self._wide = wide
        for mid, btn in self._buttons.items():
            self._apply_button_mode(btn, mid)
        self._brand.setVisible(not collapsed)
        self._apply_width()

    # --- internals -------------------------------------------------------
    def _build_brand(self) -> QWidget:
        brand = QWidget(self)
        brand.setObjectName("sidebarBrand")
        row = QHBoxLayout(brand)
        row.setContentsMargins(8, 8, 8, 14)
        row.setSpacing(10)

        self._logo = _BrandLogo(brand)
        self._logo.set_letter(strings.APP_NAME[:1] if strings.APP_NAME else "A")
        row.addWidget(self._logo, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(0)

        self._brand_title = QLabel(strings.APP_NAME, brand)
        self._brand_title.setObjectName("sidebarBrandTitle")
        title_font = self._brand_title.font()
        title_font.setPixelSize(14)
        title_font.setWeight(QFont.Weight.DemiBold)
        self._brand_title.setFont(title_font)

        version_text = self._resolve_version()
        self._brand_version = QLabel(version_text, brand)
        self._brand_version.setObjectName("sidebarBrandVersion")
        self._brand_version.setProperty("muted", "true")

        text_col.addWidget(self._brand_title)
        text_col.addWidget(self._brand_version)
        row.addLayout(text_col, 1)

        return brand

    @staticmethod
    def _resolve_version() -> str:
        ver = getattr(strings, "APP_VERSION", "1.0.0") or "1.0.0"
        return ver if str(ver).lower().startswith("v") else f"v{ver}"

    def _build_button(self, mid: str, label: str, icon_name: str) -> QPushButton:
        btn = QPushButton(self)
        btn.setObjectName("sidebarItem")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setIconSize(QSize(18, 18))
        active_clr, inactive_clr = self._icon_colours()
        svg_icon = self._load_svg_icon(icon_name, inactive_clr)
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
        """Load SVG from assets/icons/ recoloured to a flat fill."""
        root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        svg_path = root / "assets" / "icons" / f"{name}.svg"
        if not svg_path.exists():
            return None
        try:
            svg_text = svg_path.read_text(encoding="utf-8")
        except OSError:
            return None
        fill = colour if colour is not None else self._icon_colours()[1]
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
            btn.setText(self._labels.get(mid, btn.toolTip()))

    def _apply_width(self) -> None:
        if self._collapsed:
            w = SIDEBAR_W_COLLAPSED
        elif self._wide:
            w = SIDEBAR_W_WIDE
        else:
            w = SIDEBAR_W_EXPANDED
        self.setFixedWidth(w)

    def _on_clicked(self, module_id: str) -> None:
        self.set_active(module_id)
        self.module_selected.emit(module_id)

    def _current_tokens(self) -> Tokens:
        tm = get_theme_manager()
        if tm is None:
            return DARK_TOKENS
        try:
            return tm.current_tokens()
        except AttributeError:
            return DARK_TOKENS

    def _icon_colours(self) -> tuple[str, str]:
        t = self._current_tokens()
        return t.accent, t.text_3

    def _apply_tokens(self, tokens: Tokens) -> None:
        self._logo.set_tokens(tokens)

    def _on_theme_changed(self, _theme) -> None:
        tokens = self._current_tokens()
        self._apply_tokens(tokens)
        active_clr, inactive_clr = tokens.accent, tokens.text_3
        for mid, btn in self._buttons.items():
            icon_name = self._icon_names.get(mid, "")
            colour = active_clr if mid == self._active_id else inactive_clr
            icon = self._load_svg_icon(icon_name, colour)
            if icon is not None:
                btn.setIcon(icon)


__all__ = [
    "Sidebar",
    "SIDEBAR_W_EXPANDED",
    "SIDEBAR_W_COLLAPSED",
    "SIDEBAR_W_WIDE",
    "COLLAPSE_THRESHOLD",
    "WIDE_THRESHOLD",
]
