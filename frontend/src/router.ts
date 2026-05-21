import { createRouter, createMemoryHistory, type RouteRecordRaw } from "vue-router";

import Connections from "@/views/Connections.vue";
import Terminal from "@/views/Terminal.vue";
import Installer from "@/views/Installer.vue";
import Scrcpy from "@/views/Scrcpy.vue";
import DeviceButtons from "@/views/DeviceButtons.vue";
import DeviceInfo from "@/views/DeviceInfo.vue";
import Apps from "@/views/Apps.vue";
import Logcat from "@/views/Logcat.vue";
import Settings from "@/views/Settings.vue";

export interface NavItem {
  id: string;
  path: string;
  label: string;
  icon: string;
}

export const NAV: NavItem[] = [
  { id: "connections",  path: "/connections", label: "Connections",     icon: "link" },
  { id: "terminal",     path: "/terminal",    label: "Terminal",        icon: "term" },
  { id: "installer",    path: "/installer",   label: "Installer",       icon: "box"  },
  { id: "scrcpy",       path: "/scrcpy",      label: "Scrcpy",          icon: "screen" },
  { id: "buttons",      path: "/buttons",     label: "Device Buttons",  icon: "grid" },
  { id: "info",         path: "/info",        label: "Device Info",     icon: "info" },
  { id: "apps",         path: "/apps",        label: "Apps",            icon: "apps" },
  { id: "logcat",       path: "/logcat",      label: "Logcat",          icon: "doc"  },
  { id: "settings",     path: "/settings",    label: "Settings",        icon: "gear" },
];

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/connections" },
  { path: "/connections", name: "connections", component: Connections },
  { path: "/terminal",    name: "terminal",    component: Terminal },
  { path: "/installer",   name: "installer",   component: Installer },
  { path: "/scrcpy",      name: "scrcpy",      component: Scrcpy },
  { path: "/buttons",     name: "buttons",     component: DeviceButtons },
  { path: "/info",        name: "info",        component: DeviceInfo },
  { path: "/apps",        name: "apps",        component: Apps },
  { path: "/logcat",      name: "logcat",      component: Logcat },
  { path: "/settings",    name: "settings",    component: Settings },
];

export const router = createRouter({
  history: createMemoryHistory(),
  routes,
});
