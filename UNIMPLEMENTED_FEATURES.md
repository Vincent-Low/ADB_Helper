# UNIMPLEMENTED_FEATURES — design.html gaps (May 2026 redesign)

Список UI/UX, который зафиксирован в новом `design.html` + `handoff.md`
(handoff от **May 2026**, расположен в `/tmp/design_handoff/adb-helper/`), но
**не закрыт** текущим бэкендом (`qt-bridge`). UI отрисован по дизайну, кнопки
помечены `disabled` + `title="Not implemented yet"` и/или вызывают опциональные
slot'ы через `(bridge as any).xxx?.method?.()`.

> Источники: `design.html`, `handoff.md`, [src/types/qt-bridge.d.ts](frontend/src/types/qt-bridge.d.ts).

---

## 1. Connections

| Дизайн | Статус | Нужно |
|---|---|---|
| Кнопка `Scan network` в page-actions | **отсутствует в bridge** | новый slot `connections.scanNetwork()` + сигнал `scanResult`. UI рендерится `disabled` с tooltip. |
| Колонка `Connection port` — авто-save в SQLite по изменению | реализовано: `@change` вызывает `connections.savePaired(ip, alias, port)` после валидации через `sanitizePort` / `isValidPort` | — |
| Поля ввода: IPv4 + port + PIN | реализовано: `useInputFilters.ts` — `sanitizeIPv4Partial`, `sanitizePort`, `sanitizeDigits`, `isValidIPv4`, `isValidPort`. Pair-btn / Connect-btn активны только при пройденной валидации | — |
| Empty-state «1 device · connected via Wi-Fi» | сделано, текст зависит от `connection_type` | — |

## 2. Terminal

| Дизайн | Статус | Нужно |
|---|---|---|
| Page-actions кнопка `History` | **нет** | `terminal.history()` уже есть, нужно открывать `<dialog>` / список. UI рендерится `disabled`. |
| Карточка справа: `● Record Macro` / `▶ Play` | UI готов; `Record Macro` стоит **disabled** (нет API), `Play` запускает первый сохранённый макрос (`bridge.terminal.write` цепочкой) | новый slot `terminal.startRecord()` / `stopRecord()` для записи. |
| Подсказка `UTF-8 · 80 cols` | hard-coded | опционально подтягивать ширину из xterm. |
Сам терминал перестал работать. Скорее всего после имплементарции дизайна. Нужно вернуть терминал в рабочее состояние созласно его изначальному назначению: interactive ADB shell terminal for executing commands manually and managing macros. The terminal is always an `adb shell` session on the active device — it is not a general OS shell.

## 3. Installer

| Дизайн | Статус | Нужно |
|---|---|---|
| Чекбокс-колонка в `Files to install` | реализовано: `selectedFiles: Set<string>`, header-checkbox toggle-all, `Remove` (selected) + `Clear` (all) | — |
| Колонка `Size` | сейчас «—» | расширить `installer.pickFiles()` чтобы возвращать `{path, size_bytes}`, либо отдельный slot `installer.statFile(path)`. |
| Прогресс-бар (file × device) | визуально готов, считается по jobs.size; per-byte прогресс из adb stdout не парсится | опционально парсить `adb install` stdout. |
| Состояния `install-status` (idle/running/done/error) | сделано, ОК. | — |
| Кнопка `Cancel` → `bridge.installer.cancelAll()` | реализовано (`cancelInstall`) | — |
| Drop-target | `@dragover.prevent` + `@drop` навешан на card | bridge принимает paths через `filesDropped` сигнал на стороне Qt drag-handlerа. |

## 4. Scrcpy

| Дизайн | Статус | Нужно |
|---|---|---|
| Селект `Orientation` со значениями `Auto / Portrait / Landscape` | приведено в соответствие (`Auto` / `Portrait` (0°) / `Landscape` (90°)) | — |
| Чекбоксы Stay awake / Show touches / Turn screen off — горизонтальной строкой | сделано (`flex flex-wrap gap-3.5`) | — |
| Launch только в page-actions | сделано | — |
| Подсказка `scrcpy v4.0 · ready` | подставляется в page-sub | — |

## 5. Device Buttons

| Дизайн | Статус | Нужно |
|---|---|---|
| Кнопка `Reboot` без выпадающего списка (Normal/Bootloader/Recovery) | реализовано: при клике открывается локальное меню из 3 пунктов; bridge.reboot(mode) уже умеет все три | — |
| Tile-кнопки иконками-глифами | сделано (Home/Back/Recent/Vol+/Vol−/Mute/Camera/Power + Reboot/Screenshot/Rotate) | — |
| 4-col grid всегда | сделано | — |

## 6. Device Info

| Дизайн | Статус | Нужно |
|---|---|---|
| Two-col layout (Device+CPU+GPU слева, System справа) | сделано | — |
| Page-actions кнопка `Export to TXT` | **bridge slot отсутствует** | новый slot `info.exportTxt(serial, path)`. UI рендерится `disabled`. |
| Секции с `section-head` строками (Version / Build / Firmware) | реализовано **локально** (`SYSTEM_SUBSECTIONS` в `DeviceInfo.vue`) — разбивает плоский список полей в System на 3 sub-section по именам полей. Полей вне известного списка попадают в «Other» | предпочтительно: расширить `InfoSection` сабсекциями: `{ title, subsections: [{ name, fields[] }] }` чтобы группировка приходила с бэка. |

## 7. Apps

| Дизайн | Статус | Нужно |
|---|---|---|
| Чекбокс-колонка + bulk-action footer слева: `Delete / Disable / Enable / Export to CSV` + counter `N apps loaded · M selected` | UI сделан полностью; `Delete/Disable/Enable` — fallback цикл по per-pkg слотам; `Export to CSV` — **disabled** | bridge: `apps.bulkDisable(pkgs)` / `bulkEnable(pkgs)` / `bulkUninstall(pkgs)` / `exportCsv(pkgs, dest)`. |
| Колонка `Size, MB` (sortable) | UI выводит `sizeMb(a).toFixed(1)`; читает `(a as any).size_mb` | расширить `AppEntry` полем `size_mb: number`. |
| Sortable headers (Package / Status / Type / Size) | реализовано на клиенте — `sortCol` / `sortAsc` + `aria-sort` | — |
| Колонка `Status` с зелёным badge `Active` / красным `Disabled` | сделано. | — |
| Детальная панель: секции `Installation / Properties / Storage / Permissions` | UI отрисован, читает `install_date / updated_at / uid / target_sdk / min_sdk / apk_size_mb / data_size_mb / perms_granted / perms_denied` через `(a as any)` | расширить `AppEntry`: `install_date, updated_at, uid, target_sdk, min_sdk, apk_size_mb, data_size_mb, perms_granted, perms_denied`. |
| Кнопки в детальном footer'е: `Open / Force-stop / Clear data / Open folder` | UI рендерится с `disabled+title`; вызовы через `(bridge.apps as any).{open,forceStop,clearData,openFolder}?.()` если slot появится | bridge: `apps.open(pkg)`, `forceStop(pkg)`, `clearData(pkg)`, `openFolder(pkg)`. |
| `version` в badge | UI читает `(a as any).version_name`; пока пусто | расширить `AppEntry` полем `version_name`. |
| Empty-state правой панели «Select a package to view details» | сделано | — |

## 8. Logcat

| Дизайн | Статус | Нужно |
|---|---|---|
| Кнопка `Open folder` рядом с Export | UI сделан, вызывает `(bridge.logcat as any).openFolder?.()` | новый slot `logcat.openFolder()` (через `QDesktopServices.openUrl` на бэке). |
| Recent exports: колонка действий (открыть файл / открыть папку / удалить) | **нет** | bridge: `logcat.openFile(path)`, `logcat.deleteExport(path)`. |
| Сноска `Timezone GMT+N` | считается на клиенте через `getTimezoneOffset()` | — |

## 9. Settings

| Дизайн | Статус | Нужно |
|---|---|---|
| Поле `Theme` через `theme-btn-group` (Light / Auto / Dark) | сделано, использует `app.setTheme` | — |
| Кнопка `Open logs folder` рядом с Log level select | UI добавлен `disabled+title`, вызывает `(bridge.settings as any).openLogsFolder?.()` | новый slot `settings.openLogsFolder()`. |
| Кнопка `Open app folder` в `card-f` | UI добавлен `disabled+title`, вызывает `(bridge.settings as any).openAppFolder?.()` | новый slot `settings.openAppFolder()`. |
| `Check for updates` (footer Installed dependencies) | UI вызывает `(bridge.settings as any).checkDependencies?.()` | slot `settings.checkDependencies()` (сигнал `depsChecked` в типах есть). |
| Колонка `Action` (Install / Update per-row) | UI вызывает `(bridge.settings as any).{installDependency,updateDependency}?.(component)` | slot'ы `installDependency(component)` / `updateDependency(component)`. |
| ADB timeout — только цифры, до 4 знаков | реализовано через inline replace `/\D+/g, ''` и `maxlength=4` | — |

## 10. Status bar

| Дизайн | Статус | Нужно |
|---|---|---|
| Battery indicator (svg + проценты) | UI читает `(active as any).battery_pct` | расширить `DeviceContext` полем `battery_pct: number`; пушить из `device_monitor` (`adb shell dumpsys battery`). |
| `Android <ver> · API <n>` | UI читает `(active as any).api_level` | расширить `DeviceContext` полем `api_level: number` (из `ro.build.version.sdk`). |
| `ADB running/stopped` справа | hard-coded `running` | новый сигнал `adb_service.daemonStateChanged` → store → StatusBar. |

---

## 11. Не-UI задачи (PySide6-only) — нерелевантно для Vue-стека

Эти пункты handoff.md писались под Qt-нативный фронт; в Vue-стеке они не применимы:

- `QPalette` для нативных диалогов
- `QSS` шаблоны / `variant=primary` properties
- `QFileDialog` системные (вызываются через bridge.settings.pickFolder)
- ConPTY / `pty` shim'ы (на стороне Python-процесса терминала)

---

## Приоритет (рекомендация)

1. **P0** — расширить `DeviceContext` (`battery_pct`, `api_level`) + `AppEntry` (`size_mb`, `version_name`, `install_date`, `updated_at`, `uid`, `target_sdk`, `min_sdk`, `apk_size_mb`, `data_size_mb`, `perms_granted`, `perms_denied`). Без этого статусбар и Apps выглядят полупустыми.
2. **P0** — open-folder slots: `logcat.openFolder`, `settings.openLogsFolder`, `settings.openAppFolder`, `apps.openFolder`. Тривиально (`QDesktopServices.openUrl`).
3. **P0** — `apps.open / forceStop / clearData` через `adb shell am`.
4. **P1** — Installer file-size (`installer.pickFiles` → `{path, size}`); bulk-actions для Apps (`bulkDisable/Enable/Uninstall`), `exportCsv`.
5. **P1** — Dependencies install/update/check slot'ы (`settings.installDependency / updateDependency / checkDependencies`).
6. **P2** — Device Info `info.exportTxt`, иерархическая структура `InfoSection` с subsections.
7. **P2** — Logcat per-row actions (`openFile`, `deleteExport`).
8. **P3** — Terminal: macro recording (`terminal.startRecord / stopRecord`), History dialog UI; Connections `scanNetwork`.
9. **P3** — ADB-daemon state signal в status bar (`daemonStateChanged`).
