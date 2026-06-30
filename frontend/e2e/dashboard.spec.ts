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

  const search = page.getByPlaceholder("Symbol or asset name");
  await search.fill("AAA");
  await expect(search).toHaveValue("AAA");
  await expect(topline).toContainText("1 visible / 2 frame");
});

test("renders an actionable backend error state", async ({ page }) => {
  await page.route("**/api/config", (route) => route.abort());

  await page.goto("/");

  await expect(page.getByText("Backend service is offline")).toBeVisible();
  await expect(
    page.getByText("Start it with scripts/run_market_map_dashboard.sh"),
  ).toBeVisible();
});
