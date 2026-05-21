import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import type { DeviceContext, PairedDevice } from "@/types/qt-bridge";

export const useDevicesStore = defineStore("devices", () => {
  const devices = ref<DeviceContext[]>([]);
  const active = ref<DeviceContext | null>(null);
  const paired = ref<PairedDevice[]>([]);

  const onlineCount = computed(() =>
    devices.value.filter((d) => d.status === "online").length,
  );

  async function init() {
    const b = useBridge();
    devices.value = await b.connections.listDevices();
    active.value = await b.connections.activeDevice();
    paired.value = await b.connections.listPaired();

    b.connections.deviceConnected.connect((d) => {
      const idx = devices.value.findIndex((x) => x.serial === d.serial);
      if (idx >= 0) devices.value[idx] = d;
      else devices.value.push(d);
    });
    b.connections.deviceDisconnected.connect((serial) => {
      devices.value = devices.value.filter((d) => d.serial !== serial);
      if (active.value?.serial === serial) active.value = null;
    });
    b.connections.deviceStateChanged.connect((d) => {
      const i = devices.value.findIndex((x) => x.serial === d.serial);
      if (i >= 0) devices.value[i] = d;
      else devices.value.push(d);
    });
    b.connections.activeDeviceChanged.connect((d) => { active.value = d; });
  }

  async function setActive(serial: string) {
    await useBridge().connections.setActiveDevice(serial);
  }
  async function reloadPaired() {
    paired.value = await useBridge().connections.listPaired();
  }

  return { devices, active, paired, onlineCount, init, setActive, reloadPaired };
});
