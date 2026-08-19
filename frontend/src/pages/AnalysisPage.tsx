import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  solveCubeSatDiagnostic,
  solveMission,
  type CubeSatDiagnosticResponse,
  type EngineeringTrace,
  type EngineeringTraceSubsystem,
  type MissionInput,
  type MissionSolveResponse,
} from "../lib/api";
import { requireMissionInput, useMission } from "../state/mission";
import SolverTraceShell from "../ui/SolverTraceShell";

const DASH = "—";
const BULLET = "•";

type DetailTab = "reason" | "margins" | "metadata" | "raw";

function metaEntries(
  meta: Record<string, unknown> | null | undefined,
): Array<{ k: string; v: string }> {
  if (!meta) return [];
  if (typeof meta !== "object") return [];
  const out: Array<{ k: string; v: string }> = [];
  for (const [k, raw] of Object.entries(meta)) {
    if (!k) continue;
    let v = "";
    if (raw == null) v = DASH;
    else if (typeof raw === "string") v = raw;
    else if (typeof raw === "number" || typeof raw === "boolean") v = String(raw);
    else {
      try {
        v = JSON.stringify(raw);
      } catch {
        v = String(raw);
      }
    }
    out.push({ k, v });
  }
  out.sort((a, b) => a.k.localeCompare(b.k));
  return out;
}

function fmt(v: number | null | undefined, digits = 2): string {
  if (v == null) return DASH;
  if (!Number.isFinite(v)) return DASH;
  return Number(v).toFixed(digits);
}

function fmtCompact(v: number | null | undefined, digits = 2): string {
  if (v == null) return DASH;
  if (!Number.isFinite(v)) return DASH;
  return Number(v.toFixed(digits)).toString();
}

function fmtWithUnit(v: number | null | undefined, digits: number, unit: string): string {
  const value = fmt(v, digits);
  return value === DASH ? DASH : `${value} ${unit}`;
}

function fmtCompactWithUnit(v: number | null | undefined, digits: number, unit: string): string {
  const value = fmtCompact(v, digits);
  return value === DASH ? DASH : `${value} ${unit}`;
}

function labelize(raw: string | null | undefined): string {
  if (!raw) return DASH;
  return raw
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function domainLabel(domain: string | null | undefined): string {
  if (!domain) return "Subsystem";
  const upper = domain.toUpperCase();
  if (upper === "OBC" || upper === "ADCS" || upper === "EPS" || upper === "COMM") return upper;
  return labelize(domain);
}

function subsystemKey(s: EngineeringTraceSubsystem, index: number): string {
  return `${s.domain || "subsystem"}:${s.name || "unnamed"}:${index}`;
}

function subsystemTitle(s: EngineeringTraceSubsystem | null | undefined): string {
  if (!s) return DASH;
  const domain = domainLabel(s.domain);
  const variant = s.tier || s.name;
  return variant ? `${domain} (${variant})` : domain;
}

function cleanTraceText(text: string | null | undefined): string {
  if (!text?.trim()) return DASH;
  return text.replace(/\s+/g, " ").trim();
}

function shortSentence(text: string | null | undefined, maxLength = 132): string {
  const normalized = cleanTraceText(text);
  if (normalized === DASH) return DASH;
  const firstSentence = normalized.match(/^.+?[.!?](?:\s|$)/)?.[0]?.trim();
  const candidate = firstSentence || normalized;
  if (candidate.length <= maxLength) return candidate;
  return `${candidate.slice(0, Math.max(0, maxLength - 3)).trim()}...`;
}

function metadataCapability(meta: Record<string, unknown> | null | undefined): string {
  const entries = metaEntries(meta);
  if (!entries.length) return DASH;
  const preferred =
    entries.find((entry) =>
      /capability|accuracy|downlink|storage|power|battery|thermal/i.test(entry.k),
    ) ?? entries[0];
  return `${labelize(preferred.k)}: ${preferred.v}`;
}

function statusDisplay(status: string | null | undefined): string {
  if (!status) return "Unknown";
  return labelize(status.toLowerCase());
}

function isFeasibleStatus(status: string | null | undefined): boolean {
  const normalized = status?.toLowerCase() ?? "";
  return (
    (normalized.includes("feasible") && !normalized.includes("infeasible")) ||
    normalized.includes("optimal")
  );
}

function badgeClass(status: string | null | undefined): string {
  const normalized = status?.toUpperCase() ?? "";
  if (normalized === "PASS" || normalized === "FEASIBLE" || normalized === "OPTIMAL") {
    return "badge badgePass";
  }
  if (normalized === "FAIL" || normalized.includes("INFEASIBLE")) return "badge badgeFail";
  return "badge badgeUnknown";
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="traceSection">
      <div className="traceSectionHeader">
        <div>
          <div className="traceSectionTitle">{title}</div>
          {subtitle ? (
            <div className="muted" style={{ marginTop: 4 }}>
              {subtitle}
            </div>
          ) : null}
        </div>
      </div>
      <div className="traceSectionBody">{children}</div>
    </section>
  );
}

function MetricGrid({ items }: { items: Array<{ label: string; value: string }> }) {
  return (
    <div className="traceMetricGrid">
      {items.map((it) => (
        <div className="traceMetric" key={it.label}>
          <div className="traceMetricLabel">{it.label}</div>
          <div className="traceMetricValue">{it.value}</div>
        </div>
      ))}
    </div>
  );
}

function SolverSummaryBar({
  trace,
  data,
}: {
  trace: EngineeringTrace;
  data: MissionSolveResponse;
}) {
  const busSize = trace.selection?.bus_size_u ?? data.solution.platform.bus_size_u ?? null;
  const totalMass = trace.budgets?.total_mass_kg ?? data.solution.budgets.total_mass_kg;
  const avgPower = trace.budgets?.total_avg_power_w ?? data.solution.budgets.total_avg_power_w;
  const peakPower = trace.budgets?.total_peak_power_w ?? data.solution.budgets.total_peak_power_w;
  const totalCost = trace.budgets?.total_cost_kusd ?? data.solution.budgets.total_cost_kusd;
  const status = trace.solver?.status ?? "UNKNOWN";
  const feasible = isFeasibleStatus(status);

  const items = [
    { label: "Bus Size", value: busSize != null ? `${busSize}U` : DASH },
    { label: "Total Mass", value: fmtCompactWithUnit(totalMass, 2, "kg") },
    { label: "Avg Power", value: fmtCompactWithUnit(avgPower, 2, "W") },
    { label: "Peak Power", value: fmtCompactWithUnit(peakPower, 1, "W") },
    { label: "Total Cost", value: fmtCompactWithUnit(totalCost, 1, "kUSD") },
  ];

  return (
    <section className="traceSummaryBar" aria-label="Solver Trace Summary">
      {items.map((item) => (
        <div className="traceSummaryItem" key={item.label}>
          <div className="traceSummaryLabel">{item.label}</div>
          <div className="traceSummaryValue">{item.value}</div>
        </div>
      ))}
      <div className="traceSummaryItem traceSummaryFeasibility">
        <div className="traceSummaryLabel">Feasibility</div>
        <div
          className={feasible ? "traceStatus traceStatusGood" : "traceStatus traceStatusNeutral"}
        >
          {feasible ? <span aria-hidden="true">✓</span> : null}
          <span>{statusDisplay(status)}</span>
        </div>
      </div>
    </section>
  );
}

function SubsystemCard({
  subsystem,
  selected,
  onViewDetails,
}: {
  subsystem: EngineeringTraceSubsystem;
  selected: boolean;
  onViewDetails: () => void;
}) {
  return (
    <article
      className={selected ? "traceSubsystemCard traceSubsystemCardActive" : "traceSubsystemCard"}
    >
      <div className="traceSubsystemCardTop">
        <div>
          <div className="traceSubsystemTitle">{subsystemTitle(subsystem)}</div>
        </div>
        <span className="traceSelectedBadge">Selected</span>
      </div>

      <div className="traceSubsystemMetrics">
        <div>
          <span>Mass</span>
          <strong>{fmtWithUnit(subsystem.mass_kg, 2, "kg")}</strong>
        </div>
        <div>
          <span>Avg Power</span>
          <strong>{fmtWithUnit(subsystem.avg_power_w, 1, "W")}</strong>
        </div>
        <div>
          <span>Peak Power</span>
          <strong>{fmtWithUnit(subsystem.peak_power_w, 1, "W")}</strong>
        </div>
        <div>
          <span>Cost</span>
          <strong>{fmtWithUnit(subsystem.cost_kusd, 1, "kUSD")}</strong>
        </div>
      </div>

      <div className="traceWhyBlock">
        <span>Why selected</span>
        <p>{shortSentence(subsystem.selection_reason, 96)}</p>
      </div>

      <button type="button" className="traceDetailsButton" onClick={onViewDetails}>
        View details
      </button>
    </article>
  );
}

function TraceRows({ rows }: { rows: Array<{ label: string; value: string }> }) {
  return (
    <div className="traceDetailRows">
      {rows.map((row) => (
        <div className="traceDetailRow" key={row.label}>
          <div className="traceDetailKey">{row.label}</div>
          <div className="traceDetailValue">{row.value}</div>
        </div>
      ))}
    </div>
  );
}

function MarginTable({ budgets }: { budgets: EngineeringTrace["budgets"] }) {
  const rows = [
    { label: "Mass Margin", value: fmt(budgets?.mass_margin_kg, 2), unit: "kg" },
    { label: "Avg Power Margin", value: fmt(budgets?.avg_power_margin_w, 1), unit: "W" },
    { label: "Peak Power Margin", value: fmt(budgets?.peak_power_margin_w, 1), unit: "W" },
    { label: "Volume Margin", value: fmt(budgets?.bus_volume_margin_u, 2), unit: "U" },
  ];

  return (
    <div className="traceCompactTableWrap">
      <table className="traceCompactTable" aria-label="Subsystem margin summary">
        <thead>
          <tr>
            <th>Margin Type</th>
            <th>Margin Value</th>
            <th>Unit</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td>{row.value}</td>
              <td>{row.value === DASH ? DASH : row.unit}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConstraintsTable({ trace }: { trace: EngineeringTrace }) {
  if (!trace.constraints?.length) {
    return <div className="muted">No constraint rows returned.</div>;
  }

  return (
    <div className="traceTableScroll">
      <table className="constraintTable" aria-label="Constraints Table">
        <thead>
          <tr>
            <th>Constraint</th>
            <th>Required</th>
            <th>Capacity</th>
            <th>Margin</th>
            <th>Units</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {trace.constraints.map((c) => (
            <tr key={c.name}>
              <td>{c.name}</td>
              <td>{c.required != null ? fmt(c.required, 3) : DASH}</td>
              <td>{c.capacity != null ? fmt(c.capacity, 3) : DASH}</td>
              <td>{c.margin != null ? fmt(c.margin, 3) : DASH}</td>
              <td>{c.units ?? DASH}</td>
              <td>
                <span className={badgeClass(c.status)}>{c.status ?? "UNKNOWN"}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PreferenceTable({ trace }: { trace: EngineeringTrace }) {
  if (!trace.preferences?.length) {
    return <div className="muted">No preference trace rows returned.</div>;
  }

  return (
    <div className="traceTableScroll">
      <table className="traceTable" aria-label="Engineering preference application">
        <thead>
          <tr>
            <th>Preference</th>
            <th>Value</th>
            <th>Status</th>
            <th>Effect</th>
          </tr>
        </thead>
        <tbody>
          {trace.preferences.map((pref) => (
            <tr key={`${String(pref.preference)}-${String(pref.value)}`}>
              <td>{String(pref.preference ?? DASH)}</td>
              <td>{String(pref.value ?? DASH)}</td>
              <td>{String(pref.status ?? DASH)}</td>
              <td>{String(pref.effect ?? DASH)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TraceDetailPanel({
  trace,
  data,
  input,
  selectedSubsystem,
  activeTab,
  onTabChange,
}: {
  trace: EngineeringTrace;
  data: MissionSolveResponse;
  input: MissionInput;
  selectedSubsystem: EngineeringTraceSubsystem | null;
  activeTab: DetailTab;
  onTabChange: (tab: DetailTab) => void;
}) {
  const metadata = metaEntries(selectedSubsystem?.metadata);
  const tabs: Array<{ id: DetailTab; label: string }> = [
    { id: "reason", label: "Reason" },
    { id: "margins", label: "Margins" },
    { id: "metadata", label: "Metadata" },
    { id: "raw", label: "Raw Trace" },
  ];

  return (
    <aside className="traceDetailPanel" aria-label="Selected subsystem details">
      <div className="traceDetailHeader">
        <div>
          <div className="traceDetailEyebrow">Selected Subsystem</div>
          <h2>{subsystemTitle(selectedSubsystem)}</h2>
        </div>
        <span className="traceSelectedBadge">Selected</span>
      </div>

      <div className="traceDetailTabs" role="tablist" aria-label="Subsystem detail sections">
        {tabs.map((tab) => (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? "traceTab traceTabActive" : "traceTab"}
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="traceDetailBody">
        {!selectedSubsystem ? <div className="muted">No subsystem details returned.</div> : null}

        {selectedSubsystem && activeTab === "reason" ? (
          <TraceRows
            rows={[
              {
                label: "Requirement",
                value: shortSentence(
                  selectedSubsystem.capacity_basis ?? selectedSubsystem.margin_basis,
                ),
              },
              {
                label: "Selected Capability",
                value: metadataCapability(selectedSubsystem.metadata),
              },
              { label: "Decision", value: cleanTraceText(selectedSubsystem.selection_reason) },
            ]}
          />
        ) : null}

        {selectedSubsystem && activeTab === "margins" ? (
          <MarginTable budgets={trace.budgets} />
        ) : null}

        {selectedSubsystem && activeTab === "metadata" ? (
          <>
            <TraceRows
              rows={[
                { label: "Source database", value: selectedSubsystem.source_database ?? DASH },
                { label: "Source library", value: selectedSubsystem.source_library ?? DASH },
                { label: "Capacity basis", value: selectedSubsystem.capacity_basis ?? DASH },
              ]}
            />
            <details className="traceRawDisclosure">
              <summary>Additional metadata</summary>
              {metadata.length ? (
                <div className="traceMetaList">
                  {metadata.map((m) => (
                    <div key={`${selectedSubsystem.domain}:${selectedSubsystem.name}:${m.k}`}>
                      <span className="traceMetaKey">{m.k}</span>:{" "}
                      <span className="traceMetaVal">{m.v}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="muted">No metadata entries returned.</div>
              )}
            </details>
          </>
        ) : null}

        {selectedSubsystem && activeTab === "raw" ? (
          <div className="traceRawStack">
            <details className="traceRawDisclosure">
              <summary>Selected subsystem JSON</summary>
              <pre className="jsonPanel">{JSON.stringify(selectedSubsystem, null, 2)}</pre>
            </details>
            <details className="traceRawDisclosure">
              <summary>Solver metadata and mission context</summary>
              <pre className="jsonPanel">
                {JSON.stringify(
                  {
                    solver: trace.solver,
                    selection: trace.selection,
                    budgets: trace.budgets,
                    input,
                    requirements: data.requirements ?? null,
                    platform: data.solution.platform,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
            <details className="traceRawDisclosure">
              <summary>Constraint margins</summary>
              <ConstraintsTable trace={trace} />
            </details>
            <details className="traceRawDisclosure">
              <summary>Engineering preferences</summary>
              <PreferenceTable trace={trace} />
            </details>
            <details className="traceRawDisclosure">
              <summary>Trace lines and warnings</summary>
              {trace.trace?.length ? (
                <ul className="traceList">
                  {trace.trace.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              ) : (
                <div className="muted">No trace strings returned.</div>
              )}
              {trace.warnings?.length ? (
                <div className="warnBox" style={{ marginTop: 10 }}>
                  {trace.warnings.map((w) => (
                    <div key={w}>
                      {BULLET} {w}
                    </div>
                  ))}
                </div>
              ) : null}
            </details>
          </div>
        ) : null}
      </div>
    </aside>
  );
}

export default function AnalysisPage() {
  const { draft } = useMission();

  const input = useMemo(() => {
    try {
      return requireMissionInput(draft);
    } catch {
      return null;
    }
  }, [draft]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MissionSolveResponse | null>(null);

  useEffect(() => {
    if (!input) {
      setLoading(false);
      setError(null);
      setData(null);
      return;
    }
    let alive = true;
    setLoading(true);
    solveMission(input)
      .then((r) => {
        if (!alive) return;
        setData(r);
        setError(null);
      })
      .catch((e) => {
        if (!alive) return;
        setError(String(e?.message ?? e));
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [input]);

  const trace: EngineeringTrace | null = data?.engineering_trace ?? null;
  const subsystems = useMemo(() => trace?.subsystems ?? [], [trace?.subsystems]);

  const [selectedSubsystemKey, setSelectedSubsystemKey] = useState<string | null>(null);
  const [activeDetailTab, setActiveDetailTab] = useState<DetailTab>("reason");

  useEffect(() => {
    const firstKey = subsystems.length ? subsystemKey(subsystems[0], 0) : null;
    const hasSelection =
      selectedSubsystemKey != null &&
      subsystems.some(
        (subsystem, index) => subsystemKey(subsystem, index) === selectedSubsystemKey,
      );

    if (!firstKey) {
      if (selectedSubsystemKey != null) setSelectedSubsystemKey(null);
      return;
    }

    if (!hasSelection) {
      setSelectedSubsystemKey(firstKey);
    }
  }, [selectedSubsystemKey, subsystems]);

  const selectedSubsystem = useMemo(() => {
    const effectiveKey =
      selectedSubsystemKey ?? (subsystems.length ? subsystemKey(subsystems[0], 0) : null);
    if (!effectiveKey) return null;
    return (
      subsystems.find((subsystem, index) => subsystemKey(subsystem, index) === effectiveKey) ?? null
    );
  }, [selectedSubsystemKey, subsystems]);

  const catalogPayloadId =
    input?.payload?.type === "catalog" && input.payload.payload_id
      ? input.payload.payload_id
      : null;

  const [diagLoading, setDiagLoading] = useState(false);
  const [diagError, setDiagError] = useState<string | null>(null);
  const [diag, setDiag] = useState<CubeSatDiagnosticResponse | null>(null);

  useEffect(() => {
    setDiag(null);
    setDiagError(null);
    setDiagLoading(false);
  }, [catalogPayloadId]);

  const runDiagnostic = async () => {
    if (!catalogPayloadId) return;
    if (diagLoading) return;
    setDiagLoading(true);
    setDiagError(null);
    try {
      const out = await solveCubeSatDiagnostic(catalogPayloadId);
      setDiag(out);
    } catch (e: unknown) {
      setDiag(null);
      setDiagError(e instanceof Error ? e.message : String(e));
    } finally {
      setDiagLoading(false);
    }
  };

  const setupChecklist: Array<{ label: string; ok: boolean }> = [
    { label: "Mission family", ok: Boolean(draft.family) },
    { label: "Payload", ok: Boolean(draft.payload) },
    { label: "Region of interest", ok: Boolean(draft.roi) },
    { label: "Mission parameters", ok: typeof draft.parameters?.revisit_time_hours === "number" },
  ];

  return (
    <SolverTraceShell
      title={input ? "Solver Trace" : "Solver Trace unavailable"}
      subtitle={
        input
          ? "Backend mirror: requirement derivation, subsystem selection, constraint margins, and solver trace."
          : "Complete Mission Setup first to generate a backend execution trace."
      }
      backTo="/result"
      testId="page-analysis"
    >
      {!input ? (
        <div className="result">
          <div className="resultCardWide">
            <div className="resultLabel">Solver Trace unavailable</div>
            <div className="muted" style={{ marginTop: 6 }}>
              Complete Mission Setup first to generate a backend execution trace.
            </div>

            <div className="muted" style={{ marginTop: 10 }}>
              Checklist:
            </div>
            <ul className="traceList" style={{ marginTop: 6 }}>
              {setupChecklist.map((c) => (
                <li key={c.label}>
                  {c.label}: {c.ok ? "OK" : "Missing"}
                </li>
              ))}
            </ul>

            <div className="actions">
              <Link className="btn btnPrimary" to="/">
                Go to Mission Setup
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <>
          {loading ? <div className="muted">Loading analysis...</div> : null}
          {error ? <div className="error">Solve error: {error}</div> : null}

          {!loading && !error && data ? (
            trace ? (
              <div className="traceRoot">
                <SolverSummaryBar trace={trace} data={data} />

                <div className="traceWorkspace">
                  <section className="traceSubsystemRegion" aria-label="Subsystem Cards">
                    <div className="traceRegionHeader">
                      <div>
                        <div className="traceSectionTitle">Subsystem Cards</div>
                        <div className="muted">Selected variants and compact resource usage.</div>
                      </div>
                    </div>

                    {subsystems.length ? (
                      <div className="traceSubsystemGrid">
                        {subsystems.map((subsystem, index) => {
                          const key = subsystemKey(subsystem, index);
                          return (
                            <SubsystemCard
                              key={key}
                              subsystem={subsystem}
                              selected={
                                key ===
                                (selectedSubsystemKey ??
                                  (subsystems.length ? subsystemKey(subsystems[0], 0) : null))
                              }
                              onViewDetails={() => {
                                setSelectedSubsystemKey(key);
                                setActiveDetailTab("reason");
                              }}
                            />
                          );
                        })}
                      </div>
                    ) : (
                      <div className="traceEmptyCard">No subsystem details returned.</div>
                    )}
                  </section>

                  <TraceDetailPanel
                    trace={trace}
                    data={data}
                    input={input}
                    selectedSubsystem={selectedSubsystem}
                    activeTab={activeDetailTab}
                    onTabChange={setActiveDetailTab}
                  />
                </div>

                <Section
                  title="CP-SAT Diagnostic"
                  subtitle="Optional manual panel (catalog payloads only)."
                >
                  {catalogPayloadId ? (
                    <>
                      <div className="muted">
                        payload_id:{" "}
                        <span style={{ fontFamily: "monospace" }}>{catalogPayloadId}</span> {BULLET}{" "}
                        endpoint:{" "}
                        <span style={{ fontFamily: "monospace" }}>/api/solve/cubesat</span>
                      </div>

                      <div
                        style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}
                      >
                        <button
                          type="button"
                          className="btn btnSecondary"
                          onClick={runDiagnostic}
                          disabled={diagLoading}
                        >
                          {diagLoading ? "Running..." : "Run CP-SAT Diagnostic"}
                        </button>
                      </div>

                      {diagError ? <div className="error">CP-SAT error: {diagError}</div> : null}

                      {diag ? (
                        <div className="resultCardWide" style={{ marginTop: 10 }}>
                          <div className="resultLabel">CP-SAT Diagnostic</div>
                          <div className="muted" style={{ marginTop: 6 }}>
                            Payload: {String(diag.payload_id ?? catalogPayloadId)}
                          </div>

                          {diag.payload_meta ? (
                            <MetricGrid
                              items={[
                                {
                                  label: "Product",
                                  value:
                                    diag.payload_meta.product_name != null
                                      ? String(diag.payload_meta.product_name)
                                      : DASH,
                                },
                                {
                                  label: "Vendor",
                                  value:
                                    diag.payload_meta.vendor != null
                                      ? String(diag.payload_meta.vendor)
                                      : DASH,
                                },
                                {
                                  label: "Recommended bus",
                                  value:
                                    diag.payload_meta.recommended_bus_min_u != null
                                      ? `${String(diag.payload_meta.recommended_bus_min_u)}U`
                                      : DASH,
                                },
                                {
                                  label: "Recommended mass",
                                  value:
                                    diag.payload_meta.recommended_bus_min_mass_kg != null
                                      ? `${String(diag.payload_meta.recommended_bus_min_mass_kg)} kg`
                                      : DASH,
                                },
                              ]}
                            />
                          ) : null}

                          {Array.isArray(diag.bus_cases) && diag.bus_cases.length ? (
                            <div className="traceTableScroll">
                              <table
                                className="constraintTable"
                                aria-label="CP-SAT Diagnostic Bus Cases"
                              >
                                <thead>
                                  <tr>
                                    <th>Bus</th>
                                    <th>Status</th>
                                    <th>Objective</th>
                                    <th>Violations</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {diag.bus_cases.map((c, idx) => {
                                    const status = String(c.status ?? "UNKNOWN");
                                    const violations = Array.isArray(c.violated_families)
                                      ? c.violated_families.length
                                      : c.violated_families != null
                                        ? 1
                                        : 0;
                                    return (
                                      <tr key={`${String(c.bus_class ?? idx)}:${idx}`}>
                                        <td>{c.bus_class != null ? String(c.bus_class) : DASH}</td>
                                        <td>
                                          <span className={badgeClass(status)}>{status}</span>
                                        </td>
                                        <td>
                                          {c.objective_value != null
                                            ? String(c.objective_value)
                                            : DASH}
                                        </td>
                                        <td>{violations ? String(violations) : DASH}</td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="muted" style={{ marginTop: 10 }}>
                              No diagnostic bus cases returned.
                            </div>
                          )}

                          <details className="traceRawDisclosure">
                            <summary>Raw diagnostic JSON</summary>
                            <pre className="jsonPanel">{JSON.stringify(diag, null, 2)}</pre>
                          </details>
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <div className="muted">
                      CP-SAT diagnostic is available only for catalog payloads.
                    </div>
                  )}
                </Section>
              </div>
            ) : (
              <div className="muted">Engineering trace is not available for this solve.</div>
            )
          ) : null}
        </>
      )}
    </SolverTraceShell>
  );
}
