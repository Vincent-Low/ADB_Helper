<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

const pairIp = ref("");
const pairPort = ref("");
const pairPin = ref("");
const pairing = ref(false);
const pairMsg = ref("");

const connIp = ref("");
const connPort = ref("5555");
const connecting = ref(false);
const connMsg = ref("");

// Map cmd_id → { kind, ip }.  Survives rapid double-clicks: a second pair
// click no longer overwrites the first cmd_id, so both responses route to
// the correct handler.
type PendingKind = "pair" | "connect";
interface PendingEntry { kind: PendingKind; ip: string }
const pending = ref<Map<string, PendingEntry>>(new Map());

onMounted(() => {
  on(bridge.connections.commandFinished, (cid, res) => {
    const entry = pending.value.get(cid);
    if (!entry) return;
    pending.value.delete(cid);
    if (entry.kind === "pair") {
      pairing.value = pendingOf("pair") > 0;
      pairMsg.value = (res.stdout || "Paired.").trim();
      devices.reloadPaired();
      if (entry.ip) {
        bridge.connections.savePaired(entry.ip, "Wi-Fi Device", null);
      }
    } else {
      connecting.value = pendingOf("connect") > 0;
      connMsg.value = (res.stdout || "Connected.").trim();
      devices.reloadPaired();
    }
  });
  on(bridge.connections.commandFailed, (cid, res) => {
    const entry = pending.value.get(cid);
    if (!entry) return;
    pending.value.delete(cid);
    const msg = (res.stderr || res.status || `${entry.kind} failed.`).trim();
    if (entry.kind === "pair") {
      pairing.value = pendingOf("pair") > 0;
      pairMsg.value = msg;
    } else {
      connecting.value = pendingOf("connect") > 0;
      connMsg.value = msg;
    }
  });
});

function pendingOf(kind: PendingKind): number {
  let n = 0;
  for (const e of pending.value.values()) if (e.kind === kind) n++;
  return n;
}

async function doPair() {
  if (!pairIp.value || !pairPort.value || pairPin.value.length !== 6) {
    pairMsg.value = "IP, port, and 6-digit PIN required.";
    return;
  }
  pairing.value = true;
  pairMsg.value = "Pairing…";
  const cid = await bridge.connections.pair(
    pairIp.value, Number(pairPort.value), pairPin.value,
  );
  pending.value.set(cid, { kind: "pair", ip: pairIp.value });
}
async function doConnect() {
  if (!connIp.value || !connPort.value) {
    connMsg.value = "Enter IP and port.";
    return;
  }
  connecting.value = true;
  connMsg.value = "Connecting…";
  const cid = await bridge.connections.connect(
    connIp.value, Number(connPort.value),
  );
  pending.value.set(cid, { kind: "connect", ip: connIp.value });
}
async function refresh() {
  await devices.reloadPaired();
}
async function disconnect(target: string) {
  await bridge.connections.disconnect(target);
}
async function forget(ip: string) {
  await bridge.connections.forgetPaired(ip);
  await devices.reloadPaired();
}
async function reconnect(ip: string, port: number | null) {
  if (!port) return;
  await bridge.connections.connect(ip, port);
}
async function selectRow(serial: string) {
  await devices.setActive(serial);
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Connections</h1>
    <span class="page-sub">Connect over Wi-Fi or pair a new Android 11+ device</span>
    <div class="page-actions">
      <button class="btn" @click="refresh">Refresh</button>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
    <!-- Wi-Fi Pairing -->
    <section class="card">
      <div class="card-h"><div class="label">Wi-Fi Pairing (Android 11+)</div></div>
      <div class="card-b">
        <div class="field">
          <label>IP Address</label>
          <input v-model="pairIp" class="input" placeholder="192.168.1.10" />
        </div>
        <div class="field">
          <label>Pairing Port</label>
          <div class="flex items-center gap-2.5 flex-wrap">
            <input v-model="pairPort" class="input num" placeholder="44331" style="flex:0 0 130px" />
            <label class="text-text2 text-sm ml-1.5">PIN</label>
            <input v-model="pairPin" class="input pin" maxlength="6" placeholder="123456" style="flex:0 0 130px" />
            <button class="btn btn-primary ml-auto" :disabled="pairing" @click="doPair">Pair</button>
          </div>
        </div>
        <p v-if="pairMsg" class="hint mt-2">{{ pairMsg }}</p>
      </div>
    </section>

    <!-- Wi-Fi Connection -->
    <section class="card">
      <div class="card-h"><div class="label">Wi-Fi Connection (Legacy)</div></div>
      <div class="card-b">
        <div class="field">
          <label>IP Address</label>
          <input v-model="connIp" class="input" placeholder="192.168.1.10" />
        </div>
        <div class="field">
          <label>Port</label>
          <div class="flex items-center gap-2.5 flex-wrap">
            <input v-model="connPort" class="input num" style="flex:0 0 130px" />
            <button class="btn btn-primary ml-auto" :disabled="connecting" @click="doConnect">Connect</button>
          </div>
        </div>
        <p v-if="connMsg" class="hint mt-2">{{ connMsg }}</p>
      </div>
    </section>

    <!-- Connected -->
    <section class="card">
      <div class="card-h">
        <div class="label">Connected Devices</div>
        <div class="right">
          <span class="badge ok"><span class="dot ok"></span>{{ devices.onlineCount }} online</span>
        </div>
      </div>
      <div class="card-b" style="padding:0">
        <table class="table">
          <thead>
            <tr>
              <th>Serial</th><th>IP</th><th>Model</th><th class="w-24">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="d in devices.devices" :key="d.serial"
              :class="devices.active?.serial === d.serial ? 'selected' : ''"
              class="cursor-pointer" @click="selectRow(d.serial)"
            >
              <td class="num">{{ d.serial }}</td>
              <td class="num">{{ d.serial.includes(':') ? d.serial.split(':')[0] : '—' }}</td>
              <td>{{ d.model || '—' }}</td>
              <td>
                <span class="badge" :class="d.status === 'online' ? 'ok' : d.status === 'unauthorized' ? 'warn' : 'err'">
                  <span class="dot" :class="d.status === 'online' ? 'ok' : d.status === 'unauthorized' ? 'warn' : 'err'"></span>
                  {{ d.status === 'online' ? 'Online' : d.status === 'unauthorized' ? 'Unauthorized' : 'Offline' }}
                </span>
              </td>
            </tr>
            <tr v-if="!devices.devices.length">
              <td colspan="4"><div class="empty">No devices connected.</div></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-f">
        <span class="hint">{{ devices.devices.length }} device(s)</span>
        <button
          class="btn btn-danger ml-auto"
          :disabled="!devices.active"
          @click="devices.active && disconnect(devices.active.serial)"
        >Disconnect</button>
      </div>
    </section>

    <!-- Paired -->
    <section class="card">
      <div class="card-h"><div class="label">Paired Devices</div></div>
      <div class="card-b" style="padding:0">
        <table class="table">
          <thead>
            <tr>
              <th>Alias</th><th>IP Address</th><th class="w-36">Connection port</th>
              <th>Last connected</th><th class="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in devices.paired" :key="p.ip">
              <td>{{ p.alias }}</td>
              <td class="num">{{ p.ip }}</td>
              <td><input class="input small num" :value="p.connect_port ?? ''" disabled /></td>
              <td class="num">{{ p.last_connected ?? '—' }}</td>
              <td>
                <div class="flex items-center gap-1.5">
                  <button class="btn small" :disabled="!p.connect_port" @click="reconnect(p.ip, p.connect_port)">Connect</button>
                  <button class="btn small btn-danger" @click="forget(p.ip)">Forget</button>
                </div>
              </td>
            </tr>
            <tr v-if="!devices.paired.length">
              <td colspan="5"><div class="empty">No paired devices.</div></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
