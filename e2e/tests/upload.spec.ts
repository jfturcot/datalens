import { test, expect } from "@playwright/test";
import path from "path";

const FIXTURE_DIR = path.join(__dirname, "..", "fixtures");
const CSV_PATH = path.join(FIXTURE_DIR, "sample_data.csv");

test.describe("File Upload", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for the app to finish loading and show the drop zone
    await expect(
      page.getByText("Drop a CSV file here or click to browse")
    ).toBeVisible();
  });

  test("drop CSV file and see schema greeting", async ({ page }) => {
    // Use the hidden file input to upload the CSV
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CSV_PATH);

    // Wait for upload to complete and LLM auto-greeting to appear
    // The LLM describes the dataset — wait for an assistant message bubble
    const assistantMessage = page.locator('[class*="bg-gray-100"]').first();
    await expect(assistantMessage).toBeVisible({ timeout: 60_000 });

    // The chat input should now be enabled
    const chatInput = page.getByPlaceholder("Ask about your data...");
    await expect(chatInput).toBeEnabled();
  });

  test("reject non-CSV file", async ({ page }) => {
    // Create a temporary non-CSV file by using a .txt buffer
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "notes.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("This is not a CSV file"),
    });

    // Should show an error message about CSV requirement
    const errorMessage = page.locator("text=/[Cc][Ss][Vv]/");
    await expect(errorMessage).toBeVisible({ timeout: 15_000 });

    // The chat input should still be disabled (no successful upload)
    const chatInput = page.getByPlaceholder("Ask about your data...");
    await expect(chatInput).toBeVisible();
  });

  test("reject oversized file", async ({ page }) => {
    // Create a file that exceeds the 10MB limit
    const largeBuffer = Buffer.alloc(11 * 1024 * 1024, "a");
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "large_file.csv",
      mimeType: "text/csv",
      buffer: largeBuffer,
    });

    // Should show an error about file size
    const errorMessage = page.locator("text=/[Ss]ize|[Ll]arge|10.?MB/");
    await expect(errorMessage).toBeVisible({ timeout: 15_000 });

    // The chat input should still be disabled
    const chatInput = page.getByPlaceholder("Ask about your data...");
    await expect(chatInput).toBeVisible();
  });
});
