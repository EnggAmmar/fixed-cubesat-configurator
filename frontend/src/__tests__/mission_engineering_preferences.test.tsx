import { render, waitFor } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";
import { useEffect, useRef } from "react";

import { MissionProvider, requireMissionInput, useMission } from "../state/mission";

beforeEach(() => {
  localStorage.clear();
});

test("requireMissionInput includes engineering_preferences when present", () => {
  const input = requireMissionInput({
    family: "remote_sensing",
    payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
    roi: { type: "global" },
    parameters: {
      revisit_time_hours: 48,
      engineering_preferences: {
        altitude_km: 500,
        orbit_type: "leo",
        lifetime_years: 2,
        propulsion_preference: "electric",
        pointing_precision_preference: "fine",
        downlink_rate_preference: "high",
        optimization_priority: "balanced",
        max_budget_usd: 500000,
        max_bus_u: 12,
      },
    },
  });

  expect(input.parameters.revisit_time_hours).toBe(48);
  expect(input.parameters.engineering_preferences?.orbit_type).toBe("leo");
  expect(input.parameters.engineering_preferences?.propulsion_preference).toBe("electric");
});

test("legacy drafts without engineering_preferences still pass requireMissionInput", () => {
  const input = requireMissionInput({
    family: "remote_sensing",
    payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
    roi: { type: "global" },
    parameters: { revisit_time_hours: 48 },
  });
  expect(input.parameters.engineering_preferences).toBeUndefined();
});

test("setEngineeringPreferences merges and persists without erasing revisit_time_hours", async () => {
  function Harness() {
    const { draft, setFamily, setPayload, setRoi, setRevisitHours, setEngineeringPreferences } =
      useMission();
    const ranInit = useRef(false);
    const ranPrefs = useRef(false);
    useEffect(() => {
      if (ranInit.current) return;
      ranInit.current = true;
      setFamily("remote_sensing");
      setPayload({ type: "catalog", payload_id: "rs_vhr_optical_v1" });
      setRoi({ type: "global" });
      setRevisitHours(24);
    }, [setFamily, setPayload, setRevisitHours, setRoi]);

    useEffect(() => {
      if (ranPrefs.current) return;
      if (draft.parameters?.revisit_time_hours !== 24) return;
      ranPrefs.current = true;
      setEngineeringPreferences({ orbit_type: "leo", altitude_km: 500 });
      setEngineeringPreferences({ propulsion_preference: "electric" });
    }, [draft.parameters?.revisit_time_hours, setEngineeringPreferences]);
    return null;
  }

  render(
    <MissionProvider>
      <Harness />
    </MissionProvider>,
  );

  await waitFor(() => {
    const raw = localStorage.getItem("mission_draft_v1");
    expect(raw).toBeTruthy();
    const draft = JSON.parse(raw as string) as any;
    expect(draft.parameters.revisit_time_hours).toBe(24);
    expect(draft.parameters.engineering_preferences.orbit_type).toBe("leo");
    expect(draft.parameters.engineering_preferences.altitude_km).toBe(500);
    expect(draft.parameters.engineering_preferences.propulsion_preference).toBe("electric");
  });
});
