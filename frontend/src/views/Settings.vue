<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useAppStore } from "@/stores/app";

const bridge = useBridge();
const app = useAppStore();

const settings = ref<Record<string, any>>({});
const deps = ref<Array<{ component: string; installed: boolean; version: string; latest: string; status: string }>>([]);

async function reload() {
  settings.value = await bridge.settings.all();
  deps.value = await bridge.settings.dependencies();
}

onMounted(reload);

async function pick(key: "screenshots_folder" | "logcat_folder", title: string) {
  const next = await bridge.settings.pickFolder(title, settings.value[key] || "");
  if (next) {
    settings.value[key] = next;
    await bridge.settings.set(key, next);
  }
}

async function setTheme(mode: "light" | "system" | "dark") {
  await app.setTheme(mode);
}

async function onAdbTimeoutChange(v: string) {
  const n = parseInt(v, 10);
  if (Number.isFinite(n)) await bridge.settings.set("adb_timeout", n);
}
async function setLogLevel(e: Event) {
  await bridge.settings.set("log_level", (e.target as HTMLSelectElement).value);
}

function depBadge(d: { installed: boolean; version: string; latest: string; status: string }) {
  if (!d.installed) return { cls: "err", dot: "err", text: "Missing" };
  if (d.status === "outdated" || (d.latest && d.version && d.latest !== d.version))
    return { cls: "warn", dot: "warn", text: "Update available" };
  return { cls: "ok", dot: "ok", text: "Up to date" };
}

async function depAction(d: { installed: boolean; component: string }) {
  const b: any = bridge;
  if (!d.installed && b.settings?.installDependency) {
    await b.settings.installDependency(d.component);
  } else if (b.settings?.updateDependency) {
    await b.settings.updateDependency(d.component);
  }
  await reload();
}
async function checkForUpdates() {
  const b: any = bridge;
  if (b.settings?.checkDependencies) await b.settings.checkDependencies();
  await reload();
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Settings</h1>
    <span class="page-sub">App preferences &amp; dependencies</span>
  </div>

  <div class="grid gap-4" style="grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); align-items: stretch">
    <!-- LEFT: General -->
    <section class="card flex flex-col">
      <div class="card-h"><div class="label">General</div></div>
      <div class="card-b" style="flex:1; padding:0">
        <div class="meta-row">
          <span class="lbl">Theme</span>
          <div class="theme-btn-group" role="group">
            <button class="theme-btn" :aria-pressed="app.theme === 'light'" @click="setTheme('light')">Light</button>
            <button class="theme-btn" :aria-pressed="app.theme === 'system'" @click="setTheme('system')">Auto</button>
            <button class="theme-btn" :aria-pressed="app.theme === 'dark'" @click="setTheme('dark')">Dark</button>
          </div>
        </div>
        <div class="meta-row">
          <span class="lbl">Screenshots folder</span>
          <div class="row" style="gap:6px">
            <input class="input flex-1" v-model="settings.screenshots_folder" readonly />
            <button class="btn" @click="pick('screenshots_folder', 'Select Screenshots Folder')">Browse…</button>
          </div>
        </div>
        <div class="meta-row">
          <span class="lbl">Logcat folder</span>
          <div class="row" style="gap:6px">
            <input class="input flex-1" v-model="settings.logcat_folder" readonly />
            <button class="btn" @click="pick('logcat_folder', 'Select Logcat Folder')">Browse…</button>
          </div>
        </div>
        <div class="meta-row">
          <span class="lbl">ADB command timeout</span>
          <div class="row" style="gap:6px">
            <input class="input num" style="max-width:64px"
                   :value="settings.adb_timeout"
                   @change="onAdbTimeoutChange(($event.target as HTMLInputElement).value)" />
            <span class="hint">seconds</span>
          </div>
        </div>
        <div class="meta-row">
          <span class="lbl">Log level</span>
          <div class="row" style="gap:6px">
            <select class="select" style="max-width:130px"
                    :value="settings.log_level" @change="setLogLevel">
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>
      <div class="card-f">
        <div class="row" style="gap:10px; flex:1">
          <div class="app-ico" style="width:40px; height:40px; border-radius:10px">A</div>
          <div>
            <div class="font-semibold">ADB_Helper</div>
            <div class="hint">v{{ app.appVersion }} · Python 3.12 · PySide6 · Qt 6 · Vue 3</div>
          </div>
        </div>
      </div>
    </section>

    <!-- RIGHT: Installed dependencies -->
    <section class="card flex flex-col">
      <div class="card-h"><div class="label">Installed dependencies</div></div>
      <div class="card-b" style="padding:0; flex:1">
        <table class="table">
          <thead><tr>
            <th>Component</th>
            <th class="col-installed">Installed</th>
            <th class="col-latest">Latest</th>
            <th class="col-dep-status">Status</th>
            <th class="col-action-cell">Action</th>
          </tr></thead>
          <tbody>
            <tr v-for="d in deps" :key="d.component">
              <td>{{ d.component }}</td>
              <td>
                <span v-if="d.installed">{{ d.version || "yes" }}</span>
                <span v-else class="hint">Not installed</span>
              </td>
              <td>{{ d.latest || "—" }}</td>
              <td>
                <span class="badge" :class="depBadge(d).cls">
                  <span class="dot" :class="depBadge(d).dot"></span>
                  {{ depBadge(d).text }}
                </span>
              </td>
              <td>
                <button v-if="!d.installed" class="btn small btn-primary" @click="depAction(d)">Install</button>
                <button v-else-if="depBadge(d).text === 'Update available'" class="btn small" @click="depAction(d)">Update</button>
                <button v-else class="btn small" disabled>Update</button>
              </td>
            </tr>
            <tr v-if="!deps.length">
              <td colspan="5"><div class="empty">No dependencies registered.</div></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-f">
        <button class="btn small" @click="checkForUpdates">Check for updates</button>
      </div>
    </section>
  </div>
</template>
