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
const checked = ref<Set<string>>(new Set());

type SortCol = "package" | "status" | "type" | "size";
const sortCol = ref<SortCol>("package");
const sortAsc = ref(true);

const filtered = computed(() => {
  const list = apps.value
    .filter((a) => showSystem.value || a.type === "user")
    .filter((a) => showDisabled.value || a.status !== "disabled")
    .filter((a) => !search.value || a.package.toLowerCase().includes(search.value.toLowerCase()));
  const dir = sortAsc.value ? 1 : -1;
  const out = [...list];
  out.sort((a, b) => {
    let av: string | number = "";
    let bv: string | number = "";
    if (sortCol.value === "package") { av = a.package; bv = b.package; }
    else if (sortCol.value === "status") { av = a.status; bv = b.status; }
    else if (sortCol.value === "type") { av = a.type; bv = b.type; }
    else { av = sizeMb(a); bv = sizeMb(b); }
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av).localeCompare(String(bv)) * dir;
  });
  return out;
});

const selectedApp = computed(() => apps.value.find((a) => a.package === selectedPkg.value));

function sizeMb(a: AppEntry): number {
  const v = (a as any).size_mb;
  return typeof v === "number" ? v : 0;
}
function versionName(a: AppEntry): string {
  return (a as any).version_name || "";
}
function installDate(a: AppEntry): string { return (a as any).install_date || "—"; }
function updatedAt(a: AppEntry): string { return (a as any).updated_at || "—"; }
function uid(a: AppEntry): string { return (a as any).uid || "—"; }
function targetSdk(a: AppEntry): string { return (a as any).target_sdk || "—"; }
function minSdk(a: AppEntry): string { return (a as any).min_sdk || "—"; }
function apkSizeMb(a: AppEntry): string {
  const v = (a as any).apk_size_mb ?? (a as any).size_mb;
  return typeof v === "number" ? `${v.toFixed(1)} MB` : "—";
}
function dataSizeMb(a: AppEntry): string {
  const v = (a as any).data_size_mb;
  return typeof v === "number" ? `${v.toFixed(1)} MB` : "—";
}
function permsGranted(a: AppEntry): string {
  const v = (a as any).perms_granted;
  return typeof v === "number" ? String(v) : "—";
}
function permsDenied(a: AppEntry): string {
  const v = (a as any).perms_denied;
  return typeof v === "number" ? String(v) : "—";
}

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
    checked.value = new Set();
    await bridge.apps.loadAll(devices.active.serial);
  }
}
async function uninstall(pkg: string) {
  await bridge.apps.uninstall(pkg);
}

function toggleSort(col: SortCol) {
  if (sortCol.value === col) sortAsc.value = !sortAsc.value;
  else { sortCol.value = col; sortAsc.value = true; }
}
function sortAttr(col: SortCol) {
  if (sortCol.value !== col) return undefined;
  return sortAsc.value ? "ascending" : "descending";
}

function toggleCheck(pkg: string, v: boolean) {
  const s = new Set(checked.value);
  if (v) s.add(pkg); else s.delete(pkg);
  checked.value = s;
}
function toggleAll(v: boolean) {
  checked.value = v ? new Set(filtered.value.map((a) => a.package)) : new Set();
}
async function bulkDisable() {
  const pkgs = [...checked.value];
  const b: any = bridge.apps;
  if (b.bulkDisable) { await b.bulkDisable(pkgs); }
  else { for (const p of pkgs) await bridge.apps.disablePackage(p); }
}
async function bulkEnable() {
  const pkgs = [...checked.value];
  const b: any = bridge.apps;
  if (b.bulkEnable) { await b.bulkEnable(pkgs); }
  else { for (const p of pkgs) await bridge.apps.enablePackage(p); }
}
async function bulkDelete() {
  const pkgs = [...checked.value];
  const b: any = bridge.apps;
  if (b.bulkUninstall) { await b.bulkUninstall(pkgs); }
  else { for (const p of pkgs) await bridge.apps.uninstall(p); }
}
async function exportCsv() {
  const b: any = bridge.apps;
  if (b.exportCsv) await b.exportCsv([...checked.value]);
}

async function openApp() {
  const b: any = bridge.apps;
  if (selectedApp.value && b.open) await b.open(selectedApp.value.package);
}
async function forceStop() {
  const b: any = bridge.apps;
  if (selectedApp.value && b.forceStop) await b.forceStop(selectedApp.value.package);
}
async function clearData() {
  const b: any = bridge.apps;
  if (selectedApp.value && b.clearData) await b.clearData(selectedApp.value.package);
}
async function openFolder() {
  const b: any = bridge.apps;
  if (selectedApp.value && b.openFolder) await b.openFolder(selectedApp.value.package);
}

const ramPct = computed(() => ram.value.total ? Math.round(ram.value.used / ram.value.total * 100) : 0);
const storagePct = computed(() => storage.value.total ? Math.round(storage.value.used / storage.value.total * 100) : 0);

function fmtSize(mb: number) {
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`;
}
</script>

<template>
  <div class="flex flex-col flex-1 min-h-0">
    <div class="page-header" style="flex:none">
      <h1 class="page-title">Apps</h1>
      <span class="page-sub">{{ apps.length }} packages on device</span>
      <div class="page-actions">
        <button class="btn" :disabled="!devices.active" @click="refresh">Refresh</button>
      </div>
    </div>

    <section class="card" style="flex:none; margin-bottom:16px">
      <div class="card-b grid gap-6" style="grid-template-columns: 1fr 1fr">
        <div class="stat">
          <div class="flex items-baseline justify-between">
            <span class="lbl">RAM</span>
            <span class="hint">{{ ramPct }}%</span>
          </div>
          <div class="meter"><i class="meter-fill" :style="{ width: ramPct + '%' }"></i></div>
          <div class="val">Used {{ fmtSize(ram.used) }} / {{ fmtSize(ram.total) }}</div>
        </div>
        <div class="stat">
          <div class="flex items-baseline justify-between">
            <span class="lbl">Storage</span>
            <span class="hint">{{ storagePct }}%</span>
          </div>
          <div class="meter"><i class="meter-fill" :style="{ width: storagePct + '%' }"></i></div>
          <div class="val">Used {{ fmtSize(storage.used) }} / {{ fmtSize(storage.total) }}</div>
        </div>
      </div>
    </section>

    <div class="grid gap-4 flex-1 min-h-0" style="grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr)">
      <!-- LEFT: list -->
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
          <table class="table apps-table">
            <colgroup>
              <col class="col-check" />
              <col />
              <col class="col-status" />
              <col class="col-type" />
              <col class="col-mb" />
            </colgroup>
            <thead><tr>
              <th class="col-check">
                <input
                  type="checkbox" class="check"
                  :checked="filtered.length > 0 && checked.size === filtered.length"
                  :disabled="!filtered.length"
                  @change="toggleAll(($event.target as HTMLInputElement).checked)"
                />
              </th>
              <th class="sortable" :aria-sort="sortAttr('package')" @click="toggleSort('package')">Package name</th>
              <th class="col-status sortable" :aria-sort="sortAttr('status')" @click="toggleSort('status')">Status</th>
              <th class="col-type sortable" :aria-sort="sortAttr('type')" @click="toggleSort('type')">Type</th>
              <th class="col-mb sortable" :aria-sort="sortAttr('size')" @click="toggleSort('size')">Size, MB</th>
            </tr></thead>
            <tbody>
              <tr v-for="a in filtered" :key="a.package"
                  :class="selectedPkg === a.package ? 'selected' : ''"
                  class="cursor-pointer" @click="selectedPkg = a.package">
                <td @click.stop>
                  <input
                    type="checkbox" class="check"
                    :checked="checked.has(a.package)"
                    @change="toggleCheck(a.package, ($event.target as HTMLInputElement).checked)"
                  />
                </td>
                <td class="pkg-cell" :title="a.package"><span class="font-mono">{{ a.package }}</span></td>
                <td>
                  <span class="badge" :class="a.status === 'active' ? 'ok' : 'err'">
                    <span class="dot" :class="a.status === 'active' ? 'ok' : 'err'"></span>
                    {{ a.status === 'active' ? 'Active' : 'Disabled' }}
                  </span>
                </td>
                <td><span class="hint">{{ a.type }}</span></td>
                <td class="col-mb">{{ sizeMb(a).toFixed(1) }}</td>
              </tr>
              <tr v-if="!filtered.length"><td colspan="5"><div class="empty">No apps.</div></td></tr>
            </tbody>
          </table>
        </div>
        <div class="card-f">
          <button class="btn btn-danger small" :disabled="!checked.size" @click="bulkDelete">Delete</button>
          <button class="btn small" :disabled="!checked.size" @click="bulkDisable">Disable</button>
          <button class="btn small" :disabled="!checked.size" @click="bulkEnable">Enable</button>
          <button class="btn small" disabled title="Not implemented yet" @click="exportCsv">Export to CSV</button>
          <span class="hint" style="margin-left:auto">{{ apps.length }} apps loaded · {{ checked.size }} selected</span>
        </div>
      </section>

      <!-- RIGHT: details -->
      <aside class="card flex flex-col min-h-0 overflow-hidden">
        <div class="card-h"><div class="label">App details</div></div>
        <div v-if="selectedApp" class="card-b overflow-auto flex flex-col flex-1" style="padding:0; gap:0">
          <div class="grid items-center gap-3" style="grid-template-columns: 50px 1fr; padding:14px; border-bottom:1px solid var(--border)">
            <div class="app-ico">{{ selectedApp.package.slice(0, 2).toUpperCase() }}</div>
            <div>
              <div class="font-semibold text-md break-words">{{ selectedApp.name || selectedApp.package }}</div>
              <div class="text-text2 text-sm font-mono break-all">{{ selectedApp.package }}</div>
              <div class="row" style="gap:6px; margin-top:6px">
                <span class="badge" :class="selectedApp.status === 'active' ? 'ok' : 'err'">
                  <span class="dot" :class="selectedApp.status === 'active' ? 'ok' : 'err'"></span>
                  {{ selectedApp.status === 'active' ? 'Active' : 'Disabled' }}
                </span>
                <span class="badge">{{ selectedApp.type }}</span>
                <span v-if="versionName(selectedApp)" class="badge">v{{ versionName(selectedApp) }}</span>
              </div>
            </div>
          </div>

          <table class="detail-table">
            <tbody>
              <tr class="section-head"><td colspan="2">Installation</td></tr>
              <tr><td>Install date</td><td>{{ installDate(selectedApp) }}</td></tr>
              <tr><td>Updated</td><td>{{ updatedAt(selectedApp) }}</td></tr>
              <tr class="section-head"><td colspan="2">Properties</td></tr>
              <tr><td>UID</td><td>{{ uid(selectedApp) }}</td></tr>
              <tr><td>Target SDK</td><td>{{ targetSdk(selectedApp) }}</td></tr>
              <tr><td>Min SDK</td><td>{{ minSdk(selectedApp) }}</td></tr>
              <tr class="section-head"><td colspan="2">Storage</td></tr>
              <tr><td>APK size</td><td>{{ apkSizeMb(selectedApp) }}</td></tr>
              <tr><td>Data size</td><td>{{ dataSizeMb(selectedApp) }}</td></tr>
              <tr><td>Path</td><td class="break-all">{{ selectedApp.apk_path || "—" }}</td></tr>
              <tr class="section-head"><td colspan="2">Permissions</td></tr>
              <tr><td>Granted</td><td>{{ permsGranted(selectedApp) }}</td></tr>
              <tr><td>Denied</td><td>{{ permsDenied(selectedApp) }}</td></tr>
            </tbody>
          </table>
        </div>
        <div v-else class="card-b flex-1"><div class="empty">Select a package to view details</div></div>
        <div class="card-f">
          <button class="btn small" :disabled="!selectedApp" title="Not implemented yet" @click="openApp">Open</button>
          <button class="btn small" :disabled="!selectedApp" title="Not implemented yet" @click="forceStop">Force-stop</button>
          <button class="btn small" :disabled="!selectedApp" title="Not implemented yet" @click="clearData">Clear data</button>
          <button class="btn small" :disabled="!selectedApp" title="Not implemented yet" @click="openFolder">Open folder</button>
          <button v-if="selectedApp && selectedApp.type === 'user'"
                  class="btn btn-danger small" style="margin-left:auto"
                  @click="uninstall(selectedApp.package)">Uninstall</button>
        </div>
      </aside>
    </div>
  </div>
</template>
