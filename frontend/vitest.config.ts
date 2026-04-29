import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./"),
    },
  },
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: './vitest.setup.ts',
    exclude: ["tests/e2e/**", "playwright/**", "**/*.spec.{ts,tsx}", "node_modules/**"],
    // Keep a single worker for stability/perf, but isolate modules per file so
    // local vi.mock() calls do not leak across the shared run.
    poolOptions: {
      threads: {
        singleThread: true,
      },
    },
    isolate: true,
  },
});
