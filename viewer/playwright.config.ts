import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  outputDir: "./test-results",
  use: {
    baseURL: "http://127.0.0.1:5173",
    screenshot: "only-on-failure",
  },
});

