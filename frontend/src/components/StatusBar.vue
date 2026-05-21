<script setup lang="ts">
import { computed } from "vue";
import { useDevicesStore } from "@/stores/devices";

const devices = useDevicesStore();
const active = computed(() => devices.active);
const transport = computed(() => active.value?.connection_type === "wifi" ? "Wi-Fi" : "USB");
const battery = computed<number | null>(() => {
  const v = (active.value as any)?.battery_pct;
  return typeof v === "number" ? v : null;
});
const apiLevel = computed(() => (active.value as any)?.api_level || null);
</script>

<template>
  <footer class="statusbar">
    <template v-if="active">
      <span class="seg">
        <span class="dot ok"></span>
        <strong>{{ active.model || active.serial }}</strong>
        <span style="color:var(--text-3)">·</span>
        <span class="num">{{ active.serial }}</span>
      </span>
      <span class="sep"></span>
      <span class="seg">Transport: <strong>{{ transport }}</strong></span>
      <span class="sep"></span>
      <span class="seg">
        Android <strong>{{ active.sdk_version || "—" }}</strong>
        <template v-if="apiLevel"> · API {{ apiLevel }}</template>
      </span>
      <span v-if="battery !== null" class="sep"></span>
      <span v-if="battery !== null" class="seg" title="Battery">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="7" width="16" height="10" rx="2"></rect>
          <line x1="22" y1="11" x2="22" y2="13"></line>
          <line x1="6" y1="11" :x2="6 + 8 * (battery / 100)" y2="11" stroke-width="6"></line>
        </svg>
        <strong>{{ battery }}%</strong>
      </span>
    </template>
    <template v-else>
      <span class="seg"><span class="dot"></span>No device selected</span>
    </template>
    <span class="right-side">
      <span class="sep"></span>
      <span class="seg">ADB <strong style="color:var(--success)">running</strong></span>
    </span>
  </footer>
</template>
