import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import WizardShell from "../components/WizardShell";
import {
  downloadMissionReport,
  solveMission,
  type MissionReportFormat,
  type MissionSolveResponse,
} from "../lib/api";
import { requireMissionInput, useMission } from "../state/mission";
import { useSceneStore } from "../store/sceneStore";

export default function ResultPage() {
  const nav = useNavigate();
  const { draft } = useMission();
  const setConstellation = useSceneStore((s) => s.setConstellation);

  const input = useMemo(() => {
    try {
      return requireMissionInput(draft);
    } catch {
      return null;
    }
  }, [draft]);

  useEffect(() => {
    if (!draft.family) {
      nav("/", { replace: true });
      return;
    }
    if (!draft.payload) {
      nav("/payload", { replace: true });
      return;
    }
    if (!draft.roi) {
      nav("/roi", { replace: true });
      return;
    }
    if (!draft.parameters) {
      nav("/parameters", { replace: true });
    }
  }, [draft.family, draft.payload, draft.roi, draft.parameters, nav]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MissionSolveResponse | null>(null);
  const [reportLoading, setReportLoading] = useState<MissionReportFormat | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    if (!input) return;
    let alive = true;
    setLoading(true);
    solveMission(input)
      .then((r) => {
        if (!alive) return;
        setData(r);
        setConstellation({
          totalSatellites: r.constellation.satellites,
          planes: r.constellation.planes,
        });
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
  }, [input, setConstellation]);

  return (
    <WizardShell
      title="Your Constellation"
      backTo="/parameters"
      testId="page-result"
    >
      {loading ? <div className="muted">Solving...</div> : null}
      {error ? <div className="error">Solve error: {error}</div> : null}

      {!loading && !error && data ? (
        <div className="result">
          <div className="resultRow">
            <div className="resultCard">
              <div className="resultLabel">Constellation</div>
              <div data-testid="solution-satellites" className="resultValue">
                {data.constellation.satellites} satellites
              </div>
              <div className="muted">{data.constellation.orbit_type}</div>
            </div>

            <div className="resultCard">
              <div className="resultLabel">Platform</div>
              <div data-testid="solution-platform" className="resultValue">
                {data.solution.platform.bus_size_u}U Platform
              </div>
              <div className="muted">{data.solution.platform.name}</div>
            </div>

            <div className="resultCard">
              <div className="resultLabel">Indicative Cost</div>
              <div className="resultValue">
                ${Math.round(data.solution.budgets.total_cost_kusd)}K
              </div>
              <div className="muted">kUSD base sum</div>
            </div>
          </div>

          <div className="resultCardWide">
            <div className="resultLabel">Subsystems</div>
            <div className="subList">
              {data.solution.subsystems.map((s) => (
                <div key={s.domain} className="subItem">
                  <div className="subDomain">{s.domain}</div>
                  <div className="subName">{s.name}</div>
                </div>
              ))}
            </div>
            {data.solution.warnings?.length ? (
              <div className="warnBox">
                {data.solution.warnings.map((w: string) => (
                  <div key={w}>• {w}</div>
                ))}
              </div>
            ) : null}
          </div>

          <div className="actions">
            <button className="btn btnSecondary" type="button" onClick={() => nav("/solver-trace")}>
              View Solver Trace
            </button>
            {(
              [
                ["pdf", "Download Mission Report PDF", "cubesat-mission-report.pdf"],
                ["json", "Download JSON", "mission-report.json"],
                ["html", "Download HTML", "mission-report.html"],
              ] as const
            ).map(([format, label, filename]) => (
              <button
                key={format}
                className={format === "pdf" ? "btn btnPrimary" : "btn btnSecondary"}
                type="button"
                disabled={reportLoading !== null}
                onClick={async () => {
                  if (!input || reportLoading) return;
                  setReportLoading(format);
                  setReportError(null);
                  try {
                    const blob = await downloadMissionReport(input, format);
                    const url = URL.createObjectURL(blob);
                    try {
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = filename;
                      a.click();
                    } finally {
                      URL.revokeObjectURL(url);
                    }
                  } catch (e) {
                    setReportError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setReportLoading(null);
                  }
                }}
              >
                {reportLoading === format ? "Generating..." : label}
              </button>
            ))}
          </div>
          {reportError ? <div className="error">Report error: {reportError}</div> : null}
        </div>
      ) : null}
    </WizardShell>
  );
}
