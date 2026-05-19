# ADB_Helper Redesign — Implementation Guide

## Overview
This redesign modernizes ADB_Helper with a **dev-tool aesthetic** (clean, high-contrast, no-shadow), adaptive density (compact/comfortable/spacious), and platform-aware layout (Windows 11 & Ubuntu 22+).

**Key improvement:** Text 13px (vs 12px), fixed window height 100vh, sidebar auto-collapses at <1100px.

---

## Color System

### Dark Theme (default)
```
bg:             #05070a  (very dark, almost black)
bg-elev:        #0d1117  (titlebar, sidebar, headers)
surface:        #181d24  (card bodies, main surfaces)
surface-2:      #1c2128  (buttons, hover backgrounds)
surface-3:      #232932  (scrollbar, secondary elements)
border:         #1f242b  (card borders, section dividers)
border-strong:  #2a3038  (input borders, strong dividers)
text-primary:   #e6e8eb  (main text, labels)
text-secondary: #9aa3ad  (secondary text, timestamps)
text-muted:     #5f6873  (field labels, captions)
accent:         #2ec5c5  (teal — primary actions, focus rings)
success:        #2eb872  (online indicator)
warn:           #d4a017  (warnings, device offline)
danger:         #d94c3a  (errors, destructive actions)
```

### Light Theme
```
bg:             #e6e9ee  (light gray background)
bg-elev:        #ffffff  (white headers, titlebar)
surface:        #ffffff  (white card bodies)
surface-2:      #f1f3f5  (light gray buttons, hover)
surface-3:      #e7eaee  (light dividers)
border:         #e3e6ea  (light borders)
border-strong:  #d2d7dd  (darker borders for inputs)
text-primary:   #14181c  (almost black text)
text-secondary: #4a525b  (dark gray secondary)
text-muted:     #8993a0  (lighter gray for captions)
accent:         #2ec5c5  (same teal)
(success/warn/danger same as dark)
```

---

## Typography

### Font Families
- **Sans (UI):** Geist → Segoe UI → system-ui → sans-serif
- **Mono (terminal, code):** JetBrains Mono (Linux) / Cascadia Code (Windows) → ui-monospace

### Font Sizes
```
text:       13px  (base UI text, labels — UP FROM 12px)
text-sm:    12px  (buttons, inputs, table cells)
text-xs:    11px  (status bar, breadcrumbs, captions)
module-h1:  15px  (screen title)
card-head:  12px uppercase (card section headers)
terminal:   13pt  (monospace, JetBrains/Cascadia)
```

---

## Layout & Spacing

### Window
- **Default:** 1280×800 px
- **Minimum:** 960×600 px
- **Height:** Fixed 100vh (content area scrolls internally)

### Sidebar
- **Expanded:** 220px wide
- **Collapsed:** 64px (icon-only)
- **Auto-collapse threshold:** <1100px window width
- **Collapsed appearance:** Icons + tooltips on hover

### Spacing Scale (default density)
```
pad-x:    18px  (module body left/right padding)
pad-y:    14px  (module body top/bottom)
gap:      14px  (grid gaps between panels)
gap-sm:   8px   (small inline gaps, button groups)
row-h:    36px  (table row height)
radius:   6px   (cards, modals)
radius-sm: 4px  (buttons, inputs, tags)
```

**Compact density:** All values reduced by ~20% (pad-x→14px, gap→10px, row-h→30px)

---

## Visual Style

### Borders & Shadows
- **No box-shadows.** Visual hierarchy via:
  - 1px solid borders (color: var(--border))
  - Contrast between surface tones
  - Accent color for focus/active states
- **Border radius:** 6px cards, 4px buttons/inputs
- **Active states:** Accent background + no border change

### Component Styling
```css
/* Cards/Groups */
QGroupBox {
  border: 1px solid var(--border);
  border-radius: 6px;
  background-color: var(--surface);
  padding: 14px;
}

/* Buttons */
QPushButton {
  min-height: 44px;
  padding: 10px 16px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background-color: var(--surface-2);
  color: var(--text-primary);
}
QPushButton:hover {
  background-color: var(--surface-3);
}
QPushButton[variant="primary"] {
  background-color: var(--accent);
  color: #000;
  border: none;
}

/* Inputs */
QLineEdit, QTextEdit {
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  background-color: var(--surface);
  color: var(--text-primary);
}
QLineEdit:focus {
  border: 1px solid var(--accent);
}

/* Tables */
QTableView {
  border: 1px solid var(--border);
  border-radius: 6px;
  gridline-color: var(--border);
}
QHeaderView::section {
  background-color: var(--bg-elev);
  border: none;
  border-bottom: 1px solid var(--border);
}
QTableView::item:selected {
  background-color: var(--accent-faint);
  color: var(--text-primary);
}
```

---

## Implementation Steps

### 1. Update QSS Files
Edit `src/adb_helper/ui/qss/dark.qss` and `light.qss`:
- Replace all color values with hex codes from **DESIGN_TOKENS.json**
- Use CSS variables: `var(--bg)`, `var(--surface)`, `var(--accent)`, etc.
- Remove any `box-shadow` properties; use `border` instead
- Set button min-height to 44px

**Example dark.qss:**
```css
* {
  --bg: #05070a;
  --bg-elev: #0d1117;
  --surface: #181d24;
  --surface-2: #1c2128;
  --border: #1f242b;
  --text-primary: #e6e8eb;
  --text-secondary: #9aa3ad;
  --accent: #2ec5c5;
}

QWidget {
  background-color: var(--bg);
  color: var(--text-primary);
  font-size: 13px;
}

QGroupBox {
  border: 1px solid var(--border);
  border-radius: 6px;
  background-color: var(--surface);
  padding: 14px;
}

/* ... etc */
```

### 2. Update Main Window (main_window.py)
```python
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADB_Helper")
        
        # Fixed window size
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(960, 600)
        
        # Create scrollable content area
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: var(--bg); }")
        self.scroll.setWidgetResizable(True)
        
        self.central = QWidget()  # Your main content widget
        self.scroll.setWidget(self.central)
        self.setCentralWidget(self.scroll)
        
        # Track window resize for sidebar auto-collapse
        self.resize_timer = QTimer()
        self.resize_timer.timeout.connect(self._check_sidebar_collapse)
    
    def resizeEvent(self, event):
        """Auto-collapse sidebar when window < 1100px"""
        self.resize_timer.start(100)
        super().resizeEvent(event)
    
    def _check_sidebar_collapse(self):
        if self.width() < 1100:
            self.sidebar.collapse()  # Show icons + tooltips only
        else:
            self.sidebar.expand()    # Show full text labels
        self.resize_timer.stop()
```

### 3. Update Terminal Widget (terminal_widget.py)
```python
from PySide6.QtGui import QFont

class TerminalWidget(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        
        # Set to 13pt (was 12pt)
        font = QFont()
        if sys.platform == "linux":
            font.setFamily("JetBrains Mono")
        else:  # Windows
            font.setFamily("Cascadia Code")
        font.setPointSize(13)  # UP FROM 12
        font.setStyleStrategy(QFont.PreferAntialias)
        self.setFont(font)
        
        # Dark background
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: var(--bg);
                color: #d4d4d4;
                border: 1px solid var(--border);
                padding: 10px;
            }
        """)
```

### 4. Sidebar Auto-Collapse (sidebar.py)
```python
class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        self.collapsed = False
        self.expanded_width = 220
        self.collapsed_width = 64
    
    def collapse(self):
        """Show only icons + tooltips"""
        if self.collapsed:
            return
        self.setMaximumWidth(self.collapsed_width)
        self.collapsed = True
        # Hide all labels, add tooltips
        for item in self.nav_items:
            item.label_widget.hide()
            item.setToolTip(item.label_widget.text())
    
    def expand(self):
        """Show icons + text labels"""
        if not self.collapsed:
            return
        self.setMaximumWidth(self.expanded_width)
        self.collapsed = False
        for item in self.nav_items:
            item.label_widget.show()
```

### 5. Status Bar Simplification (status_bar.py)
```python
class StatusBar(QStatusBar):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QStatusBar {
                background-color: var(--bg-elev);
                color: var(--text-primary);
                border-top: 1px solid var(--border);
                padding: 0 14px;
            }
        """)
        
        # Device indicator
        device_label = QLabel()
        device_label.setText("◉ SM-A346E (192.168.1.200:40787) · Wi-Fi")
        device_label.setStyleSheet("color: var(--text-primary); font-size: 11px;")
        self.addWidget(device_label)
        
        # Remove: ADB version, window width, density indicator
```

### 6. Add Recent Actions (scrcpy.py, device_buttons.py)

**Scrcpy module — add "Recent launches" table:**
```python
# After launch options card, add:
recent_table = QTableWidget(3, 4)  # 3 rows, 4 cols
recent_table.setHorizontalHeaderLabels(["Time", "Device", "Flags", "Duration"])
recent_table.horizontalHeader().setStretchLastSection(False)
recent_table.setColumnWidth(0, 80)
recent_table.setColumnWidth(1, 140)
recent_table.setColumnWidth(2, 200)
recent_table.setColumnWidth(3, 80)

# Add rows from mock data
data = [
    ["14:12:08", "SM-A346E", "8 Mbps · Auto · stay-awake", "00:12:41"],
    ["12:48:33", "SM-A346E", "8 Mbps · Auto", "00:03:19"],
    ["Yesterday 22:01", "SM-A346E", "12 Mbps · 1080p", "00:48:02"],
]
for i, row in enumerate(data):
    for j, val in enumerate(row):
        item = QTableWidgetItem(val)
        recent_table.setItem(i, j, item)

layout.addWidget(recent_table)
```

**Device Buttons — add "Recent actions" table:**
```python
# After button grids, add:
actions_table = QTableWidget(5, 4)  # 5 rows, 4 cols
actions_table.setHorizontalHeaderLabels(["Time", "Action", "Command", "Result"])
# Similar population as above
```

---

## Testing Checklist

- [ ] Windows 11: text readable at 125% & 150% DPI scaling
- [ ] Ubuntu 22+: no font rendering artifacts (smooth anti-aliasing)
- [ ] **Light theme:** no invisible text, all borders visible
- [ ] **Dark theme:** no washed-out colors, text clear on all backgrounds
- [ ] **Resize window:** sidebar collapses smoothly at <1100px width
- [ ] **Content scrolling:** main area scrolls, window doesn't resize
- [ ] **Scrcpy/Device Buttons:** recent data tables visible and functional
- [ ] **Terminal:** 13pt font comfortable, no lag or rendering issues
- [ ] **Keyboard shortcuts:** Ctrl+1–8, Ctrl+, work on both platforms
- [ ] **Status bar:** shows device + connection, nothing else

---

## File Checklist

```
src/adb_helper/ui/
  ├── qss/
  │   ├── dark.qss          (UPDATE: colors, no shadows, 13px base)
  │   └── light.qss         (UPDATE: lighter colors, same structure)
  ├── main_window.py        (UPDATE: fixed 1280×800, scrollable content)
  ├── sidebar.py            (UPDATE: auto-collapse, tooltips)
  ├── status_bar.py         (UPDATE: simplified, remove version/width)
  ├── terminal_widget.py    (UPDATE: 13pt font)
  ├── theme_manager.py      (no change — existing logic applies)
  └── DESIGN_TOKENS.md      (UPDATE: add new color values)

src/adb_helper/modules/
  ├── scrcpy.py             (ADD: recent launches table)
  ├── device_buttons.py     (ADD: recent actions table)
  └── (others unchanged)
```

---

## Quick Color Copy-Paste (Dark)

For fast implementation, copy this into your QSS file:

```css
--bg: #05070a;
--bg-elev: #0d1117;
--surface: #181d24;
--surface-2: #1c2128;
--surface-3: #232932;
--border: #1f242b;
--border-strong: #2a3038;
--text-primary: #e6e8eb;
--text-secondary: #9aa3ad;
--text-muted: #5f6873;
--accent: #2ec5c5;
--success: #2eb872;
--warn: #d4a017;
--danger: #d94c3a;
```

Done! Questions? Check the screenshots in the proto project or ask Claude Code in VSCode.
