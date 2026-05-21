<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

interface ActionRow { time: string; action: string; result: string }
const recent = ref<ActionRow[]>([]);

const TILES: Array<[string, string, string]> = [
  ["home",        "Home",          "⌂"],
  ["back",        "Back",          "‹"],
  ["recent",      "Recent Apps",   "▭"],
  ["volume_up",   "Volume +",      "+"],
  ["volume_down", "Volume −",      "−"],
  ["mute",        "Mute",          "✕"],
  ["camera",      "Camera",        "◉"],
  ["power",       "Power",         "⏻"],
];

onMounted(() => {
  on(bridge.buttons.actionFinished, (d) => {
    recent.value.unshift({
      time: new Date().toLocaleTimeString(),
      action: d.action,
      result: d.ok ? "OK" : `Failed: ${d.message}`,
    });
    recent.value = recent.value.slice(0, 30);
  });
  on(bridge.buttons.screenshotSaved, (path) => {
    recent.value.unshift({
      time: new Date().toLocaleTimeString(),
      action: "screenshot",
      result: `Saved to ${path}`,
    });
    recent.value = recent.value.slice(0, 30);
  });
});

async function press(key: string) {
  if (!devices.active) return;
  await bridge.buttons.pressKey(key);
}
async function takeScreenshot() {
  if (!devices.active) return;
  await bridge.buttons.screenshot();
}
async function reboot(mode: "normal" | "bootloader" | "recovery") {
  if (!devices.active) return;
  await bridge.buttons.reboot(mode);
}
async function rotate() {
  if (!devices.active) return;
  await bridge.buttons.toggleRotation();
}

function clearHistory() { recent.value = []; }

const rebootMenu = ref(false);
function toggleRebootMenu() { rebootMenu.value = !rebootMenu.value; }
function pickReboot(mode: "normal" | "bootloader" | "recovery") {
  rebootMenu.value = false;
  reboot(mode);
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Device Buttons</h1>
    <span class="page-sub">Send virtual key events to the device</span>
  </div>

  <section class="card">
    <div class="card-h"><div class="label">Keys</div></div>
    <div class="card-b">
      <div class="grid gap-2.5" style="grid-template-columns: repeat(4, minmax(0, 1fr))">
        <button v-for="[k, label, glyph] in TILES" :key="k"
                class="btn-tile" :disabled="!devices.active" @click="press(k)">
          <span class="glyph">{{ glyph }}</span>{{ label }}
        </button>
        <div class="relative" style="position:relative">
          <button class="btn-tile w-full" :disabled="!devices.active" @click="toggleRebootMenu">
            <span class="glyph">↻</span>Reboot
          </button>
          <div v-if="rebootMenu" class="reboot-menu">
            <button class="reboot-item" @click="pickReboot('normal')">Normal</button>
            <button class="reboot-item" @click="pickReboot('bootloader')">Bootloader</button>
            <button class="reboot-item" @click="pickReboot('recovery')">Recovery</button>
          </div>
        </div>
        <button class="btn-tile" :disabled="!devices.active" @click="takeScreenshot">
          <span class="glyph">▣</span>Screenshot
        </button>
        <button class="btn-tile" :disabled="!devices.active" @click="rotate">
          <span class="glyph">⤿</span>Screen Rotate
        </button>
      </div>
    </div>
  </section>

  <section class="card mt-4">
    <div class="card-h">
      <div class="label">Recent actions</div>
      <div class="right"><button class="btn small btn-ghost" @click="clearHistory">Clear history</button></div>
    </div>
    <div class="card-b" style="padding:0">
      <div class="table-scroll" style="max-height:340px">
        <table class="table">
          <thead><tr><th>Time</th><th>Action</th><th>Result</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in recent" :key="i">
              <td class="num">{{ r.time }}</td>
              <td>{{ r.action }}</td>
              <td class="hint">{{ r.result }}</td>
            </tr>
            <tr v-if="!recent.length"><td colspan="3"><div class="empty">No actions yet.</div></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
