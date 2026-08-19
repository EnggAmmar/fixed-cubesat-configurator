import { render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { MissionProvider } from "../state/mission";
import AnalysisPage from "../pages/AnalysisPage";
import * as api from "../lib/api";
import type { MissionSolveResponse } from "../lib/api";

function renderAtAnalysis() {
  return render(
    <MemoryRouter initialEntries={["/analysis"]}>
      <MissionProvider>
        <Routes>
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/result" element={<div>result</div>} />
          <Route path="/" element={<div>home</div>} />
          <Route path="/payload" element={<div>payload</div>} />
          <Route path="/roi" element={<div>roi</div>} />
          <Route path="/parameters" element={<div>parameters</div>} />
        </Routes>
      </MissionProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );
});

test("AnalysisPage renders loading state", async () => {
  vi.spyOn(api, "solveMission").mockImplementation(
    () => new Promise<MissionSolveResponse>(() => undefined),
  );

  renderAtAnalysis();
  expect(screen.getByRole("link", { name: "Back to Results" })).toHaveAttribute("href", "/result");
  expect(await screen.findByText("Loading analysis...")).toBeInTheDocument();
});

test("AnalysisPage renders the redesigned Solver Trace dashboard for a successful solve", async () => {
  vi.spyOn(api, "solveMission").mockResolvedValueOnce({
    input: {
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    },
    requirements: {
      payload_mass_kg: 2.2,
      payload_volume_cm3: 1000,
      payload_avg_power_w: 10,
      payload_peak_power_w: 18,
      min_downlink_mbps: 80,
      max_pointing_error_deg: 0.2,
      thermal_class: "standard",
    },
    constellation: { satellites: 2, planes: 2, orbit_type: "Sun-synchronous" },
    solution: {
      platform: {
        name: "8U Platform",
        bus_size_u: 8,
        max_total_mass_kg: 16,
        max_payload_volume_cm3: 6000,
        avg_power_gen_w: 70,
        peak_power_gen_w: 110,
      },
      budgets: { total_cost_kusd: 600, total_mass_kg: 12.3 },
      subsystems: [{ domain: "comm", name: "X-band Downlink" }],
      warnings: [],
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
        subsystem_count: 1,
      },
      budgets: {
        total_mass_kg: 12.3,
        total_avg_power_w: 20,
        total_peak_power_w: 30,
        total_cost_kusd: 600,
        mass_margin_kg: 1,
        avg_power_margin_w: 2,
        peak_power_margin_w: 3,
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
          tier: null,
          metadata: { downlink_mbps: 120 },
          selection_reason: "Meets downlink rate requirement with margin.",
          source_database: "catalog.json",
          source_library: "internal_catalog",
          capacity_basis: "downlink_mbps >= requirement",
          margin_basis: "capacity - required",
        },
      ],
      constraints: [
        { name: "Mass Budget", required: 5, capacity: 10, margin: 5, units: "kg", status: "PASS" },
      ],
      trace: ["trace line"],
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
  } satisfies MissionSolveResponse);

  renderAtAnalysis();

  expect(await screen.findByTestId("page-analysis")).toBeInTheDocument();
  expect(screen.getByLabelText("Solver Trace Summary")).toBeInTheDocument();
  expect(screen.getByText("Bus Size")).toBeInTheDocument();
  expect(screen.getByText("8U")).toBeInTheDocument();
  expect(screen.getByText("Feasible")).toBeInTheDocument();
  expect(screen.getByText("Subsystem Cards")).toBeInTheDocument();
  expect(screen.getAllByText("COMM (X-band Downlink)").length).toBeGreaterThan(0);
  expect(screen.getByText("Why selected")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "View details" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Reason" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: "Margins" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Metadata" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Raw Trace" })).toBeInTheDocument();
  expect(screen.getByText("Requirement")).toBeInTheDocument();
  expect(screen.getByText("Selected Capability")).toBeInTheDocument();
  expect(screen.getByText("Decision")).toBeInTheDocument();
  expect(screen.getByText("CP-SAT Diagnostic")).toBeInTheDocument();

  const detailPanel = screen.getByLabelText("Selected subsystem details");
  expect(within(detailPanel).getByText(/downlink_mbps/i)).toBeInTheDocument();
  expect(within(detailPanel).getByText(/Meets downlink rate requirement/i)).toBeInTheDocument();
});

test("AnalysisPage tolerates missing optional fields (renders em dash)", async () => {
  vi.spyOn(api, "solveMission").mockResolvedValueOnce({
    constellation: { satellites: 1, planes: 1, orbit_type: "LEO" },
    solution: {
      platform: { name: "6U Platform", bus_size_u: 6 },
      budgets: { total_cost_kusd: 100, total_mass_kg: 5 },
      subsystems: [{ domain: "comm", name: "X-band Downlink" }],
      warnings: [],
    },
    engineering_trace: {
      solver: { route_used: "/api/v1/mission/solve", solver_name: "x", status: "FEASIBLE" },
      selection: { platform_name: "6U Platform", bus_size_u: 6, payload_source: "catalog" },
      budgets: { total_cost_kusd: 100 },
      subsystems: [{ domain: "comm", name: "X-band Downlink", metadata: null }],
      constraints: [{ name: "Mass Budget", status: "PASS" }],
      trace: [],
      warnings: [],
    },
  } satisfies MissionSolveResponse);

  renderAtAnalysis();
  await screen.findByTestId("page-analysis");
  expect(screen.getByText("Subsystem Cards")).toBeInTheDocument();
  expect(screen.getAllByText("COMM (X-band Downlink)").length).toBeGreaterThan(0);
  expect(screen.getAllByText("—").length).toBeGreaterThan(0);
});

test("AnalysisPage shows empty message if engineering_trace is missing", async () => {
  vi.spyOn(api, "solveMission").mockResolvedValueOnce({
    constellation: { satellites: 1, planes: 1, orbit_type: "LEO" },
    solution: {
      platform: { name: "6U Platform", bus_size_u: 6 },
      budgets: { total_cost_kusd: 100, total_mass_kg: 5 },
      subsystems: [],
      warnings: [],
    },
  } satisfies MissionSolveResponse);

  renderAtAnalysis();
  expect(
    await screen.findByText("Engineering trace is not available for this solve."),
  ).toBeInTheDocument();
});
