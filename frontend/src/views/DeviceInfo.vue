<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
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

// System card sub-sections (Version / Build / Firmware) — derived locally
// from field names until the backend can return nested subsections.
// See UNIMPLEMENTED_FEATURES.md → Device Info.
const SYSTEM_SUBSECTIONS: Array<{ title: string; fields: string[] }> = [
  {
    title: "Version",
    fields: ["Android", "API level", "Security patch", "Kernel"],
  },
  {
    title: "Build",
    fields: ["Build number", "Fingerprint", "Type", "Date"],
  },
  {
    title: "Firmware",
    fields: ["Bootloader", "Baseband", "Radio"],
  },
];

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

// Approximate height weight: card header (~44px) + rows (~36px each).
// For System, count subsection headers too.
const SYSTEM_HEADER_COUNT = SYSTEM_SUBSECTIONS.length + 1; // 3 subs + "Other"
function sectionWeight(s: InfoSection): number {
  if (s.title.toLowerCase() === "system") {
    return 44 + s.fields.length * 36 + SYSTEM_HEADER_COUNT * 28;
  }
  return 44 + s.fields.length * 36;
}

// Greedy bin-packing: place each section into the shorter column.
// System sticks to whichever column it's first assigned, but its size
// dominates so it usually ends up alone in one column with smaller
// sections balancing in the other.
const columns = computed(() => {
  const left: InfoSection[] = [];
  const right: InfoSection[] = [];
  let lh = 0;
  let rh = 0;
  // Place System first (heaviest); subsequent sections fill the lighter col.
  const ordered = [...sections.value].sort((a, b) => sectionWeight(b) - sectionWeight(a));
  for (const s of ordered) {
    const w = sectionWeight(s);
    if (lh <= rh) { left.push(s); lh += w; }
    else { right.push(s); rh += w; }
  }
  return { left, right };
});

function fieldsForSub(sub: { title: string; fields: string[] }, sys: InfoSection): string[] {
  const known = new Set(sub.fields);
  return sys.fields.filter((f) => known.has(f));
}
function leftoverSystemFields(sys: InfoSection): string[] {
  const taken = new Set(SYSTEM_SUBSECTIONS.flatMap((s) => s.fields));
  return sys.fields.filter((f) => !taken.has(f));
}

async function exportTxt() {
  // bridge.info.exportTxt — not yet implemented in qt-bridge.
  // See UNIMPLEMENTED_FEATURES.md → Device Info.
  const b: any = bridge;
  if (b.info?.exportTxt && devices.active) {
    await b.info.exportTxt(devices.active.serial);
  }
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
      <button class="btn" disabled title="Not implemented yet" @click="exportTxt">Export to TXT</button>
      <button class="btn" :disabled="!devices.active || loading" @click="refresh">Refresh</button>
    </div>
  </div>

  <div v-if="loading" class="progress mb-4"><i :style="{ width: progress.total ? (progress.done / progress.total * 100) + '%' : '20%' }"></i></div>

  <div class="grid gap-4" style="grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start">
    <div v-for="(col, ci) in [columns.left, columns.right]" :key="ci" class="flex flex-col gap-4">
      <section v-for="sec in col" :key="sec.title" class="card">
        <div class="card-h"><div class="label">{{ sec.title }}</div></div>
        <table class="detail-table">
          <tbody v-if="sec.title.toLowerCase() === 'system'">
            <template v-for="sub in SYSTEM_SUBSECTIONS" :key="sub.title">
              <template v-if="fieldsForSub(sub, sec).length">
                <tr class="section-head"><td colspan="2">{{ sub.title }}</td></tr>
                <tr v-for="f in fieldsForSub(sub, sec)" :key="f">
                  <td>{{ f }}</td>
                  <td>{{ fields[f] || "—" }}</td>
                </tr>
              </template>
            </template>
            <template v-if="leftoverSystemFields(sec).length">
              <tr class="section-head"><td colspan="2">Other</td></tr>
              <tr v-for="f in leftoverSystemFields(sec)" :key="f">
                <td>{{ f }}</td>
                <td>{{ fields[f] || "—" }}</td>
              </tr>
            </template>
          </tbody>
          <tbody v-else>
            <tr v-for="f in sec.fields" :key="f">
              <td>{{ f }}</td>
              <td>{{ fields[f] || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>
