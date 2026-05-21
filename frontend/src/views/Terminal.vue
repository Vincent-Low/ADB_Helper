<script setup lang="ts">
import { ref, onMounted, onActivated, onBeforeUnmount, nextTick, watch } from "vue";
import { Terminal } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

const termEl = ref<HTMLDivElement | null>(null);
const supportsPty = ref(true);
const macros = ref<Array<{ id: number; name: string; commands: string[]; created_at: string }>>([]);
const status = ref("");

let term: Terminal | null = null;
let fitAddon: FitAddon | null = null;
let resizeObs: ResizeObserver | null = null;

function decodeB64(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}
const decoder = new TextDecoder("utf-8");

async function refit() {
  await nextTick();
  setTimeout(() => fitAddon?.fit(), 50);
}

async function start(serial: string) {
  if (!serial) {
    status.value = "No active device. Connect a device in the Connections module.";
    return;
  }
  if (!supportsPty.value) {
    status.value = "PTY shell requires Linux. Use a Linux host.";
    return;
  }
  term?.clear();
  status.value = `Starting adb shell on ${serial}…`;
  const ok = await bridge.terminal.start(serial);
  if (!ok) {
    status.value = "Failed to start adb shell.";
  } else {
    status.value = "";
  }
}

onMounted(async () => {
  supportsPty.value = await bridge.terminal.supportsPty();

  term = new Terminal({
    fontFamily: 'JetBrains Mono, "Cascadia Code", Menlo, Consolas, monospace',
    fontSize: 13,
    theme: { background: "#0a0e15", foreground: "#d8e0ea", cursor: "#2dd4bf" },
    convertEol: true,
    cursorBlink: true,
  });
  fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.open(termEl.value!);
  await refit();

  resizeObs = new ResizeObserver(() => fitAddon?.fit());
  resizeObs.observe(termEl.value!);

  on(bridge.terminal.output, (b64) => {
    if (!term) return;
    term.write(decoder.decode(decodeB64(b64), { stream: true }));
  });
  on(bridge.terminal.exited, (code) => {
    term?.writeln(`\r\n\x1b[33m[exit ${code}]\x1b[0m`);
  });

  term.onData((data) => { void bridge.terminal.write(data); });

  macros.value = await bridge.terminal.listMacros();
  if (devices.active?.serial) await start(devices.active.serial);
});

// KeepAlive cache restore — xterm canvas can go stale, refit AND refresh.
onActivated(async () => {
  await nextTick();
  setTimeout(() => {
    fitAddon?.fit();
    if (term) {
      try {
        term.refresh(0, term.rows - 1);
      } catch {
        /* xterm may not be ready */
      }
    }
  }, 50);
});

watch(
  () => devices.active?.serial,
  async (serial, prev) => {
    if (serial === prev) return;
    await bridge.terminal.close();
    if (serial) await start(serial);
  },
);

onBeforeUnmount(async () => {
  resizeObs?.disconnect();
  await bridge.terminal.close();
  term?.dispose();
  term = null;
  fitAddon = null;
});

async function clear() {
  term?.clear();
}
async function playMacro(id: number) {
  const m = macros.value.find((x) => x.id === id);
  if (!m) return;
  for (const cmd of m.commands) {
    await bridge.terminal.write(cmd + "\n");
  }
}
async function deleteMacro(id: number) {
  await bridge.terminal.deleteMacro(id);
  macros.value = await bridge.terminal.listMacros();
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Terminal</h1>
    <span class="page-sub">
      adb shell · {{ devices.active?.serial ?? "no device" }}
    </span>
    <div class="page-actions">
      <button class="btn" @click="clear">Clear</button>
    </div>
  </div>

  <div
    class="grid gap-4"
    style="grid-template-columns: minmax(0,1fr) 260px; height: calc(100vh - 240px); min-height: 460px"
  >
    <section class="card flex flex-col min-h-0">
      <div class="card-h">
        <div class="label">Output</div>
        <div class="right"><span class="hint">UTF-8</span></div>
      </div>
      <div class="card-b flex-1 flex flex-col gap-2.5 min-h-0">
        <div
          v-if="status"
          class="rounded-md bg-card-2 border border-border px-3 py-2 font-mono text-sm text-text2"
        >{{ status }}</div>
        <div ref="termEl" class="flex-1 rounded-md overflow-hidden border border-border" style="background:#0a0e15"></div>
      </div>
    </section>

    <section class="card flex flex-col min-h-0">
      <div class="card-h"><div class="label">Macros</div></div>
      <div class="card-b flex flex-col gap-2.5 min-h-0 flex-1">
        <div v-if="!macros.length" class="hint">No macros saved.</div>
        <ul v-else class="flex flex-col gap-1">
          <li v-for="m in macros" :key="m.id" class="flex items-center gap-1.5">
            <span class="flex-1 text-sm truncate">{{ m.name }} <span class="hint">({{ m.commands.length }})</span></span>
            <button class="btn small" @click="playMacro(m.id)">▶</button>
            <button class="btn small btn-danger" @click="deleteMacro(m.id)">✕</button>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>
