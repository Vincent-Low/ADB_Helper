<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

const state = ref({ ready: false, version: "", path: "" });
const status = ref("Checking scrcpy binary…");
const recent = ref<Array<{ time: string; device: string; flags: string; status: string; pid?: string }>>([]);

const bitrate = ref("8M");
const maxResolution = ref<string>("0");
const orientation = ref<string>("");
const stayAwake = ref(false);
const showTouches = ref(false);
const turnScreenOff = ref(false);

onMounted(async () => {
  on(bridge.scrcpy.statusChanged, (s) => { status.value = s; });
  on(bridge.scrcpy.binaryReady, (d) => {
    state.value = { ready: !!d.ok, version: d.version, path: d.path };
    status.value = d.ok ? `scrcpy ${d.version || ""} ready.` : d.message;
  });
  on(bridge.scrcpy.processStopped, (pid, rc) => {
    const r = recent.value.find((x) => x.pid === pid);
    if (r) { r.status = rc === 0 ? "Launched" : "Failed"; recent.value = [...recent.value]; }
  });
  state.value = await bridge.scrcpy.state();
  if (!state.value.ready) bridge.scrcpy.ensureBinary();
  else status.value = `scrcpy ${state.value.version || ""} ready.`;
});

async function launch() {
  const opts: any = {
    bitrate: bitrate.value,
    maxResolution: maxResolution.value === "0" ? undefined : Number(maxResolution.value),
    orientation: orientation.value === "" ? undefined : Number(orientation.value),
    stayAwake: stayAwake.value,
    showTouches: showTouches.value,
    turnScreenOff: turnScreenOff.value,
  };
  const result = await bridge.scrcpy.launch(opts);
  if (result.ok) {
    const time = new Date().toLocaleTimeString();
    const flags = (result.argv || []).slice(3).join(" ") || "default";
    recent.value.unshift({
      time, device: devices.active?.model || devices.active?.serial || "—",
      flags, status: "Running", pid: result.pid,
    });
    recent.value = recent.value.slice(0, 10);
  } else {
    status.value = result.message || "Launch failed.";
  }
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Scrcpy</h1>
    <span class="page-sub">{{ status }}</span>
    <div class="page-actions">
      <button class="btn btn-primary" :disabled="!state.ready || !devices.active" @click="launch">▶ Launch</button>
    </div>
  </div>

  <div class="grid gap-4" style="grid-template-columns: minmax(360px,1fr) minmax(420px,1.2fr)">
    <section class="card">
      <div class="card-h"><div class="label">Launch options</div></div>
      <div class="card-b">
        <div class="field"><label>Video bitrate</label>
          <select v-model="bitrate" class="select">
            <option value="2M">2 Mbps</option>
            <option value="4M">4 Mbps</option>
            <option value="8M">8 Mbps</option>
            <option value="16M">16 Mbps</option>
            <option value="32M">32 Mbps</option>
          </select>
        </div>
        <div class="field"><label>Max resolution</label>
          <select v-model="maxResolution" class="select">
            <option value="0">No limit</option>
            <option value="1920">1920</option>
            <option value="1280">1280</option>
            <option value="1024">1024</option>
            <option value="800">800</option>
          </select>
        </div>
        <div class="field"><label>Orientation lock</label>
          <select v-model="orientation" class="select">
            <option value="">Auto</option>
            <option value="0">0°</option>
            <option value="90">90°</option>
            <option value="180">180°</option>
            <option value="270">270°</option>
          </select>
        </div>
        <div class="field">
          <label></label>
          <div class="flex flex-wrap gap-3.5">
            <label class="inline-flex items-center gap-2 text-sm text-text2">
              <input type="checkbox" class="check" v-model="stayAwake" /> Stay awake
            </label>
            <label class="inline-flex items-center gap-2 text-sm text-text2">
              <input type="checkbox" class="check" v-model="showTouches" /> Show touches
            </label>
            <label class="inline-flex items-center gap-2 text-sm text-text2">
              <input type="checkbox" class="check" v-model="turnScreenOff" /> Turn screen off
            </label>
          </div>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="card-h"><div class="label">Recent launches</div></div>
      <div class="card-b" style="padding:0">
        <div class="table-scroll" style="max-height:380px">
          <table class="table">
            <thead><tr><th>When</th><th>Device</th><th>Options</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="(r, i) in recent" :key="i">
                <td class="num">{{ r.time }}</td>
                <td>{{ r.device }}</td>
                <td class="hint truncate" style="max-width:240px">{{ r.flags }}</td>
                <td><span class="badge" :class="r.status === 'Failed' ? 'err' : r.status === 'Launched' ? 'ok' : 'warn'">{{ r.status }}</span></td>
              </tr>
              <tr v-if="!recent.length"><td colspan="4"><div class="empty">No launches yet.</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>
