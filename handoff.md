# ADB_Helper — UI Redesign Handoff (для Claude Code)

> **Стек:** Python 3.12 · PySide6 · Qt 6.
> **Цель:** имплементировать новый дизайн на существующих экранах без изменения функциональности.
> **Референс:** `design.html` (в корне проекта) — открыть и сверять каждый экран попиксельно.
> **Темы:** Light, Dark, Auto (следует за системой через `QStyleHints::colorScheme()` в Qt 6.5+).
> **Платформы:** Windows 11, Ubuntu 22.04+. Должно нативно выглядеть на обеих.

---

## 1. Архитектура стилизации

### 1.1. Базовый стиль приложения

Используем **Fusion** как базовый Qt-стиль (одинаков на Windows и Linux) + наш QSS поверх.

```python
# main.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt

app = QApplication(sys.argv)
app.setStyle("Fusion")               # одинаковая база на Win/Linux
app.setAttribute(Qt.AA_DontUseNativeDialogs, False)  # системные file-dialogs
```

### 1.2. Toolkit темы

Темы — это **(а)** `QPalette` + **(б)** QSS-стрингтемплейт с подстановкой токенов.

```
app/
  theming/
    __init__.py
    tokens.py        # dataclass с цветами/радиусами/spacing
    palette.py       # build_palette(tokens) -> QPalette
    qss.py           # render_qss(tokens) -> str
    theme_manager.py # ThemeManager(QObject): apply(mode: "light"|"dark"|"auto")
    light.py         # LIGHT_TOKENS = Tokens(...)
    dark.py          # DARK_TOKENS  = Tokens(...)
```

### 1.3. Применение темы

```python
class ThemeManager(QObject):
    themeChanged = Signal(str)

    def apply(self, mode: str):
        if mode == "auto":
            scheme = QGuiApplication.styleHints().colorScheme()
            tokens = DARK_TOKENS if scheme == Qt.ColorScheme.Dark else LIGHT_TOKENS
        else:
            tokens = DARK_TOKENS if mode == "dark" else LIGHT_TOKENS

        QApplication.instance().setPalette(build_palette(tokens))
        QApplication.instance().setStyleSheet(render_qss(tokens))
        self.themeChanged.emit(mode)

    # подписаться на смену системной темы для mode="auto"
    def __init__(self):
        super().__init__()
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            lambda _: self.apply("auto") if self._mode == "auto" else None
        )
```

⚠️ **Важно:** QSS-стрингтемплейт перестраивать при каждой смене — не пытайтесь хранить два готовых QSS-строки, пускай один шаблон рендерится с разными токенами.

---

## 2. Design tokens

Скопировать **1:1** из `design.html` (`:root` и `[data-theme="light"]`).

```python
# tokens.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Tokens:
    # Surfaces
    bg_app: str          # окно
    bg_content: str      # сайдбар, статус-бар, заголовки
    bg_card: str         # карточки/секции
    bg_card_2: str       # вложенные карточки, header rows
    bg_elevated: str     # hover/selected fill
    bg_input: str
    bg_row_alt: str      # zebra striping в таблицах
    bg_row_selected: str # выбранная строка
    bg_row_hover: str

    # Borders
    border: str          # обычная линия
    border_strong: str   # выделенная
    border_input: str    # инпуты/кнопки

    # Text
    text_1: str          # основной
    text_2: str          # вторичный
    text_3: str          # подсказки
    text_disabled: str

    # Accent
    accent: str          # teal
    accent_strong: str   # hover
    accent_soft: str     # focus ring / selection bg (с альфой!)
    accent_fg: str       # текст на акцентной кнопке

    # Semantics
    success: str
    warning: str
    danger: str

    # Geometry
    r_sm: int = 4
    r_md: int = 6
    r_lg: int = 8
    sp_2: int = 8
    sp_3: int = 12
    sp_4: int = 16
    input_h: int = 32
    btn_h: int = 32
    row_h: int = 36

DARK = Tokens(
    bg_app="#0d1015", bg_content="#121620", bg_card="#171c26",
    bg_card_2="#1d2330", bg_elevated="#232a39", bg_input="#131822",
    bg_row_alt="rgba(255,255,255,0.025)", bg_row_selected="rgba(45,212,191,0.12)",
    bg_row_hover="rgba(255,255,255,0.05)",
    border="#262d3c", border_strong="#344055", border_input="#2a3243",
    text_1="#e6eaf0", text_2="#a5acba", text_3="#6b7280", text_disabled="#4b5260",
    accent="#2dd4bf", accent_strong="#14b8a6",
    accent_soft="rgba(45,212,191,0.14)", accent_fg="#08201d",
    success="#34d399", warning="#fbbf24", danger="#f87171",
)

LIGHT = Tokens(
    bg_app="#eef0f3", bg_content="#f4f6f8", bg_card="#ffffff",
    bg_card_2="#fafbfc", bg_elevated="#f0f2f5", bg_input="#ffffff",
    bg_row_alt="rgba(0,0,0,0.025)", bg_row_selected="rgba(13,148,136,0.10)",
    bg_row_hover="rgba(0,0,0,0.04)",
    border="#e2e5ea", border_strong="#cbd1d9", border_input="#d4d9e1",
    text_1="#1a1d23", text_2="#5b6371", text_3="#868d99", text_disabled="#b6bcc6",
    accent="#0d9488", accent_strong="#0f766e",
    accent_soft="rgba(13,148,136,0.10)", accent_fg="#ffffff",
    success="#10b981", warning="#d97706", danger="#dc2626",
)
```

### 2.1. QPalette

`QPalette` влияет на нативные виджеты ДО применения QSS — нужно, чтобы `QFileDialog`, `QMessageBox`, скроллбары на Win11 не выпадали из темы.

```python
def build_palette(t: Tokens) -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window,         QColor(t.bg_app))
    p.setColor(QPalette.WindowText,     QColor(t.text_1))
    p.setColor(QPalette.Base,           QColor(t.bg_input))
    p.setColor(QPalette.AlternateBase,  QColor(t.bg_card_2))
    p.setColor(QPalette.Text,           QColor(t.text_1))
    p.setColor(QPalette.Button,         QColor(t.bg_card_2))
    p.setColor(QPalette.ButtonText,     QColor(t.text_1))
    p.setColor(QPalette.Highlight,      QColor(t.accent))
    p.setColor(QPalette.HighlightedText, QColor(t.accent_fg))
    p.setColor(QPalette.ToolTipBase,    QColor(t.bg_card))
    p.setColor(QPalette.ToolTipText,    QColor(t.text_1))
    p.setColor(QPalette.Disabled, QPalette.Text,       QColor(t.text_disabled))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(t.text_disabled))
    p.setColor(QPalette.Link,           QColor(t.accent))
    return p
```

---

## 3. QSS — шаблон

Полный шаблон ниже. Передавать токены через `str.format_map(asdict(tokens))` или f-строку.

```python
QSS = """
* {{
  outline: 0;
  font-family: "Segoe UI", "Ubuntu", "Inter", -apple-system, sans-serif;
  font-size: 13px;
  color: {text_1};
}}

QMainWindow, QWidget#central {{
  background: {bg_app};
}}

/* ---- Сайдбар ---- */
QFrame#Sidebar {{
  background: {bg_content};
  border-right: 1px solid {border};
}}
QPushButton#NavItem {{
  text-align: left;
  padding: 8px 10px;
  border: 0;
  border-radius: {r_md}px;
  color: {text_2};
  background: transparent;
}}
QPushButton#NavItem:hover {{
  background: rgba(255,255,255,0.04);
  color: {text_1};
}}
QPushButton#NavItem:checked {{
  background: {accent_soft};
  color: {accent};
}}

/* ---- Карточки / секции ---- */
QFrame[role="card"] {{
  background: {bg_card};
  border: 1px solid {border};
  border-radius: {r_lg}px;
}}
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
QLabel[role="hint"] {{
  color: {text_2};
  font-size: 12px;
}}

/* ---- Кнопки ---- */
QPushButton {{
  min-height: {btn_h}px;
  padding: 0 14px;
  background: {bg_card_2};
  border: 1px solid {border_input};
  border-radius: {r_md}px;
  color: {text_1};
}}
QPushButton:hover  {{ background: {bg_elevated}; }}
QPushButton:pressed{{ background: {bg_input}; }}
QPushButton:disabled {{
  color: {text_disabled};
  background: {bg_card_2};
  border-color: {border};
}}
QPushButton[variant="primary"] {{
  background: {accent};
  color: {accent_fg};
  border-color: transparent;
  font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background: {accent_strong}; }}
QPushButton[variant="primary"]:disabled {{
  background: {bg_card_2};
  color: {text_disabled};
  border: 1px solid {border};
}}
QPushButton[variant="danger"]   {{ color: {danger}; }}
QPushButton[variant="danger"]:hover {{ background: rgba(248,113,113,0.10); }}
QPushButton[variant="ghost"] {{
  background: transparent; border-color: transparent; color: {text_2};
}}
QPushButton[variant="ghost"]:hover {{
  background: rgba(255,255,255,0.04); color: {text_1};
}}

/* ---- Инпуты ---- */
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit, QDateEdit, QTimeEdit {{
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
QLineEdit:focus, QSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
  border: 1px solid {accent};
}}
QLineEdit:disabled {{ color: {text_disabled}; background: {bg_card_2}; }}
QLineEdit[role="search"] {{
  padding-left: 30px;            /* место под лупу-иконку (через QAction addAction) */
}}

/* ---- ComboBox dropdown ---- */
QComboBox::drop-down {{ border: 0; width: 22px; }}
QComboBox::down-arrow {{ image: url(:/icons/chevron-down.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
  background: {bg_card};
  border: 1px solid {border};
  border-radius: {r_md}px;
  selection-background-color: {bg_row_selected};
  selection-color: {text_1};
  padding: 4px;
  outline: 0;
}}

/* ---- Таблицы ---- */
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
QTableView, QTableWidget, QTreeView {{
  background: {bg_card};
  alternate-background-color: {bg_card_2};   /* zebra */
  gridline-color: {border};
  border: 0;
  selection-background-color: {bg_row_selected};
  selection-color: {text_1};
}}
QTableView::item, QTreeView::item {{
  padding: 8px 12px;
  border-bottom: 1px solid {border};
  color: {text_1};
}}
QTableView::item:hover {{ background: {bg_row_hover}; }}
QTableView::item:selected {{
  background: {bg_row_selected};
  color: {text_1};
}}
QTableCornerButton::section {{
  background: {bg_card_2};
  border: 0;
  border-bottom: 1px solid {border};
}}

/* ---- Чекбоксы (фикс невидимости в Dark) ---- */
QCheckBox {{
  spacing: 8px;
  color: {text_1};
}}
QCheckBox::indicator {{
  width: 16px; height: 16px;
  border: 1.5px solid {border_strong};
  background: {bg_input};
  border-radius: 3px;
}}
QCheckBox::indicator:hover    {{ border-color: {accent}; }}
QCheckBox::indicator:checked  {{
  border: 1.5px solid {accent};
  background: {accent};
  image: url(:/icons/check.svg);
}}
QCheckBox::indicator:disabled {{
  border-color: {border};
  background: {bg_card_2};
}}

/* ---- Radio ---- */
QRadioButton::indicator {{
  width: 16px; height: 16px;
  border: 1.5px solid {border_strong};
  background: {bg_input};
  border-radius: 8px;
}}
QRadioButton::indicator:checked {{
  border: 4px solid {accent};
  background: {bg_input};
}}

/* ---- Progress bar ---- */
QProgressBar {{
  background: {bg_elevated};
  border: 0;
  border-radius: 999px;
  text-align: center;
  color: {text_2};
  height: 6px;
}}
QProgressBar::chunk {{
  background: {accent};
  border-radius: 999px;
}}

/* ---- Tabs (если используется QTabWidget) ---- */
QTabWidget::pane {{ border: 1px solid {border}; border-radius: {r_lg}px; top: -1px; }}
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
QTabBar::tab:selected {{ background: {bg_card}; color: {accent}; border-color: {border}; }}

/* ---- Status bar ---- */
QStatusBar {{
  background: {bg_content};
  border-top: 1px solid {border};
  color: {text_2};
  font-size: 11px;
}}
QStatusBar QLabel    {{ color: {text_2}; padding: 0 6px; }}
QStatusBar::item     {{ border: 0; }}
QFrame#StatusSep     {{ background: {border}; max-width: 1px; min-width: 1px; max-height: 14px; }}

/* ---- ScrollBars ---- */
QScrollBar:vertical {{
  background: transparent; width: 10px; margin: 4px;
}}
QScrollBar::handle:vertical {{
  background: {border_strong}; border-radius: 4px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {text_3}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 4px; }}
QScrollBar::handle:horizontal {{
  background: {border_strong}; border-radius: 4px; min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---- Tooltip ---- */
QToolTip {{
  background: {bg_card};
  color: {text_1};
  border: 1px solid {border};
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
}}

/* ---- Group box (вместо рамки используем секцию с заголовком) ---- */
QGroupBox {{ border: 0; margin-top: 0; padding-top: 0; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 0; padding: 0 0 6px; color: {text_2}; }}

/* ---- Terminal output ---- */
QPlainTextEdit#TerminalOutput {{
  background: #0a0e15;
  color: #d8e0ea;
  font-family: "JetBrains Mono", "Cascadia Code", "Ubuntu Mono", monospace;
  border: 1px solid {border};
  border-radius: {r_md}px;
  padding: 12px;
}}
QLabel#TerminalStatus {{
  background: {bg_card_2};
  border: 1px solid {border};
  border-radius: {r_md}px;
  padding: 8px 12px;
  color: {text_2};
  font-family: "JetBrains Mono", monospace;
}}
"""
```

> **Кастомные кнопки** разрешаются через property: `btn.setProperty("variant", "primary")` → `btn.style().unpolish(btn); btn.style().polish(btn)` после смены темы.

---

## 4. Структура окна

```
QMainWindow
└── QWidget#central
    └── QHBoxLayout (margin=0)
        ├── Sidebar (QFrame#Sidebar, fixedWidth=220)
        │   ├── Brand (logo + name + ver)
        │   ├── QButtonGroup (exclusive) из NavItem (QPushButton checkable)
        │   └── stretch (spacer)
        └── QFrame (main column)
            └── QVBoxLayout
                ├── QStackedWidget (страницы)
                └── StatusBar (QStatusBar + кастомные QLabel)
```

> **Нет переключателя тем в титлбаре** и **нет footer-meta** внизу сайдбара — тема переключается исключительно из **Settings → Theme** (`QComboBox`, подключённый к `ThemeManager.apply()`).

### 4.1. Сайдбар как `QButtonGroup`

```python
class Sidebar(QFrame):
    pageRequested = Signal(int)

    def __init__(self):
        super().__init__(objectName="Sidebar")
        self.setFixedWidth(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12); layout.setSpacing(2)
        layout.addWidget(self._brand())

        self.group = QButtonGroup(self); self.group.setExclusive(True)
        for idx, (icon, label) in enumerate(NAV_ITEMS):
            btn = QPushButton(label, objectName="NavItem", checkable=True)
            btn.setIcon(QIcon(icon))
            btn.setIconSize(QSize(18, 18))
            btn.setCheckable(True)
            self.group.addButton(btn, idx)
            layout.addWidget(btn)

        layout.addStretch(1)   # прижимает nav-итемы кверху; футер убран
        self.group.idClicked.connect(self.pageRequested)
        self.group.button(0).setChecked(True)
```

### 4.2. Адаптивный сайдбар (брейкпоинт)

На экранах ≥1700px шире — `setFixedWidth(256)`:

```python
def resizeEvent(self, e):
    super().resizeEvent(e)
    w = 256 if self.width() >= 1700 else 220
    self.sidebar.setFixedWidth(w)
```

---

## 5. Глобальные правила компоновки

1. **Никаких фиксированных pixel-широт у инпутов/кнопок** в основной поток, кроме маленьких (порт, PIN). Используем `QHBoxLayout` + `addStretch()` для размещения кнопки справа.
2. **Все таблицы**: первая строка — `QHeaderView::ResizeMode.Stretch` для семантически главной колонки (Serial, Package name, File), остальные — `ResizeToContents` или `Interactive`. Для колонок с кнопками — `ResizeToContents` + `setMinimumSectionSize(120)`.
3. **Строки-карточки** (`role="card"`) сами «прокачивают» внутренний padding через layout 14px, а не через QSS-`padding` (Qt QSS не учитывает padding в `sizeHint` контейнеров — лучше через `setContentsMargins`).
4. **Радиусы**: 8px карточки, 6px кнопки/инпуты, 4px чекбоксы, 999px — pills/progress.
5. **Шрифт**: системный стек. На Linux `QFont` по умолчанию даёт Ubuntu/DejaVu — оставить. Размер 13px (~10pt). Заголовок секции 11px UPPERCASE letter-spacing 1px (QFont `setLetterSpacing(QFont.AbsoluteSpacing, 1.0)`).

---

## 6. Конкретные фиксы для текущих багов

### 6.1. Раздел Connections — поле `Connection port` в таблице обрезается

**Причина:** ширина колонки фиксирована по содержимому header'а, а `QLineEdit` шире.

**Фикс:**

```python
view = self.pairedTable
view.setItemDelegateForColumn(COL_PORT, PortEditDelegate(view))  # либо persistent editor
view.horizontalHeader().setSectionResizeMode(COL_PORT, QHeaderView.ResizeMode.Interactive)
view.horizontalHeader().resizeSection(COL_PORT, 140)             # min 140px
view.verticalHeader().setDefaultSectionSize(40)                  # высота строки 40, чтобы инпут 28px вписался
```

И в QSS — `.input.small { height: 28px; }`. Инпут не должен «вылезать» выше высоты строки.

### 6.2. Раздел Settings → Installed Dependencies — кнопки Action перекрываются

**Причина:** колонка слишком узкая для `QPushButton` с padding 14px.

**Фикс:**

```python
hdr = self.depsTable.horizontalHeader()
hdr.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.Fixed)
hdr.resizeSection(COL_ACTION, 130)
self.depsTable.setColumnWidth(COL_ACTION, 130)
# кнопка
btn = QPushButton("Install"); btn.setProperty("variant", "primary")
btn.setMinimumSize(0, 26); btn.setMaximumHeight(26)               # small variant
self.depsTable.setCellWidget(row, COL_ACTION, _wrap_center(btn))  # центрируем в QWidget-wrapper
```

`_wrap_center` — обёртка с QHBoxLayout(contentsMargins=4) и stretch по краям.

### 6.3. Logcat — белая шапка в темной теме

**Причина:** виджет (вероятно `QPlainTextEdit` или `QFrame`) забит inline-палитрой (`setStyleSheet("background:white")` или захардкоженной палитрой). Перебивает тему.

**Фикс:** убрать все inline `setStyleSheet`/`palette` у этого блока. Стилизация только через объектные имена в QSS. Сделать его `QLabel#LogcatCommandPreview` и положить в `role="card"`:

```python
preview = QLabel(objectName="LogcatCommandPreview")
preview.setTextFormat(Qt.RichText)
preview.setWordWrap(True)
preview.setText("$ adb -s … logcat -d > /home/…/logcat_…txt")
preview.setStyleSheet("")  # никаких inline-стилей
```

QSS:

```css
QLabel#LogcatCommandPreview {
  background: {bg_input};
  border: 1px solid {border_input};
  border-radius: {r_md}px;
  padding: 10px 12px;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  color: {text_1};
}
```

### 6.4. Apps — невидимые чекбоксы в темной теме

**Причина:** Qt-default индикатор чекбокса в `QTableView` берет иконку из системной темы, она не видна на тёмном фоне. Чередующиеся `alternate-background-color` ещё сильнее «утапливают» белый чекбокс.

**Фикс:** **(а)** в QSS прописать `QCheckBox::indicator` + `QTableView::indicator` явно с нашими цветами (см. блок выше). **(б)** Если первая колонка — это `Qt.ItemIsUserCheckable` (а не `QCheckBox` через `setIndexWidget`), стилизуй индикатор в таблице:

```css
QTableView::indicator {
  width: 16px; height: 16px;
  border: 1.5px solid {border_strong};
  background: {bg_input};
  border-radius: 3px;
}
QTableView::indicator:checked {
  background: {accent};
  border: 1.5px solid {accent};
  image: url(:/icons/check.svg);
}
```

Иконка `check.svg` — белая галка (`stroke="{accent_fg}"`), для светлой темы — белая, для тёмной — почти-чёрная (`#08201d`). Можно держать **две версии** в `:/icons/light/check.svg` и `:/icons/dark/check.svg` и подменять путь в шаблоне.

---

## 7. Постранично

### 7.1. Connections

**Layout:** **2×2 сетка**. Карточки в одной строке всегда одной высоты (по самой высокой в ряду).

```
┌──────────────────┬──────────────────┐
│ Wi-Fi Pairing    │ Wi-Fi Connection │   row 1 (auto, equal-height)
│ (Android 11+)    │ (Legacy)         │
├──────────────────┼──────────────────┤
│ Connected        │ Paired           │   row 2 (auto, equal-height)
│ Devices          │ Devices          │
└──────────────────┴──────────────────┘
```

```python
grid = QGridLayout()
grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
grid.setHorizontalSpacing(16); grid.setVerticalSpacing(16)

grid.addWidget(self.wifiPairCard,    0, 0)    # TL
grid.addWidget(self.wifiConnectCard, 0, 1)    # TR
grid.addWidget(self.connectedCard,   1, 0)    # BL
grid.addWidget(self.pairedCard,      1, 1)    # BR
```

В `QGridLayout` ячейки одного ряда растягиваются по высоте самой высокой (аналог CSS `align-items: stretch` + `grid-template-rows: auto auto`).

**Форма Pairing** — PIN рядом с Pairing Port на одной строке:

```python
row = QHBoxLayout()
row.setSpacing(10)
row.addWidget(self.pairPortInput, 0, Qt.AlignVCenter)   # QLineEdit, fixedWidth=130
row.addSpacing(6)
row.addWidget(QLabel("PIN"), 0, Qt.AlignVCenter)
row.addWidget(self.pinInput, 0, Qt.AlignVCenter)        # QLineEdit, fixedWidth=130
row.addStretch(1)
row.addWidget(self.pairBtn)                             # variant=primary
self.pairForm.addRow("Pairing Port:", row)              # QFormLayout
```

**Pair / Connect** кнопки — `variant=primary`, прижаты справа через `addStretch()`.

**Колонка `Connection port`** в таблице Paired Devices: `QHeaderView.ResizeMode.Interactive`, ширина 140px, высота строки 40px чтобы `QLineEdit` 28px не обрезался (см. § 6.1).

**Пин-input** — placeholder `"123456"`, `setMaxLength(6)`, валидатор `QRegularExpressionValidator(QRegularExpression("\\d{0,6}"))`.

### 7.2. Terminal

- Главный layout: `QHBoxLayout` → слева `terminalCard` (stretch=1), справа `macrosCard` (fixedWidth=260).
- `QPlainTextEdit#TerminalOutput` + под ним `QFrame#TerminalPrompt` (QHBoxLayout: prefix `QLabel` `192.168.1.200:40787:/ $` + `QLineEdit` без рамки).
- Шапка `QLabel#TerminalStatus` со статусом в card-header.
- **Не использовать** `QTextEdit` для вывода — `QPlainTextEdit` гораздо быстрее на больших логах.

### 7.3. Installer

- 4 карточки сверху-вниз: Files / Targets / Installation / Results.
- **Никакого локального скролла в таблицах.** Каждая таблица растёт вместе с содержимым, вся страница прокручивается через внешний `QScrollArea` (или обёртку `QStackedWidget` страницы).
- **Files**: пустое состояние оставляет место под ~2 строки (`setMinimumHeight(96)`). При наполнении — растягивается по реальным строкам.
- **Results**: пустое состояние ~3 строки (`setMinimumHeight(132)`).
- Размер таблиц по содержимому: `view.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)` + `view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)`.
- В `Installation` карточке layout (`QVBoxLayout`, gap 10):
  - Ряд 1: `QHBoxLayout` → `[Install] [Cancel] [QProgressBar=stretch] [QLabel "0%"]`.
  - Ряд 2: **строка статуса** — `QFrame#InstallStatus` (внутри `[QLabel#dot] [QLabel#text]`). Состояния через `setProperty("state", "idle|running|done|error")`. Примеры текстов:
    - `idle`: «Idle — add files and select a target device to begin.»
    - `running`: «Installing 2 of 5 — com.example.app on SM-A346E…»
    - `done`: «Installed 5 of 5 · 0 errors»
    - `error`: «Install failed — see Results»
- Таблица файлов: `setSelectionBehavior(SelectRows)`, `setSelectionMode(ExtendedSelection)`. Drop-target — на самой `QTableView` (`acceptDrops=True`, переопределить `dragEnterEvent` / `dropEvent`).

QSS для статус-строки:

```css
QFrame#InstallStatus {
  background: {bg_card_2};
  border: 1px solid {border};
  border-radius: {r_md}px;
  padding: 6px 12px;
  min-height: 32px;
}
QFrame#InstallStatus[state="running"] { border-color: {accent_soft}; color: {accent}; }
QFrame#InstallStatus[state="error"]   { color: {danger}; }
QFrame#InstallStatus QLabel#text { font-family: "JetBrains Mono", monospace; }
```

### 7.4. Scrcpy

- Двухколоночная сетка: Launch options (form) слева, Recent launches (table) справа. Соотношение 1 : 1.2.
- Кнопка Launch — в `page-actions` (правый верх) **и** дублировать внизу формы (опционально).
- Чекбоксы вертикальные → переделать в горизонтальную линию `Stay awake · Show touches · Turn screen off` (см. дизайн).

### 7.5. Device Buttons

- `QGridLayout` 4 колонки × 3 ряда, `setSpacing(10)`, кнопки `QPushButton` с `objectName="ButtonTile"`, высота 64px, equal stretch (`grid.setColumnStretch(i, 1)`).
- На ширине <1300 — сделать 3 колонки.
- Иконка слева от текста, цвет иконки = `accent`. Иконки — `QSvgRenderer` или ресурсные .svg.

### 7.6. Device Info

- 2×N сетка (минимум 2 колонки): Device, System, CPU, GPU, Memory, Display и т.д.
- Контент — `QFormLayout` с `setLabelAlignment(Qt.AlignLeft)`, `setFormAlignment(Qt.AlignLeft|Qt.AlignTop)`, лейблы шириной 180px.
- Значения — `QLabel` с `setTextInteractionFlags(Qt.TextSelectableByMouse)` и моноширинным шрифтом для технических полей.

### 7.7. Apps — split-view

```
Apps page
└── QVBoxLayout
    ├── QFrame#ResourceStats  (RAM bar | Storage bar | Refresh) — 1 ряд
    └── QSplitter(Horizontal)
        ├── QFrame#AppsList   (~58%)
        │   ├── card-header     («Packages» label + count hint)
        │   ├── toolbar-row    (search + 2 чекбокса)   ← ОТДЕЛЬНО от card-h!
        │   ├── QTableView
        │   └── Bulk actions footer (Delete/Disable/Enable/Export + counter)
        └── QFrame#AppDetails (~42%)
            ├── card-header     («App details» label + open-link btn)
            ├── meta (icon + pkg name + badges; QFormLayout: 8 строк)
            └── actions footer (Open / Force-stop / Clear data / Uninstall)
```

- **Toolbar вынесён из card-header** в отдельный `QFrame#AppsToolbar` ниже card-header с подложкой `bg_card_2`. Нужно для того чтобы высоты card-header'ов левой и правой карточек были равны (иначе инпуты в хедере «раздувают» левый и split рассинхронизировывается).

```css
QFrame#AppsToolbar {
  background: {bg_card_2};
  border-bottom: 1px solid {border};
  padding: 10px 14px;
}
```

- Splitter: `setStretchFactor(0, 1.4)`, `setStretchFactor(1, 1)`, `setChildrenCollapsible(False)`, `setHandleWidth(8)`.
- На узких экранах (<800px) — детальная панель скрывается и открывается по выбору строки (`splitter.widget(1).setVisible(False)` + кнопка-возврат).
- Иконка приложения: `QIcon` из APK через `aapt` (если есть pre-cached) или `app-ico`-placeholder из первых 2 букв пакета.
- Permissions — отдельная вкладка/линк, можно скрыть за `QPushButton "View permissions →"` → диалог.

### 7.8. Logcat

- 2-колоночная сетка (всегда две колонки): основная (Capture + Recent exports) — 1.5 width, справа Configuration — 0.9 width.
- Превью команды — `QLabel#LogcatCommandPreview` (см. фикс 6.3). Большая команда разбивается на две строки через ` \` в конце первой и hanging-indent `padding-left: 2ch` на второй. Путь подсвечен цветом `accent`, остальное — `text_1`.
- Большая первичная кнопка `⇣ Export logcat` `variant=primary`, secondary `Open folder` справа от неё.
- Recent exports — без локального скролла (аналогично Installer): растягивается в высоту, внешняя прокрутка страницы.

### 7.9. Settings

- 3 секции: About, Installed dependencies, General.
- About — мини app-icon (40px) + название + версия + кнопка `Check for updates`.
- Dependencies — таблица с **видимыми бейджами статуса** (`Missing` / `Up to date` / `Update available`) и кнопкой действия в каждой строке (см. § 6.2 про фикс перекрытия).
- General — `QFormLayout`. Поля Theme и Log level — `QComboBox`, остальные — `QLineEdit + QPushButton "Browse…"` в `QHBoxLayout`.
- **Theme подключен к `ThemeManager.apply()`**: 3 варианта — «Auto (follow system)», «Dark», «Light». Сохранять выбор в `QSettings`, восстанавливать при старте приложения.

---

## 8. Status bar

Кастомный тонкий `QStatusBar` с виджетами:

```
[● green]  SM-A346E · 192.168.1.200:40787 | Transport: Wi-Fi | Android 16 · API 36
                                                          [🔋 78%] | ADB: running
```

- Левый блок (`addWidget`) — устройство + IP + transport + Android version.
- Правый блок (`addPermanentWidget`) — индикаторы: battery (svg + %), ADB-daemon status (`running` зелёный / `stopped` красный).
- **«Last refresh» в статус-баре НЕ показываем** — при необходимости время последнего обновления выносится в tooltip кнопки Refresh на соответствующей странице.
- Разделители — `QFrame#StatusSep` (width=1, fixedHeight=14, цвет border).
- Точка-индикатор статуса — кастомный `QLabel` с `paintEvent` (заливка `success`/`warning`/`danger` радиусом 4px).

Обновление индикаторов — через сигналы из core-сервиса:
```python
device_service.statusChanged.connect(self.statusBar_.setDeviceStatus)
device_service.batteryChanged.connect(self.statusBar_.setBattery)
adb_service.daemonStateChanged.connect(self.statusBar_.setAdbState)
```

---

## 9. DPI и масштабирование

- Qt 6 включает High-DPI scaling по умолчанию — **не** трогать `AA_EnableHighDpiScaling` (deprecated).
- В QSS все размеры — в px. Они масштабируются через DPR.
- Иконки — **SVG** (`QIcon(":/icons/foo.svg")`). Не использовать .png.
- На 32″ 4K не нужно «растягивать» компоненты — сетка из коробки даст больше воздуха через `addStretch`. Гриды и сплит-вью всегда 2-колоночные при нормальной рабочей ширине (сворачиваются в 1 колонку только при ширине <720px — это аварийный fallback). Брейкпоинты:
  - **≥1700px:** Sidebar 256px (вместо 220), карточки получают max-width 1600 (центрировать через `addStretch` слева и справа в page-layout, чтобы не растягивались бесконечно на 4K).
- Device Buttons — 4 колонки всегда (`QGridLayout` 4×3, equal stretch). При экстремально узком экране можно свернуть до 2 через `resizeEvent`.

```python
class Page(QWidget):
    def __init__(self):
        outer = QHBoxLayout(self)
        outer.addStretch(0)
        self.inner = QWidget(); self.inner.setMaximumWidth(1600)
        outer.addWidget(self.inner, 1)
        outer.addStretch(0)
        # outer stretches: 0 / 1 / 0 — inner растягивается до своего max
```

---

## 10. Шрифт

Не задавать в QSS конкретное семейство там, где можно положиться на систему — у нас `font-family: "Segoe UI", "Ubuntu", "Inter", ...`. На Linux Qt подберёт Ubuntu, на Windows — Segoe UI, на macOS — system-ui.

Размеры:
- base — 13px
- caption / hint — 12px
- section label — 11px UPPERCASE letter-spacing=1
- page title — 16px / 600

Моноширинный шрифт (терминал, технические поля, числа в таблицах):
`"JetBrains Mono", "Cascadia Code", "Ubuntu Mono", "Menlo", Consolas, monospace`

---

## 11. Ресурсы (.qrc)

```
resources/
  icons/
    nav-connections.svg
    nav-terminal.svg
    nav-installer.svg
    nav-scrcpy.svg
    nav-buttons.svg
    nav-info.svg
    nav-apps.svg
    nav-logcat.svg
    nav-settings.svg
    check.svg          # белая галка
    check-dark.svg     # тёмная галка (для светлой акцентной заливки в Light)
    chevron-down.svg
    battery.svg
```

Все SVG со `stroke="currentColor"`, чтобы перекрашивались через `QIcon` + `QPainter` или просто использовались на акцентном фоне (`color: var(--accent-fg)`).

---

## 12. Чек-лист имплементации

- [ ] Подключить Fusion-стиль и `ThemeManager`.
- [ ] Создать `tokens.py`, `palette.py`, `qss.py` (см. секции 2–3).
- [ ] Сайдбар на `QButtonGroup` + `objectName="NavItem"`. **Без футер-meta** внизу.
- [ ] **Без переключателя тем в титлбаре** — тема меняется из Settings → Theme (`QComboBox`).
- [ ] StatusBar с индикаторами: устройство + IP / transport / Android / battery / ADB-daemon. **Без «Last refresh»**.
- [ ] Стилизовать `QCheckBox::indicator` и `QTableView::indicator` (фикс 6.4).
- [ ] `QHeaderView`: главная колонка — `Stretch`, остальные — `Interactive` с мин-ширинами.
- [ ] **Connections**: 2×2 `QGridLayout` (Pairing TL, Legacy TR, Connected BL, Paired BR). PIN рядом с Pairing Port на одной строке (§ 7.1). Колонка paired-port: высота строки 40px, `QLineEdit` 28px. PIN placeholder «123456».
- [ ] **Installer**: без локального скролла в таблицах, min-height пустых Files=96 / Results=132. Строка статуса в Installation (`QFrame#InstallStatus`, § 7.3).
- [ ] **Logcat**: убрать inline-стили, `QLabel#LogcatCommandPreview` с hanging-indent.
- [ ] **Apps**: `QSplitter` с toolbar-строкой НИЖЕ card-header (отдельный `QFrame#AppsToolbar`). Правая панель обновляется через `currentRowChanged`.
- [ ] **Settings → Dependencies**: колонка `Action` фикс 130px, кнопки `small variant`.
- [ ] **Settings → Theme**: подключить к `ThemeManager.apply()` с `QSettings`-persistence.
- [ ] Все SVG иконки в `.qrc`.
- [ ] Светлая/Тёмная/Авто переключаются и применяются ко всем виджетам (включая открытые диалоги).
- [ ] Шрифт — системный, размеры из секции 10.
- [ ] Проверить на 1920×1080 @100%/125% и 3840×2160 @150%/200% в обеих темах.

---

## 13. Известные подводные камни Qt 6

1. **QSS не каскадирует через child-widget'ы**, на которых уже задан `setStyleSheet("...")` — он перебивает родительский. Не задавай inline-стили из кода, всё через глобальный QSS + property selectors.
2. **`alternate-background-color` в `QTableView`** — только если `setAlternatingRowColors(True)`.
3. **`QHeaderView` не реагирует** на `:hover` через QSS, если включена sortable сортировка — рисуй иконку через `QHeaderView::section { padding-right: 16px; }`.
4. **Качество SVG-иконок** через `QIcon` — выставь `QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)` (хотя в Qt 6 это уже по умолчанию).
5. **`QFileDialog`** должен использовать системный — `QFileDialog.getOpenFileName(...)` без флага `DontUseNativeDialog`. Тогда он берёт системную тему ОС, не нашу. Это **намеренно** — нативно выглядит лучше.
6. **`QDarkStyle` или `qt-material`** не использовать — они конфликтуют с нашими токенами. Только наша своя система.

---

## 14. Файлы на выходе

- `app/theming/` — модуль тем (`tokens.py`, `palette.py`, `qss.py`, `theme_manager.py`).
- `app/ui/widgets/sidebar.py` — Sidebar.
- `app/ui/widgets/status_bar.py` — кастомный StatusBar.
- `app/ui/pages/*.py` — 9 страниц.
- `resources/icons/*.svg` + `resources.qrc`.
- В `main.py`: `app.setStyle("Fusion")` + `ThemeManager().apply("auto")`.
