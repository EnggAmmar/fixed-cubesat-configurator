import { useEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";
import { useNavigate } from "react-router-dom";
import WizardShell from "../components/WizardShell";
import { useMission } from "../state/mission";
import { useSceneStore } from "../store/sceneStore";
import { resolveCountry } from "../lib/geo/countrySearch";

export default function RoiPage() {
  const nav = useNavigate();
  const { draft, setRoi } = useMission();
  const setSelectedRegion = useSceneStore((s) => s.setSelectedRegion);
  const setRegionQuery = useSceneStore((s) => s.setRegionQuery);

  useEffect(() => {
    if (!draft.family) {
      nav("/", { replace: true });
      return;
    }
    if (!draft.payload) {
      nav("/payload", { replace: true });
    }
  }, [draft.family, draft.payload, nav]);

  const initialGlobal = useMemo(() => draft.roi?.type === "global", [draft.roi?.type]);
  const [global, setGlobal] = useState<boolean>(initialGlobal);
  const [query, setQuery] = useState<string>(() =>
    draft.roi?.type === "region" ? draft.roi.query : "",
  );

  // Live preview for ROI step: highlight real country polygons when possible.
  useEffect(() => {
    if (global) {
      setRegionQuery("");
      setSelectedRegion(null);
      return;
    }

    const q = query.trim();
    setRegionQuery(q);

    if (q.length < 2) {
      setSelectedRegion(null);
      return;
    }

    const match = resolveCountry(q);
    setSelectedRegion(match ? { id: match.id, name: match.name, lat: match.lat, lon: match.lon } : null);
  }, [global, query, setRegionQuery, setSelectedRegion]);

  return (
    <WizardShell
      title="Region of Interest"
      subtitle="Choose the geographic area the mission should observe."
      backTo="/payload"
      testId="page-roi"
    >
      <div className="form">
        <label className="toggleRow">
          <input
            type="checkbox"
            checked={global}
            onChange={(e) => setGlobal(e.target.checked)}
            aria-label="Global Coverage"
          />
          <span>Global Coverage</span>
        </label>

        {!global ? (
          <label>
            Region Search
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter country, region, city..."
              aria-label="Region Search"
            />
          </label>
        ) : null}
      </div>

      <div className="actions">
        <button
          className="btn btnPrimary"
          type="button"
          onClick={() => {
            if (global) {
              flushSync(() => setRoi({ type: "global" }));
              nav("/parameters");
              return;
            }
            if (query.trim().length < 2) return;
            flushSync(() => setRoi({ type: "region", query: query.trim() }));
            nav("/parameters");
          }}
          disabled={!global && query.trim().length < 2}
        >
          Next
        </button>
      </div>
    </WizardShell>
  );
}
