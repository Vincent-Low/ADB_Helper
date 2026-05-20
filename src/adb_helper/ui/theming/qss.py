"""QSS template + render_qss(tokens) → stylesheet string.

The template uses ``str.format_map`` with the asdict(Tokens) keys plus an
``icons_dir`` key for any ``image: url(...)`` references. Every literal
``{`` / ``}`` in the template must be doubled (``{{`` / ``}}``) — only
token placeholders stay single-braced.

The ICONS_DIR assert fails loudly if the package directory layout shifts
or assets get moved (handoff §6 / plan §1).
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .tokens import Tokens

# repo_root/assets/icons — five .parent hops from this file:
#   qss.py -> theming -> ui -> adb_helper -> src -> repo_root
ICONS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "assets" / "icons"
)
assert ICONS_DIR.exists(), f"icons dir missing: {ICONS_DIR}"


QSS_TEMPLATE = """\
/* ============================================================
   Base / reset
   ============================================================ */
* {{
    outline: 0;
    font-family: "Segoe UI", "Ubuntu", "Inter", -apple-system, sans-serif;
    font-size: 13px;
    color: {text_1};
}}

QMainWindow, QWidget#appCentral {{
    background: {bg_app};
}}
QWidget {{
    background: {bg_app};
    color: {text_1};
}}
QFrame {{
    background: transparent;
    border: none;
}}
QLabel {{
    background: transparent;
    color: {text_1};
}}
QLabel[muted="true"]     {{ color: {text_3}; font-size: 11px; }}
QLabel[secondary="true"] {{ color: {text_2}; font-size: 12px; }}
QLabel[role="hint"]      {{ color: {text_2}; font-size: 12px; }}
QLabel[role="section-label"] {{
    color: {text_2};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QLabel[role="page-title"] {{
    font-size: 16px;
    font-weight: 600;
    color: {text_1};
}}

/* ============================================================
   Sidebar
   ============================================================ */
QWidget#appSidebar {{
    background: {bg_content};
    border-right: 1px solid {border};
}}
QPushButton#sidebarItem {{
    background: transparent;
    color: {text_2};
    border: none;
    border-left: 2px solid transparent;
    border-radius: {r_md}px;
    padding: 8px 12px;
    text-align: left;
    min-height: 36px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#sidebarItem:hover {{
    background: {bg_card};
    color: {text_1};
}}
QPushButton#sidebarItem[active="true"] {{
    background: {accent_soft};
    color: {accent};
    border-left: 2px solid {accent};
}}
QPushButton#sidebarBrand {{
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0;
    min-height: 0;
}}
QPushButton#sidebarBrand:hover {{
    background: transparent;
    border: none;
}}

/* ============================================================
   Cards / sections
   ============================================================ */
QFrame[role="card"] {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: {r_lg}px;
}}
QFrame[role="card-h"] {{
    background: {bg_card_2};
    border: none;
    border-bottom: 1px solid {border};
    border-top-left-radius: {r_lg}px;
    border-top-right-radius: {r_lg}px;
    padding: 10px 14px;
}}
QFrame[role="card-b"] {{
    background: transparent;
    border: none;
    padding: 14px;
}}
QFrame[role="card-f"] {{
    background: {bg_card_2};
    border: none;
    border-top: 1px solid {border};
    border-bottom-left-radius: {r_lg}px;
    border-bottom-right-radius: {r_lg}px;
    padding: 10px 14px;
}}

/* GroupBox kept until per-module migration replaces it with QFrame[role="card"]. */
QGroupBox {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: {r_lg}px;
    margin-top: 18px;
    padding: 14px;
    font-size: 12px;
    font-weight: 600;
    color: {text_2};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background: {bg_card_2};
    color: {text_2};
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-radius: {r_sm}px;
}}

/* ============================================================
   Buttons
   ============================================================ */
QPushButton {{
    min-height: {btn_h}px;
    padding: 0 14px;
    background: {bg_card_2};
    border: 1px solid {border_input};
    border-radius: {r_md}px;
    color: {text_1};
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover    {{ background: {bg_elevated}; }}
QPushButton:pressed  {{ background: {bg_input}; }}
QPushButton:disabled {{
    color: {text_disabled};
    background: {bg_card_2};
    border-color: {border};
}}
QPushButton[variant="primary"] {{
    background: {accent};
    color: {accent_fg};
    border: 1px solid {accent};
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover    {{ background: {accent_strong}; border-color: {accent_strong}; }}
QPushButton[variant="primary"]:pressed  {{ background: {accent_strong}; }}
QPushButton[variant="primary"]:disabled {{
    background: {bg_card_2};
    color: {text_disabled};
    border: 1px solid {border};
}}
QPushButton[variant="danger"] {{
    color: {danger};
    background: {bg_card_2};
    border: 1px solid {border_input};
}}
QPushButton[variant="danger"]:hover {{ background: {bg_elevated}; }}
QPushButton[variant="destructive"] {{
    color: {danger};
    background: {bg_card_2};
    border: 1px solid {border_input};
}}
QPushButton[variant="destructive"]:hover {{
    background: {bg_elevated};
    border-color: {danger};
}}
QPushButton[variant="destructive"]:disabled {{
    color: {text_disabled};
    background: {bg_card_2};
    border-color: {border};
}}
QPushButton[variant="ghost"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {text_2};
}}
QPushButton[variant="ghost"]:hover {{
    background: {bg_card};
    color: {text_1};
    border-color: {border};
}}
QPushButton[size="sm"] {{
    min-height: 28px;
    padding: 0 10px;
    font-size: 11px;
}}

/* ============================================================
   Inputs
   ============================================================ */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
QPlainTextEdit, QTextEdit, QDateEdit, QTimeEdit {{
    min-height: {input_h}px;
    padding: 0 10px;
    background: {bg_input};
    border: 1px solid {border_input};
    border-radius: {r_md}px;
    color: {text_1};
    selection-background-color: {accent_soft};
    selection-color: {text_1};
}}
QPlainTextEdit, QTextEdit {{
    padding: 8px 10px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {accent};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QComboBox:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {{
    color: {text_disabled};
    background: {bg_card_2};
    border-color: {border};
}}
QLineEdit[size="sm"] {{
    min-height: 28px;
    padding: 0 8px;
}}
QLineEdit[role="search"] {{
    padding-left: 30px;
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {bg_card_2};
    border: none;
    width: 18px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {bg_elevated};
}}

/* ============================================================
   ComboBox
   ============================================================ */
QComboBox::drop-down {{
    border: 0;
    width: 22px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}}
QComboBox::down-arrow {{
    image: url({icons_dir}/chevron-down.svg);
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: {r_md}px;
    selection-background-color: {bg_row_selected};
    selection-color: {text_1};
    padding: 4px;
    outline: 0;
}}

/* ============================================================
   Tables / lists / trees
   ============================================================ */
QHeaderView::section {{
    background: {bg_card_2};
    color: {text_3};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 8px 12px;
    border: 0;
    border-bottom: 1px solid {border};
}}
QTableCornerButton::section {{
    background: {bg_card_2};
    border: 0;
    border-bottom: 1px solid {border};
}}
QAbstractItemView {{
    background: {bg_card};
    color: {text_1};
    alternate-background-color: {bg_card_2};
    gridline-color: {border};
    border: 0;
    selection-background-color: {bg_row_selected};
    selection-color: {text_1};
    outline: 0;
}}
QTableView, QTableWidget, QTreeView, QTreeWidget {{
    background: {bg_card};
    alternate-background-color: {bg_card_2};
    gridline-color: {border};
    border: 0;
    selection-background-color: {bg_row_selected};
    selection-color: {text_1};
}}
QTableView::item, QTreeView::item, QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {border};
    color: {text_1};
}}
QTableView::item:hover, QTreeView::item:hover {{
    background: {bg_row_hover};
}}
QTableView::item:selected, QTreeView::item:selected {{
    background: {bg_row_selected};
    color: {text_1};
}}
QListView, QListWidget {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: {r_md}px;
}}

/* In-table checkbox (Qt.ItemIsUserCheckable) — fix invisibility in dark theme. */
QTableView::indicator, QTreeView::indicator, QListView::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {border_strong};
    background: {bg_input};
    border-radius: 3px;
}}
QTableView::indicator:hover, QTreeView::indicator:hover, QListView::indicator:hover {{
    border-color: {accent};
}}
QTableView::indicator:checked, QTreeView::indicator:checked, QListView::indicator:checked {{
    background: {accent};
    border: 1.5px solid {accent};
    image: url({icons_dir}/check.svg);
}}

/* ============================================================
   CheckBox / RadioButton
   ============================================================ */
QCheckBox {{
    spacing: 8px;
    color: {text_1};
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {border_strong};
    background: {bg_input};
    border-radius: 3px;
}}
QCheckBox::indicator:hover    {{ border-color: {accent}; }}
QCheckBox::indicator:checked  {{
    border: 1.5px solid {accent};
    background: {accent};
    image: url({icons_dir}/check.svg);
}}
QCheckBox::indicator:disabled {{
    border-color: {border};
    background: {bg_card_2};
}}

QRadioButton {{
    spacing: 8px;
    color: {text_1};
    background: transparent;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {border_strong};
    background: {bg_input};
    border-radius: 8px;
}}
QRadioButton::indicator:checked {{
    border: 4px solid {accent};
    background: {bg_input};
}}

/* ============================================================
   ProgressBar
   ============================================================ */
QProgressBar {{
    background: {bg_elevated};
    border: 0;
    border-radius: 999px;
    text-align: center;
    color: {text_2};
    max-height: 6px;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: {accent};
    border-radius: 999px;
}}
QProgressBar[state="warn"]::chunk    {{ background: {warning}; }}
QProgressBar[state="danger"]::chunk  {{ background: {danger}; }}
QProgressBar[state="success"]::chunk {{ background: {success}; }}

/* ============================================================
   Tabs
   ============================================================ */
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: {r_lg}px;
    top: -1px;
    background: {bg_card};
}}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    padding: 8px 14px;
    margin-right: 4px;
    background: transparent;
    color: {text_2};
    border: 1px solid transparent;
    border-bottom: 0;
    border-top-left-radius: {r_md}px;
    border-top-right-radius: {r_md}px;
}}
QTabBar::tab:hover    {{ color: {text_1}; }}
QTabBar::tab:selected {{
    background: {bg_card};
    color: {accent};
    border-color: {border};
}}

/* ============================================================
   Status bar
   ============================================================ */
QStatusBar {{
    background: {bg_content};
    border-top: 1px solid {border};
    color: {text_2};
    font-size: 11px;
    min-height: 28px;
}}
QStatusBar QLabel {{ color: {text_2}; padding: 0 6px; background: transparent; }}
QStatusBar::item {{ border: 0; }}
QFrame#StatusSep {{
    background: {border};
    max-width: 1px;
    min-width: 1px;
    max-height: 14px;
}}

/* ============================================================
   ScrollBars
   ============================================================ */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {border_strong};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {text_3}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {border_strong};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {text_3}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: transparent; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ============================================================
   Tooltip
   ============================================================ */
QToolTip {{
    background: {bg_card};
    color: {text_1};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ============================================================
   Splitter
   ============================================================ */
QSplitter::handle             {{ background: {border}; }}
QSplitter::handle:horizontal  {{ width: 1px; }}
QSplitter::handle:vertical    {{ height: 1px; }}

/* ============================================================
   Dialog / Menu / ToolBar / MessageBox
   ============================================================ */
QDialog {{
    background: {bg_card};
    color: {text_1};
    border: 1px solid {border};
}}
QDialog QLabel {{ color: {text_1}; }}
QMessageBox {{ background: {bg_card}; color: {text_1}; }}
QMessageBox QLabel {{ color: {text_1}; }}

QMenu {{
    background: {bg_card};
    color: {text_1};
    border: 1px solid {border};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 14px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background: {bg_row_selected};
    color: {text_1};
}}
QMenu::separator {{
    height: 1px;
    background: {border};
    margin: 4px 6px;
}}
QMenuBar {{
    background: {bg_content};
    color: {text_1};
    border-bottom: 1px solid {border};
}}
QMenuBar::item {{ padding: 6px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {bg_card}; }}
QToolBar {{
    background: {bg_content};
    border: none;
    spacing: 4px;
    padding: 4px;
}}

/* ============================================================
   Status pill labels  (existing setProperty("pill", "...") rule)
   ============================================================ */
QLabel[pill="online"] {{
    color: {success};
    background: {accent_soft};
    border: 1px solid {success};
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 10px;
}}
QLabel[pill="offline"] {{
    color: {text_3};
    background: {bg_card_2};
    border: 1px solid {border};
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 10px;
}}
QLabel[pill="warn"] {{
    color: {warning};
    background: {bg_card_2};
    border: 1px solid {warning};
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 10px;
}}
QLabel[pill="danger"], QLabel[pill="err"] {{
    color: {danger};
    background: {bg_card_2};
    border: 1px solid {danger};
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 10px;
}}
QLabel[pill="accent"] {{
    color: {accent};
    background: {accent_soft};
    border: 1px solid {accent};
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 10px;
}}

/* ============================================================
   Terminal output — palette owned by ui/terminal_palette.py.
   QSS only sets the frame; text colours come from the ANSI palette.
   ============================================================ */
QPlainTextEdit#terminal-output {{
    background: transparent;
    border: none;
    padding: 0;
    selection-background-color: {accent_soft};
}}
QLabel#TerminalStatus {{
    background: {bg_card_2};
    border: 1px solid {border};
    border-radius: {r_md}px;
    padding: 8px 12px;
    color: {text_2};
    font-family: "JetBrains Mono", "Cascadia Code", "Ubuntu Mono", monospace;
}}
QWidget#macroPanel {{
    background: {bg_content};
    border-left: 1px solid {border};
}}

/* ============================================================
   Device Buttons grid
   ============================================================ */
QWidget#deviceButtonsGrid QPushButton {{
    min-height: 56px;
    font-size: 13px;
    background: {bg_card_2};
    border: 1px solid {border};
    border-radius: {r_md}px;
}}
QWidget#deviceButtonsGrid QPushButton:hover {{
    background: {bg_elevated};
    border-color: {border_strong};
}}
QPushButton#ButtonTile {{
    min-height: 64px;
    background: {bg_card_2};
    border: 1px solid {border};
    border-radius: {r_md}px;
    color: {text_1};
    text-align: left;
    padding: 0 14px;
}}
QPushButton#ButtonTile:hover {{
    background: {bg_elevated};
    border-color: {border_strong};
}}

/* ============================================================
   Installer status frame
   ============================================================ */
QFrame#InstallStatus {{
    background: {bg_card_2};
    border: 1px solid {border};
    border-radius: {r_md}px;
    padding: 6px 12px;
    min-height: 32px;
}}
QFrame#InstallStatus[state="idle"]    {{ color: {text_2}; }}
QFrame#InstallStatus[state="running"] {{
    border-color: {accent};
    color: {accent};
}}
QFrame#InstallStatus[state="done"]    {{
    border-color: {success};
    color: {success};
}}
QFrame#InstallStatus[state="error"]   {{
    border-color: {danger};
    color: {danger};
}}
QFrame#InstallStatus QLabel#statusText {{
    font-family: "JetBrains Mono", "Cascadia Code", "Ubuntu Mono", monospace;
    background: transparent;
}}

/* ============================================================
   Logcat command preview  (legacy id kept until module rename in §5.8)
   ============================================================ */
QLabel#LogcatCommandPreview, QLabel#logcatCmdPreview {{
    background: {bg_input};
    border: 1px solid {border_input};
    border-radius: {r_md}px;
    padding: 10px 12px;
    font-family: "JetBrains Mono", "Cascadia Code", "Ubuntu Mono", monospace;
    font-size: 12px;
    color: {text_1};
}}

/* ============================================================
   Apps page toolbar (lifted out of card-header — see handoff §7.7)
   ============================================================ */
QFrame#AppsToolbar {{
    background: {bg_card_2};
    border: none;
    border-bottom: 1px solid {border};
    padding: 10px 14px;
}}
QFrame#ResourceStats {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: {r_lg}px;
    padding: 12px 14px;
}}
QFrame#AppsList, QFrame#AppDetails {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: {r_lg}px;
}}
"""


def render_qss(t: Tokens) -> str:
    """Render the QSS template using ``t`` plus the runtime ``icons_dir`` path."""
    mapping = asdict(t)
    mapping["icons_dir"] = str(ICONS_DIR).replace("\\", "/")
    return QSS_TEMPLATE.format_map(mapping)


__all__ = ["QSS_TEMPLATE", "ICONS_DIR", "render_qss"]
