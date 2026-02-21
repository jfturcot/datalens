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

    // Wait for upload to complete and greeting to appear
    // The greeting should mention the filename and column names
    const greeting = page.locator("text=I've loaded");
    await expect(greeting).toBeVisible({ timeout: 30_000 });

    // Verify the greeting contains schema information
    await expect(page.getByText("sample_data.csv")).toBeVisible();
    await expect(page.getByText("company_name")).toBeVisible();
    await expect(page.getByText("industry_vertical")).toBeVisible();
    await expect(page.getByText("arr_thousands")).toBeVisible();
    await expect(page.getByText("20 rows")).toBeVisible();

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
    const chatInput = page.getByPlaceholder(
      "Upload a CSV file to start chatting"
    );
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
    const chatInput = page.getByPlaceholder(
      "Upload a CSV file to start chatting"
    );
    await expect(chatInput).toBeVisible();
  });
});
