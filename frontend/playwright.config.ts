import { defineConfig, devices } from "@playwright/test";

const noProxy = new Set(
  `${process.env.NO_PROXY ?? ""},${process.env.no_proxy ?? ""}`
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean),
);
noProxy.add("127.0.0.1");
noProxy.add("localhost");
process.env.NO_PROXY = [...noProxy].join(",");
process.env.no_proxy = process.env.NO_PROXY;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:8765",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "../scripts/run_fixture_dashboard.sh 8765",
    url: "http://127.0.0.1:8765/api/ready",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
