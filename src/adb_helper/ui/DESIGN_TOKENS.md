# Design Tokens

Extracted from `adb-helper_handoff_Claude_Design/project/styles.css`. This file is the reference for all QSS generation. When the prototype's choices conflict with the technical specification, the spec wins — those cases are flagged below.

OKLCH values are precomputed to sRGB hex once here and reused in the QSS files (Qt QSS does not support OKLCH). The OKLCH source is preserved in comments next to each constant in the QSS so the colour remains editable.

## Typography

| Role                | Family (in order)                                                 | Notes                                                                                          |
| ------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Sans (UI)           | Geist → `-apple-system` → Segoe UI → system-ui → sans-serif       | Prototype loads Geist from Google Fonts. For the Qt port, fall back to system sans if Geist is not bundled. |
| Mono (terminal, tags, version strings) | Geist Mono → JetBrains Mono → Cascadia Code → ui-monospace → monospace | **Spec override (§2.2.1):** terminal widget uses **Cascadia Code on Windows 11**, **JetBrains Mono on Linux** (bundled under `assets/fonts/`). Geist Mono is the prototype's choice; do not adopt it for the terminal. |

### Sizes

| Token       | Value | Where it's used                                                              |
| ----------- | ----- | ---------------------------------------------------------------------------- |
| `--text`    | 13 px | Base UI text and sidebar items                                               |
| `--text-sm` | 12 px | Buttons, inputs, table cells, secondary text                                 |
| `--text-xs` | 11 px | Status bar, field labels, breadcrumb, info-row values                        |
| Module H1   | 15 px | Module header title (`.module-header h1`)                                    |
| Card head   | 12 px uppercase, letter-spacing 0.02em — `.card-head h3`                          |
| Section label | 10 px uppercase | Sidebar section label, table headers                                    |
| Terminal    | 13 pt | **Spec §2.2.1** (the prototype uses 12.5 px in the mock; the spec is normative.) |

Compact density (`data-density="compact"`) drops the three text-* sizes to 12 / 11 / 10 px and tightens the spacing scale (see Spacing).

## Colour — Dark theme (default)

| Token                | Hex / function                          | sRGB precomputed | Use                                                                  |
| -------------------- | --------------------------------------- | ---------------- | -------------------------------------------------------------------- |
| `--bg`               | `#05070a`                               | —                | App background, table body, terminal screen background               |
| `--bg-elev`          | `#0d1117`                               | —                | Titlebar, sidebar, status bar, table headers, terminal input row     |
| `--surface`          | `#181d24`                               | —                | Cards, inputs, dropzones, screenshot frame inner                     |
| `--surface-2`        | `#1c2128`                               | —                | Buttons, hover row backgrounds, segmented control                    |
| `--surface-3`        | `#232932`                               | —                | Scrollbar thumb, pill badges                                         |
| `--border`           | `#1f242b`                               | —                | Section dividers, card borders                                       |
| `--border-strong`    | `#2a3038`                               | —                | Input borders, button outlines, dashed dropzone                      |
| `--text-primary`     | `#e6e8eb`                               | —                | Default text                                                         |
| `--text-secondary`   | `#9aa3ad`                               | —                | Secondary labels, sidebar inactive items                             |
| `--text-muted`       | `#5f6873`                               | —                | Field labels, captions, "N/A" placeholders                           |
| `--accent`           | `oklch(0.78 0.13 180)`                  | `#2ec5c5`        | Active item indicator, primary button, focus rings, terminal prompt  |
| `--accent-soft`      | `oklch(0.78 0.13 180 / 0.15)`           | `rgba(46,197,197,38)` | Active sidebar badge, active accent pill                        |
| `--accent-faint`     | `oklch(0.78 0.13 180 / 0.08)`           | `rgba(46,197,197,20)` | Hover background, selected table row, focus shadow              |
| `--success`          | `oklch(0.74 0.16 145)`                  | `#2eb872`        | Online dot, success toast, online pill                               |
| `--warn`             | `oklch(0.78 0.15 75)`                   | `#d4a017`        | Warning dot, warn pill, progress bar in caution                      |
| `--danger`           | `oklch(0.68 0.20 25)`                   | `#d94c3a`        | Danger button text, error toast, recording indicator                 |
| `--danger-faint`     | `oklch(0.68 0.20 25 / 0.10)`            | `rgba(217,76,58,26)`  | Hover background on `.btn.danger`, modal destructive accents    |
| `--danger-border`    | `oklch(0.68 0.20 25 / 0.40)`            | `rgba(217,76,58,102)` | Hover border on `.btn.danger`                                  |

### Shadows (dark)

| Token         | CSS                                                                                |
| ------------- | ---------------------------------------------------------------------------------- |
| `--shadow-1`  | `0 1px 0 0 rgba(255,255,255,0.02) inset, 0 1px 2px rgba(0,0,0,0.3)`                |
| `--shadow-pop`| `0 8px 24px rgba(0,0,0,0.4), 0 1px 0 0 rgba(255,255,255,0.03) inset`               |

QSS does not support `box-shadow`; document the intent here, fall back to a 1px border on the matching widget in the stylesheet.

## Colour — Light theme

Overrides only the surface/text/shadow tokens (accent and status colours are shared with the dark theme):

| Token                | Hex                |
| -------------------- | ------------------ |
| `--bg`               | `#e6e9ee`          |
| `--bg-elev`          | `#ffffff`          |
| `--surface`          | `#ffffff`          |
| `--surface-2`        | `#f1f3f5`          |
| `--surface-3`        | `#e7eaee`          |
| `--border`           | `#e3e6ea`          |
| `--border-strong`    | `#d2d7dd`          |
| `--text-primary`     | `#14181c`          |
| `--text-secondary`   | `#4a525b`          |
| `--text-muted`       | `#8993a0`          |
| `--shadow-1`         | `0 1px 2px rgba(0,0,0,0.04)`  |
| `--shadow-pop`       | `0 12px 32px rgba(0,0,0,0.10)` |

Accent / success / warn / danger are reused unchanged from the dark theme.

## Terminal ANSI palette

The terminal widget uses the curated 16-colour palette defined in **Spec §2.2.1** — that table is normative and takes precedence over anything in `styles.css`. Background / foreground per theme:

- Dark: bg `#1E1E1E`, fg `#D4D4D4`
- Light: bg `#FFFFFF`, fg `#1E1E1E`

See the spec for the full role mapping (black, red, green, yellow, blue, magenta, cyan, white, plus their bright variants on each theme). **The terminal output `QPlainTextEdit` carries `objectName="terminal-output"` and MUST be excluded from generic `QPlainTextEdit` rules in the QSS** — colours come exclusively from `ui/terminal_palette.py`.

## Spacing scale

| Token        | Default | Compact | Purpose                                                  |
| ------------ | ------- | ------- | -------------------------------------------------------- |
| `--pad-x`    | 18 px   | 14 px   | Module body horizontal padding                           |
| `--pad-y`    | 14 px   | 10 px   | Module body vertical padding                             |
| `--gap`      | 14 px   | 10 px   | Grid gaps between panels                                 |
| `--gap-sm`   | 8 px    | 6 px    | Small inline gaps                                        |
| `--row-h`    | 36 px   | 30 px   | Table row height                                         |
| `--radius`   | 6 px    | —       | Cards, modals                                            |
| `--radius-sm`| 4 px    | —       | Buttons, inputs, sidebar items, tags                     |

## Layout dimensions

| Token                   | Value  | Use                                |
| ----------------------- | ------ | ---------------------------------- |
| `--sidebar-w`           | 220 px | Expanded sidebar                   |
| `--sidebar-w-collapsed` | 64 px  | Collapsed sidebar (icon-only)      |
| `--titlebar-h`          | 38 px  | Custom titlebar height (prototype only — see notes) |
| `--statusbar-h`         | 28 px  | Bottom status bar                  |

Window: default 1280 × 800, minimum 960 × 600 (Spec §2.1). Sidebar collapses to icon-only when window width drops below 1100 px (Redesign v1.0).

## Component patterns

The prototype primitives translate to QSS selectors as follows:

| Prototype class            | Qt mapping                                                       |
| -------------------------- | ---------------------------------------------------------------- |
| `.btn` (default)           | `QPushButton` base style                                         |
| `.btn.primary`             | `QPushButton[variant="primary"]` — accent fill, dark text        |
| `.btn.danger` / Delete     | `QPushButton[variant="destructive"]` — danger text, danger hover |
| `.btn.ghost`               | `QPushButton[variant="ghost"]` — transparent, hover surface-2    |
| `.btn.sm`                  | `QPushButton[size="sm"]` — 24 px tall                            |
| `.input`, `.select`, `.textarea` | `QLineEdit`, `QComboBox`, `QPlainTextEdit` / `QTextEdit`   |
| `.card`                    | `QGroupBox` (uppercase title styled in QSS)                      |
| `.table`                   | `QTableView`, `QTableWidget` (sticky header, accent-faint selection) |
| `.pill`                    | `QLabel[pill="online" \| "offline" \| "warn" \| "danger" \| "accent"]` |
| `.seg`                     | `QTabBar` (closest native equivalent)                            |
| `.cb`                      | `QCheckBox::indicator` (14×14, accent fill when checked)         |
| `.bar`                     | `QProgressBar` (6 px tall, `state="warn"`/`state="danger"`)      |
| `.modal`                   | `QDialog`                                                        |
| Sidebar items              | `QPushButton#sidebarItem`, `active="true"` for the current page  |

### Variant property values

- Primary actions (Install, Connect, Pair, Export Logcat, Record Macro): `setProperty("variant", "primary")`
- Destructive actions (Delete, Forget, Remove): `setProperty("variant", "destructive")`
- After mutating: `style().unpolish(btn); style().polish(btn)` to re-evaluate the selector.

## Status indicators

- `.dot.online` — green with soft glow; Qt fallback: 7 px circle, no shadow.
- `.dot.offline` — muted grey.
- `.dot.warn` — amber.
- Recording indicator: pulsing red dot; Qt fallback: static red dot + label.
- Cursor: 8 × 14 px solid accent block; rendered by the QLineEdit, not styleable.

## Notes for QSS port

- OKLCH is unsupported by Qt's QSS — see the precomputed hex column above. OKLCH is preserved in QSS comments next to the hex value.
- Custom titlebar with traffic-light dots is a prototype affordance only; the spec does not mandate a frameless window. The default uses the native window frame.
- The prototype loads Geist over the network; for the desktop app, ship a bundled monospace (JetBrains Mono on Linux per §6.2) and rely on the system sans for the UI font. Do not require an internet connection for fonts.
- `box-shadow` and `aspect-ratio` from CSS do not translate to QSS; document the intent, fall back to a 1 px border or fixed pixel sizing on the affected widget.
