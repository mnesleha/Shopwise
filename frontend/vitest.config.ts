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
    // Performance optimizations
    poolOptions: {
      threads: {
        singleThread: true,  // Shared environment between tests
      },
    },
    isolate: false,  // Do not isolate each test file (faster)
  },
});
