import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { MissionProvider } from "../state/mission";
import ParametersPage from "../pages/ParametersPage";

function renderAtParameters() {
  return render(
    <MemoryRouter initialEntries={["/parameters"]}>
      <MissionProvider>
        <Routes>
          <Route path="/parameters" element={<ParametersPage />} />
          <Route path="/result" element={<div>result</div>} />
          <Route path="/" element={<div>home</div>} />
          <Route path="/payload" element={<div>payload</div>} />
          <Route path="/roi" element={<div>roi</div>} />
        </Routes>
      </MissionProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
});

test("ParametersPage renders revisit and advanced preferences section", async () => {
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );

  renderAtParameters();

  expect(await screen.findByRole("heading", { name: "Mission Parameters" })).toBeInTheDocument();
  expect(screen.getByLabelText("Revisit Hours")).toBeInTheDocument();
  expect(screen.getByText(/Advanced Engineering Preferences/i)).toBeInTheDocument();
  expect(screen.queryByText(/Optional constraints and preferences/i)).not.toBeInTheDocument();
});

test("Finish persists engineering_preferences and revisit_time_hours; empty max budget and Any bus omit values", async () => {
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );

  renderAtParameters();
  await screen.findByRole("heading", { name: "Mission Parameters" });

  fireEvent.change(screen.getByLabelText("Revisit Hours"), { target: { value: "24" } });
  fireEvent.change(screen.getByLabelText("Orbit Altitude Numeric"), { target: { value: "600" } });
  fireEvent.change(screen.getByLabelText("Orbit Type"), { target: { value: "sso" } });
  fireEvent.change(screen.getByLabelText("Mission Lifetime (years)"), { target: { value: "3" } });
  fireEvent.change(screen.getByLabelText("Propulsion Preference"), { target: { value: "electric" } });
  fireEvent.change(screen.getByLabelText("Pointing Precision"), { target: { value: "fine" } });
  fireEvent.change(screen.getByLabelText("Downlink Rate Preference"), { target: { value: "high" } });
  fireEvent.change(screen.getByLabelText("Optimization Priority"), { target: { value: "lowest_mass" } });

  // Leave these empty/Any and ensure we don't store NaN or empty string
  fireEvent.change(screen.getByLabelText("Max Budget (USD)"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Max Bus Size"), { target: { value: "any" } });

  fireEvent.click(screen.getByRole("button", { name: "Finish" }));

  expect(await screen.findByText("result")).toBeInTheDocument();

  await waitFor(() => {
    const raw = localStorage.getItem("mission_draft_v1");
    expect(raw).toBeTruthy();
    const draft = JSON.parse(raw as string) as any;
    expect(draft.parameters.revisit_time_hours).toBe(24);

    const prefs = draft.parameters.engineering_preferences;
    expect(prefs.altitude_km).toBe(600);
    expect(prefs.orbit_type).toBe("sso");
    expect(prefs.lifetime_years).toBe(3);
    expect(prefs.propulsion_preference).toBe("electric");
    expect(prefs.pointing_precision_preference).toBe("fine");
    expect(prefs.downlink_rate_preference).toBe("high");
    expect(prefs.optimization_priority).toBe("lowest_mass");
    expect(prefs.max_budget_usd).toBeUndefined();
    expect(prefs.max_bus_u).toBeUndefined();
  });
});

test("Old draft without engineering_preferences still renders with defaults", async () => {
  localStorage.setItem(
    "mission_draft_v1",
    JSON.stringify({
      family: "remote_sensing",
      payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      roi: { type: "global" },
      parameters: { revisit_time_hours: 48 },
    }),
  );

  renderAtParameters();
  await screen.findByRole("heading", { name: "Mission Parameters" });

  expect(await screen.findByLabelText("Orbit Altitude Numeric")).toHaveValue(500);
  expect(screen.getByLabelText("Orbit Type")).toHaveValue("leo");
  expect(screen.getByLabelText("Mission Lifetime (years)")).toHaveValue("2");
  expect(screen.getByLabelText("Propulsion Preference")).toHaveValue("no_preference");
});
