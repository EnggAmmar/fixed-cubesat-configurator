import { expect, test } from "vitest";
import type { MissionSolveResponse } from "../lib/api";

test("MissionSolveResponse type accepts optional engineering_trace", () => {
  const resp: MissionSolveResponse = {
    constellation: { satellites: 1, planes: 1, orbit_type: "LEO" },
    solution: {
      platform: { name: "8U Platform", bus_size_u: 8 },
      budgets: { total_cost_kusd: 100, total_mass_kg: 10 },
      subsystems: [{ domain: "comm", name: "Radio" }],
      warnings: [],
    },
    engineering_trace: {
      solver: { route_used: "/api/v1/mission/solve", solver_name: "x", solve_time_ms: 1 },
      selection: { bus_size_u: 8, payload_source: "catalog" },
      budgets: { total_mass_kg: 10 },
      subsystems: [{ domain: "comm", name: "Radio" }],
      constraints: [{ name: "Mass Budget", status: "PASS" }],
      trace: ["ok"],
      warnings: [],
    },
  };

  expect(resp.engineering_trace?.solver.route_used).toBe("/api/v1/mission/solve");
});

