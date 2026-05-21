<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { NAV } from "@/router";
import { useAppStore } from "@/stores/app";
import NavIcon from "./NavIcon.vue";

const route = useRoute();
const router = useRouter();
const app = useAppStore();
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="logo">A</div>
      <div>
        <div class="name">ADB_Helper</div>
        <div class="ver">v{{ app.appVersion }}</div>
      </div>
    </div>
    <nav aria-label="Primary" class="flex flex-col gap-0.5">
      <button
        v-for="item in NAV" :key="item.id"
        class="nav-item"
        :aria-current="route.name === item.id ? 'page' : 'false'"
        @click="router.push(item.path)"
      >
        <NavIcon :name="item.icon" />
        <span>{{ item.label }}</span>
      </button>
    </nav>
    <div class="flex-1" />
  </aside>
</template>
