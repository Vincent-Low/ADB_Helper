<script setup lang="ts">
import { RouterView } from "vue-router";
import Sidebar from "@/components/Sidebar.vue";
import StatusBar from "@/components/StatusBar.vue";

const layoutStyle = {
  gridTemplateColumns: "var(--sidebar-w) 1fr",
  gridTemplateRows: "1fr var(--status-h)",
  gridTemplateAreas: `"side main" "side status"`,
};
</script>

<template>
  <div
    class="grid h-screen text-text1"
    :style="layoutStyle"
  >
    <Sidebar style="grid-area: side" />
    <main class="overflow-auto bg-app px-6 py-5 min-w-0" style="grid-area: main">
      <RouterView v-slot="{ Component }">
        <KeepAlive :max="9">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>
    <StatusBar style="grid-area: status" />
  </div>
</template>
