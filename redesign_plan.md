# ADB_Helper — Redesign Implementation Plan

## Context

`handoff.md` + `design.html` define a full visual redesign (new dark+light palettes, sidebar brand block, status bar with device/battery/ADB indicators, per-module layout fixes). Existing code at v1.0.0 already implements all 9 modules functionally, but visuals diverge from the design and several known bugs are listed in `handoff.md §6` (truncated Connection-port column, overlapping Action buttons in Settings, white logcat command preview header, invisible checkboxes in Apps). This plan replaces the theming layer with a tokens-driven system, rebuilds the sidebar + status bar, and applies design-compliant layouts to every module — without touching ADB I/O, persistence schemas, or `§9 Out of Scope` features.

User-confirmed scope choices:
- **Tokens-based rewrite** (new `src/adb_helper/ui/theming/` package; replaces static `ui/qss/*.qss` files and current `ThemeManager`).
- **Keep `Theme.SYSTEM`/`LIGHT`/`DARK` enum** (no settings migration).
- **Full pass** in one plan: theming + chrome + all 9 modules.
- **Add brand row** (logo + name + version) to the sidebar.

---

## 1. New theming package — `src/adb_helper/ui/theming/`

Create:
- `__init__.py` — re-export `Theme`, `ThemeManager`, `Tokens`.
- `tokens.py` — `@dataclass(frozen=True) Tokens` with all surfaces / borders / text / accent / semantic colors + geometry (r_sm/md/lg, sp_*, input_h, btn_h, row_h). Values copied **1:1** from `design.html :root` and `[data-theme="light"]` (see handoff §2, including alpha-rgba for `bg_row_*` and `accent_soft`).
- `palette.py` — `build_palette(t: Tokens) -> QPalette` (Window/WindowText/Base/AlternateBase/Text/Button/ButtonText/Highlight/HighlightedText/ToolTipBase/ToolTipText + Disabled variants + Link). Per handoff §2.1 — needed so `QFileDialog`/`QMessageBox`/Win11 scrollbars don't fall outside the theme.
- `qss.py` — module-level `QSS_TEMPLATE` string + `render_qss(t: Tokens) -> str` (uses `str.format_map(asdict(t))`). On import, compute `ICONS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "assets" / "icons"` and `assert ICONS_DIR.exists(), f"icons dir missing: {ICONS_DIR}"` — fails loudly if package depth changes or assets get moved. **All literal `{` / `}` inside `QSS_TEMPLATE` must be doubled (`{{` / `}}`) — applies to QSS rule blocks, CSS comments, and `url(...)` arguments. Only token placeholders like `{accent}` stay single-braced.** Content = handoff §3 template, **plus**:
  - Sidebar selectors that match existing `QWidget#appSidebar` + `QPushButton#sidebarItem[active="true"]` object/property names (avoids touching `sidebar.py` selectors).
  - `QFrame#InstallStatus[state="idle|running|done|error"]` (handoff §7.3).
  - `QLabel#LogcatCommandPreview` (handoff §6.3).
  - `QFrame#AppsToolbar` (handoff §7.7).
  - `QPushButton#sidebarBrand` (no border, no hover effect — see §4.2).
- `theme_manager.py` — replace `src/adb_helper/ui/theme_manager.py`. Same public API (`Theme`, `ThemeManager`, `get_theme_manager`), same `Signal theme_changed`, same `apply(app, theme)` signature. Internally:
  - `_apply(effective: Theme)`: `tokens = DARK_TOKENS if effective == DARK else LIGHT_TOKENS`, then `app.setPalette(build_palette(tokens))` **then** `app.setStyleSheet(render_qss(tokens))`.
  - Keep `darkdetect` polling on Linux (system theme follow already works).
  - Re-polish every top-level widget on theme change (`for w in app.allWidgets(): w.style().unpolish(w); w.style().polish(w)`) — required so `setProperty("variant", ...)` selectors re-evaluate.

**Delete** after migration:
- `src/adb_helper/ui/qss/dark.qss`
- `src/adb_helper/ui/qss/light.qss`
- `src/adb_helper/ui/qss/` directory.
- Old `src/adb_helper/ui/theme_manager.py` (replaced by package).

`main.py` import line `from adb_helper.ui.theme_manager import Theme, ThemeManager` keeps working because `theming/__init__.py` re-exports — but switch import to `from adb_helper.ui.theming import ...` for clarity. `MainWindow` import same.

Terminal palette (`src/adb_helper/ui/terminal_palette.py`) stays as-is — terminal output colors are owned there per existing comment in `dark.qss`. Add a hook in `ThemeManager._apply` to call `terminal_palette.refresh_for(effective)` so terminal palette tracks theme.

---

## 2. Sidebar — `src/adb_helper/ui/sidebar.py`

Modify in place (do NOT rewrite). Changes:

1. **Add brand row** at top:
   - `QWidget#sidebarBrand`: `QHBoxLayout` (margins 8,8,8,14, spacing 10).
   - Left: `QLabel#sidebarLogo` size 26×26, gradient bg `linear-gradient(135deg, accent, accent_strong)`, centered letter `A` in `accent_fg`, font 700 / 13px. (Implement via paintEvent — QSS gradient on a label works but text centering is finicky; alternatively a `QFrame` + child `QLabel`.)
   - Right: vertical column with `QLabel("ADB_Helper")` (`fs_lg`, weight 600) + `QLabel("v1.0.0")` (`fs_xs`, color `text_3`). Version sourced from `strings.APP_VERSION` if present, else hardcoded `"v1.0.0"`.
   - Brand row hidden when collapsed (`update_for_window_width < 1100`): `self._brand.setVisible(not collapsed)`.
2. **Adaptive width**: extend `update_for_window_width` so width ≥1700 → `SIDEBAR_W_WIDE = 256`, else current 220/64 logic (handoff §4.2). Add `SIDEBAR_W_WIDE = 256`.
3. **Active item style** — drop hardcoded `_ICON_ACTIVE = "#2ec5c5"` and `_ICON_INACTIVE = "#4a525b"`. Read from current tokens via `theme_manager.current_tokens()` (new method returning `Tokens`) — fall back to defaults if not initialized. Re-render SVG icons on `theme_changed` signal (connect in `__init__`).
4. **Keep**: `module_selected` signal, `_load_svg_icon`, `setProperty("active", ...)` mechanic (matches new QSS).
5. Remove footer-meta if any exists (it does not — confirmed by reading `sidebar.py`).

---

## 3. Status bar — `src/adb_helper/ui/status_bar.py`

Rewrite contents (keep file path + class name `AppStatusBar`). Per handoff §8 + design.html lines 763-777:

Layout (left → right via `addWidget` / `addPermanentWidget`):
- **Device segment** (`QWidget#statusDeviceSeg`): `QLabel#statusDot` (custom paintEvent, 8×8 round, color from `success/warning/danger` based on connection state) + `QLabel#statusDeviceLabel` (model bold + ` · ` + serial). Hidden if no device.
- `QFrame#StatusSep` (1px × 14px tall, color `border`).
- **Transport segment**: `Transport: <strong>USB|Wi-Fi</strong>`.
- `QFrame#StatusSep`.
- **Android version segment**: `Android <strong>16</strong> · API 36` (from `DeviceContext`).
- Spacer (`addPermanentWidget(spacer, 1)` won't work — use `setStretch` or rely on the layout).
- **Battery segment** (right side, `addPermanentWidget`): SVG battery icon + `<strong>NN%</strong>`. Hidden if battery unknown.
- `QFrame#StatusSep`.
- **ADB daemon segment**: `ADB <strong style="success">running</strong>` / red `stopped`.

Public API:
- `update_device(ctx: Optional[DeviceContext])` — existing signature, fills device + transport + android segments.
- `set_battery(percent: Optional[int])` — new slot, hides segment on `None`.
- `set_adb_state(running: bool)` — new slot.
- `show_message(text)` — drop the status-bar render entirely. Route to `logger.info(text)` only. Design has no transient message slot. Keep the method signature so existing callers compile, but the body just forwards to the logger.

Wire-up in `main_window.py`:
- Connect `adb_service` battery / daemon signals if they exist; if not, leave segments at default values and add a TODO comment.

Removed:
- "Last refresh" indicator — never existed; handoff §8 confirms not adding.

---

## 4. Main window — `src/adb_helper/ui/main_window.py`

Minimal changes:
- `_on_theme_changed`: extend to walk `QApplication.allWidgets()` and re-polish each, then re-render sidebar SVG icons (currently only re-polishes self).
- Adaptive sidebar width hook: already calls `self._sidebar.update_for_window_width(width)` — keep.
- Set `objectName="appCentral"` already done — keep, matches QSS.
- Set `central.setProperty("page", "true")` is not required; new QSS scopes via `QMainWindow, QWidget#appCentral` selectors.

---

## 5. Per-module changes

Each module is a `QWidget` (`IModule`). The pattern: **wrap inner layout in `QWidget#pageRoot` with a `QHBoxLayout` outer that pins `setMaximumWidth(1600)` (handoff §9 wide-screen rule), and add a `page-header` row at top** (title + subtitle + optional right-side actions).

Add a tiny helper in `src/adb_helper/ui/style_utils.py` (already exists per `__init__`):
- `page_header(title: str, subtitle: str = "", actions: Iterable[QWidget] = ()) -> QWidget` — emits an `HBox` with `QLabel[role="page-title"]` + `QLabel[role="hint"]` + spacer + actions.
- `card(label: str, body: QWidget, actions: Iterable[QWidget] = ()) -> QFrame` — wraps `QFrame[role="card"]` with header (`QLabel[role="section-label"]`), body container, and optional `card-f` footer.
- `set_variant(btn, "primary"|"danger"|"ghost"|"destructive")` — already exists; reuse.

### 5.1 Connections (`modules/connections.py`)

Rebuild `_build_ui`:
- Replace stacked `QGroupBox` rows with a top-level `QGridLayout(2 cols × 2 rows)`, equal `setColumnStretch(0,1); setColumnStretch(1,1)`, h+v spacing 16:
  - (0,0) **Wi-Fi Pairing** card (currently `_build_wifi_pairing_group`).
  - (0,1) **Wi-Fi Connection (Legacy)** card (currently `_build_wifi_classic_group`).
  - (1,0) **Connected Devices** card (live table).
  - (1,1) **Paired Devices** card.
- Convert each `QGroupBox` → `QFrame` with `setProperty("role","card")` + `card-h` row + `card-b` body. Replace title `QLabel` with the section-label spec.
- **Pairing form**: PIN sits in same row as Pairing Port (handoff §7.1) — `QHBoxLayout` with `pairPortInput` (fixedWidth 130) + label `PIN` + `pinInput` (fixedWidth 130, `setMaxLength(6)`, `QRegularExpressionValidator("\\d{0,6}")`, placeholder `123456`) + `addStretch(1)` + Pair button (`set_variant("primary")`).
- **Live (Connected) table**: cols Serial / IP / Model / Status. Status cell gets a `QLabel` with `setProperty("pill","online"|"offline"|"warn")` so existing pill QSS rules apply.
- **Paired table fix (handoff §6.1)**: column `_PCOL_PORT` → `QHeaderView.ResizeMode.Interactive`, `resizeSection(_PCOL_PORT, 140)`, `verticalHeader().setDefaultSectionSize(40)`. Drop the inline `port_edit.setStyleSheet(...)` at line 576 — replace by `port_edit.setProperty("size","sm")` (matches new QSS small-input rule, add `QLineEdit[size="sm"] { min-height: 28px; padding: 0 8px; }` to template).
- Page header: title `Connections`, subtitle `Connect over Wi-Fi or pair a new Android 11+ device`, right actions: `Scan network` (kept visible, `setEnabled(False)`, `setToolTip("Not implemented yet")`), `Refresh` (variant=primary).

### 5.2 Terminal (`modules/terminal.py`)

- Replace top-level layout with `QHBoxLayout`: left `terminalCard` (stretch=1) + right `macroPanel` (`setFixedWidth(260)`).
- Terminal card body: `QFrame#TerminalStatus` (one line, `QLabel`-based, monospace) → existing terminal output `QPlainTextEdit#terminal-output` (already correctly named per QSS) → `QFrame#TerminalPrompt` (HBox: prefix `QLabel` `serial:/ $` accent-colored + frameless `QLineEdit`).
- Macro panel content (`QWidget#macroPanel`): card-header `Macros`; body row with `QPushButton "Record"` + `QPushButton "Play"` both `setEnabled(False)` + `setToolTip("Not implemented yet")`; below, centered placeholder `QLabel "No macros saved."` with `role="hint"`. Panel must not be empty.
- Page header: `Terminal` + subtitle showing active serial. Right actions: `History`, `Clear`.

### 5.3 Installer (`modules/installer.py`)

- 4 stacked cards: **Files** / **Targets** / **Installation** / **Results**.
- Each table: `setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)`, `setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)`, wrap the whole page in a `QScrollArea` so the page scrolls, not individual tables.
- Empty-state rows: spanning `QLabel` centered, `Files` `setMinimumHeight(96)`, `Results` `setMinimumHeight(132)`.
- **Installation card**:
  - Row 1: `Install` (primary) + `Cancel` + `QProgressBar` (stretch=1, height 6, `setTextVisible(False)`) + `QLabel` `0%` (mono, min-width 40).
  - Row 2: `QFrame#InstallStatus` with property `state="idle|running|done|error"` and a `QLabel#statusDot` + `QLabel#statusText` (mono). Default state `idle` with text `Idle — add files and select a target device to begin.`
- Drop targets: `setAcceptDrops(True)` on the page; intercept `dragEnterEvent` / `dropEvent` for `.apk`/`.aab` filtering.
- Page header: `Installer` + `Install APK / AAB on selected devices` (no right actions).

### 5.4 Scrcpy (`modules/scrcpy.py`)

- 2-column `QGridLayout`: Launch options (form, col-stretch 1) | Recent launches (table, col-stretch 1.2).
- Launch options form: `QFormLayout` with `Video bitrate` (QComboBox), `Max resolution` (QComboBox), `Orientation lock` (QComboBox), then a "switches" row containing `Stay awake`, `Show touches`, `Turn screen off` as horizontal `QCheckBox`es (handoff §7.4).
- Launch button: **only in page header** (`▶ Launch`, variant=primary). No duplicate inside the form. Remove the existing form-footer Launch and any "(optional)" annotation in current code.

### 5.5 Device Buttons (`modules/device_buttons.py`)

- `QGridLayout` **4 cols × 3 rows always**, spacing 10, equal column stretch (`setColumnStretch(i, 1) for i in range(4)`). No resizeEvent breakpoint logic — 4 columns at every width.
- Buttons: `QPushButton#ButtonTile` height 64, icon-left + label-right, icon color = `accent` (set via SVG `currentColor`). Add QSS rule `QPushButton#ButtonTile { min-height: 64; background: bg_card_2; border: 1px solid border; border-radius: r_md; }` + hover.
- Recent actions table card below the grid.

### 5.6 Device Info (`modules/device_info.py`)

- Repack the **existing** section cards from current `device_info.py` into a 2-column `QGridLayout` (cards flow left→right, top→bottom). Do NOT add new sections (no Memory / Display / Network — only what the module already collects).
- Inside each card: `QFormLayout` with label width 180, label color `text_2` (`role="hint"`), value `QLabel` with `setTextInteractionFlags(Qt.TextSelectableByMouse)` + monospace font on technical fields (build fingerprint, paths).
- Page header: `Device Info` + `Auto-collected from <serial>`. Right actions: `Refresh`, `Export to TXT`.

### 5.7 Apps (`modules/apps.py`)

- Top: `QFrame#ResourceStats` (one card) — `QHBoxLayout`: RAM block (label + `QProgressBar` + value text) | Storage block | spacer | Refresh button.
- Body: `QSplitter(Qt.Horizontal)`:
  - Left `QFrame#AppsList` (stretchFactor 1.4): card-header (`Packages` label + count hint) → **separate `QFrame#AppsToolbar` below card-header** (search input + 2 checkboxes) → `QTableView` → footer (`Delete/Disable/Enable/Export to CSV` + counter on right).
  - Right `QFrame#AppDetails` (stretchFactor 1): card-header (`App details` + `↗` open button) → `app-meta` row (icon block + pkg name + badges) → `QFormLayout` with 8 meta rows → footer (`Open / Force-stop / Clear data / Uninstall`).
  - **Empty state**: when no package selected, the detail panel body shows a single centered `QLabel "Select a package to view details"` (`role="hint"`, vertically + horizontally centered). The meta/form/footer rows are hidden in this state. Toggle visibility on `currentRowChanged`.
  - `setChildrenCollapsible(False)`, `setHandleWidth(8)`.
- **Fix invisible checkboxes (handoff §6.4)**: in QSS template add `QTableView::indicator { width: 16; height: 16; border: 1.5px solid border_strong; background: bg_input; border-radius: 3; }` + `:checked { background: accent; border-color: accent; image: url(<icons_dir>/check.svg); }`. Bundle `check.svg` (white) and `check-dark.svg` (color `accent_fg` = `#08201d` for dark accent fill) in `assets/icons/`. **Cross-platform path test required**: before shipping, verify on Windows that `setStyleSheet` with `image: url(...)` resolves correctly when `icons_dir` contains spaces or Cyrillic characters (common in Windows user paths like `C:\Users\Андрей\…`). If resolution fails, fall back: drop the `image:` rule entirely and paint the check programmatically — subclass `QStyledItemDelegate` for the apps table column or install a `QProxyStyle` that draws `PE_IndicatorCheckBox` via `QPainter` with the accent color. Same fallback path for `QCheckBox::indicator:checked` glyph if the QSS `image:` doesn't render.
- Search field `setPlaceholderText("Search by package…")`, debounce on `textChanged` (existing logic, keep).
- On `currentRowChanged` of the apps table, refresh detail panel via signal.
- Narrow-screen behaviour (<800 width): `splitter.widget(1).setVisible(False)` and add a "back" button to return to list; for v1 just allow Qt's natural collapse since `setChildrenCollapsible(False)` prevents it — leave responsive collapse as **deferred** with TODO.

### 5.8 Logcat (`modules/logcat.py`)

- 2-column `QGridLayout`: left col (stretch 1.5) holds Capture card + Recent exports card stacked; right col (stretch 0.9) holds Configuration card.
- **Fix white preview header (handoff §6.3)**: drop inline `setStyleSheet` at line 133. Rename widget `self._cmd_preview` → `QLabel#LogcatCommandPreview` (objectName), set `setTextFormat(Qt.RichText)`, `setWordWrap(True)`. Style entirely from QSS template (already in §1 above).
- Build the rich-text command with `<span style="color:{accent}">{path}</span>` color via current tokens (helper in `style_utils`: `accent_color() -> str`).
- Page header right actions: `⇣ Export logcat` (variant=primary) **moved** into the Capture card per design — keep the page header empty.

### 5.9 Settings (`modules/settings.py`)

- 3 cards: **About** / **Installed dependencies** / **General**.
- **About**: small app-ico (40×40) + `ADB_Helper` + `v1.0.0 · Python 3.12 · PySide6 · Qt 6` + right-side `Release notes`, `Check for updates`.
- **Installed dependencies**: table cols Component / Installed / Latest / Status / Action. **Fix overlapping Action (handoff §6.2)**: `hdr.setSectionResizeMode(COL_ACTION, Fixed); hdr.resizeSection(COL_ACTION, 130); table.setColumnWidth(COL_ACTION, 130)`. Each action cell uses `_wrap_center(QPushButton)` (HBox margins 4, stretch both sides). Buttons `setProperty("size","sm")` + variant per state. Status uses pill `QLabel` (`pill="online"|"offline"|"warn"|"err"`).
- **General**: `QFormLayout`. Theme `QComboBox` items: `Auto (follow system)` → value `system`, `Dark` → `dark`, `Light` → `light`. On `currentIndexChanged`: `theme_mgr.apply(QApplication.instance(), Theme(value))` + `settings.set("theme", value)`. Restore on startup (already wired in `main.py`).
- Removed if currently present: any hidden theme-toggle in titlebar/sidebar (none exists per `sidebar.py` read).

---

## 6. Resources / icons

Existing `assets/icons/` directory has sidebar icons. Add (or verify):
- `assets/icons/check.svg` — white checkmark (stroke `currentColor`, used on `accent` background).
- `assets/icons/check-dark.svg` — dark checkmark (`accent_fg` `#08201d`) for light theme.
- `assets/icons/chevron-down.svg` — for ComboBox arrow.
- `assets/icons/battery.svg` — status bar.

Reference in QSS template via `url(:/icons/check.svg)` requires a `.qrc` resource file. **Decision**: skip the `.qrc` step (Spec doesn't mandate it). Use direct file paths via `assets/icons/<name>.svg` resolved at runtime by the same helper Sidebar uses (`pathlib` → file://). For QSS `image:` rules, generate paths in `render_qss()` by injecting an `icons_dir` token (`Path(__file__).parent.parent.parent.parent / "assets" / "icons"`). Use `str(path).replace("\\", "/")` for cross-platform forward slashes.

---

## 7. CLAUDE.md invariants — compliance check

- **Invariant 1 (ADB I/O isolation)**: no module gains direct ADB calls. ✓
- **Invariant 2 (IModule contract)**: signatures unchanged. ✓
- **Invariant 3 (strings centralised)**: every new label (e.g. `Idle — add files and select a target device to begin.`) goes into `src/adb_helper/core/strings.py`. New entries:
  - `INSTALL_STATUS_IDLE`, `INSTALL_STATUS_RUNNING` (parametrised), `INSTALL_STATUS_DONE`, `INSTALL_STATUS_ERROR`
  - `STATUS_BAR_TRANSPORT_USB`, `STATUS_BAR_TRANSPORT_WIFI`, `STATUS_BAR_ADB_RUNNING`, `STATUS_BAR_ADB_STOPPED`
  - Page-header subtitles per module (`PAGE_SUBTITLE_CONNECTIONS`, etc.)
- **Invariant 4 (platform shims)**: no new `sys.platform` branches outside `core/platform.py`. ✓
- **Invariant 5 (§9 out of scope)**: nothing in the redesign adds banned features. ✓

---

## 8. Critical files modified / created / deleted

**Created:**
- `src/adb_helper/ui/theming/__init__.py`
- `src/adb_helper/ui/theming/tokens.py`
- `src/adb_helper/ui/theming/palette.py`
- `src/adb_helper/ui/theming/qss.py`
- `src/adb_helper/ui/theming/theme_manager.py`
- `assets/icons/check.svg`, `check-dark.svg`, `chevron-down.svg`, `battery.svg`

**Modified:**
- `main.py` — import path → `from adb_helper.ui.theming import Theme, ThemeManager`.
- `src/adb_helper/ui/sidebar.py` — brand row, wide-mode width, token-driven icon colors.
- `src/adb_helper/ui/status_bar.py` — full rebuild (4 segments + dot + sep).
- `src/adb_helper/ui/main_window.py` — re-polish all widgets on theme change.
- `src/adb_helper/ui/style_utils.py` — add `page_header()`, `card()` helpers; keep `set_variant`.
- `src/adb_helper/core/strings.py` — new string constants.
- `src/adb_helper/modules/connections.py` — 2×2 grid, pairing-row layout, remove inline `setStyleSheet` on port_edit.
- `src/adb_helper/modules/terminal.py` — HBox + macro panel + status header.
- `src/adb_helper/modules/installer.py` — 4-card layout, install-status frame, drop-target on table, page-scrolls-not-tables.
- `src/adb_helper/modules/scrcpy.py` — 2-col grid, horizontal switches row.
- `src/adb_helper/modules/device_buttons.py` — 4-col grid, ButtonTile object name + QSS.
- `src/adb_helper/modules/device_info.py` — 2-col grid of section cards.
- `src/adb_helper/modules/apps.py` — Splitter, AppsToolbar frame, detail panel, fix checkbox indicator.
- `src/adb_helper/modules/logcat.py` — drop inline preview style, 2-col grid, primary Export button.
- `src/adb_helper/modules/settings.py` — 3 cards, dependencies action column 130px fix, Theme combo wired to `ThemeManager`.

**Deleted:**
- `src/adb_helper/ui/qss/dark.qss`
- `src/adb_helper/ui/qss/light.qss`
- `src/adb_helper/ui/qss/` (empty dir).
- `src/adb_helper/ui/theme_manager.py` (replaced by package).

---

## 9. Verification

End-to-end manual run (no automated UI tests in repo per CLAUDE.md):

1. **Smoke**: `python main.py` — app launches, default page is Connections, no Qt warnings about unknown property selectors.
2. **Theme switch**: Settings → Theme → cycle through `Auto/Dark/Light`. Verify:
   - All 9 pages re-paint within ~100ms.
   - `QMessageBox` (trigger by disconnecting device or attempting a failing connect) follows theme — fix needed if it doesn't (means `setPalette` not applied before `setStyleSheet`).
   - `QFileDialog` (Settings → Browse… for screenshots folder) uses **system** theme (intentional per handoff §13.5).
3. **Per-bug regression**:
   - **§6.1**: Connections → Paired table → Connection port column is 140px wide, the `QLineEdit` (28px tall) fits within the 40px row.
   - **§6.2**: Settings → Installed dependencies → Action column is 130px, Install/Update buttons don't visually overflow.
   - **§6.3**: Logcat → command preview is themed (no white background in Dark).
   - **§6.4**: Apps → table checkboxes visible in both themes, checked state shows the accent fill + check.svg glyph.
4. **Adaptive sidebar**: resize the window narrower than 1100 → brand row hides, labels hide, width = 64. Resize to ≥1700 → width = 256.
5. **Connections 2×2**: verify the four cards form a strict 2-row grid with equal-height pairs.
6. **Installer status states**: trigger an install (or fake by setting property in dev) — `InstallStatus` shows accent border in `running`, success dot in `done`, danger color in `error`.
7. **DPI smoke**: launch under `QT_SCALE_FACTOR=1.5` and `QT_SCALE_FACTOR=2.0` — text doesn't clip, no pixel snapping issues on borders.
8. **Settings persistence**: change theme to Light → close → relaunch → still Light. (`settings.json` `theme` key.)

If any of the above fails, fix in the relevant module file before the implementation is considered complete.

---

## 10. Out of scope (explicitly NOT in this plan)

- Any change to `core/adb_service.py`, `core/db_manager.py`, `core/device_monitor.py`, `core/pty_session.py` or other core layer files.
- Adding new ADB commands or features.
- Schema migrations (`db/migrations/`).
- macOS support (banned per CLAUDE.md §9).
- Live logcat streaming, file push/pull, app-icon extraction (banned).
- Replacing `darkdetect` with `QGuiApplication.styleHints().colorScheme()` (handoff §1.3 mentions it, but current Qt 6 versions on the target platforms can keep `darkdetect` polling — defer to a follow-up if perf becomes an issue).
- Generating `.qrc` resource bundle — direct filesystem paths to `assets/icons/` are sufficient.
