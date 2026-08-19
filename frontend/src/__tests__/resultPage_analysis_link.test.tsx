import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { MissionProvider } from "../state/mission";
import ResultPage from "../pages/ResultPage";
import * as api from "../lib/api";
import type { MissionSolveResponse } from "../lib/api";

function renderAtResult() {
  return render(
    <MemoryRouter initialEntries={["/result"]}>
      <MissionProvider>
        <Routes>
          <Route path="/result" element={<ResultPage />} />
          <Route path="/solver-trace" element={<div>analysis</div>} />
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

test("ResultPage includes View Solver Trace action", async () => {
  const solveResponse: MissionSolveResponse = {
    constellation: { satellites: 2, planes: 2, orbit_type: "Sun-synchronous" },
    solution: {
      platform: { name: "8U Platform", bus_size_u: 8 },
      budgets: { total_cost_kusd: 600, total_mass_kg: 12.3 },
      subsystems: [{ domain: "comm", name: "X-band Downlink" }],
      warnings: [],
    },
    engineering_trace: {
      solver: { route_used: "/api/v1/mission/solve", solver_name: "x" },
      selection: { bus_size_u: 8, payload_source: "catalog" },
      budgets: {},
    },
  };
  vi.spyOn(api, "solveMission").mockResolvedValueOnce(solveResponse);

  renderAtResult();

  expect(await screen.findByTestId("page-result")).toBeInTheDocument();
  const btn = await screen.findByRole("button", { name: "View Solver Trace" });
  fireEvent.click(btn);
  expect(await screen.findByText("analysis")).toBeInTheDocument();
});

test("ResultPage downloads mission PDF with loading state", async () => {
  const solveResponse: MissionSolveResponse = {
    constellation: { satellites: 2, planes: 2, orbit_type: "Sun-synchronous" },
    solution: {
      platform: { name: "8U Platform", bus_size_u: 8 },
      budgets: { total_cost_kusd: 600, total_mass_kg: 12.3 },
      subsystems: [{ domain: "comm", name: "X-band Downlink" }],
      warnings: [],
    },
  };
  vi.spyOn(api, "solveMission").mockResolvedValueOnce(solveResponse);

  let resolveDownload: (blob: Blob) => void = () => {};
  const downloadPromise = new Promise<Blob>((resolve) => {
    resolveDownload = resolve;
  });
  const downloadSpy = vi.spyOn(api, "downloadMissionReport").mockReturnValueOnce(downloadPromise);
  const createObjectURL = vi.fn(() => "blob:mission-report");
  const revokeObjectURL = vi.fn();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
  const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

  renderAtResult();

  const button = await screen.findByRole("button", { name: "Download Mission Report PDF" });
  fireEvent.click(button);

  expect(button).toBeDisabled();
  expect(await screen.findByRole("button", { name: "Generating..." })).toBeDisabled();

  resolveDownload(new Blob(["pdf"], { type: "application/pdf" }));

  await waitFor(() => expect(downloadSpy).toHaveBeenCalledTimes(1));
  expect(downloadSpy).toHaveBeenCalledWith(expect.anything(), "pdf");
  await waitFor(() => expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob)));
  expect(clickSpy).toHaveBeenCalledTimes(1);
  expect(revokeObjectURL).toHaveBeenCalledWith("blob:mission-report");
  expect(await screen.findByRole("button", { name: "Download Mission Report PDF" })).toBeEnabled();
});
