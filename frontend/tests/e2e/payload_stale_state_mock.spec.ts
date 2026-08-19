import { test, expect } from "@playwright/test";
import { mockTaxonomy } from "./mocks";

test("payload page renders cards even with stale persisted mission family (mocked backend)", async ({ page }) => {
  await mockTaxonomy(page);

  await page.addInitScript(() => {
    localStorage.setItem("mission_draft_v1", JSON.stringify({ family: "bad_family" }));
  });

  await page.goto("/payload");
  await page.getByTestId("page-payload").waitFor();
  await page.getByRole("heading", { name: "Select Payload" }).waitFor();

  await expect(page.getByRole("button", { name: /VHR Optical/i })).toBeVisible();
});

