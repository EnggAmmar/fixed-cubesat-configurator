import { expect, test, type Page } from "@playwright/test";
import { mockTaxonomy } from "./mocks";

const COMPLETE_DRAFT = {
  family: "remote_sensing",
  payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
  roi: { type: "global" },
  parameters: { revisit_time_hours: 24 },
};

const LONG_SOLVE_MOCK = {
  input: COMPLETE_DRAFT,
  requirements: {
    payload_mass_kg: 2.2,
    payload_volume_cm3: 1000,
    payload_avg_power_w: 10,
    payload_peak_power_w: 18,
    min_downlink_mbps: 50,
    max_pointing_error_deg: 0.5,
    thermal_class: "standard",
  },
  constellation: { satellites: 12, planes: 3, orbit_type: "Sun-synchronous" },
  solution: {
    platform: {
      name: "8U Platform",
      bus_size_u: 8,
      max_total_mass_kg: 15,
      max_payload_volume_cm3: 8000,
      avg_power_gen_w: 80,
      peak_power_gen_w: 140,
    },
    budgets: {
      total_cost_kusd: 600,
      total_mass_kg: 12.3,
      total_avg_power_w: 42,
      total_peak_power_w: 75,
      mass_margin_kg: 2.7,
      avg_power_margin_w: 38,
      peak_power_margin_w: 65,
    },
    subsystems: [
      { domain: "structure", name: "8U Platform" },
      { domain: "eps", name: "Deployable Solar EPS" },
      { domain: "adcs", name: "Fine Pointing ADCS" },
      { domain: "obc", name: "Radiation Tolerant OBC" },
      { domain: "comm", name: "X-band Downlink" },
      { domain: "thermal", name: "Passive Thermal Kit" },
      { domain: "propulsion", name: "Cold Gas Module" },
    ],
    warnings: ["Tight bus volume margin."],
  },
  engineering_trace: {
    solver: {
      route_used: "/api/v1/mission/solve",
      solver_name: "v1_requirement_constellation_subsystem_solver",
      status: "FEASIBLE",
      solve_time_ms: 12,
      objective_value: 123.45,
      notes: ["Engineering preferences are connected to solver constraints/objective."],
    },
    selection: {
      platform_name: "8U Platform",
      bus_size_u: 8,
      payload_id: "rs_vhr_optical_v1",
      payload_source: "catalog",
      subsystem_count: 7,
    },
    budgets: {
      total_mass_kg: 12.3,
      total_avg_power_w: 42,
      total_peak_power_w: 75,
      total_cost_kusd: 600,
      mass_margin_kg: 2.7,
      avg_power_margin_w: 38,
      peak_power_margin_w: 65,
      bus_volume_margin_u: 1.4,
    },
    subsystems: Array.from({ length: 12 }, (_, index) => ({
      domain: ["structure", "eps", "adcs", "obc", "comm", "thermal"][index % 6],
      name: `Trace Component ${index + 1}`,
      mass_kg: 0.5 + index / 10,
      avg_power_w: 3 + index,
      peak_power_w: 6 + index,
      cost_kusd: 40 + index * 5,
      metadata: { tier: "engineering", index },
      selection_reason: `Selected to satisfy margin case ${index + 1}.`,
      source_database: "mock",
      source_library: "mock-lib",
      capacity_basis: "capacity check",
      margin_basis: "margin check",
    })),
    constraints: Array.from({ length: 16 }, (_, index) => ({
      name: `Constraint ${index + 1}`,
      required: 10 + index,
      capacity: 20 + index,
      margin: 10,
      units: index % 2 ? "W" : "kg",
      status: "PASS",
    })),
    trace: Array.from({ length: 24 }, (_, index) => `Solver trace line ${index + 1}`),
    warnings: ["Mock warning 1", "Mock warning 2"],
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

async function seedDraft(page: Page, draft: unknown) {
  await page.addInitScript((value) => {
    localStorage.setItem("mission_draft_v1", JSON.stringify(value));
  }, draft);
}

async function expectDockWheelScrolls(page: Page) {
  const dockScroll = page.locator(".dockScroll");
  await expect(dockScroll).toBeVisible();

  const dimensions = await dockScroll.evaluate((el) => ({
    clientHeight: el.clientHeight,
    scrollHeight: el.scrollHeight,
  }));
  expect(dimensions.scrollHeight).toBeGreaterThan(dimensions.clientHeight);

  const box = await dockScroll.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.wheel(0, 500);

  await expect.poll(() => dockScroll.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
}

test("payload page dock scrolls with reduced viewport and panel width slider still resizes dock", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 360 });
  await mockTaxonomy(page);
  await seedDraft(page, { family: "remote_sensing" });

  await page.goto("/payload");
  await page.getByTestId("page-payload").waitFor();
  await page.getByRole("button", { name: "My Payload" }).click();

  await expectDockWheelScrolls(page);

  const dock = page.locator(".dock");
  const widthBefore = await dock.evaluate((el) => el.getBoundingClientRect().width);
  const slider = page.getByLabel("Panel width");
  await expect(slider).toBeVisible();
  await expect(slider).toHaveAttribute("aria-label", "Panel width");

  await slider.evaluate((node) => {
    const input = node as HTMLInputElement;
    const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    valueSetter?.call(input, "680");
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  await expect
    .poll(() =>
      page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--dockW")),
    )
    .toBe("680px");
  await expect
    .poll(() => dock.evaluate((el) => el.getBoundingClientRect().width))
    .toBeGreaterThan(widthBefore);
});

test("solver trace dock scrolls when trace content overflows", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 420 });
  await seedDraft(page, COMPLETE_DRAFT);
  await page.route("**/api/v1/mission/solve", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(LONG_SOLVE_MOCK),
    });
  });
  await page.route("**/api/solve/cubesat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        payload_id: "rs_vhr_optical_v1",
        payload_meta: {
          vendor: "Long Diagnostic Vendor",
          product_name: "Very Long Diagnostic Payload Product Name That Must Wrap",
          recommended_bus_min_u: 6,
          recommended_bus_min_mass_kg: 8.5,
        },
        bus_cases: [
          {
            bus_class: "6U_PLUS_LONG_DIAGNOSTIC_CASE_NAME",
            status: "PASS_WITH_LONG_STATUS_LABEL",
            objective_value: 123456.789,
            violated_families: [
              "thermal_margin_with_extremely_long_family_name",
              "downlink_margin_with_extremely_long_family_name",
            ],
          },
          {
            bus_class: "8U_EXTENDED_DIAGNOSTIC_CASE_NAME",
            status: "FAIL_WITH_LONG_STATUS_LABEL",
            objective_value: 987654.321,
            violated_families: ["mass_margin_with_extremely_long_family_name"],
          },
        ],
      }),
    });
  });

  await page.goto("/solver-trace");
  await page.getByTestId("page-analysis").waitFor();
  await page.getByText("Subsystem Cards").waitFor();

  await expectDockWheelScrolls(page);

  await page.getByRole("button", { name: "Run CP-SAT Diagnostic" }).click();
  const diagnosticTable = page.getByRole("table", { name: "CP-SAT Diagnostic Bus Cases" });
  await expect(diagnosticTable).toBeVisible();

  const diagnosticScroller = page.locator(".traceTableScroll").filter({ has: diagnosticTable });
  const scrollMetrics = await diagnosticScroller.evaluate((el) => ({
    clientWidth: el.clientWidth,
    scrollWidth: el.scrollWidth,
  }));
  expect(scrollMetrics.scrollWidth).toBeGreaterThanOrEqual(scrollMetrics.clientWidth);

  await diagnosticScroller.evaluate((el) => {
    el.scrollLeft = el.scrollWidth;
  });
  await expect
    .poll(() => diagnosticScroller.evaluate((el) => el.scrollWidth >= el.clientWidth))
    .toBe(true);
});

test("result page dock scrolls through long warnings and report actions", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 360 });
  await seedDraft(page, COMPLETE_DRAFT);
  await page.route("**/api/v1/mission/solve", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...LONG_SOLVE_MOCK,
        solution: {
          ...LONG_SOLVE_MOCK.solution,
          warnings: Array.from(
            { length: 12 },
            (_, index) => `Radiation screening warning ${index + 1}: mock long warning text.`,
          ),
        },
      }),
    });
  });

  await page.goto("/result");
  await page.getByTestId("page-result").waitFor();
  await page.getByText("Subsystems").waitFor();

  await expectDockWheelScrolls(page);

  const dockScroll = page.locator(".dockScroll");
  await dockScroll.evaluate((el) => {
    el.scrollTop = el.scrollHeight;
  });
  await expect(page.getByRole("button", { name: "Download Mission Report PDF" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download JSON" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download HTML" })).toBeVisible();
});
