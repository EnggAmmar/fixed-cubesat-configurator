import { test, expect } from "@playwright/test";
import { mockSolve, mockTaxonomy } from "./mocks";

test("my payload wizard journey (mocked backend)", async ({ page }) => {
  await mockTaxonomy(page);
  await mockSolve(page);

  await page.goto("/");
  await page.getByTestId("page-mission-family").waitFor();
  await page.getByRole("heading", { name: "Select Mission Family" }).waitFor();
  await page.getByRole("button", { name: "Remote Sensing" }).click();

  await page.getByTestId("page-payload").waitFor();
  await page.getByRole("heading", { name: "Select Payload" }).waitFor();
  await page.getByRole("button", { name: /My Payload/i }).click();

  await page.getByLabel("Name").fill("Confidential Payload");
  await page.getByLabel("Mass (kg)").fill("2.1");
  await page.getByLabel("L (mm)").fill("180");
  await page.getByLabel("W (mm)").fill("90");
  await page.getByLabel("H (mm)").fill("90");
  await page.getByLabel("Avg power (W)").fill("8");
  await page.getByLabel("Peak power (W)").fill("14");

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
  await expect(page.getByTestId("solution-platform")).toBeVisible();
});
