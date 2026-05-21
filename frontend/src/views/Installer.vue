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
const statusState = ref<"idle" | "running" | "done" | "error">("idle");

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
    finalizeStatus();
  });
});

function finalizeStatus() {
  const all = [...jobs.value.values()];
  const failed = all.filter((x) => x.status === "fail").length;
  const ok = all.filter((x) => x.status === "ok").length;
  if (failed && !ok) {
    statusState.value = "error";
    status.value = "Install failed — see Results";
  } else if (failed) {
    statusState.value = "error";
    status.value = `Installed ${ok} of ${all.length} · ${failed} error(s)`;
  } else {
    statusState.value = "done";
    status.value = `Installed ${ok} of ${all.length} · 0 errors`;
  }
}

function maybeDone() {
  const pending = [...jobs.value.values()].some(
    (x) => x.status === "queued" || x.status === "running",
  );
  if (!pending) {
    running.value = false;
    finalizeStatus();
  } else {
    const running_ = [...jobs.value.values()].find((x) => x.status === "running");
    const done = [...jobs.value.values()].filter((x) => x.status === "ok" || x.status === "fail").length;
    if (running_) {
      status.value = `Installing ${done + 1} of ${jobs.value.size} — ${fileName(running_.file)} on ${running_.serial}…`;
    }
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
  statusState.value = "idle";
  if (!files.value.length || !targetCount.value) {
    status.value = idleStatus;
  } else {
    status.value = `Ready — ${files.value.length} file(s) × ${targetCount.value} device(s).`;
  }
}

const progressPct = computed(() => {
  if (!jobs.value.size) return 0;
  const done = [...jobs.value.values()].filter((x) => x.status === "ok" || x.status === "fail").length;
  return Math.round((done / jobs.value.size) * 100);
});

async function install() {
  if (!files.value.length || !targetCount.value) return;
  running.value = true;
  statusState.value = "running";
  status.value = "Starting installation…";
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
        <thead><tr>
          <th>File</th>
          <th class="col-type">Type</th>
          <th class="col-num">Size</th>
          <th class="col-actions"></th>
        </tr></thead>
        <tbody>
          <tr v-for="p in files" :key="p">
            <td class="num">{{ fileName(p) }}</td>
            <td>{{ (p.split('.').pop() || '').toUpperCase() }}</td>
            <td class="col-num">—</td>
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
        <thead><tr>
          <th class="col-check"></th>
          <th>Device</th>
          <th>Serial</th>
          <th class="col-status">Status</th>
        </tr></thead>
        <tbody>
          <tr v-for="d in devices.devices" :key="d.serial"
              :class="selected.has(d.serial) ? 'selected' : ''">
            <td>
              <input
                type="checkbox" class="check"
                :checked="selected.has(d.serial)"
                @change="toggleTarget(d.serial, ($event.target as HTMLInputElement).checked)"
              />
            </td>
            <td>{{ d.model || "—" }} <span class="hint">· {{ d.manufacturer || "" }}</span></td>
            <td class="num">{{ d.serial }}</td>
            <td>
              <span class="badge" :class="d.status === 'online' ? 'ok' : 'err'">
                <span class="dot" :class="d.status === 'online' ? 'ok' : 'err'"></span>{{ d.status }}
              </span>
            </td>
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
      <div class="row">
        <button class="btn btn-primary" :disabled="running || !files.length || !targetCount" @click="install">Install</button>
        <button class="btn" :disabled="!running">Cancel</button>
        <div class="progress" style="margin:0 12px">
          <i :style="{ width: progressPct + '%' }"></i>
        </div>
        <span class="num" style="color:var(--text-2); min-width:40px; text-align:right">{{ progressPct }}%</span>
      </div>
      <div class="install-status" :class="`is-${statusState}`">
        <span class="dot"></span>
        <span class="status-text">{{ status }}</span>
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
        <thead><tr>
          <th>File</th>
          <th>Serial</th>
          <th>Result</th>
          <th>Message</th>
        </tr></thead>
        <tbody>
          <tr v-for="[cid, j] in jobs" :key="cid">
            <td class="num">{{ fileName(j.file) }}</td>
            <td class="num">{{ j.serial }}</td>
            <td>
              <span class="badge" :class="badgeClass(j.status)">
                <span class="dot" :class="badgeClass(j.status)"></span>{{ statusLabel(j.status) }}
              </span>
            </td>
            <td class="hint truncate" style="max-width:300px">{{ j.message || "" }}</td>
          </tr>
          <tr v-if="!jobs.size">
            <td colspan="4">
              <div class="empty" style="min-height:132px">No installations yet.</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
