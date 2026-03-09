import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from '@tailwindcss/vite';
import path from "path";
import { TanStackRouterVite } from '@tanstack/router-vite-plugin'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), TanStackRouterVite(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      // Vite 7 treats unresolved-import warnings as errors by default.
      // In pnpm workspaces, transitive deps (e.g. @radix-ui sub-packages)
      // are hoisted to root node_modules/ but not symlinked into each
      // workspace package. Rollup flags these as "unresolved" even though
      // Node resolves them at runtime via the hoisted location. Downgrade
      // these back to warnings so the build succeeds.
      onLog(level, log, handler) {
        if (log.code === 'UNRESOLVED_IMPORT') {
          handler('warn', log);
          return;
        }
        handler(level, log);
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
        autoRewrite: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        autoRewrite: true,
      },
    },
  },
});