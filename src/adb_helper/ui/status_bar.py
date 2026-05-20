"""Application status bar (Spec §2.1 + Redesign plan §3).

Segment layout, left → right:
    [● dot] model · serial | Transport: USB|Wi-Fi | Android <release> · API <sdk>
            ┄┄┄ stretch ┄┄┄
    [🔋] NN% | ADB: running|stopped

Battery + ADB-daemon segments live on the right via ``addPermanentWidget``.
Theme-driven colours come from ``ThemeManager.current_tokens()``; the
status dot and the battery icon repaint on ``theme_changed``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStatusBar,
    QWidget,
)

from ..core import strings
from ..core.device_context import DeviceContext
from ..core.logger import get_logger
from .theming import DARK_TOKENS, Tokens, get_theme_manager

_log = get_logger(__name__)

NO_DEVICE_TEXT = strings.STATUS_NO_DEVICE

# SDK level → Android marketing version (recent releases only — fall back
# to API-only display when unmapped).
_SDK_TO_ANDROID: dict[int, str] = {
    29: "10",
    30: "11",
    31: "12",
    32: "12L",
    33: "13",
    34: "14",
    35: "15",
    36: "16",
    37: "17",
}


class _StatusDot(QLabel):
    """8×8 round status indicator. Color set via ``set_state``."""

    _SIZE = 8

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusDot")
        self.setFixedSize(QSize(self._SIZE + 6, self._SIZE + 4))
        self._color: QColor = QColor(DARK_TOKENS.text_3)

    def set_color(self, color_hex: str) -> None:
        new_color = QColor(color_hex)
        if new_color == self._color:
            return
        self._color = new_color
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: D401 — Qt callback
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = self._SIZE / 2.0
        rect = QRectF(cx - r, cy - r, self._SIZE, self._SIZE)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(rect)
        p.end()


def _separator(parent: QWidget) -> QFrame:
    sep = QFrame(parent)
    sep.setObjectName("StatusSep")
    sep.setFrameShape(QFrame.Shape.NoFrame)
    sep.setFixedSize(QSize(1, 14))
    return sep


def _battery_pixmap(tokens: Tokens) -> Optional[QPixmap]:
    """Render assets/icons/battery.svg recoloured to ``tokens.text_2``."""
    svg_path = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "icons" / "battery.svg"
    if not svg_path.exists():
        return None
    try:
        svg_text = svg_path.read_text(encoding="utf-8")
    except OSError:
        return None
    data = svg_text.replace("currentColor", tokens.text_2).encode("utf-8")
    renderer = QSvgRenderer(data)
    pix = QPixmap(QSize(20, 12))
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return pix


class AppStatusBar(QStatusBar):
    """Status bar with device / transport / Android / battery / ADB segments."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSizeGripEnabled(False)

        self._tokens: Tokens = self._current_tokens()
        self._adb_running: bool = True
        self._battery_pct: Optional[int] = None

        # --- Left container -------------------------------------------------
        left = QWidget(self)
        left_row = QHBoxLayout(left)
        left_row.setContentsMargins(8, 0, 8, 0)
        left_row.setSpacing(8)

        # Device segment
        self._device_seg = QWidget(left)
        self._device_seg.setObjectName("statusDeviceSeg")
        dev_row = QHBoxLayout(self._device_seg)
        dev_row.setContentsMargins(0, 0, 0, 0)
        dev_row.setSpacing(6)
        self._dot = _StatusDot(self._device_seg)
        self._device_label = QLabel(NO_DEVICE_TEXT, self._device_seg)
        self._device_label.setObjectName("statusDeviceLabel")
        self._device_label.setTextFormat(Qt.TextFormat.RichText)
        dev_row.addWidget(self._dot)
        dev_row.addWidget(self._device_label)
        left_row.addWidget(self._device_seg)

        # Transport segment
        self._sep_transport = _separator(left)
        self._transport_label = QLabel("", left)
        self._transport_label.setObjectName("statusTransport")
        self._transport_label.setTextFormat(Qt.TextFormat.RichText)
        left_row.addWidget(self._sep_transport)
        left_row.addWidget(self._transport_label)

        # Android version segment
        self._sep_android = _separator(left)
        self._android_label = QLabel("", left)
        self._android_label.setObjectName("statusAndroid")
        self._android_label.setTextFormat(Qt.TextFormat.RichText)
        left_row.addWidget(self._sep_android)
        left_row.addWidget(self._android_label)

        left_row.addStretch(1)
        self.addWidget(left, 1)

        # --- Right container (permanent) -----------------------------------
        right = QWidget(self)
        right_row = QHBoxLayout(right)
        right_row.setContentsMargins(8, 0, 8, 0)
        right_row.setSpacing(8)

        # Battery
        self._battery_seg = QWidget(right)
        self._battery_seg.setObjectName("statusBatterySeg")
        bat_row = QHBoxLayout(self._battery_seg)
        bat_row.setContentsMargins(0, 0, 0, 0)
        bat_row.setSpacing(4)
        self._battery_icon = QLabel(self._battery_seg)
        self._battery_icon.setObjectName("statusBatteryIcon")
        self._battery_label = QLabel("", self._battery_seg)
        self._battery_label.setObjectName("statusBatteryLabel")
        self._battery_label.setTextFormat(Qt.TextFormat.RichText)
        bat_row.addWidget(self._battery_icon)
        bat_row.addWidget(self._battery_label)
        right_row.addWidget(self._battery_seg)

        # ADB daemon
        self._sep_adb = _separator(right)
        self._adb_label = QLabel("", right)
        self._adb_label.setObjectName("statusAdb")
        self._adb_label.setTextFormat(Qt.TextFormat.RichText)
        right_row.addWidget(self._sep_adb)
        right_row.addWidget(self._adb_label)

        self.addPermanentWidget(right)

        # Initial state
        self._apply_tokens(self._tokens)
        self.update_device(None)
        self.set_battery(None)
        self.set_adb_state(True)

        tm = get_theme_manager()
        if tm is not None:
            tm.theme_changed.connect(self._on_theme_changed)

    # --- public slots ---------------------------------------------------
    def update_device(self, ctx: Optional[DeviceContext]) -> None:
        if ctx is None:
            self._dot.set_color(self._tokens.text_3)
            self._device_label.setText(NO_DEVICE_TEXT)
            self._device_seg.show()
            self._sep_transport.hide()
            self._transport_label.hide()
            self._sep_android.hide()
            self._android_label.hide()
            return

        self._device_seg.show()
        self._sep_transport.show()
        self._transport_label.show()
        self._sep_android.show()
        self._android_label.show()

        self._dot.set_color(self._dot_color_for_status(ctx.status))
        model = ctx.model or ctx.serial or "device"
        self._device_label.setText(
            f"<b>{_esc(model)}</b> · {_esc(ctx.serial)}"
        )

        transport = (
            strings.STATUS_BAR_TRANSPORT_USB
            if ctx.connection_type == "usb"
            else strings.STATUS_BAR_TRANSPORT_WIFI
        )
        self._transport_label.setText(
            f"{strings.STATUS_BAR_TRANSPORT_LABEL} <b>{_esc(transport)}</b>"
        )

        self._android_label.setText(self._format_android(ctx.sdk_version))

    def set_battery(self, percent: Optional[int]) -> None:
        self._battery_pct = percent
        if percent is None:
            self._battery_seg.hide()
            return
        clamped = max(0, min(100, int(percent)))
        self._battery_label.setText(
            f"<b>{strings.STATUS_BAR_BATTERY_FMT.format(pct=clamped)}</b>"
        )
        self._battery_seg.show()

    def set_adb_state(self, running: bool) -> None:
        self._adb_running = bool(running)
        state_text = (
            strings.STATUS_BAR_ADB_RUNNING if running else strings.STATUS_BAR_ADB_STOPPED
        )
        color = self._tokens.success if running else self._tokens.danger
        self._adb_label.setText(
            f"{strings.STATUS_BAR_ADB_PREFIX} "
            f"<b style=\"color:{color};\">{_esc(state_text)}</b>"
        )

    def show_message(self, text: str) -> None:
        """Compat shim — design has no transient slot. Route to logger only."""
        if text:
            _log.info("status: %s", text)

    # --- helpers --------------------------------------------------------
    def _current_tokens(self) -> Tokens:
        tm = get_theme_manager()
        if tm is None:
            return DARK_TOKENS
        try:
            return tm.current_tokens()
        except AttributeError:
            return DARK_TOKENS

    def _apply_tokens(self, tokens: Tokens) -> None:
        self._tokens = tokens
        pix = _battery_pixmap(tokens)
        if pix is not None:
            self._battery_icon.setPixmap(pix)
        # Re-render colour-bearing segments.
        self.set_adb_state(self._adb_running)
        if self._device_seg.isHidden():
            self._dot.set_color(tokens.text_3)

    def _on_theme_changed(self, _theme) -> None:
        self._apply_tokens(self._current_tokens())

    def _dot_color_for_status(self, status: str) -> str:
        if status == "online":
            return self._tokens.success
        if status == "unauthorized":
            return self._tokens.warning
        return self._tokens.danger

    def _format_android(self, sdk_version: str) -> str:
        sdk_str = (sdk_version or "").strip()
        if not sdk_str:
            return ""
        try:
            sdk_int = int(sdk_str)
        except ValueError:
            return strings.STATUS_BAR_API_ONLY_FMT.format(sdk=_esc(sdk_str))
        release = _SDK_TO_ANDROID.get(sdk_int)
        if release is None:
            return strings.STATUS_BAR_API_ONLY_FMT.format(sdk=sdk_int).replace(
                f"{sdk_int}", f"<b>{sdk_int}</b>"
            )
        # Bold release + sdk inside the localised format string.
        return strings.STATUS_BAR_ANDROID_FMT.format(
            release=f"<b>{release}</b>",
            sdk=f"<b>{sdk_int}</b>",
        )


def _esc(text: str) -> str:
    """Minimal HTML escape for RichText QLabel content."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


__all__ = ["AppStatusBar", "NO_DEVICE_TEXT"]
