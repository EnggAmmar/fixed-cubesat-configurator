export type MissionFamily = "remote_sensing" | "iot_communication" | "navigation";

export type TaxonomyPayloadCategory = {
  category_id: string;
  label: string;
  description: string;
  payloads: Array<{ payload_id: string; label: string }>;
};

export type TaxonomyMissionFamily = {
  family_id: MissionFamily;
  label: string;
  description: string;
  payload_categories: TaxonomyPayloadCategory[];
};

export type TaxonomyResponse = {
  version: string;
  families: TaxonomyMissionFamily[];
};

export type Roi = { type: "global" } | { type: "region"; query: string };

export type PayloadSelection =
  | { type: "catalog"; payload_id: string }
  | {
      type: "my_payload";
      name: string;
      length_mm: number;
      width_mm: number;
      height_mm: number;
      mass_kg: number;
      avg_power_w: number;
      peak_power_w: number;
      data_rate_mbps?: number;
      pointing_accuracy_deg?: number;
      thermal_class?: "standard" | "sensitive";
    };

export type OrbitType = "leo" | "sso" | "polar" | "equatorial" | "custom";

export type PropulsionPreference =
  | "no_preference"
  | "none"
  | "cold_gas"
  | "electric"
  | "chemical"
  | "green_monoprop";

export type PointingPrecisionPreference =
  | "no_preference"
  | "coarse"
  | "medium"
  | "fine"
  | "ultra_fine";

export type DownlinkRatePreference =
  | "no_preference"
  | "low"
  | "medium"
  | "high"
  | "optical_extreme";

export type OptimizationPriority =
  | "balanced"
  | "lowest_cost"
  | "lowest_mass"
  | "highest_performance"
  | "lowest_risk";

export type EngineeringPreferences = {
  altitude_km?: number;
  orbit_type?: OrbitType;
  lifetime_years?: number;
  propulsion_preference?: PropulsionPreference;
  pointing_precision_preference?: PointingPrecisionPreference;
  downlink_rate_preference?: DownlinkRatePreference;
  optimization_priority?: OptimizationPriority;
  max_budget_usd?: number;
  max_bus_u?: number;
};

export interface MissionInput {
  family: MissionFamily;
  payload: PayloadSelection;
  roi: Roi;
  parameters: { revisit_time_hours: number; engineering_preferences?: EngineeringPreferences };
}

export interface MissionSolveResponse {
  input?: MissionInput;
  requirements?: {
    payload_mass_kg: number;
    payload_volume_cm3: number;
    payload_avg_power_w: number;
    payload_peak_power_w: number;
    min_downlink_mbps?: number | null;
    max_pointing_error_deg?: number | null;
    thermal_class?: "standard" | "sensitive" | string;
  };
  constellation: { satellites: number; planes: number; orbit_type: string };
  solution: {
    platform: {
      name: string;
      bus_size_u: number;
      max_total_mass_kg?: number;
      max_payload_volume_cm3?: number;
      avg_power_gen_w?: number;
      peak_power_gen_w?: number;
      platform_id?: string;
    };
    budgets: {
      total_cost_kusd: number;
      total_mass_kg: number;
      total_avg_power_w?: number;
      total_peak_power_w?: number;
      mass_margin_kg?: number;
      avg_power_margin_w?: number;
      peak_power_margin_w?: number;
    };
    subsystems: Array<{
      domain: string;
      name: string;
      mass_kg?: number;
      avg_power_w?: number;
      peak_power_w?: number;
      cost_kusd?: number;
      item_id?: string;
      metadata?: Record<string, unknown>;
    }>;
    warnings: string[];
  };
  engineering_trace?: EngineeringTrace;
}

export type EngineeringTraceSolver = {
  route_used: string;
  solver_name: string;
  status?: string | null;
  solve_time_ms?: number | null;
  objective_value?: number | null;
  objective_weights?: Record<string, number> | null;
  notes?: string[];
};

export type EngineeringTraceSelection = {
  platform_name?: string | null;
  bus_size_u?: number | null;
  payload_id?: string | null;
  payload_source?: string | null;
  subsystem_count?: number | null;
};

export type EngineeringTraceBudget = {
  total_mass_kg?: number | null;
  total_avg_power_w?: number | null;
  total_peak_power_w?: number | null;
  total_cost_kusd?: number | null;
  mass_margin_kg?: number | null;
  avg_power_margin_w?: number | null;
  peak_power_margin_w?: number | null;
  bus_volume_margin_u?: number | null;
};

export type EngineeringTraceSubsystem = {
  domain: string;
  name: string;
  mass_kg?: number | null;
  avg_power_w?: number | null;
  peak_power_w?: number | null;
  cost_kusd?: number | null;
  tier?: string | null;
  metadata?: Record<string, unknown> | null;
  selection_reason?: string | null;
  source_library?: string | null;
  source_database?: string | null;
  capacity_basis?: string | null;
  margin_basis?: string | null;
};

export type EngineeringTraceConstraint = {
  name: string;
  required?: number | null;
  capacity?: number | null;
  margin?: number | null;
  units?: string | null;
  status?: string;
};

export type EngineeringTrace = {
  solver: EngineeringTraceSolver;
  selection: EngineeringTraceSelection;
  budgets: EngineeringTraceBudget;
  subsystems?: EngineeringTraceSubsystem[];
  constraints?: EngineeringTraceConstraint[];
  trace?: string[];
  warnings?: string[];
  preferences?: Array<Record<string, unknown>>;
};

export type CubeSatDiagnosticResponse = {
  payload_id: string;
  payload_meta?: {
    vendor?: unknown;
    product_name?: unknown;
    recommended_bus_min_u?: unknown;
    recommended_bus_min_mass_kg?: unknown;
  };
  bus_cases?: Array<{
    bus_class?: unknown;
    status?: unknown;
    objective_value?: unknown;
    violated_families?: unknown;
    first_order_families?: unknown;
    margins?: unknown;
  }>;
  [k: string]: unknown;
};

export async function solveMission(input: MissionInput): Promise<MissionSolveResponse> {
  const resp = await fetch("/api/v1/mission/solve", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input }),
  });
  if (!resp.ok) {
    let detail: string | null = null;
    try {
      const body = (await resp.json()) as unknown;
      if (body && typeof body === "object") {
        const record = body as Record<string, unknown>;
        if (typeof record.detail === "string") detail = record.detail;
        else if (typeof record.message === "string") detail = record.message;
        else detail = JSON.stringify(record);
      }
    } catch {
      try {
        const text = await resp.text();
        detail = text || null;
      } catch {
        detail = null;
      }
    }
    const suffix = detail ? `: ${detail}` : "";
    throw new Error(`Solve failed (${resp.status})${suffix}`);
  }
  return resp.json();
}

export async function solveCubeSatDiagnostic(
  payload_id: string,
): Promise<CubeSatDiagnosticResponse> {
  const resp = await fetch("/api/solve/cubesat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ payload_id, diagnostic: true, top_n: 1 }),
  });
  if (!resp.ok) {
    let detail: string | null = null;
    try {
      const body = (await resp.json()) as unknown;
      if (body && typeof body === "object") {
        const record = body as Record<string, unknown>;
        if (typeof record.detail === "string") detail = record.detail;
        else if (typeof record.message === "string") detail = record.message;
        else detail = JSON.stringify(record);
      }
    } catch {
      try {
        const text = await resp.text();
        detail = text || null;
      } catch {
        detail = null;
      }
    }

    const suffix = detail ? `: ${detail}` : "";
    throw new Error(`CP-SAT diagnostic failed (${resp.status})${suffix}`);
  }
  return resp.json();
}

export type MissionReportFormat = "pdf" | "json" | "html";

export async function downloadMissionReport(
  input: MissionInput,
  format: MissionReportFormat = "pdf",
): Promise<Blob> {
  const resp = await fetch(`/api/v1/mission/report?format=${format}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input }),
  });
  if (!resp.ok) {
    let detail: string | null = null;
    try {
      const body = (await resp.json()) as unknown;
      if (body && typeof body === "object") {
        const record = body as Record<string, unknown>;
        if (typeof record.detail === "string") detail = record.detail;
        else if (typeof record.message === "string") detail = record.message;
        else detail = JSON.stringify(record);
      }
    } catch {
      try {
        const text = await resp.text();
        detail = text || null;
      } catch {
        detail = null;
      }
    }
    const suffix = detail ? `: ${detail}` : "";
    throw new Error(`Report generation failed (${resp.status})${suffix}`);
  }
  return resp.blob();
}

export async function getTaxonomy(): Promise<TaxonomyResponse> {
  const resp = await fetch("/api/v1/taxonomy", { method: "GET" });
  if (!resp.ok) throw new Error(`Taxonomy failed: ${resp.status}`);
  return resp.json();
}
