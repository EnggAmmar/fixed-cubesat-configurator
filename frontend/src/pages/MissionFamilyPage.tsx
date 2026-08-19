import { useEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";
import { useNavigate } from "react-router-dom";
import WizardShell from "../components/WizardShell";
import { getTaxonomy, type TaxonomyMissionFamily } from "../lib/api";
import { useMission } from "../state/mission";

const FALLBACK: TaxonomyMissionFamily[] = [
  {
    family_id: "remote_sensing",
    label: "Remote Sensing",
    description: "Earth observation missions (optical, hyperspectral, thermal, SAR).",
    payload_categories: [],
  },
  {
    family_id: "iot_communication",
    label: "IoT / Communication",
    description: "Store-and-forward IoT and communications missions.",
    payload_categories: [],
  },
  {
    family_id: "navigation",
    label: "Navigation",
    description: "Navigation-related missions and timing experiments.",
    payload_categories: [],
  },
];

export default function MissionFamilyPage() {
  const nav = useNavigate();
  const { setFamily, reset } = useMission();

  const [families, setFamilies] = useState<TaxonomyMissionFamily[]>(FALLBACK);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (import.meta.env.VITE_DISABLE_TAXONOMY_FETCH === "1") return;
    let alive = true;
    setLoading(true);
    getTaxonomy()
      .then((t) => {
        if (!alive) return;
        setFamilies(t.families);
      })
      .catch(() => {
        // fall back to local defaults
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const cards = useMemo(
    () =>
      families.map((f) => ({
        id: f.family_id,
        label: f.label,
        desc: f.description,
      })),
    [families],
  );

  return (
    <WizardShell
      title="Select Mission Family"
      subtitle="Start from mission intent. The backend derives requirements and selects a feasible subsystem set."
      testId="page-mission-family"
    >
      {loading ? <div className="muted">Loading options...</div> : null}
      <div className="grid">
        {cards.map((f) => (
          <button
            key={f.id}
            className="card"
            onClick={() => {
              flushSync(() => {
                reset();
                setFamily(f.id);
              });
              nav("/payload");
            }}
            type="button"
            aria-label={f.label}
          >
            <div className="cardTitle">{f.label}</div>
            <div className="cardDesc">{f.desc}</div>
            <div className="cardCta">Select</div>
          </button>
        ))}
      </div>
    </WizardShell>
  );
}
