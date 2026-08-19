import { test, expect } from "@playwright/test";
import { mockTaxonomy } from "./mocks";

test("landing renders mission family selection", async ({ page }) => {
  await mockTaxonomy(page);
  await page.goto("/");
  await expect(page.getByTestId("page-mission-family")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Select Mission Family" })).toBeVisible();
});
