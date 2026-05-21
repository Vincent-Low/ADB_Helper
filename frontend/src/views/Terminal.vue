<script setup lang="ts">
import { ref, onMounted, onActivated, onBeforeUnmount, nextTick, watch } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

const outputEl = ref<HTMLDivElement | null>(null);
const inputEl = ref<HTMLInputElement | null>(null);
const supportsPty = ref(true);
const macros = ref<Array<{ id: number; name: string; commands: string[]; created_at: string }>>([]);
const status = ref("");
const buffer = ref("");
const cmdInput = ref("");
const history: string[] = [];
const histIdx = ref(-1);

const decoder = new TextDecoder("utf-8");
const ANSI_RE = /\x1b\[[0-9;?]*[A-Za-z]/g;

function decodeB64(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

function appendChunk(text: string) {
  // Strip ANSI escape sequences for plain-text display
  buffer.value += text.replace(ANSI_RE, "");
  scrollToEnd();
}

function scrollToEnd() {
  nextTick(() => {
    const el = outputEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
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
  buffer.value = "";
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

  on(bridge.terminal.output, (b64) => {
    appendChunk(decoder.decode(decodeB64(b64), { stream: true }));
  });
  on(bridge.terminal.exited, (code) => {
    buffer.value += `\n[exit ${code}]\n`;
    scrollToEnd();
  });

  macros.value = await bridge.terminal.listMacros();
  if (devices.active?.serial) await start(devices.active.serial);
});

onActivated(async () => {
  await nextTick();
  inputEl.value?.focus();
  scrollToEnd();
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
  await bridge.terminal.close();
});

async function submitCmd() {
  const cmd = cmdInput.value;
  if (!cmd) {
    await bridge.terminal.write("\n");
    return;
  }
  history.push(cmd);
  histIdx.value = history.length;
  cmdInput.value = "";
  await bridge.terminal.write(cmd + "\n");
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Enter") {
    e.preventDefault();
    void submitCmd();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (history.length === 0) return;
    histIdx.value = Math.max(0, histIdx.value - 1);
    cmdInput.value = history[histIdx.value] ?? "";
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    if (history.length === 0) return;
    histIdx.value = Math.min(history.length, histIdx.value + 1);
    cmdInput.value = history[histIdx.value] ?? "";
  } else if (e.ctrlKey && e.key.toLowerCase() === "c") {
    void bridge.terminal.write("\x03");
  } else if (e.ctrlKey && e.key.toLowerCase() === "d") {
    e.preventDefault();
    void bridge.terminal.write("\x04");
  }
}

function clear() {
  buffer.value = "";
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

function focusInput() { inputEl.value?.focus(); }
</script>

<template>
  <div style="display:flex; flex-direction:column; flex:1; min-height:0; gap:0">
    <div class="page-header" style="flex:none; margin-bottom:0">
      <h1 class="page-title">Terminal</h1>
      <span class="page-sub">
        adb shell · {{ devices.active?.serial ?? "no device" }}
      </span>
      <div class="page-actions">
        <button class="btn" disabled title="Not implemented yet">History</button>
        <button class="btn" @click="clear">Clear</button>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns: minmax(0, 1fr) 260px; gap:16px; flex:1; min-height:0; margin-top:16px"
    >
      <section class="card flex flex-col min-h-0">
        <div class="card-h">
          <div class="label">Output</div>
          <div class="right"><span class="hint">UTF-8 · 80 cols</span></div>
        </div>
        <div class="card-b flex-1 flex flex-col gap-2.5 min-h-0">
          <div v-if="status" class="term-status">
            <span class="pfx">$</span>
            <span>{{ status }}</span>
          </div>
          <div
            ref="outputEl"
            class="terminal-host flex-1"
            @click="focusInput"
          >{{ buffer }}</div>
          <div class="term-prompt" @click="focusInput">
            <span class="term-cursor"></span>
            <input
              ref="inputEl"
              v-model="cmdInput"
              :disabled="!devices.active || !supportsPty"
              autocomplete="off" spellcheck="false"
              @keydown="onKey"
            />
          </div>
        </div>
      </section>

      <section class="card flex flex-col min-h-0">
        <div class="card-h"><div class="label">Macros</div></div>
        <div class="card-b flex flex-col gap-2.5 min-h-0 flex-1">
          <div class="row">
            <button class="btn btn-primary" style="flex:1" disabled title="Not implemented yet">● Record Macro</button>
            <button class="btn" style="flex:1" :disabled="!macros.length" @click="macros.length && playMacro(macros[0].id)">▶ Play</button>
          </div>
          <div class="card flex-1 overflow-auto" style="background:var(--bg-card-2)">
            <div v-if="!macros.length" style="padding:10px 12px; display:flex; flex-direction:column; gap:6px">
              <div class="hint">No macros saved.</div>
              <div class="hint" style="color:var(--text-3); font-size:var(--fs-xs)">
                Recorded commands will appear here. Click ▶ to replay them in the terminal.
              </div>
            </div>
            <ul v-else class="flex flex-col gap-1" style="padding:10px 12px">
              <li v-for="m in macros" :key="m.id" class="flex items-center gap-1.5">
                <span class="flex-1 text-sm truncate">{{ m.name }} <span class="hint">({{ m.commands.length }})</span></span>
                <button class="btn small" @click="playMacro(m.id)">▶</button>
                <button class="btn small btn-danger" @click="deleteMacro(m.id)">✕</button>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.terminal-host {
  white-space: pre-wrap;
  word-break: break-all;
  cursor: text;
}
</style>
