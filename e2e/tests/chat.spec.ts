import { test, expect } from "@playwright/test";
import path from "path";

const CSV_PATH = path.join(__dirname, "..", "fixtures", "sample_data.csv");

/**
 * Helper: upload CSV and wait for the schema greeting before running chat tests.
 */
async function uploadAndWaitForGreeting(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(
    page.getByText("Drop a CSV file here or click to browse")
  ).toBeVisible();

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(CSV_PATH);

  // Wait for greeting with schema info
  await expect(page.getByText("I've loaded")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByPlaceholder("Ask about your data...")).toBeEnabled();
}

/**
 * Helper: send a chat message and wait for the assistant to finish responding.
 */
async function sendMessage(page: import("@playwright/test").Page, text: string) {
  const chatInput = page.getByPlaceholder("Ask about your data...");
  await chatInput.fill(text);
  await page.getByRole("button", { name: "Send" }).click();

  // Wait for the assistant response to finish streaming.
  // During streaming the Stop button is visible; when done, Send returns.
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({
    timeout: 90_000,
  });

  // Small delay to ensure the final message_complete event has been rendered
  await page.waitForTimeout(1000);
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

    // The last assistant message should contain a numeric value.
    // The fintech companies in our fixture have ARR: 1200, 1850, 1650, 780, 1400, 2100
    // Average = ~1330
    // Look for any number pattern in the assistant's response
    const assistantMessages = page.locator(
      'div.justify-start >> p.whitespace-pre-wrap'
    );
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
    const assistantMessages = page.locator(
      'div.justify-start >> p.whitespace-pre-wrap'
    );
    const lastMessage = assistantMessages.last();
    await expect(lastMessage).toBeVisible();

    const text = await lastMessage.textContent();
    expect(text).toBeTruthy();
    // The response should mention PivotAI (the company with highest growth rate)
    expect(text).toMatch(/PivotAI/i);
  });

  test("ask malformed question and verify graceful error or response", async ({
    page,
  }) => {
    await sendMessage(
      page,
      "SELECT DROP TABLE * FROM nonexistent WHERE 1=1;;;"
    );

    // The agent should handle this gracefully — either provide a polite error message
    // or explain it can't process the request. It should NOT crash.
    const assistantMessages = page.locator(
      'div.justify-start >> p.whitespace-pre-wrap'
    );
    const lastMessage = assistantMessages.last();
    await expect(lastMessage).toBeVisible();

    const text = await lastMessage.textContent();
    expect(text).toBeTruthy();
    // The response should have some content (not empty/crashed)
    expect(text!.length).toBeGreaterThan(10);
  });
});
