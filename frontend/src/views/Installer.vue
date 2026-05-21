<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

interface JobRow {
  file: string;
  serial: string;
  status: "queued" | "running" | "ok" | "fail";
  message?: string;
  cmd_id?: string;
}

const files = ref<string[]>([]);
const selected = ref<Set<string>>(new Set());
// Sequential dispatcher: rows are seeded by `file|serial` BEFORE cmd_ids
// are known.  installStarted fills in the cmd_id and flips to "running".
const jobs = ref<Map<string, JobRow>>(new Map());
const cmdToKey = ref<Map<string, string>>(new Map());
const running = ref(false);
const dragging = ref(false);
const idleStatus = "Idle — add files and select a target device to begin.";
const status = ref(idleStatus);

function pairKey(file: string, serial: string) {
  return `${file}|${serial}`;
}

onMounted(() => {
  on(bridge.installer.filesDropped, (paths) => {
    for (const p of paths) {
      if (!files.value.includes(p)) files.value.push(p);
    }
    refreshStatus();
  });
  on(bridge.installer.installStarted, (payload) => {
    const key = pairKey(payload.file, payload.serial);
    cmdToKey.value.set(payload.cmd_id, key);
    const j = jobs.value.get(key);
    if (j) {
      j.cmd_id = payload.cmd_id;
      j.status = "running";
      jobs.value = new Map(jobs.value);
    }
  });
  on(bridge.installer.installFinished, (cid, res) => {
    const key = cmdToKey.value.get(cid);
    if (key) {
      const j = jobs.value.get(key);
      if (j) {
        j.status = res.status === "succeeded" ? "ok" : "fail";
        j.message = (res.stdout || res.stderr || "").trim();
        jobs.value = new Map(jobs.value);
      }
    }
    maybeDone();
  });
  on(bridge.installer.installFailed, (cid, res) => {
    const key = cmdToKey.value.get(cid);
    if (key) {
      const j = jobs.value.get(key);
      if (j) {
        j.status = "fail";
        j.message = (res.stderr || res.status || "Failed.").trim();
        jobs.value = new Map(jobs.value);
      }
    }
    maybeDone();
  });
  on(bridge.installer.queueDrained, () => {
    running.value = false;
    status.value = "Done.";
  });
});

function maybeDone() {
  const pending = [...jobs.value.values()].some(
    (x) => x.status === "queued" || x.status === "running",
  );
  if (!pending) {
    running.value = false;
    status.value = "Done.";
  }
}

const targetCount = computed(() => Array.from(selected.value).length);

async function addFiles() {
  const picked = await bridge.installer.pickFiles();
  for (const p of picked) if (!files.value.includes(p)) files.value.push(p);
  refreshStatus();
}
function cancelJobsForFile(path: string) {
  for (const j of jobs.value.values()) {
    if (j.file === path && j.cmd_id && (j.status === "queued" || j.status === "running")) {
      bridge.installer.cancel(j.cmd_id);
    }
  }
}
function removeFile(path: string) {
  cancelJobsForFile(path);
  files.value = files.value.filter((p) => p !== path);
  refreshStatus();
}
function clearFiles() {
  for (const p of files.value) cancelJobsForFile(p);
  files.value = [];
  refreshStatus();
}

function toggleTarget(serial: string, checked: boolean) {
  const s = new Set(selected.value);
  if (checked) s.add(serial); else s.delete(serial);
  selected.value = s;
  refreshStatus();
}

function refreshStatus() {
  if (running.value) return;
  if (!files.value.length || !targetCount.value) {
    status.value = idleStatus;
  } else {
    status.value = `Ready — ${files.value.length} file(s) × ${targetCount.value} device(s).`;
  }
}

async function install() {
  if (!files.value.length || !targetCount.value) return;
  running.value = true;
  status.value = "Installing…";
  // Seed all rows as "queued"; cmd_ids arrive via installStarted as the
  // sequential dispatcher drains the queue per device.
  const next = new Map<string, JobRow>();
  for (const f of files.value) {
    for (const serial of selected.value) {
      next.set(pairKey(f, serial), { file: f, serial, status: "queued" });
    }
  }
  jobs.value = next;
  cmdToKey.value = new Map();
  await bridge.installer.installFiles([...files.value], [...selected.value]);
}

function dragOver(e: DragEvent) { e.preventDefault(); dragging.value = true; }
function dragLeave() { dragging.value = false; }
function drop(e: DragEvent) { e.preventDefault(); dragging.value = false; }

function statusLabel(s: string) {
  return s === "ok" ? "Success" : s === "fail" ? "Failed" : s === "running" ? "Installing…" : "Pending";
}
function badgeClass(s: string) {
  return s === "ok" ? "ok" : s === "fail" ? "err" : s === "running" ? "warn" : "";
}
function fileName(p: string) { return p.split(/[\\/]/).pop() || p; }
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Installer</h1>
    <span class="page-sub">Install APK / AAB on selected devices</span>
  </div>

  <section
    class="card"
    @dragover="dragOver" @dragleave="dragLeave" @drop="drop"
    :class="dragging ? 'border-accent' : ''"
  >
    <div class="card-h">
      <div class="label">Files to install</div>
      <div class="right"><span class="hint">{{ files.length }} files</span></div>
    </div>
    <div class="card-b" style="padding:0">
      <table class="table">
        <thead><tr><th>File</th><th class="w-20">Type</th><th class="text-right">Size</th><th class="col-actions"></th></tr></thead>
        <tbody>
          <tr v-for="p in files" :key="p">
            <td class="num">{{ fileName(p) }}</td>
            <td>{{ p.split('.').pop() }}</td>
            <td class="text-right num">—</td>
            <td><button class="btn small btn-danger" @click="removeFile(p)">Remove</button></td>
          </tr>
          <tr v-if="!files.length">
            <td colspan="4">
              <div class="empty" style="min-height:96px">
                Drop APK/AAB files here, or click "Add files…"
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="card-f">
      <button class="btn" @click="addFiles">Add files…</button>
      <button class="btn" :disabled="!files.length" @click="clearFiles">Clear</button>
    </div>
  </section>

  <section class="card mt-4">
    <div class="card-h">
      <div class="label">Target devices</div>
      <div class="right"><span class="hint">{{ targetCount }} selected</span></div>
    </div>
    <div class="card-b" style="padding:0">
      <table class="table">
        <thead><tr><th class="col-check"></th><th>Device</th><th>Serial</th><th class="w-24">Status</th></tr></thead>
        <tbody>
          <tr v-for="d in devices.devices" :key="d.serial">
            <td>
              <input
                type="checkbox" class="check"
                :checked="selected.has(d.serial)"
                @change="toggleTarget(d.serial, ($event.target as HTMLInputElement).checked)"
              />
            </td>
            <td>{{ d.model || "—" }} <span class="hint">· {{ d.manufacturer || "" }}</span></td>
            <td class="num">{{ d.serial }}</td>
            <td><span class="badge" :class="d.status === 'online' ? 'ok' : 'err'">{{ d.status }}</span></td>
          </tr>
          <tr v-if="!devices.devices.length">
            <td colspan="4"><div class="empty">No connected devices.</div></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="card mt-4">
    <div class="card-h"><div class="label">Installation</div></div>
    <div class="card-b flex flex-col gap-2.5">
      <div class="flex items-center gap-2">
        <button class="btn btn-primary" :disabled="running || !files.length || !targetCount" @click="install">Install</button>
        <button class="btn" :disabled="!running">Cancel</button>
      </div>
      <div class="rounded-md bg-card-2 border border-border px-3 py-2 text-sm text-text2 font-mono">
        {{ status }}
      </div>
    </div>
  </section>

  <section class="card mt-4">
    <div class="card-h">
      <div class="label">Results</div>
      <div class="right"><span class="hint">{{ jobs.size }} records</span></div>
    </div>
    <div class="card-b" style="padding:0">
      <table class="table">
        <thead><tr><th>File</th><th>Serial</th><th>Status</th><th>Message</th></tr></thead>
        <tbody>
          <tr v-for="[cid, j] in jobs" :key="cid">
            <td class="num">{{ fileName(j.file) }}</td>
            <td class="num">{{ j.serial }}</td>
            <td><span class="badge" :class="badgeClass(j.status)">{{ statusLabel(j.status) }}</span></td>
            <td class="hint truncate" style="max-width:300px">{{ j.message || "" }}</td>
          </tr>
          <tr v-if="!jobs.size"><td colspan="4"><div class="empty">No installations yet.</div></td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
