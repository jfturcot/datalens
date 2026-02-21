import { test, expect } from "@playwright/test";
import path from "path";
import { mockLLMResponses } from "../fixtures/mock-sse";

const CSV_PATH = path.join(__dirname, "..", "fixtures", "sample_data.csv");

/**
 * Helper: upload CSV and wait for the auto-greeting before running chat tests.
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
 * Helper: send a chat message and wait for the assistant to finish responding.
 */
async function sendMessage(page: import("@playwright/test").Page, text: string) {
  const chatInput = page.getByPlaceholder("Ask about your data...");
  await chatInput.fill(text);
  await page.getByRole("button", { name: "Send" }).click();

  // Wait for streaming to finish (Send button reappears)
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({
    timeout: 30_000,
  });

  // Small delay to ensure the final message_complete event has been rendered
  await page.waitForTimeout(500);
}

test.describe("Chat", () => {
  test.beforeEach(async ({ page }) => {
    await uploadAndWaitForGreeting(page);
  });

  test("ask average ARR for fintech companies and verify numeric answer", async ({
    page,
  }) => {
    await sendMessage(
      page,
      "What is the average ARR for fintech companies?"
    );

    // The last assistant message should contain a numeric value (~1330)
    const assistantMessages = page.locator("div.justify-start");
    const lastMessage = assistantMessages.last();
    await expect(lastMessage).toBeVisible();

    const text = await lastMessage.textContent();
    expect(text).toBeTruthy();
    // Should contain a number (the average ARR value)
    expect(text).toMatch(/\d+/);
  });

  test("ask which company has the highest growth rate and verify company name", async ({
    page,
  }) => {
    await sendMessage(
      page,
      "Which company has the highest growth rate?"
    );

    // PivotAI has 85.2% yoy_growth_rate_percent — the highest in our fixture
    const assistantMessages = page.locator("div.justify-start");
    const lastMessage = assistantMessages.last();
    await expect(lastMessage).toBeVisible();

    const text = await lastMessage.textContent();
    expect(text).toBeTruthy();
    // The response should mention PivotAI
    expect(text).toMatch(/PivotAI/i);
  });

  test("ask malformed question and verify graceful response", async ({
    page,
  }) => {
    await sendMessage(
      page,
      "SELECT DROP TABLE * FROM nonexistent WHERE 1=1;;;"
    );

    // The agent should handle this gracefully
    const assistantMessages = page.locator("div.justify-start");
    const lastMessage = assistantMessages.last();
    await expect(lastMessage).toBeVisible();

    const text = await lastMessage.textContent();
    expect(text).toBeTruthy();
    // The response should have some content (not empty/crashed)
    expect(text!.length).toBeGreaterThan(10);
  });
});
