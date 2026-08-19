import { test, expect } from "@playwright/test";

test("wizard completes and shows solution", async ({ page }) => {
  test.skip(process.env.E2E_FULL !== "1", "Full flow requires backend running.");
  await page.goto("/");

  await page.getByTestId("page-mission-family").waitFor();
  await page.getByRole("heading", { name: "Select Mission Family" }).waitFor();
  await page.getByRole("button", { name: "Remote Sensing" }).click();

  await page.getByTestId("page-payload").waitFor();
  await page.getByRole("heading", { name: "Select Payload" }).waitFor();
  await page.getByRole("button", { name: /VHR Optical/i }).click();
  await page.getByRole("button", { name: "Next" }).click();

  await page.getByTestId("page-roi").waitFor();
  await page.getByRole("heading", { name: "Region of Interest" }).waitFor();
  await page.getByLabel("Global Coverage").uncheck();
  await page.getByLabel("Region Search").fill("Pakistan");
  await page.getByRole("button", { name: "Next" }).click();

  await page.getByTestId("page-parameters").waitFor();
  await page.getByRole("heading", { name: "Mission Parameters" }).waitFor();
  await page.getByLabel("Revisit Hours").fill("48");
  await page.getByRole("button", { name: "Finish" }).click();

  await page.getByTestId("page-result").waitFor();
  await page.getByRole("heading", { name: "Your Constellation" }).waitFor();
  await expect(page.getByTestId("solution-platform")).toContainText("Platform");
  await expect(page.getByTestId("solution-satellites")).toContainText("satellites");
});
