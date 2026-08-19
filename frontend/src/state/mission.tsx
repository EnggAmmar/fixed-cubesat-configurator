import React, { createContext, useContext, useMemo, useState } from "react";
import type {
  EngineeringPreferences,
  MissionFamily,
  MissionInput,
  OptimizationPriority,
  OrbitType,
  PayloadSelection,
  PointingPrecisionPreference,
  PropulsionPreference,
  Roi,
  DownlinkRatePreference,
} from "../lib/api";

export type MissionDraft = Partial<MissionInput> & {
  family?: MissionFamily;
  payload?: PayloadSelection;
  roi?: Roi;
  parameters?: { revisit_time_hours: number; engineering_preferences?: EngineeringPreferences };
};

type MissionContextValue = {
  draft: MissionDraft;
  setFamily: (family: MissionFamily) => void;
  setPayload: (payload: PayloadSelection) => void;
  setRoi: (roi: Roi) => void;
  setRevisitHours: (hours: number) => void;
  setEngineeringPreferences: (prefs: Partial<EngineeringPreferences>) => void;
  reset: () => void;
};

const MissionContext = createContext<MissionContextValue | null>(null);

const STORAGE_KEY = "mission_draft_v1";

const VALID_FAMILIES: MissionFamily[] = ["remote_sensing", "iot_communication", "navigation"];
const VALID_ORBIT_TYPES: OrbitType[] = ["leo", "sso", "polar", "equatorial", "custom"];
const VALID_PROPULSION_PREFS: PropulsionPreference[] = [
  "no_preference",
  "none",
  "cold_gas",
  "electric",
  "chemical",
  "green_monoprop",
];
const VALID_POINTING_PREFS: PointingPrecisionPreference[] = [
  "no_preference",
  "coarse",
  "medium",
  "fine",
  "ultra_fine",
];
const VALID_DOWNLINK_PREFS: DownlinkRatePreference[] = [
  "no_preference",
  "low",
  "medium",
  "high",
  "optical_extreme",
];
const VALID_OPTIMIZATION: OptimizationPriority[] = [
  "balanced",
  "lowest_cost",
  "lowest_mass",
  "highest_performance",
  "lowest_risk",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asFiniteNumber(value: unknown): number | undefined {
  if (typeof value !== "number") return undefined;
  if (!Number.isFinite(value)) return undefined;
  return value;
}

function pickEngineeringPreferences(raw: unknown): EngineeringPreferences | undefined {
  if (!isRecord(raw)) return undefined;

  const altitude_km = asFiniteNumber(raw.altitude_km);
  const lifetime_years = asFiniteNumber(raw.lifetime_years);
  const max_budget_usd = asFiniteNumber(raw.max_budget_usd);
  const max_bus_u = asFiniteNumber(raw.max_bus_u);

  const orbit_type =
    typeof raw.orbit_type === "string" && VALID_ORBIT_TYPES.includes(raw.orbit_type as OrbitType)
      ? (raw.orbit_type as OrbitType)
      : undefined;

  const propulsion_preference =
    typeof raw.propulsion_preference === "string" &&
    VALID_PROPULSION_PREFS.includes(raw.propulsion_preference as PropulsionPreference)
      ? (raw.propulsion_preference as PropulsionPreference)
      : undefined;

  const pointing_precision_preference =
    typeof raw.pointing_precision_preference === "string" &&
    VALID_POINTING_PREFS.includes(
      raw.pointing_precision_preference as PointingPrecisionPreference,
    )
      ? (raw.pointing_precision_preference as PointingPrecisionPreference)
      : undefined;

  const downlink_rate_preference =
    typeof raw.downlink_rate_preference === "string" &&
    VALID_DOWNLINK_PREFS.includes(raw.downlink_rate_preference as DownlinkRatePreference)
      ? (raw.downlink_rate_preference as DownlinkRatePreference)
      : undefined;

  const optimization_priority =
    typeof raw.optimization_priority === "string" &&
    VALID_OPTIMIZATION.includes(raw.optimization_priority as OptimizationPriority)
      ? (raw.optimization_priority as OptimizationPriority)
      : undefined;

  const prefs: EngineeringPreferences = {
    altitude_km,
    orbit_type,
    lifetime_years,
    propulsion_preference,
    pointing_precision_preference,
    downlink_rate_preference,
    optimization_priority,
    max_budget_usd,
    max_bus_u,
  };

  if (Object.values(prefs).every((v) => v === undefined)) return undefined;
  return prefs;
}

function sanitizeDraft(raw: unknown): MissionDraft {
  if (!isRecord(raw)) return {};

  const out: MissionDraft = {};

  if (typeof raw.family === "string") {
    out.family = VALID_FAMILIES.includes(raw.family as MissionFamily)
      ? (raw.family as MissionFamily)
      : "remote_sensing";
  }

  if (isRecord(raw.payload) && typeof raw.payload.type === "string") {
    if (raw.payload.type === "catalog" && typeof raw.payload.payload_id === "string") {
      out.payload = { type: "catalog", payload_id: raw.payload.payload_id };
    } else if (raw.payload.type === "my_payload") {
      // Be tolerant for forward/backward compatibility: keep unknown optional keys, but
      // only if the required core fields look present.
      const nameOk = typeof raw.payload.name === "string" && raw.payload.name.length > 0;
      const lengthOk = typeof raw.payload.length_mm === "number";
      const widthOk = typeof raw.payload.width_mm === "number";
      const heightOk = typeof raw.payload.height_mm === "number";
      const massOk = typeof raw.payload.mass_kg === "number";
      const avgOk = typeof raw.payload.avg_power_w === "number";
      const peakOk = typeof raw.payload.peak_power_w === "number";

      if (nameOk && lengthOk && widthOk && heightOk && massOk && avgOk && peakOk) {
        out.payload = raw.payload as PayloadSelection;
      }
    }
  }

  if (isRecord(raw.roi) && typeof raw.roi.type === "string") {
    if (raw.roi.type === "global") {
      out.roi = { type: "global" };
    } else if (raw.roi.type === "region" && typeof raw.roi.query === "string") {
      out.roi = { type: "region", query: raw.roi.query };
    }
  }

  if (isRecord(raw.parameters)) {
    const revisit = asFiniteNumber(raw.parameters.revisit_time_hours);
    const engineering_preferences = pickEngineeringPreferences(raw.parameters.engineering_preferences);
    if (revisit !== undefined) {
      out.parameters = {
        revisit_time_hours: revisit,
        ...(engineering_preferences ? { engineering_preferences } : {}),
      };
    } else if (engineering_preferences) {
      // Keep preferences without forcing revisit_time_hours; the wizard will populate revisit later.
      out.parameters = { revisit_time_hours: 48, engineering_preferences };
    }
  }

  return out;
}

export function getDefaultEngineeringPreferences(): EngineeringPreferences {
  return {
    altitude_km: 500,
    orbit_type: "leo",
    lifetime_years: 2,
    propulsion_preference: "no_preference",
    pointing_precision_preference: "no_preference",
    downlink_rate_preference: "no_preference",
    optimization_priority: "balanced",
    max_budget_usd: undefined,
    max_bus_u: undefined,
  };
}

function loadInitial(): MissionDraft {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return sanitizeDraft(JSON.parse(raw));
  } catch {
    return {};
  }
}

export function MissionProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraft] = useState<MissionDraft>(() => loadInitial());

  const value = useMemo<MissionContextValue>(() => {
    const persist = (updater: (prev: MissionDraft) => MissionDraft) => {
      setDraft((prev) => {
        const next = updater(prev);
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
    };

    return {
      draft,
      setFamily: (family) =>
        persist(() => ({ family, payload: undefined, roi: undefined, parameters: undefined })),
      setPayload: (payload) => persist((prev) => ({ ...prev, payload })),
      setRoi: (roi) => persist((prev) => ({ ...prev, roi })),
      setRevisitHours: (hours) =>
        persist((prev) => ({
          ...prev,
          parameters: {
            revisit_time_hours: hours,
            engineering_preferences: prev.parameters?.engineering_preferences,
          },
        })),
      setEngineeringPreferences: (prefs) =>
        persist((prev) => {
          const current = prev.parameters?.engineering_preferences ?? {};
          const merged = { ...current, ...prefs };
          return {
            ...prev,
            parameters: {
              revisit_time_hours: prev.parameters?.revisit_time_hours ?? 48,
              engineering_preferences: merged,
            },
          };
        }),
      reset: () => persist(() => ({})),
    };
  }, [draft]);

  return <MissionContext.Provider value={value}>{children}</MissionContext.Provider>;
}

export function useMission() {
  const ctx = useContext(MissionContext);
  if (!ctx) throw new Error("useMission must be used within MissionProvider");
  return ctx;
}

export function requireMissionInput(draft: MissionDraft): MissionInput {
  if (!draft.family) throw new Error("Missing mission family");
  if (!draft.payload) throw new Error("Missing payload selection");
  if (!draft.roi) throw new Error("Missing ROI");
  if (!draft.parameters) throw new Error("Missing mission parameters");
  if (typeof draft.parameters.revisit_time_hours !== "number") {
    throw new Error("Missing revisit_time_hours");
  }
  return {
    family: draft.family,
    payload: draft.payload,
    roi: draft.roi,
    parameters: {
      revisit_time_hours: draft.parameters.revisit_time_hours,
      engineering_preferences: draft.parameters.engineering_preferences,
    },
  };
}
