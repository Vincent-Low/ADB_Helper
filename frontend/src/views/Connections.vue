<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";
import {
  sanitizeIPv4Partial,
  sanitizePort,
  isValidIPv4,
  isValidPort,
} from "@/composables/useInputFilters";

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

const pairFormValid = computed(
  () =>
    isValidIPv4(pairIp.value) &&
    isValidPort(pairPort.value) &&
    pairPin.value.length === 6,
);
const connFormValid = computed(
  () => isValidIPv4(connIp.value) && isValidPort(connPort.value),
);

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
  if (!pairFormValid.value) {
    pairMsg.value = "Valid IPv4, port (1-65535), and 6-digit PIN required.";
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
  if (!connFormValid.value) {
    connMsg.value = "Valid IPv4 and port (1-65535) required.";
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
async function savePortEdit(p: { ip: string; alias: string }, raw: string) {
  const portStr = sanitizePort(raw);
  if (!isValidPort(portStr)) return;
  await bridge.connections.savePaired(p.ip, p.alias, Number(portStr));
  await devices.reloadPaired();
}
async function selectRow(serial: string) {
  await devices.setActive(serial);
}

function onIpInput(target: "pair" | "conn", e: Event) {
  const el = e.target as HTMLInputElement;
  const sanitized = sanitizeIPv4Partial(el.value);
  if (target === "pair") pairIp.value = sanitized;
  else connIp.value = sanitized;
  if (el.value !== sanitized) el.value = sanitized;
}
function onPortInput(target: "pair" | "conn", e: Event) {
  const el = e.target as HTMLInputElement;
  const sanitized = sanitizePort(el.value);
  if (target === "pair") pairPort.value = sanitized;
  else connPort.value = sanitized;
  if (el.value !== sanitized) el.value = sanitized;
}
function onPinInput(e: Event) {
  const el = e.target as HTMLInputElement;
  const trimmed = el.value.slice(0, 6);
  pairPin.value = trimmed;
  if (el.value !== trimmed) el.value = trimmed;
}
function onPairedPortInput(e: Event) {
  const el = e.target as HTMLInputElement;
  const sanitized = sanitizePort(el.value);
  if (el.value !== sanitized) el.value = sanitized;
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Connections</h1>
    <span class="page-sub">Connect over Wi-Fi or pair a new Android 11+ device</span>
    <div class="page-actions">
      <button class="btn" disabled title="Not implemented yet">Scan network</button>
      <button class="btn btn-primary" @click="refresh">Refresh</button>
    </div>
  </div>

  <div class="conn-grid">
    <!-- TOP-LEFT: Wi-Fi Pairing -->
    <section class="card">
      <div class="card-h"><div class="label">Wi-Fi Pairing (Android 11+)</div></div>
      <div class="card-b">
        <div class="field">
          <label>IP Address</label>
          <input
            :value="pairIp" class="input" placeholder="192.168.1.10"
            maxlength="15" inputmode="decimal" autocomplete="off"
            @input="onIpInput('pair', $event)"
          />
        </div>
        <div class="field">
          <label>Pairing Port</label>
          <div class="row" style="gap:10px">
            <input
              :value="pairPort" class="input num" placeholder="44331"
              maxlength="5" inputmode="numeric" pattern="[0-9]*" autocomplete="off"
              style="flex:0 0 130px" @input="onPortInput('pair', $event)"
            />
            <label style="color:var(--text-2); font-size:var(--fs-sm); margin-left:6px">PIN</label>
            <input
              :value="pairPin" class="input pin" placeholder="123456"
              maxlength="6" autocomplete="off"
              style="flex:0 0 130px" @input="onPinInput"
            />
            <button class="btn btn-primary" style="margin-left:auto"
                    :disabled="pairing || !pairFormValid" @click="doPair">Pair</button>
          </div>
        </div>
        <p v-if="pairMsg" class="hint mt-2">{{ pairMsg }}</p>
      </div>
    </section>

    <!-- TOP-RIGHT: Wi-Fi Connection (Legacy) -->
    <section class="card">
      <div class="card-h"><div class="label">Wi-Fi Connection (Legacy)</div></div>
      <div class="card-b">
        <div class="field">
          <label>IP Address</label>
          <input
            :value="connIp" class="input" placeholder="192.168.1.10"
            maxlength="15" inputmode="decimal" autocomplete="off"
            @input="onIpInput('conn', $event)"
          />
        </div>
        <div class="field">
          <label>Port</label>
          <div class="row" style="gap:10px">
            <input
              :value="connPort" class="input num"
              maxlength="5" inputmode="numeric" pattern="[0-9]*" autocomplete="off"
              style="flex:0 0 130px" @input="onPortInput('conn', $event)"
            />
            <button class="btn btn-primary" style="margin-left:auto"
                    :disabled="connecting || !connFormValid" @click="doConnect">Connect</button>
          </div>
        </div>
        <p v-if="connMsg" class="hint mt-2">{{ connMsg }}</p>
      </div>
    </section>

    <!-- BOTTOM-LEFT: Connected Devices -->
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
              <th>Serial</th>
              <th>IP Address</th>
              <th>Model</th>
              <th class="col-status">Status</th>
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
        <span class="hint">
          {{ devices.devices.length }} device{{ devices.devices.length === 1 ? '' : 's' }}{{ devices.active?.connection_type === 'wifi' ? ' · connected via Wi-Fi' : '' }}
        </span>
        <button
          class="btn btn-danger" style="margin-left:auto"
          :disabled="!devices.active"
          @click="devices.active && disconnect(devices.active.serial)"
        >Disconnect</button>
      </div>
    </section>

    <!-- BOTTOM-RIGHT: Paired Devices -->
    <section class="card">
      <div class="card-h"><div class="label">Paired Devices</div></div>
      <div class="card-b" style="padding:0">
        <table class="table">
          <thead>
            <tr>
              <th>Alias</th>
              <th>IP Address</th>
              <th class="col-port">Connection port</th>
              <th>Last connected</th>
              <th class="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in devices.paired" :key="p.ip" style="height:40px">
              <td>{{ p.alias }}</td>
              <td class="num">{{ p.ip }}</td>
              <td>
                <input
                  class="input small num"
                  :value="p.connect_port ?? ''"
                  maxlength="5" inputmode="numeric" pattern="[0-9]*"
                  @input="onPairedPortInput"
                  @change="savePortEdit(p, ($event.target as HTMLInputElement).value)"
                />
              </td>
              <td class="num">{{ p.last_connected ?? '—' }}</td>
              <td>
                <div class="row" style="gap:6px">
                  <button class="btn small" style="min-width:74px"
                          :disabled="!p.connect_port"
                          @click="reconnect(p.ip, p.connect_port)">Connect</button>
                  <button class="btn small btn-danger" style="min-width:74px"
                          @click="forget(p.ip)">Forget</button>
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
