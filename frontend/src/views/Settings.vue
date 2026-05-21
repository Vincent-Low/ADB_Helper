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

async function changeTheme(e: Event) {
  const v = (e.target as HTMLSelectElement).value as "system" | "light" | "dark";
  await app.setTheme(v);
}

async function onAdbTimeoutChange(v: string) {
  const n = parseInt(v, 10);
  if (Number.isFinite(n)) await bridge.settings.set("adb_timeout", n);
}
async function setLogLevel(e: Event) {
  await bridge.settings.set("log_level", (e.target as HTMLSelectElement).value);
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Settings</h1>
    <span class="page-sub">App preferences & dependencies</span>
  </div>

  <section class="card">
    <div class="card-h"><div class="label">About</div></div>
    <div class="card-b flex items-center gap-3">
      <div class="app-ico" style="width:40px; height:40px; border-radius:10px">A</div>
      <div>
        <div class="font-semibold">ADB_Helper</div>
        <div class="hint">v{{ app.appVersion }} · Python 3.12 · PySide6 · Qt 6 · Vue 3</div>
      </div>
    </div>
  </section>

  <section class="card mt-4">
    <div class="card-h"><div class="label">Installed dependencies</div></div>
    <div class="card-b" style="padding:0">
      <table class="table">
        <thead><tr><th>Component</th><th>Installed</th><th class="w-24">Status</th></tr></thead>
        <tbody>
          <tr v-for="d in deps" :key="d.component">
            <td>{{ d.component }}</td>
            <td><span class="hint">{{ d.installed ? (d.version || "yes") : "Not installed" }}</span></td>
            <td>
              <span class="badge" :class="d.installed ? 'ok' : 'err'">
                <span class="dot" :class="d.installed ? 'ok' : 'err'"></span>
                {{ d.installed ? "Installed" : "Missing" }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="card-f">
      <button class="btn small" @click="reload">Re-check</button>
    </div>
  </section>

  <section class="card mt-4">
    <div class="card-h"><div class="label">General</div></div>
    <div class="card-b">
      <div class="grid items-center gap-3 py-1.5" style="grid-template-columns: 200px 1fr">
        <div class="text-text2 text-sm">Theme</div>
        <select class="select max-w-[260px]" :value="app.theme" @change="changeTheme">
          <option value="system">Auto (follow system)</option>
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </select>

        <div class="text-text2 text-sm">Screenshots folder</div>
        <div class="flex gap-1.5">
          <input class="input flex-1" v-model="settings.screenshots_folder" readonly />
          <button class="btn" @click="pick('screenshots_folder', 'Select Screenshots Folder')">Browse…</button>
        </div>

        <div class="text-text2 text-sm">Logcat folder</div>
        <div class="flex gap-1.5">
          <input class="input flex-1" v-model="settings.logcat_folder" readonly />
          <button class="btn" @click="pick('logcat_folder', 'Select Logcat Folder')">Browse…</button>
        </div>

        <div class="text-text2 text-sm">ADB command timeout</div>
        <div class="flex gap-1.5 items-center">
          <input class="input num" :value="settings.adb_timeout" @change="onAdbTimeoutChange(($event.target as HTMLInputElement).value)" />
          <span class="hint">seconds</span>
        </div>

        <div class="text-text2 text-sm">Log level</div>
        <select class="select max-w-[260px]" :value="settings.log_level" @change="setLogLevel">
          <option value="debug">Debug</option><option value="info">Info</option>
          <option value="warning">Warning</option><option value="error">Error</option>
        </select>
      </div>
    </div>
  </section>
</template>
