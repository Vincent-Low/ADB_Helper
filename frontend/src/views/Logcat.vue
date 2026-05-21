<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

const folder = ref("");
const recent = ref<Array<{ path: string; size: number; saved: string }>>([]);
const status = ref("");
const exporting = ref(false);

async function reload() {
  const st = await bridge.logcat.state();
  folder.value = st.folder;
  recent.value = st.recent || [];
}

onMounted(() => {
  reload();
  on(bridge.logcat.exportStarted, (path) => {
    exporting.value = true;
    status.value = `Exporting → ${path}`;
  });
  on(bridge.logcat.exportFinished, (d) => {
    exporting.value = false;
    status.value = d.ok ? `Saved: ${d.path} (${(d.size_bytes / 1024).toFixed(1)} KB)` : `Failed: ${d.message}`;
    reload();
  });
});

async function doExport() {
  if (!devices.active) return;
  status.value = "Capturing…";
  await bridge.logcat.export(devices.active.serial);
}

async function pickFolder() {
  const picked = await bridge.settings.pickFolder("Select Logcat Folder", folder.value);
  if (picked) {
    folder.value = picked;
    await bridge.logcat.setFolder(picked);
  }
}

async function openFolder() {
  // bridge.logcat.openFolder is not wired yet — see UNIMPLEMENTED_FEATURES.md
  const b: any = bridge;
  if (b.logcat?.openFolder) await b.logcat.openFolder();
  else status.value = "Open folder: not wired in qt-bridge yet.";
}

const tzLabel = computed(() => {
  const off = -new Date().getTimezoneOffset() / 60;
  const sign = off >= 0 ? "+" : "−";
  return `GMT${sign}${Math.abs(off)}`;
});

function fmtSize(n: number) {
  if (n >= 1024 * 1024) return `${(n / 1048576).toFixed(1)} MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${n} B`;
}
function fileName(p: string) { return p.split(/[\\/]/).pop() || p; }
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Logcat</h1>
    <span class="page-sub">Capture device log to disk</span>
  </div>

  <div class="grid gap-4" style="grid-template-columns: minmax(0,1.5fr) minmax(280px,0.9fr)">
    <div>
      <section class="card">
        <div class="card-h"><div class="label">Capture</div></div>
        <div class="card-b">
          <p class="hint" style="margin-bottom:8px">
            Captures the current device log (one-shot
            <code class="num" style="color:var(--text-1)">adb logcat -d</code>) and saves it to the configured Logcat folder.
          </p>
          <div class="codeblock">
            <span class="line"><span class="muted">$</span> adb -s {{ devices.active?.serial ?? '&lt;serial&gt;' }} logcat -d \</span><span
            class="line cont">&gt; <span class="accent">{{ folder }}/</span>logcat_DD.MM.YY_HH.mm_GMT±N.txt</span>
          </div>
          <div class="row" style="margin-top:12px">
            <button class="btn btn-primary" style="flex:1"
                    :disabled="!devices.active || exporting" @click="doExport">
              ⇣ Export logcat
            </button>
            <button class="btn" @click="openFolder">Open folder</button>
          </div>
          <div v-if="status" class="hint mt-2">{{ status }}</div>
        </div>
      </section>

      <section class="card mt-4">
        <div class="card-h">
          <div class="label">Recent exports</div>
          <div class="right"><span class="hint">{{ recent.length }} files</span></div>
        </div>
        <div class="card-b" style="padding:0">
          <table class="table">
            <thead><tr>
              <th>File</th>
              <th>Saved</th>
              <th class="col-num">Size</th>
            </tr></thead>
            <tbody>
              <tr v-for="r in recent" :key="r.path">
                <td class="num">{{ fileName(r.path) }}</td>
                <td class="num">{{ r.saved }}</td>
                <td class="col-num">{{ fmtSize(r.size) }}</td>
              </tr>
              <tr v-if="!recent.length"><td colspan="3"><div class="empty">No exports yet.</div></td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="card">
      <div class="card-h"><div class="label">Configuration</div></div>
      <div class="card-b" style="padding:0">
        <div class="meta-row">
          <span class="lbl">Save folder</span>
          <div class="row" style="gap:6px">
            <input class="input flex-1" v-model="folder" readonly />
            <button class="btn" @click="pickFolder">Browse…</button>
          </div>
        </div>
        <div class="meta-row">
          <span class="lbl">Filename pattern</span>
          <span class="val font-mono">logcat_&lt;date&gt;_&lt;time&gt;_GMT±N.txt</span>
        </div>
        <div class="meta-row">
          <span class="lbl">Mode</span>
          <span class="val font-mono">Single-shot (−d flag)</span>
        </div>
        <div class="meta-row">
          <span class="lbl">Timezone</span>
          <span class="val font-mono">{{ tzLabel }}</span>
        </div>
      </div>
    </section>
  </div>
</template>
