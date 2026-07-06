import { expect, test } from "@playwright/test";

test("loads fixture data and supports filters and playback controls", async ({ page }) => {
  await page.goto("/");

  const topline = page.locator(".workspace-topline");
  await expect(topline).toContainText("2026-06-28");
  await expect(topline).toContainText("1 visible / 2 frame / 2 assets / 2 dates");
  await expect(page.locator(".scatter-chart canvas")).toBeVisible();

  await page.getByRole("button", { name: "First" }).click();
  await expect(topline).toContainText("2026-06-27");
  await page.getByRole("button", { name: "Next" }).click();
  await expect(topline).toContainText("2026-06-28");

  await page.getByLabel("Asset Class").selectOption("instruments");
  await expect(topline).toContainText("1 visible / 2 frame");
  await expect(page.getByLabel("Velocity")).toHaveCount(0);

  const search = page.getByPlaceholder("Symbol or asset name");
  await search.fill("AAA");
  await expect(search).toHaveValue("AAA");
  await expect(topline).toContainText("1 visible / 2 frame");
  await search.press("Enter");

  const detailPanel = page.locator(".detail-panel");
  await expect(detailPanel).toBeVisible();
  await expect(detailPanel.getByText("杠杆资金水平")).toBeVisible();
  await expect(detailPanel.getByText("杠杆速率分")).toHaveCount(0);
  await expect(detailPanel.getByText("杠杆速率", { exact: true })).toHaveCount(0);

  const leverageChart = detailPanel.locator(".mini-chart").filter({ hasText: "杠杆资金水位变化" });
  await expect(leverageChart.locator("path.mini-chart-path")).toBeVisible();
  await expect(detailPanel.locator("path.mini-chart-path")).toHaveCount(3);
  await expect(detailPanel.locator(".mini-chart circle")).toHaveCount(0);
  await expect(detailPanel.getByText("杠杆速率分变化")).toHaveCount(0);
});

test("renders an actionable backend error state", async ({ page }) => {
  await page.route("**/api/config", (route) => route.abort());

  await page.goto("/");

  await expect(page.getByText("Backend service is offline")).toBeVisible();
  await expect(
    page.getByText("Start it with scripts/run_market_map_dashboard.sh"),
  ).toBeVisible();
});
