import { test, expect } from "@playwright/test";
import { mockTaxonomy, SOLVE_MOCK } from "./mocks";

test("parameters page persists engineering preferences (mocked backend)", async ({ page }) => {
  await mockTaxonomy(page);

  await page.route("**/api/v1/mission/solve", async (route) => {
    const req = route.request();
    const body = req.postDataJSON() as any;

    const prefs = body?.input?.parameters?.engineering_preferences;
    expect(prefs).toBeTruthy();
    expect(prefs.altitude_km).toBe(600);
    expect(prefs.orbit_type).toBe("sso");
    expect(prefs.lifetime_years).toBe(3);
    expect(prefs.propulsion_preference).toBe("electric");
    expect(prefs.pointing_precision_preference).toBe("fine");
    expect(prefs.downlink_rate_preference).toBe("high");
    expect(prefs.optimization_priority).toBe("lowest_mass");
    expect(prefs.max_budget_usd).toBeUndefined();
    expect(prefs.max_bus_u).toBeUndefined();

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SOLVE_MOCK),
    });
  });

  await page.goto("/");

  await page.getByTestId("page-mission-family").waitFor();
  await page.getByRole("button", { name: "Remote Sensing" }).click();

  await page.getByTestId("page-payload").waitFor();
  await page.getByRole("button", { name: /VHR Optical/i }).click();
  await page.getByRole("button", { name: "Next" }).click();

  await page.getByTestId("page-roi").waitFor();
  await page.getByLabel("Global Coverage").check();
  await page.getByRole("button", { name: "Next" }).click();

  await page.getByTestId("page-parameters").waitFor();
  await page.getByLabel("Revisit Hours").fill("24");

  await page.getByLabel("Orbit Altitude Numeric").fill("600");
  await page.getByLabel("Orbit Type").selectOption("sso");
  await page.getByLabel("Mission Lifetime (years)").selectOption("3");
  await page.getByLabel("Propulsion Preference").selectOption("electric");
  await page.getByLabel("Pointing Precision").selectOption("fine");
  await page.getByLabel("Downlink Rate Preference").selectOption("high");
  await page.getByLabel("Optimization Priority").selectOption("lowest_mass");
  await page.getByLabel("Max Budget (USD)").fill("");
  await page.getByLabel("Max Bus Size").selectOption("any");

  await page.getByRole("button", { name: "Finish" }).click();

  await page.getByTestId("page-result").waitFor();
  await page.getByRole("heading", { name: "Your Constellation" }).waitFor();

  const draft = await page.evaluate(() => JSON.parse(localStorage.getItem("mission_draft_v1") || "{}"));
  expect(draft.parameters.revisit_time_hours).toBe(24);
  expect(draft.parameters.engineering_preferences.orbit_type).toBe("sso");
  expect(draft.parameters.engineering_preferences.altitude_km).toBe(600);
});

