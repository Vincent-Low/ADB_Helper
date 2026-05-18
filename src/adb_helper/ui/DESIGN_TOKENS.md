# Design Tokens

Extracted from `adb-helper_handoff_Claude_Design/project/styles.css`. This file is the reference for all QSS generation. When the prototype's choices conflict with the technical specification, the spec wins — those cases are flagged below.

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
| Section label | 10 px uppercase | Sidebar section label, table headers, card-head H3 (12 px)              |
| Terminal    | 13 pt | **Spec §2.2.1** (the prototype uses 12.5 px in the mock; the spec is normative.) |

Compact density (`data-density="compact"`) drops the three text-* sizes to 12 / 11 / 10 px and tightens the spacing scale (see Spacing).

## Colour — Dark theme (default)

| Token                | Hex / function                          | Use                                                                  |
| -------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| `--bg`               | `#0b0d10`                               | App background                                                       |
| `--bg-elev`          | `#111418`                               | Titlebar, sidebar, status bar, table headers                         |
| `--surface`          | `#161a1f`                               | Cards, inputs, dropzones                                             |
| `--surface-2`        | `#1c2128`                               | Buttons, hover row backgrounds, segmented control                    |
| `--surface-3`        | `#232932`                               | Scrollbar thumb, pill badges                                         |
| `--border`           | `#1f242b`                               | Section dividers, card borders                                       |
| `--border-strong`    | `#2a3038`                               | Input borders, button outlines, dashed dropzone                      |
| `--text-primary`     | `#e6e8eb`                               | Default text                                                         |
| `--text-secondary`   | `#9aa3ad`                               | Secondary labels, sidebar inactive items                             |
| `--text-muted`       | `#5f6873`                               | Field labels, captions, "N/A" placeholders                           |
| `--accent`           | `oklch(0.78 0.13 180)` (≈ cyan-teal)    | Active item indicator, primary button, focus rings, terminal prompt  |
| `--accent-soft`      | `oklch(0.78 0.13 180 / 0.15)`           | Active sidebar badge, active accent pill                             |
| `--accent-faint`     | `oklch(0.78 0.13 180 / 0.08)`           | Hover background, selected table row, focus shadow                   |
| `--success`          | `oklch(0.74 0.16 145)` (≈ green)        | Online dot, success toast, online pill                               |
| `--warn`             | `oklch(0.78 0.15 75)` (≈ amber)         | Warning dot, warn pill, progress bar in caution                      |
| `--danger`           | `oklch(0.68 0.20 25)` (≈ red)           | Danger button text, error toast, recording indicator                 |
| `--shadow-1`         | inset hairline + `0 1px 2px rgba(0,0,0,0.3)` | Buttons, cards                                                  |
| `--shadow-pop`       | `0 8px 24px rgba(0,0,0,0.4)` + inset hairline | Modal, toast, sidebar logo glow                              |

## Colour — Light theme

Overrides only the surface/text/shadow tokens (accent and status colours are shared with the dark theme):

| Token                | Hex                |
| -------------------- | ------------------ |
| `--bg`               | `#f6f7f8`          |
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

## Terminal ANSI palette

The terminal widget uses the curated 16-colour palette defined in **Spec §2.2.1** — that table is normative and takes precedence over anything in `styles.css`. Background / foreground per theme:

- Dark: bg `#1E1E1E`, fg `#D4D4D4`
- Light: bg `#FFFFFF`, fg `#1E1E1E`

See the spec for the full role mapping (black, red, green, yellow, blue, magenta, cyan, white, plus their bright variants on each theme).

## Spacing scale

| Token        | Default | Compact | Purpose                                                  |
| ------------ | ------- | ------- | -------------------------------------------------------- |
| `--pad-x`    | 18 px   | 14 px   | Module body horizontal padding                           |
| `--pad-y`    | 14 px   | 10 px   | Module body vertical padding                             |
| `--gap`      | 14 px   | 10 px   | Grid gaps between panels                                 |
| `--gap-sm`   | 8 px    | 6 px    | Small inline gaps                                        |
| `--row-h`    | 36 px   | 30 px   | Table row height                                         |
| `--radius`   | 6 px    | —       | Cards, modals, primary controls                          |
| `--radius-sm`| 4 px    | —       | Buttons, inputs, sidebar items, tags                     |

## Layout dimensions

| Token                   | Value  | Use                                |
| ----------------------- | ------ | ---------------------------------- |
| `--sidebar-w`           | 220 px | Expanded sidebar                   |
| `--sidebar-w-collapsed` | 56 px  | Collapsed sidebar (icon-only)      |
| `--titlebar-h`          | 38 px  | Custom titlebar height             |
| `--statusbar-h`         | 28 px  | Bottom status bar                  |

Window: default 1280 × 800, minimum 960 × 600 (Spec §2.1).

Sidebar collapses to icon-only when window width drops below 1280 px (Spec §2.1); the prototype animates this with a 180 ms ease transition on the `width` CSS property.

## Component patterns

The prototype defines reusable primitives that translate to QSS object names:

- **Buttons:** `.btn` (default), `.btn.primary` (accent fill, white text on cyan), `.btn.ghost` (transparent), `.btn.danger` (red text), `.btn.sm`, `.btn.icon-only`. Heights: 30 px default, 24 px small.
- **Inputs:** `.input`, `.select`, `.textarea` — 30 px height, surface fill, accent focus ring with 3 px faint shadow.
- **Cards:** `.card` with `.card-head` (uppercase 12 px label) and `.card-body`.
- **Tables:** `.table` with sticky header, hover row, accent-faint selected row, accent left rail on selection.
- **Pills:** `.pill` (status badges) with variants `online`, `offline`, `warn`, `danger`, `accent`.
- **Segmented control:** `.seg` — pill-shaped button group with active highlight.
- **Checkbox:** `.cb` 14×14 square, accent fill + checkmark when checked.
- **Progress bar:** `.bar` 6 px tall, accent fill by default, `warn`/`danger` variants.
- **Toast:** anchored bottom-right, slide-in animation. Variants: default, `success`, `warn`, `error`.
- **Modal:** centered overlay (rgba(0,0,0,0.55)), 440 px wide, `--shadow-pop`.

## Status indicators

- `.dot.online` — green with soft glow (`box-shadow: 0 0 6px oklch(0.74 0.16 145 / 0.6)`)
- `.dot.offline` — muted grey
- `.dot.warn` — amber
- Recording indicator: pulsing red dot (`@keyframes pulse`, 1.2 s)
- Cursor: 8 × 14 px solid accent block, blink at 1 s step-end

## Notes for QSS port

- OKLCH is not supported by Qt's QSS; precompute equivalents to sRGB hex at build time and emit those into the stylesheet. Document the OKLCH source values as comments next to the hex constants so they remain editable.
- Custom titlebar with traffic-light dots is a prototype affordance; the spec does not mandate a frameless window. The default is to use the native window frame unless the user requests otherwise.
- The prototype loads Geist over the network; for the desktop app, ship a bundled monospace (JetBrains Mono on Linux per §6.2) and rely on the system sans for the UI font. Do not require an internet connection for fonts.
