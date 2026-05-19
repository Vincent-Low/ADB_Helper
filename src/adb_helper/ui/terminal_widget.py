"""TerminalWidget — QPlainTextEdit-backed ANSI renderer + input line.

Spec §3.2.1 + §2.2.1. The widget owns ANSI parsing and rendering, command
history navigation in the input field, and the Ctrl+L clear shortcut. It is
display-only: it does NOT spawn or talk to ADB — the surrounding module
wires it to a :class:`PtySession`.

CLAUDE.md invariant 1: this file is in ``ui/`` and contains zero
command-construction sites for ``adb``.

ANSI support (pragmatic subset that covers ``adb shell`` prompts/output):

  - SGR (``CSI ... m``): reset (0), bold (1), default fg (39) / bg (49),
    fg colours 30–37 / 90–97, bg colours 40–47 / 100–107.
  - Erase display ``CSI 2 J`` clears the screen and homes the cursor.
  - Erase line ``CSI K`` / ``CSI 0 K`` clears from the cursor to end of line.
  - ``\\r`` moves the cursor to the start of the current line (overwrite).
  - ``\\n`` inserts a newline (also flushes any pending column tracking).
  - ``\\b`` deletes the previous character.
  - OSC (``ESC ] ... BEL`` / ``ESC ] ... ESC \\``) is consumed and ignored
    (title-change sequences).

This is intentionally not a full vt100 emulator — full cursor positioning
(top/top-right output like ``top``) renders only partially.
"""
from __future__ import annotations

import codecs
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QPalette,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core import strings
from ..core.platform import get_monospace_font
from ..core.logger import get_logger
from .terminal_palette import DARK_PALETTE, LIGHT_PALETTE

_log = get_logger(__name__)

_TERM_FONT_PT = 13
_MONO_FALLBACKS = ("Cascadia Code", "JetBrains Mono", "Consolas", "Menlo", "DejaVu Sans Mono")

# SGR colour-index → palette key.
_FG_BY_CODE: Dict[int, str] = {
    30: "black", 31: "red", 32: "green", 33: "yellow",
    34: "blue", 35: "magenta", 36: "cyan", 37: "white",
    90: "bright_black", 91: "bright_red", 92: "bright_green", 93: "bright_yellow",
    94: "bright_blue", 95: "bright_magenta", 96: "bright_cyan", 97: "bright_white",
}
_BG_BY_CODE: Dict[int, str] = {
    40: "black", 41: "red", 42: "green", 43: "yellow",
    44: "blue", 45: "magenta", 46: "cyan", 47: "white",
    100: "bright_black", 101: "bright_red", 102: "bright_green", 103: "bright_yellow",
    104: "bright_blue", 105: "bright_magenta", 106: "bright_cyan", 107: "bright_white",
}


def _build_terminal_font() -> QFont:
    families = QFontDatabase.families()
    preferred = get_monospace_font()
    for name in (preferred, *_MONO_FALLBACKS):
        if name in families:
            font = QFont(name, _TERM_FONT_PT)
            font.setStyleHint(QFont.StyleHint.Monospace)
            font.setFixedPitch(True)
            return font
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPointSize(_TERM_FONT_PT)
    return font


class _AnsiRenderer:
    """Byte-stream → QPlainTextEdit translator with a small CSI state machine."""

    _NORMAL = 0
    _ESC = 1
    _CSI = 2
    _OSC = 3

    def __init__(self, view: QPlainTextEdit, palette: Dict[str, str]) -> None:
        self._view = view
        self._palette = palette
        self._state = self._NORMAL
        self._params = bytearray()
        self._pending_text = bytearray()
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._default_fmt = QTextCharFormat()
        self._cur_fmt = QTextCharFormat()
        self._osc_prev_esc = False
        self._apply_palette_to_format(self._default_fmt, palette)
        self._cur_fmt = QTextCharFormat(self._default_fmt)

    # --- public API ----------------------------------------------------
    def set_palette(self, palette: Dict[str, str]) -> None:
        self._palette = palette
        self._default_fmt = QTextCharFormat()
        self._apply_palette_to_format(self._default_fmt, palette)
        self._cur_fmt = QTextCharFormat(self._default_fmt)

    def feed(self, data: bytes) -> None:
        for b in data:
            self._process_byte(b)
        self._flush_text()

    def clear(self) -> None:
        self._view.clear()

    # --- internals -----------------------------------------------------
    @staticmethod
    def _apply_palette_to_format(fmt: QTextCharFormat, palette: Dict[str, str]) -> None:
        fg = QColor(palette["foreground"])
        fmt.setForeground(fg)
        # Background of glyphs left transparent; widget background carries
        # the palette colour. Setting it here doubles up on selection.

    def _process_byte(self, b: int) -> None:
        if self._state == self._NORMAL:
            if b == 0x1B:
                self._flush_text()
                self._state = self._ESC
            elif b == 0x07:
                pass  # BEL — ignore.
            elif b == 0x08:  # BS
                self._flush_text()
                self._backspace()
            elif b == 0x0D:  # CR
                self._flush_text()
                self._carriage_return()
            elif b == 0x0A:  # LF
                self._flush_text()
                self._newline()
            else:
                self._pending_text.append(b)
            return

        if self._state == self._ESC:
            if b == 0x5B:  # '['
                self._state = self._CSI
                self._params = bytearray()
            elif b == 0x5D:  # ']'
                self._state = self._OSC
                self._params = bytearray()
                self._osc_prev_esc = False
            else:
                self._state = self._NORMAL
            return

        if self._state == self._CSI:
            if 0x40 <= b <= 0x7E:
                self._dispatch_csi(chr(b), bytes(self._params))
                self._state = self._NORMAL
                self._params = bytearray()
            else:
                self._params.append(b)
            return

        if self._state == self._OSC:
            if b == 0x07 or (b == 0x5C and self._osc_prev_esc):
                self._state = self._NORMAL
                self._params = bytearray()
                self._osc_prev_esc = False
            else:
                self._osc_prev_esc = (b == 0x1B)
            return

    def _flush_text(self) -> None:
        if not self._pending_text:
            return
        try:
            text = self._decoder.decode(bytes(self._pending_text))
        except UnicodeDecodeError:
            text = bytes(self._pending_text).decode("utf-8", errors="replace")
        self._pending_text = bytearray()
        if not text:
            return
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for ch in text:
            if ch == "\n":
                cursor.insertText("\n", self._cur_fmt)
                continue
            # If cursor is not at end-of-block (e.g. after \r), overwrite.
            if not cursor.atBlockEnd():
                cursor.deleteChar()
            cursor.insertText(ch, self._cur_fmt)
        self._view.setTextCursor(cursor)
        self._view.ensureCursorVisible()

    def _carriage_return(self) -> None:
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        self._view.setTextCursor(cursor)

    def _newline(self) -> None:
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("\n", self._cur_fmt)
        self._view.setTextCursor(cursor)
        self._view.ensureCursorVisible()

    def _backspace(self) -> None:
        cursor = self._view.textCursor()
        if cursor.atBlockStart():
            return
        cursor.movePosition(
            QTextCursor.MoveOperation.PreviousCharacter,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.removeSelectedText()
        self._view.setTextCursor(cursor)

    def _dispatch_csi(self, final: str, params_bytes: bytes) -> None:
        # Strip leading '?' / intermediate bytes (DEC private modes etc.).
        raw = params_bytes.decode("ascii", errors="ignore")
        if raw.startswith("?"):
            # Ignore mode set/reset (e.g. ?25h hide cursor).
            return
        params = self._parse_params(raw)
        if final == "m":
            self._apply_sgr(params)
        elif final == "J":
            n = params[0] if params else 0
            if n == 2:
                self._view.clear()
                cur = self._view.textCursor()
                cur.movePosition(QTextCursor.MoveOperation.Start)
                self._view.setTextCursor(cur)
        elif final == "K":
            n = params[0] if params else 0
            if n in (0, 2):
                cursor = self._view.textCursor()
                cursor.movePosition(
                    QTextCursor.MoveOperation.EndOfBlock,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                cursor.removeSelectedText()
                self._view.setTextCursor(cursor)
        elif final == "H":
            # Simple home: only honoured when no parameters (full positioning
            # would need a grid model — out of scope here).
            if not params or params == [1, 1]:
                cur = self._view.textCursor()
                cur.movePosition(QTextCursor.MoveOperation.Start)
                self._view.setTextCursor(cur)
        # Other CSI finals (A/B/C/D cursor moves, scroll, etc.) are intentionally
        # ignored — adb shell output rarely depends on them outside of fullscreen
        # apps like `top`.

    @staticmethod
    def _parse_params(raw: str) -> List[int]:
        if not raw:
            return []
        out: List[int] = []
        for part in raw.split(";"):
            part = part.strip()
            if not part:
                out.append(0)
                continue
            try:
                out.append(int(part))
            except ValueError:
                out.append(0)
        return out

    def _apply_sgr(self, params: List[int]) -> None:
        if not params:
            params = [0]
        i = 0
        while i < len(params):
            code = params[i]
            if code == 0:
                self._cur_fmt = QTextCharFormat(self._default_fmt)
                self._cur_fmt.setFontWeight(QFont.Weight.Normal)
            elif code == 1:
                self._cur_fmt.setFontWeight(QFont.Weight.Bold)
            elif code == 22:
                self._cur_fmt.setFontWeight(QFont.Weight.Normal)
            elif code == 39:
                self._cur_fmt.setForeground(QColor(self._palette["foreground"]))
            elif code == 49:
                self._cur_fmt.clearBackground()
            elif code in _FG_BY_CODE:
                self._cur_fmt.setForeground(QColor(self._palette[_FG_BY_CODE[code]]))
            elif code in _BG_BY_CODE:
                self._cur_fmt.setBackground(QColor(self._palette[_BG_BY_CODE[code]]))
            elif code == 38 or code == 48:
                # 256-colour / truecolour — skip remaining specifier bytes.
                if i + 1 < len(params) and params[i + 1] == 5:
                    i += 2
                elif i + 1 < len(params) and params[i + 1] == 2:
                    i += 4
            i += 1


class _InputLine(QLineEdit):
    """QLineEdit with history navigation + Ctrl+L hook."""

    history_up = Signal()
    history_down = Signal()
    clear_requested = Signal()
    interrupt_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key.Key_Up and not mods:
            self.history_up.emit()
            event.accept()
            return
        if key == Qt.Key.Key_Down and not mods:
            self.history_down.emit()
            event.accept()
            return
        if key == Qt.Key.Key_L and (mods & Qt.KeyboardModifier.ControlModifier):
            self.clear_requested.emit()
            event.accept()
            return
        if key == Qt.Key.Key_C and (mods & Qt.KeyboardModifier.ControlModifier):
            self.interrupt_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class TerminalWidget(QWidget):
    """Output view + input line. Stateless w.r.t. PTY — bytes in, lines out."""

    command_entered = Signal(str)
    interrupt_pressed = Signal()
    history_up_pressed = Signal()
    history_down_pressed = Signal()

    def __init__(self, parent: Optional[QWidget] = None, dark: bool = True) -> None:
        super().__init__(parent)
        self._palette: Dict[str, str] = DARK_PALETTE if dark else LIGHT_PALETTE
        self._prompt_text = ""

        self._build_ui()
        self._renderer = _AnsiRenderer(self._view, self._palette)
        self._apply_palette()
        self._wire_signals()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        self._view = QPlainTextEdit(self)
        self._view.setObjectName("terminal-output")
        self._view.setReadOnly(True)
        self._view.setUndoRedoEnabled(False)
        self._view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._view.setFont(_build_terminal_font())
        self._view.setFrameShape(self._view.Shape.NoFrame)
        root.addWidget(self._view, 1)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(8, 4, 8, 4)
        input_row.setSpacing(6)
        self._prompt = QLabel("", self)
        self._prompt.setFont(_build_terminal_font())
        input_row.addWidget(self._prompt, 0)

        self._input = _InputLine(self)
        self._input.setFont(_build_terminal_font())
        self._input.setFrame(False)
        input_row.addWidget(self._input, 1)
        root.addLayout(input_row)

    def _wire_signals(self) -> None:
        self._input.returnPressed.connect(self._on_return)
        self._input.history_up.connect(self.history_up_pressed)
        self._input.history_down.connect(self.history_down_pressed)
        self._input.clear_requested.connect(self.clear_output)
        self._input.interrupt_requested.connect(self.interrupt_pressed)

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------
    def set_dark(self, dark: bool) -> None:
        self._palette = DARK_PALETTE if dark else LIGHT_PALETTE
        self._renderer.set_palette(self._palette)
        self._apply_palette()

    def _apply_palette(self) -> None:
        bg = QColor(self._palette["background"])
        fg = QColor(self._palette["foreground"])
        for w in (self._view, self._input, self._prompt, self):
            pal = w.palette()
            pal.setColor(QPalette.ColorRole.Base, bg)
            pal.setColor(QPalette.ColorRole.Window, bg)
            pal.setColor(QPalette.ColorRole.Text, fg)
            pal.setColor(QPalette.ColorRole.WindowText, fg)
            pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(self._palette["bright_black"]))
            w.setPalette(pal)
            w.setAutoFillBackground(True)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    def feed_bytes(self, data: bytes) -> None:
        self._renderer.feed(data)

    def write_local_line(self, text: str) -> None:
        """Inject a host-side line (info/status) into the buffer."""
        suffix = "" if text.endswith("\n") else "\n"
        self._renderer.feed((text + suffix).encode("utf-8"))

    def clear_output(self) -> None:
        self._view.clear()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def set_prompt_serial(self, serial: Optional[str]) -> None:
        if serial:
            text = strings.TERM_PROMPT_TEMPLATE.format(serial=serial)
        else:
            text = ""
        self._prompt_text = text
        self._prompt.setText(text)

    def set_input_text(self, text: str) -> None:
        self._input.setText(text)
        self._input.setCursorPosition(len(text))

    def get_input_text(self) -> str:
        return self._input.text()

    def set_input_enabled(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)

    def focus_input(self) -> None:
        self._input.setFocus()

    def _on_return(self) -> None:
        text = self._input.text()
        self._input.clear()
        self.command_entered.emit(text)


__all__ = ["TerminalWidget"]
