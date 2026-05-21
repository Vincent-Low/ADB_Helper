# UNIMPLEMENTED_FEATURES — design.html gaps

Список UI/UX, который зафиксирован в `design.html` и `adb-helper_handoff_Claude_Design/project/handoff.md`, но **не закрыт** текущим бэкендом (`qt-bridge`). Все эти места в Vue-фронте уже отрисованы по дизайну, но кнопки/значения не подключены к реальным сигналам / Slot'ам.

> Источники: `design.html`, [handoff.md](/tmp/design_bundle/adb-helper/project/handoff.md), [src/types/qt-bridge.d.ts](frontend/src/types/qt-bridge.d.ts).

---

## 1. Connections

| Дизайн | Статус | Нужно |
|---|---|---|
| Кнопка `Scan network` в page-actions | **отсутствует в bridge** | новый slot `connections.scanNetwork()` + сигнал `scanResult`. |
| Колонка `Connection port` редактируемая, авто-save | частично — `<input>` показывается, но `@change` не сохраняет порт | использовать `connections.savePaired(ip, alias, port)` при изменении. |
| Empty-state «1 device · connected via Wi-Fi» в `card-f` | сделано визуально, текст зависит от `connection_type` поля | поле есть, ок. |

## 2. Terminal

| Дизайн | Статус | Нужно |
|---|---|---|
| Карточка справа: кнопки `● Record Macro` / `▶ Play` (top of macros) | **нет UI и нет API** | добавить кнопки + bridge `terminal.startRecord()` / `stopRecord()` (сейчас есть только saveMacro/listMacros). |
| Page-actions кнопка `History` | **нет** | `terminal.history()` уже есть, нужно открывать `<dialog>` / список. |
| Подсказка `UTF-8 · 80 cols` | hard-coded | можно опционально подтягивать ширину терминала. |

## 3. Installer

| Дизайн | Статус | Нужно |
|---|---|---|
| Чекбокс-колонка в `Files to install` (select multiple → массовый Remove) | **нет** | добавить per-file `selected: Set<string>` + `card-f` кнопка `Remove` поверх существующего `Clear`. |
| Колонка `Size` | сейчас «—» | `installer.pickFiles()` должен возвращать `{path, size}`. |
| Прогресс-бар в строке `Install / Cancel / progress / 0%` | визуально готов, считается по jobs.size | сейчас по jobs.done, ок; но per-byte прогресс из adb stdout не парсится. |
| Состояния `install-status` (idle/running/done/error) | визуально + переключаются — ОК. |
| `bridge.installer.cancel(cmd_id)` уже есть, кнопка `Cancel` в Installation card | **не вызывает cancelAll** | привязать `Cancel` → `bridge.installer.cancelAll()`. |

## 4. Scrcpy

| Дизайн | Статус | Нужно |
|---|---|---|
| Селект `Orientation` со значениями `Auto / Portrait / Landscape` | сейчас 0°/90°/180°/270° | привести значения в соответствие или оставить — дизайн не догма (это `<select>`). |
| Подсказка `scrcpy v4.0 · ready` в page-sub | сейчас «status», ок. |

## 5. Device Buttons

| Дизайн | Статус | Нужно |
|---|---|---|
| Кнопка `Reboot` без выпадающего (normal/bootloader/recovery) | в коде вызывается только `reboot('normal')` | добавить меню/диалог: 3 режима. Bridge.reboot уже поддерживает 3 mode. |
| Tile-кнопки иконками-глифами (`⌂`, `‹`, `▭`, `+`, `−`, `✕`, `◉`, `⏻`, `↻`, `▣`, `⤿`) | сделано, ОК. |

## 6. Device Info

| Дизайн | Статус | Нужно |
|---|---|---|
| Page-actions кнопка `Export to TXT` | **нет** | новый slot `info.exportTxt(serial, path)`. |
| Секции с `section-head` строками (Version / Build / Firmware) | визуально через `detail-table.section-head` — сейчас не подаются с бэка, секции одного уровня | расширить `InfoSection` сабсекциями: `{ title, subsections: [{ name, fields[] }] }`. |

## 7. Apps

| Дизайн | Статус | Нужно |
|---|---|---|
| Bulk-action footer слева: `Delete / Disable / Enable / Export to CSV` + counter `503 apps loaded · 0 selected` | сейчас только counter | добавить чекбокс-колонку + `bridge.apps.bulkDisable(pkgs)` / `bulkUninstall(pkgs)` / `exportCsv(pkgs, dest)`. |
| Колонка `Size, MB` (sortable) | **нет в `AppEntry`** | расширить `AppEntry` полем `size_mb: number`. |
| Колонка `Status` с зелёным badge `Active` (вместо текста disabled/active) | сделано. |
| Детальная панель: секции `Installation / Properties / Storage / Permissions` (install date, target SDK, granted/denied perms, path, apk size, data size) | сейчас выводится только `apk_path` | расширить `AppEntry`: `install_date, updated_at, uid, target_sdk, min_sdk, apk_size_mb, data_size_mb, perms_granted, perms_denied`. |
| Кнопки в детальном footer'е: `Open / Force-stop / Clear data / Open folder` | **нет slot'ов** | `bridge.apps.open(pkg)`, `forceStop(pkg)`, `clearData(pkg)`, `openFolder(pkg)`. |
| `version` в badge | **нет в AppEntry** | добавить `version_name`. |

## 8. Logcat

| Дизайн | Статус | Нужно |
|---|---|---|
| Кнопка `Open folder` рядом с Export | **нет в bridge** | новый slot `logcat.openFolder()` (использует `QDesktopServices.openUrl` на бэке). |
| Recent exports: колонка действий (открыть файл / открыть папку / удалить) | **нет** | `logcat.openFile(path)`, `logcat.deleteExport(path)`. |
| Сноска `Timezone GMT+N` | сейчас считается на клиенте через `getTimezoneOffset()` — ОК на десктопе. |

## 9. Settings

| Дизайн | Статус | Нужно |
|---|---|---|
| `Check for updates` кнопка | **нет в bridge** | `settings.checkDependencies()` + сигнал `depsChecked` (сигнал в типах есть, slot отсутствует). |
| Колонка `Action` с кнопками `Install` / `Update` (per-row) | визуально готово, обработчики дергают `b.settings.installDependency` / `updateDependency` — **slot'ов нет**. | добавить `installDependency(component)` / `updateDependency(component)`. |
| Кнопка `Open logs folder` рядом с Log level | **нет** | `settings.openLogsFolder()`. |
| Кнопка `Open app folder` в About | **нет** | `settings.openAppFolder()`. |
| Поле `Theme` через `theme-btn-group` (Light / Auto / Dark) | сделано, использует `app.setTheme`. |

## 10. Status bar

| Дизайн | Статус | Нужно |
|---|---|---|
| Battery indicator (svg + проценты) | визуально готов, читает `active.battery_pct` | **`DeviceContext` не содержит `battery_pct`** — расширить тип + push из `device_monitor` через `adb shell dumpsys battery`. |
| `Android <ver> · API <n>` | визуально готов, читает `api_level` | **нет поля `api_level` в `DeviceContext`** — добавить (из `ro.build.version.sdk`). |
| `ADB running/stopped` справа | hard-coded `running` | нужен сигнал `adb_service.daemonStateChanged` → store → StatusBar. |

---

## 11. Не-UI задачи из handoff.md, не имеющие к нам прямого отношения (PySide6-only)

Эти пункты handoff.md писались под Qt-нативный фронт и **в Vue-стеке неактуальны**, оставляю как референс на случай отката стека:

- `QPalette` для нативных диалогов
- `QSS` шаблон, properties для `variant=primary`
- `QFileDialog` системные
- ConPTY / `pty` shim'ы

---

## Приоритет (рекомендация)

1. **P0** — расширить `DeviceContext` (battery_pct, api_level) + `AppEntry` (size_mb, version_name, install_date, sizes). Без этого статусбар и Apps выглядят полупустыми.
2. **P0** — `logcat.openFolder`, `settings.openLogsFolder/openAppFolder`, `apps.open/forceStop/clearData`. Тривиально, на бэке `QDesktopServices` + `adb shell am`.
3. **P1** — Installer file-size, multi-select files, `cancelAll()`.
4. **P1** — Dependencies install/update/check slot'ы.
5. **P2** — Device Info export TXT, sub-section structure.
6. **P2** — Apps bulk actions, CSV export.
7. **P3** — Terminal macro recording, History dialog, Scan network.
