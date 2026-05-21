<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import { useSignal } from "@/plugins/use-signal";
import { useDevicesStore } from "@/stores/devices";
import type { InfoSection } from "@/types/qt-bridge";

const bridge = useBridge();
const devices = useDevicesStore();
const on = useSignal();

const sections = ref<InfoSection[]>([]);
const fields = ref<Record<string, string>>({});
const loading = ref(false);
const progress = ref({ done: 0, total: 0 });

onMounted(async () => {
  sections.value = await bridge.info.sections();
  on(bridge.info.fetchStarted, () => { loading.value = true; });
  on(bridge.info.fetchProgress, (done, total) => { progress.value = { done, total }; });
  on(bridge.info.fetchFinished, (d) => {
    fields.value = d.fields;
    sections.value = d.sections;
    loading.value = false;
  });
  if (devices.active) bridge.info.fetch(devices.active.serial);
});

watch(() => devices.active?.serial, (serial) => {
  if (serial) bridge.info.fetch(serial);
  else { fields.value = {}; }
});

async function refresh() {
  if (devices.active) await bridge.info.fetch(devices.active.serial);
}
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">Device Info</h1>
    <span class="page-sub">
      <template v-if="devices.active">Auto-collected from <span class="num">{{ devices.active.model || devices.active.serial }}</span></template>
      <template v-else>No device selected</template>
    </span>
    <div class="page-actions">
      <button class="btn" :disabled="!devices.active || loading" @click="refresh">Refresh</button>
    </div>
  </div>

  <div v-if="loading" class="progress mb-4"><i :style="{ width: progress.total ? (progress.done / progress.total * 100) + '%' : '20%' }"></i></div>

  <div class="grid gap-4" style="grid-template-columns: repeat(2, minmax(0, 1fr)); align-items:start">
    <section v-for="sec in sections" :key="sec.title" class="card">
      <div class="card-h"><div class="label">{{ sec.title }}</div></div>
      <table class="detail-table">
        <tbody>
          <tr v-for="f in sec.fields" :key="f">
            <td>{{ f }}</td>
            <td>{{ fields[f] || "—" }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>
