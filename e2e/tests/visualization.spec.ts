import { test, expect } from "@playwright/test";
import path from "path";
import { mockLLMResponses } from "../fixtures/mock-sse";

const CSV_PATH = path.join(__dirname, "..", "fixtures", "sample_data.csv");

/**
 * Helper: upload CSV and wait for the auto-greeting.
 */
async function uploadAndWaitForGreeting(page: import("@playwright/test").Page) {
  await mockLLMResponses(page);
  await page.goto("/");
  await expect(
    page.getByText("Drop a CSV file here or click to browse")
  ).toBeVisible();

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(CSV_PATH);

  // Wait for the mocked auto-greeting content to appear
  await expect(page.getByText("20 rows")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByPlaceholder("Ask about your data...")).toBeEnabled();
}

/**
 * Helper: send a chat message and wait for the response to complete.
 */
async function sendMessage(page: import("@playwright/test").Page, text: string) {
  const chatInput = page.getByPlaceholder("Ask about your data...");
  await chatInput.fill(text);
  await page.getByRole("button", { name: "Send" }).click();

  // Wait for streaming to finish (Send button reappears)
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({
    timeout: 30_000,
  });

  await page.waitForTimeout(500);
}

test.describe("Visualization", () => {
  test.beforeEach(async ({ page }) => {
    await uploadAndWaitForGreeting(page);
  });

  test("ask question that triggers bar chart and verify chart renders", async ({
    page,
  }) => {
    // This question triggers the bar_chart mock response
    await sendMessage(
      page,
      "Show me the average ARR by industry vertical as a bar chart"
    );

    // Recharts renders SVG elements with .recharts-bar-rectangle rect elements
    const chartContainer = page.locator(".recharts-responsive-container");
    await expect(chartContainer.first()).toBeVisible({ timeout: 10_000 });

    // Verify the bar chart has actual bar rectangles rendered
    const bars = page.locator(".recharts-bar-rectangle");
    await expect(bars.first()).toBeVisible();
  });

  test("click chart and verify side panel opens", async ({ page }) => {
    await sendMessage(
      page,
      "Show me the average ARR by industry vertical as a bar chart"
    );

    // Wait for the inline chart to appear
    const chartContainer = page.locator(".recharts-responsive-container");
    await expect(chartContainer.first()).toBeVisible({ timeout: 10_000 });

    // Click the visualization area (the clickable wrapper with "Click to expand")
    const expandButton = page.locator('[aria-label="Click to expand visualization"]');
    await expect(expandButton.first()).toBeVisible();
    await expandButton.first().click();

    // The VizPanel should now be visible with a close button
    const closeButton = page.locator('[aria-label="Close panel"]');
    await expect(closeButton).toBeVisible();

    // Should have multiple recharts containers (inline + panel)
    const allCharts = page.locator(".recharts-responsive-container");
    expect(await allCharts.count()).toBeGreaterThanOrEqual(2);
  });

  test("close panel and verify return to full chat", async ({ page }) => {
    await sendMessage(
      page,
      "Show me the average ARR by industry vertical as a bar chart"
    );

    // Wait for inline chart
    const chartContainer = page.locator(".recharts-responsive-container");
    await expect(chartContainer.first()).toBeVisible({ timeout: 10_000 });

    // Open the side panel
    const expandButton = page.locator('[aria-label="Click to expand visualization"]');
    await expandButton.first().click();

    const closeButton = page.locator('[aria-label="Close panel"]');
    await expect(closeButton).toBeVisible();

    // Close the panel
    await closeButton.click();

    // The close button should no longer be visible (panel is gone)
    await expect(closeButton).not.toBeVisible();

    // The chat input should still be functional
    const chatInput = page.getByPlaceholder("Ask about your data...");
    await expect(chatInput).toBeEnabled();

    // Only the inline chart should remain (panel chart gone)
    const remainingCharts = page.locator(".recharts-responsive-container");
    expect(await remainingCharts.count()).toBe(1);
  });
});
