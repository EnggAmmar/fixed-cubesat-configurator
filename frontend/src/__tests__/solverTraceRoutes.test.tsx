import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("../scene/SceneCanvas", () => ({
  default: function SceneCanvasMock() {
    return <div data-testid="scene-canvas" />;
  },
}));
import type { MockInstance } from "vitest";
import * as api from "../lib/api";
import type { MissionSolveResponse } from "../lib/api";

import App from "../App";
import { MissionProvider } from "../state/mission";

let solveSpy: MockInstance<typeof api.solveMission>;

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  solveSpy = vi.spyOn(api, "solveMission").mockImplementation(
    () => new Promise<MissionSolveResponse>(() => {}),
  );
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

test("/analysis still renders Solver Trace page", async () => {
  render(
    <MemoryRouter initialEntries={["/analysis"]}>
      <MissionProvider>
        <App />
      </MissionProvider>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "Solver Trace" })).toBeInTheDocument();
  expect(solveSpy).toHaveBeenCalled();
});

test("/solver-trace renders Solver Trace page", async () => {
  render(
    <MemoryRouter initialEntries={["/solver-trace"]}>
      <MissionProvider>
        <App />
      </MissionProvider>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "Solver Trace" })).toBeInTheDocument();
  expect(solveSpy).toHaveBeenCalled();
});

test("/solver-trace with incomplete draft shows locked state and does not call solveMission", async () => {
  localStorage.clear();

  render(
    <MemoryRouter initialEntries={["/solver-trace"]}>
      <MissionProvider>
        <App />
      </MissionProvider>
    </MemoryRouter>,
  );

  expect(
    await screen.findByRole("heading", { name: "Solver Trace unavailable" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Go to Mission Setup" })).toHaveAttribute("href", "/");
  expect(solveSpy).not.toHaveBeenCalled();
});
