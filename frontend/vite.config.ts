import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

export default defineConfig({
  // MUST be './' — the production bundle is loaded via file:///…/frontend_dist/index.html.
  // With base: '/', Chromium resolves /assets/… against the filesystem root and 404s.
  base: "./",
  plugins: [vue()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  build: {
    outDir: path.resolve(__dirname, "..", "frontend_dist"),
    emptyOutDir: true,
    target: "chrome120",
    sourcemap: false,
  },
  server: {
    strictPort: true,
    port: 5173,
    host: "127.0.0.1",
  },
});
