<script setup lang="ts">
import { computed } from "vue";
import { useDevicesStore } from "@/stores/devices";

const devices = useDevicesStore();
const active = computed(() => devices.active);
const transport = computed(() => active.value?.connection_type === "wifi" ? "Wi-Fi" : "USB");
const ip = computed(() => {
  const s = active.value?.serial || "";
  return s.includes(":") ? s.split(":")[0] : "";
});
</script>

<template>
  <footer class="statusbar">
    <template v-if="active">
      <span class="seg"><span class="dot ok"></span><strong>{{ active.model || active.serial }}</strong>
        <span class="text-text3">·</span>
        <span class="num">{{ active.serial }}</span>
      </span>
      <span class="sep"></span>
      <span class="seg">Transport: <strong>{{ transport }}</strong></span>
      <span class="sep"></span>
      <span class="seg">Android <strong>{{ active.sdk_version || "—" }}</strong></span>
    </template>
    <template v-else>
      <span class="seg"><span class="dot"></span>No device selected</span>
    </template>
    <span class="right-side">
      <span class="seg">ADB <strong class="text-success">running</strong></span>
    </span>
  </footer>
</template>
