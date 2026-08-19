import { test, expect } from "@playwright/test";
import { mockTaxonomy } from "./mocks";

test("error handling on solve failure (mocked backend)", async ({ page }) => {
  await mockTaxonomy(page);
  await page.route("**/api/v1/mission/solve", async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "boom" }),
    });
  });

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
  await page.getByLabel("Global Coverage").check();
  await page.getByRole("button", { name: "Next" }).click();

  await page.getByTestId("page-parameters").waitFor();
  await page.getByRole("heading", { name: "Mission Parameters" }).waitFor();
  await page.getByRole("button", { name: "Finish" }).click();

  await page.getByTestId("page-result").waitFor();
  await page.getByRole("heading", { name: "Your Constellation" }).waitFor();
  await expect(page.getByText(/Solve error/i)).toBeVisible();
});
