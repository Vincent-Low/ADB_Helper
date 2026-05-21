import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router";
import { initBridge } from "@/plugins/qt-bridge";
import { useAppStore } from "@/stores/app";
import { useDevicesStore } from "@/stores/devices";
import "./style.css";

async function boot() {
  await initBridge();
  const app = createApp(App);
  const pinia = createPinia();
  app.use(pinia);
  app.use(router);

  // Hydrate global stores before first paint so the shell already has theme,
  // active device, settings — avoids a UI flicker.
  await useAppStore().init();
  await useDevicesStore().init();

  app.mount("#app");
}

boot().catch((err) => {
  console.error("ADB_Helper boot failed:", err);
  const root = document.getElementById("app");
  if (root) {
    root.innerHTML =
      '<pre style="color:#f87171;padding:24px;font-family:monospace">' +
      "Boot error:\n" + String(err) + "</pre>";
  }
});
