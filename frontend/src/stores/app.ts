import { defineStore } from "pinia";
import { ref } from "vue";
import { useBridge } from "@/plugins/qt-bridge";
import type { DeviceContext } from "@/types/qt-bridge";

export type ThemeMode = "system" | "light" | "dark";
export type EffectiveTheme = "dark" | "light";

export const useAppStore = defineStore("app", () => {
  const ready = ref(false);
  const theme = ref<ThemeMode>("system");
  const effectiveTheme = ref<EffectiveTheme>("dark");
  const settings = ref<Record<string, any>>({});
  const activeDevice = ref<DeviceContext | null>(null);
  const appVersion = ref("1.0.0");
  const strings = ref<Record<string, string>>({});

  function applyEffectiveTheme(mode: ThemeMode) {
    if (mode === "system") {
      const isLight = window.matchMedia("(prefers-color-scheme: light)").matches;
      effectiveTheme.value = isLight ? "light" : "dark";
    } else {
      effectiveTheme.value = mode;
    }
    document.documentElement.setAttribute("data-theme", effectiveTheme.value);
  }

  async function init() {
    const b = useBridge();
    const state = await b.app.getInitialState();
    theme.value = (state.theme as ThemeMode) || "system";
    effectiveTheme.value = (state.effectiveTheme as EffectiveTheme) || "dark";
    settings.value = state.settings || {};
    activeDevice.value = state.activeDevice;
    appVersion.value = state.appVersion || "1.0.0";
    strings.value = state.strings || {};
    applyEffectiveTheme(theme.value);

    b.app.themeChanged.connect((mode: string) => {
      effectiveTheme.value = (mode as EffectiveTheme) || effectiveTheme.value;
      document.documentElement.setAttribute("data-theme", effectiveTheme.value);
    });
    b.app.activeDeviceChanged.connect((d) => { activeDevice.value = d; });
    b.app.settingsChanged.connect((s) => { settings.value = { ...settings.value, ...s }; });

    window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
      if (theme.value === "system") applyEffectiveTheme("system");
    });

    ready.value = true;
  }

  async function setTheme(mode: ThemeMode) {
    theme.value = mode;
    applyEffectiveTheme(mode);
    await useBridge().app.setTheme(mode);
  }

  function S(key: string, fallback = ""): string {
    return strings.value[key] || fallback;
  }

  return {
    ready, theme, effectiveTheme, settings, activeDevice, appVersion, strings,
    init, setTheme, S,
  };
});
