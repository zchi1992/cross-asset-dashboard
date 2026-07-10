import { expect, test } from "@playwright/test";

test("loads fixture data and supports filters and playback controls", async ({ page }) => {
  await page.goto("/");

  const topline = page.locator(".workspace-topline");
  await expect(topline).toContainText("2026-06-28");
  await expect(topline).toContainText("12 visible / 13 frame / 13 assets / 11 dates");
  await expect(page.locator(".scatter-chart canvas")).toBeVisible();

  await page.getByRole("button", { name: "First" }).click();
  await expect(topline).toContainText("2026-06-18");
  await page.getByRole("button", { name: "Latest" }).click();
  await expect(topline).toContainText("2026-06-28");

  await page.getByLabel("Asset Class").selectOption("instruments");
  await expect(topline).toContainText("1 visible / 13 frame");
  await expect(page.getByLabel("Velocity")).toHaveCount(0);

  const search = page.getByPlaceholder("Symbol or asset name");
  await search.fill("AAA");
  await expect(search).toHaveValue("AAA");
  await expect(topline).toContainText("1 visible / 13 frame");
  await search.press("Enter");

  const detailPanel = page.locator(".detail-panel");
  await expect(detailPanel).toBeVisible();
  await expect(detailPanel.getByText("Fixture Alpha")).toBeVisible();
  await expect(detailPanel.getByText("杠杆资金水平")).toBeVisible();
  await expect(detailPanel.getByText("杠杆速率分")).toHaveCount(0);
  await expect(detailPanel.getByText("杠杆速率", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("img", { name: "比价分变化" })).toBeVisible();
  await expect(page.locator(".mini-chart-legend")).toContainText("early_reversal");
  await expect(page.locator(".mini-chart-legend")).toContainText("strength_momentum");
  await expect(page.locator(".mini-chart-legend")).toContainText("relative_strength");
  await expect(page.locator(".mini-chart-swatch").nth(0)).toHaveCSS("background-color", "rgb(242, 200, 75)");
  await expect(page.locator(".mini-chart-swatch").nth(1)).toHaveCSS("background-color", "rgb(199, 166, 255)");
  await expect(page.locator(".mini-chart-swatch").nth(2)).toHaveCSS("background-color", "rgb(92, 202, 102)");

  const leverageChart = detailPanel.locator(".mini-chart").filter({ hasText: "杠杆资金水位变化" });
  await expect(leverageChart.locator("path.mini-chart-path")).toBeVisible();
  await expect(detailPanel.locator("path.mini-chart-path")).toHaveCount(5);
  await expect(detailPanel.locator(".mini-chart circle")).toHaveCount(0);
  await expect(detailPanel.getByText("杠杆速率分变化")).toHaveCount(0);

  await page.getByRole("tab", { name: "Opportunities" }).click();
  await expect(page.getByTestId("strong-long-section")).toContainText("12 total / top 10 shown");
  await expect(page.getByTestId("candidate-long-section")).toContainText("11 total / top 10 shown");
  await expect(page.getByTestId("strong-long-table")).toContainText("标的类型");
  await expect(page.getByTestId("strong-long-table")).toContainText("当前杠杆持续时间");
  await expect(page.getByTestId("strong-long-table")).toContainText("10日总排名变化");
  await expect(page.getByTestId("strong-long-row")).toHaveCount(10);
  await expect(page.getByTestId("candidate-long-row")).toHaveCount(10);
  await expect(page.getByTestId("strong-long-table")).toContainText("Fixture Alpha");
  await expect(page.getByTestId("candidate-long-table")).toContainText("Candidate 10");
  await expect(page.getByText("Candidate 11")).toHaveCount(0);
  await expect(page.getByTestId("strong-long-table")).toContainText("+1");
});

test("renders an actionable backend error state", async ({ page }) => {
  await page.route("**/api/config", (route) => route.abort());

  await page.goto("/");

  await expect(page.getByText("Backend service is offline")).toBeVisible();
  await expect(
    page.getByText("Start it with scripts/run_market_map_dashboard.sh"),
  ).toBeVisible();
});
