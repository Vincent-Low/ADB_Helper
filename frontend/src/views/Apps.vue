<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";
import type { AppEntry } from "@/types/qt-bridge";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

const apps = ref<AppEntry[]>([]);
const ram = ref({ used: 0, total: 0 });
const storage = ref({ used: 0, total: 0 });
const search = ref("");
const showSystem = ref(true);
const showDisabled = ref(true);
const selectedPkg = ref<string | null>(null);

const filtered = computed(() =>
  apps.value
    .filter((a) => showSystem.value || a.type === "user")
    .filter((a) => showDisabled.value || a.status !== "disabled")
    .filter((a) => !search.value || a.package.toLowerCase().includes(search.value.toLowerCase()))
);

const selectedApp = computed(() => apps.value.find((a) => a.package === selectedPkg.value));

onMounted(() => {
  on(bridge.apps.listLoaded, (d) => {
    apps.value = d.apps;
    if (apps.value.length && !selectedPkg.value) selectedPkg.value = apps.value[0].package;
  });
  on(bridge.apps.appUpdated, (entry) => {
    const idx = apps.value.findIndex((a) => a.package === entry.package);
    if (idx >= 0) apps.value[idx] = entry;
  });
  on(bridge.apps.metersUpdated, (m) => {
    if (m.kind === "ram") ram.value = { used: m.used_mb, total: m.total_mb };
    else storage.value = { used: m.used_mb, total: m.total_mb };
  });

  if (devices.active) bridge.apps.loadAll(devices.active.serial);
});

watch(() => devices.active?.serial, (serial) => {
  if (serial) bridge.apps.loadAll(serial);
});

async function refresh() {
  if (devices.active) {
    apps.value = [];
    await bridge.apps.loadAll(devices.active.serial);
  }
}
async function uninstall(pkg: string) {
  await bridge.apps.uninstall(pkg);
}
async function toggleDisable(a: AppEntry) {
  if (a.status === "disabled") await bridge.apps.enablePackage(a.package);
  else await bridge.apps.disablePackage(a.package);
}

const ramPct = computed(() => ram.value.total ? Math.round(ram.value.used / ram.value.total * 100) : 0);
const storagePct = computed(() => storage.value.total ? Math.round(storage.value.used / storage.value.total * 100) : 0);

function fmtSize(mb: number) {
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`;
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Apps</h1>
    <span class="page-sub">{{ apps.length }} packages on device</span>
    <div class="page-actions">
      <button class="btn" :disabled="!devices.active" @click="refresh">Refresh</button>
    </div>
  </div>

  <section class="card">
    <div class="card-b grid gap-6 items-center" style="grid-template-columns: 1fr 1fr">
      <div class="stat">
        <div class="lbl">RAM</div>
        <div class="progress"><i :style="{ width: ramPct + '%' }"></i></div>
        <div class="val">Used {{ fmtSize(ram.used) }} / {{ fmtSize(ram.total) }}</div>
      </div>
      <div class="stat">
        <div class="lbl">Storage</div>
        <div class="progress"><i :style="{ width: storagePct + '%' }"></i></div>
        <div class="val">Used {{ fmtSize(storage.used) }} / {{ fmtSize(storage.total) }}</div>
      </div>
    </div>
  </section>

  <div class="grid gap-4 mt-4" style="grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); height: calc(100vh - 360px); min-height: 480px;">
    <section class="card flex flex-col min-h-0">
      <div class="card-h">
        <div class="label">Packages</div>
        <div class="right"><span class="hint">{{ filtered.length }} apps</span></div>
      </div>
      <div class="toolbar-row">
        <input class="input flex-1" placeholder="Search by package…" v-model="search" />
        <label class="switch-label"><input type="checkbox" class="check" v-model="showSystem" /> Show system apps</label>
        <label class="switch-label"><input type="checkbox" class="check" v-model="showDisabled" /> Show disabled apps</label>
      </div>
      <div class="flex-1 overflow-auto">
        <table class="table">
          <thead><tr>
            <th class="sortable">Package name</th>
            <th class="col-status sortable">Status</th>
            <th class="col-type sortable">Type</th>
          </tr></thead>
          <tbody>
            <tr v-for="a in filtered" :key="a.package"
                :class="selectedPkg === a.package ? 'selected' : ''"
                class="cursor-pointer" @click="selectedPkg = a.package">
              <td><span class="font-mono">{{ a.package }}</span></td>
              <td>
                <span class="badge" :class="a.status === 'active' ? 'ok' : 'err'">
                  <span class="dot" :class="a.status === 'active' ? 'ok' : 'err'"></span>
                  {{ a.status === 'active' ? 'Active' : 'Disabled' }}
                </span>
              </td>
              <td><span class="hint">{{ a.type }}</span></td>
            </tr>
            <tr v-if="!filtered.length"><td colspan="3"><div class="empty">No apps.</div></td></tr>
          </tbody>
        </table>
      </div>
      <div class="card-f">
        <span class="hint">{{ apps.length }} apps loaded · {{ filtered.length }} shown</span>
      </div>
    </section>

    <aside class="card flex flex-col min-h-0 overflow-hidden">
      <div class="card-h"><div class="label">App details</div></div>
      <div v-if="selectedApp" class="card-b overflow-auto flex flex-col" style="padding:0">
        <div class="grid items-center gap-3" style="grid-template-columns: 50px 1fr; padding: 14px; border-bottom: 1px solid var(--border)">
          <div class="app-ico">{{ selectedApp.package.slice(0, 2).toUpperCase() }}</div>
          <div>
            <div class="font-semibold text-md break-words">{{ selectedApp.name || selectedApp.package }}</div>
            <div class="text-text2 text-sm font-mono break-all">{{ selectedApp.package }}</div>
            <div class="row" style="gap:6px; margin-top:6px">
              <span class="badge" :class="selectedApp.status === 'active' ? 'ok' : 'err'">
                <span class="dot" :class="selectedApp.status === 'active' ? 'ok' : 'err'"></span>
                {{ selectedApp.status }}
              </span>
              <span class="badge">{{ selectedApp.type }}</span>
            </div>
          </div>
        </div>

        <table class="detail-table">
          <tbody>
            <tr class="section-head"><td colspan="2">Storage</td></tr>
            <tr><td>APK path</td><td>{{ selectedApp.apk_path || "—" }}</td></tr>
          </tbody>
        </table>
      </div>
      <div v-else class="card-b flex-1"><div class="empty">Select an app.</div></div>
      <div class="card-f">
        <button v-if="selectedApp"
          class="btn small"
          @click="toggleDisable(selectedApp)"
        >{{ selectedApp.status === 'disabled' ? 'Enable' : 'Disable' }}</button>
        <button v-if="selectedApp && selectedApp.type === 'user'"
          class="btn btn-danger small" style="margin-left:auto"
          @click="uninstall(selectedApp.package)"
        >Uninstall</button>
      </div>
    </aside>
  </div>
</template>
