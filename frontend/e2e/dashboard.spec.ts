import { expect, test } from "@playwright/test";

test("loads fixture data and supports filters and playback controls", async ({ page }) => {
  await page.goto("/");

  const topline = page.locator(".workspace-topline");
  await expect(topline).toContainText("2026-06-28");
  await expect(topline).toContainText("12 visible / 13 frame / 13 assets / 11 dates");
  const scatterChart = page.locator(".scatter-chart");
  await expect(scatterChart.locator("canvas")).toBeVisible();
  await expect(page.locator(".trend-legend")).toContainText("−40");
  await expect(page.locator(".trend-legend")).toContainText("40");
  await expect(page.getByRole("img", { name: "Market map scatter plot. Relative Strength Score ranges from 70 to 140; Leverage Value ranges from 0 to 100. Scroll to zoom, drag to pan, or use Box Zoom." })).toBeVisible();

  const chartBox = await scatterChart.boundingBox();
  if (!chartBox) throw new Error("scatter chart has no bounding box");
  const plotWidth = chartBox.width - 66 - 122;
  const plotHeight = chartBox.height - 34 - 58;
  await page.mouse.move(
    chartBox.x + 66 + ((84 - 70) / (140 - 70)) * plotWidth,
    chartBox.y + 34 + ((100 - 66) / 100) * plotHeight,
  );
  await expect(page.getByText("AAA Fixture Alpha", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "First" }).click();
  await expect(topline).toContainText("2026-06-18");
  await page.getByRole("button", { name: "Latest" }).click();
  await expect(topline).toContainText("2026-06-28");

  await page.getByLabel("Asset Class").selectOption("instruments");
  await expect(topline).toContainText("1 visible / 13 frame");
  await expect(page.getByLabel("Velocity")).toHaveCount(0);

  await page.getByLabel("Asset Class").selectOption("gs_exempt");
  await expect(topline).toContainText("1 visible / 13 frame");

  const search = page.getByPlaceholder("Symbol or asset name");
  await search.fill("AAA");
  await expect(search).toHaveValue("AAA");
  await expect(topline).toContainText("1 visible / 13 frame");
  await search.press("Enter");

  const detailPanel = page.locator(".detail-panel");
  await expect(detailPanel).toBeVisible();
  await expect(detailPanel.getByText("Fixture Alpha")).toBeVisible();
  await expect(detailPanel.getByText("高置信多头", { exact: true })).toBeVisible();
  await expect(detailPanel.getByText("快速加杠杆", { exact: true })).toBeVisible();
  await expect(detailPanel.getByText("资金加杠杆", { exact: true })).toHaveCount(0);
  await expect(detailPanel.getByText("比价领先", { exact: true })).toHaveCount(0);
  await expect(detailPanel.getByText("资金去杠杆", { exact: true })).toHaveCount(0);
  await expect(detailPanel.getByText("比价改善", { exact: true })).toHaveCount(0);
  await expect(detailPanel.getByText("观察", { exact: true })).toHaveCount(0);
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

  const trendChart = detailPanel.locator(".mini-chart").filter({ hasText: "趋势分变化" });
  await expect(trendChart.getByText("06-18")).toBeVisible();
  await expect(trendChart.getByText("06-28")).toBeVisible();
  await expect(trendChart.locator(".mini-chart-x-label")).toHaveCount(5);

  const relativeStrengthChart = detailPanel.locator(".mini-chart").filter({ hasText: "比价分变化" });
  await expect(relativeStrengthChart.locator(".mini-chart-threshold")).toHaveCount(3);
  await expect(relativeStrengthChart.locator(".mini-chart-threshold.is-baseline")).toHaveCount(1);
  await expect(relativeStrengthChart.getByText("120", { exact: true })).toBeVisible();
  await expect(relativeStrengthChart.getByText("100", { exact: true })).toBeVisible();
  await expect(relativeStrengthChart.getByText("80", { exact: true })).toBeVisible();

  const leverageChart = detailPanel.locator(".mini-chart").filter({ hasText: "杠杆资金水位变化" });
  await expect(leverageChart.locator("path.mini-chart-path")).toBeVisible();
  await expect(detailPanel.locator("path.mini-chart-path")).toHaveCount(5);
  await expect(detailPanel.locator(".mini-chart circle")).toHaveCount(0);
  await expect(detailPanel.getByText("杠杆速率分变化")).toHaveCount(0);
  await detailPanel.getByRole("button", { name: "Close detail panel" }).click();
  await expect(detailPanel).toHaveCount(0);

  await search.fill("BBB");
  await search.press("Enter");
  await expect(detailPanel.getByText("Fixture Beta")).toBeVisible();
  await expect(detailPanel.getByText("资金去杠杆", { exact: true })).toHaveCount(0);
  await expect(detailPanel.locator(".tag-row")).toHaveCount(0);
  await detailPanel.getByRole("button", { name: "Close detail panel" }).click();

  await page.getByRole("tab", { name: "Opportunities" }).click();
  await expect(page.getByTestId("strong-long-section")).toContainText("12 total / top 10 shown");
  await expect(page.getByTestId("candidate-long-section")).toContainText("11 total / top 10 shown");
  await expect(page.getByTestId("strong-short-section")).toContainText("1 total / top 1 shown");
  await expect(page.getByTestId("candidate-short-section")).toContainText("1 total / top 1 shown");
  await expect(page.getByTestId("strong-long-table")).toContainText("标的类型");
  await expect(page.getByTestId("strong-long-table")).toContainText("当前杠杆持续时间");
  await expect(page.getByTestId("strong-long-table")).toContainText("10日总排名变化");
  await expect(page.getByTestId("strong-long-row")).toHaveCount(10);
  await expect(page.getByTestId("candidate-long-row")).toHaveCount(10);
  await expect(page.getByTestId("strong-short-row")).toHaveCount(1);
  await expect(page.getByTestId("candidate-short-row")).toHaveCount(1);
  await expect(page.getByTestId("strong-long-table")).toContainText("Fixture Alpha");
  await expect(page.getByTestId("candidate-long-table")).toContainText("Candidate 10");
  await expect(page.getByText("Candidate 11")).toHaveCount(0);
  await expect(page.getByTestId("strong-long-table")).toContainText("+1");
  await expect(page.getByTestId("strong-short-table")).toContainText("Fixture Beta");
  await expect(page.getByTestId("candidate-short-table")).toContainText("Fixture Beta");
  await expect(page.getByTestId("strong-short-table")).toContainText("0");

  const opportunityRow = page.getByTestId("strong-long-row").filter({ hasText: "Fixture Alpha" });
  await opportunityRow.click();
  await expect(opportunityRow).toHaveAttribute("aria-selected", "true");
  await expect(page.locator(".opportunities-body .detail-panel")).toBeVisible();
  await expect(page.locator(".opportunities-body .detail-panel").getByText("Fixture Alpha")).toBeVisible();
  await expect(page.locator(".opportunities-body .panel-resizer")).toBeVisible();
  await page.locator(".opportunities-body .detail-panel").getByRole("button", { name: "Close detail panel" }).click();

  await page.getByLabel("Asset Class").selectOption("gs_exempt");
  await expect(page.getByTestId("strong-long-section")).toContainText("1 total / top 1 shown");
  await expect(page.getByTestId("candidate-long-section")).toContainText("0 total / top 0 shown");
  await expect(page.getByTestId("strong-long-table")).toContainText("Fixture Alpha");
  await expect(page.getByTestId("strong-long-row")).toHaveCount(1);
});

test("renders an actionable backend error state", async ({ page }) => {
  await page.route("**/api/config", (route) => route.abort());

  await page.goto("/");

  await expect(page.getByText("Backend service is offline")).toBeVisible();
  await expect(
    page.getByText("Start it with scripts/run_market_map_dashboard.sh"),
  ).toBeVisible();
});
