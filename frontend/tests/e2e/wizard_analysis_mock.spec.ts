import { test, expect } from "@playwright/test";
import { mockTaxonomy } from "./mocks";

const SOLVE_WITH_TRACE = {
  constellation: { satellites: 2, planes: 2, orbit_type: "Sun-synchronous" },
  solution: {
    platform: { name: "8U Platform", bus_size_u: 8 },
    budgets: { total_cost_kusd: 600, total_mass_kg: 12.3 },
    subsystems: [
      { domain: "structure", name: "8U Platform" },
      { domain: "comm", name: "X-band Downlink" },
    ],
    warnings: ["Tight mass margin (< 0.5 kg)."],
  },
  engineering_trace: {
    solver: {
      route_used: "/api/v1/mission/solve",
      solver_name: "v1_requirement_constellation_subsystem_solver",
      status: "FEASIBLE",
      solve_time_ms: 10,
      objective_value: null,
      objective_weights: { cost: 5, mass: 1, risk: 30, slack: 1, over_budget: 2 },
      notes: ["Engineering preferences are connected to solver constraints/objective."],
    },
    selection: {
      platform_name: "8U Platform",
      bus_size_u: 8,
      payload_id: "rs_vhr_optical_v1",
      payload_source: "catalog",
      subsystem_count: 2,
    },
    budgets: {
      total_mass_kg: 12.3,
      total_avg_power_w: 20,
      total_peak_power_w: 30,
      total_cost_kusd: 600,
      mass_margin_kg: 1.0,
      avg_power_margin_w: 2.0,
      peak_power_margin_w: 3.0,
      bus_volume_margin_u: 0.1,
    },
    subsystems: [
      {
        domain: "comm",
        name: "X-band Downlink",
        mass_kg: 0.7,
        avg_power_w: 10,
        peak_power_w: 18,
        cost_kusd: 95,
      },
    ],
    constraints: [
      {
        name: "Mass Budget",
        required: 12.3,
        capacity: 15.0,
        margin: 2.7,
        units: "kg",
        status: "PASS",
      },
    ],
    trace: ["line 1"],
    warnings: ["warn 1"],
    preferences: [
      {
        preference: "optimization_priority",
        value: "balanced",
        status: "applied_objective_modifier",
        effect: "objective weights adjusted for requested priority",
      },
    ],
  },
} as const;

test("wizard -> result -> solver trace shows engineering sections (mocked backend)", async ({
  page,
}) => {
  await mockTaxonomy(page);
  await page.route("**/api/v1/mission/solve", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SOLVE_WITH_TRACE),
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
  await page.getByRole("button", { name: "Finish" }).click();

  await page.getByTestId("page-result").waitFor();
  await page.getByRole("button", { name: "View Solver Trace" }).click();

  await page.getByTestId("page-analysis").waitFor();
  await expect(page.getByText("Bus Size", { exact: true })).toBeVisible();
  await expect(page.getByText("Subsystem Cards", { exact: true })).toBeVisible();
  await expect(page.getByText("COMM (X-band Downlink)", { exact: true }).first()).toBeVisible();
  await page.getByRole("tab", { name: "Raw Trace" }).click();
  await page.getByText("Constraint margins", { exact: true }).click();
  await expect(page.getByRole("table", { name: "Constraints Table" })).toBeVisible();
  await expect(page.getByText("Mass Budget")).toBeVisible();
});
