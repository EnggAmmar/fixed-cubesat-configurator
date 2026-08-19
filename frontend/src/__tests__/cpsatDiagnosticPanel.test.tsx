import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { MissionProvider } from "../state/mission";
import AnalysisPage from "../pages/AnalysisPage";
import * as api from "../lib/api";

function renderAtTrace() {
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
});

function mockSolveMissionOk() {
  vi.spyOn(api, "solveMission").mockResolvedValueOnce({
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
      platform: { name: "8U Platform", bus_size_u: 8 },
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
        notes: [],
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
        },
      ],
      constraints: [{ name: "Mass Budget", status: "PASS", units: "kg" }],
      trace: ["ok"],
      warnings: [],
    },
  } as any);
}

test("Solver Trace shows Run CP-SAT Diagnostic button for catalog payloads", async () => {
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );
  mockSolveMissionOk();

  renderAtTrace();
  await screen.findByTestId("page-analysis");

  expect(await screen.findByRole("button", { name: "Run CP-SAT Diagnostic" })).toBeInTheDocument();
});

test("Solver Trace does not show CP-SAT Diagnostic button for My Payload", async () => {
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: {
        type: "my_payload",
        name: "My Payload",
        length_mm: 200,
        width_mm: 120,
        height_mm: 120,
        mass_kg: 2.0,
        avg_power_w: 8.0,
        peak_power_w: 14.0,
      },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );
  mockSolveMissionOk();

  renderAtTrace();
  await screen.findByTestId("page-analysis");

  expect(await screen.findByText(/available only for catalog payloads/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Run CP-SAT Diagnostic" })).toBeNull();
});

test("Solver Trace renders diagnostic result after click", async () => {
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );
  mockSolveMissionOk();

  const diagSpy = vi.spyOn(api, "solveCubeSatDiagnostic").mockResolvedValueOnce({
    payload_id: "rs_vhr_optical_v1",
    payload_meta: { vendor: "ACME", product_name: "Camera" },
    bus_cases: [{ bus_class: "6U", status: "FEASIBLE", objective_value: 123, violated_families: [] }],
  } as any);

  renderAtTrace();
  await screen.findByTestId("page-analysis");

  fireEvent.click(await screen.findByRole("button", { name: "Run CP-SAT Diagnostic" }));

  expect(diagSpy).toHaveBeenCalledWith("rs_vhr_optical_v1");
  expect(await screen.findByText("CP-SAT Diagnostic")).toBeInTheDocument();
  expect(await screen.findByText("6U")).toBeInTheDocument();
});

test("Solver Trace shows informative error for 400 JSON detail from CP-SAT endpoint", async () => {
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );
  mockSolveMissionOk();

  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: false,
    status: 400,
    json: async () => ({ detail: "Unknown selected_payload_id: rs_vhr_optical_v1" }),
    text: async () => "",
  } as any);

  renderAtTrace();
  await screen.findByTestId("page-analysis");

  fireEvent.click(await screen.findByRole("button", { name: "Run CP-SAT Diagnostic" }));

  expect(await screen.findByText(/CP-SAT error:/i)).toBeInTheDocument();
  expect(await screen.findByText(/400/)).toBeInTheDocument();
  expect(await screen.findByText(/Unknown selected_payload_id/i)).toBeInTheDocument();
});
