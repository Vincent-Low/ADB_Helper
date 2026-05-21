<script setup lang="ts">
import { ref, onMounted } from "vue";
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
          <p class="hint mb-2">
            Captures the current device log (one-shot
            <span class="num text-text1">adb logcat -d</span>) and saves it to the configured Logcat folder.
          </p>
          <div class="rounded-md bg-input border border-border-input p-3 font-mono text-sm break-all">
            <span class="text-text3">$</span> adb -s {{ devices.active?.serial ?? '<serial>' }} logcat -d &gt;
            <span class="text-accent">{{ folder }}/</span>logcat_DD.MM.YY_HH.mm_GMT±N.txt
          </div>
          <div class="flex gap-2 mt-3">
            <button class="btn btn-primary flex-1" :disabled="!devices.active || exporting" @click="doExport">
              ⇣ Export logcat
            </button>
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
          <div class="table-scroll" style="max-height:300px">
            <table class="table">
              <thead><tr><th>File</th><th>Saved</th><th class="text-right">Size</th></tr></thead>
              <tbody>
                <tr v-for="r in recent" :key="r.path">
                  <td class="num">{{ fileName(r.path) }}</td>
                  <td class="num">{{ r.saved }}</td>
                  <td class="text-right num">{{ fmtSize(r.size) }}</td>
                </tr>
                <tr v-if="!recent.length"><td colspan="3"><div class="empty">No exports yet.</div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <section class="card">
      <div class="card-h"><div class="label">Configuration</div></div>
      <div class="card-b flex flex-col gap-3">
        <div>
          <div class="text-text2 text-sm mb-1">Save folder</div>
          <div class="flex gap-1.5">
            <input class="input flex-1" v-model="folder" readonly />
            <button class="btn" @click="pickFolder">Browse…</button>
          </div>
        </div>
        <div>
          <div class="text-text2 text-sm">Filename pattern</div>
          <div class="font-mono text-sm">logcat_&lt;date&gt;_&lt;time&gt;_GMT±N.txt</div>
        </div>
        <div>
          <div class="text-text2 text-sm">Mode</div>
          <div class="font-mono text-sm">Single-shot (−d flag)</div>
        </div>
      </div>
    </section>
  </div>
</template>
