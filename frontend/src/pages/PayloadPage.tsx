import { useEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";
import { useNavigate } from "react-router-dom";
import WizardShell from "../components/WizardShell";
import { getTaxonomy, type PayloadSelection, type TaxonomyMissionFamily } from "../lib/api";
import { firstMissingStep } from "../lib/guards";
import { useMission } from "../state/mission";

type CategoryOption = {
  categoryId: string;
  label: string;
  detail: string;
  disabled: boolean;
  payloadId?: string;
};

export default function PayloadPage() {
  const nav = useNavigate();
  const { draft, setPayload } = useMission();
  const [family, setFamily] = useState<TaxonomyMissionFamily | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const missing = firstMissingStep({ ...draft, payload: draft.payload ?? undefined });
    if (missing === "/") nav("/", { replace: true });
  }, [draft, nav]);

  useEffect(() => {
    if (import.meta.env.VITE_DISABLE_TAXONOMY_FETCH === "1") return;
    let alive = true;
    setLoading(true);
    getTaxonomy()
      .then((t) => {
        if (!alive) return;
        const fam =
          t.families.find((f) => f.family_id === (draft.family ?? "remote_sensing")) ?? null;
        setFamily(fam);
        setError(null);
      })
      .catch(() => {
        setFamily(null);
        setError("Could not load payload taxonomy.");
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [draft.family]);

  const options: CategoryOption[] = useMemo(() => {
    const fam = family;
    const cats = fam?.payload_categories ?? [];
    return cats.map((c) => {
      if (c.category_id === "my_payload") {
        return {
          categoryId: c.category_id,
          label: c.label,
          detail: c.description,
          disabled: false,
        };
      }
      const payloadId = c.payloads[0]?.payload_id;
      return {
        categoryId: c.category_id,
        label: c.label,
        detail: c.description,
        disabled: !payloadId,
        payloadId,
      };
    });
  }, [family]);

  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(() => {
    if (draft.payload?.type === "my_payload") return "my_payload";
    return null;
  });

  useEffect(() => {
    if (!family) return;
    const payload = draft.payload;
    if (payload && payload.type === "catalog") {
      for (const c of family.payload_categories) {
        if (c.payloads.some((p) => p.payload_id === payload.payload_id)) {
          setSelectedCategoryId(c.category_id);
          return;
        }
      }
    }
  }, [draft.payload, family]);

  type MyPayloadDraft = Extract<PayloadSelection, { type: "my_payload" }>;
  const [myPayload, setMyPayload] = useState<MyPayloadDraft>({
    type: "my_payload",
    name: "My Payload",
    length_mm: 200,
    width_mm: 120,
    height_mm: 120,
    mass_kg: 2.0,
    avg_power_w: 8.0,
    peak_power_w: 14.0,
    data_rate_mbps: 10.0,
    pointing_accuracy_deg: 0.6,
    thermal_class: "standard",
  });

  return (
    <WizardShell
      title="Select Payload"
      subtitle="Pick a representative payload or use My Payload for confidential inputs."
      backTo="/"
      testId="page-payload"
    >
      {loading ? <div className="muted">Loading options...</div> : null}
      {error ? <div className="error">{error}</div> : null}
      <div className="grid">
        {options.map((p) => (
          <button
            key={p.categoryId}
            className={`card ${selectedCategoryId === p.categoryId ? "cardActive" : ""}`}
            type="button"
            onClick={() => {
              if (p.disabled) return;
              setSelectedCategoryId(p.categoryId);
            }}
            aria-label={p.label}
            disabled={p.disabled}
          >
            <div className="cardTitle">{p.label}</div>
            <div className="cardDesc">{p.detail}</div>
            <div className="cardCta">{p.disabled ? "Coming soon" : "Select"}</div>
          </button>
        ))}
      </div>

      {selectedCategoryId === "my_payload" ? (
        <div className="form">
          <div className="formRow">
            <label>
              Name
              <input
                value={myPayload.name}
                onChange={(e) => setMyPayload({ ...myPayload, name: e.target.value })}
              />
            </label>
            <label>
              Mass (kg)
              <input
                type="number"
                step="0.1"
                value={myPayload.mass_kg}
                onChange={(e) => setMyPayload({ ...myPayload, mass_kg: Number(e.target.value) })}
              />
            </label>
          </div>
          <div className="formRow">
            <label>
              L (mm)
              <input
                type="number"
                value={myPayload.length_mm}
                onChange={(e) => setMyPayload({ ...myPayload, length_mm: Number(e.target.value) })}
              />
            </label>
            <label>
              W (mm)
              <input
                type="number"
                value={myPayload.width_mm}
                onChange={(e) => setMyPayload({ ...myPayload, width_mm: Number(e.target.value) })}
              />
            </label>
            <label>
              H (mm)
              <input
                type="number"
                value={myPayload.height_mm}
                onChange={(e) => setMyPayload({ ...myPayload, height_mm: Number(e.target.value) })}
              />
            </label>
          </div>
          <div className="formRow">
            <label>
              Avg power (W)
              <input
                type="number"
                value={myPayload.avg_power_w}
                onChange={(e) =>
                  setMyPayload({ ...myPayload, avg_power_w: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Peak power (W)
              <input
                type="number"
                value={myPayload.peak_power_w}
                onChange={(e) =>
                  setMyPayload({ ...myPayload, peak_power_w: Number(e.target.value) })
                }
              />
            </label>
          </div>
        </div>
      ) : null}

      <div className="actions">
        <button
          className="btn btnPrimary"
          type="button"
          disabled={!selectedCategoryId}
          onClick={() => {
            if (!selectedCategoryId) return;
            if (selectedCategoryId === "my_payload") {
              flushSync(() => setPayload(myPayload));
            } else {
              const opt = options.find((o) => o.categoryId === selectedCategoryId);
              if (!opt?.payloadId) return;
              const payloadId = opt.payloadId;
              flushSync(() => setPayload({ type: "catalog", payload_id: payloadId }));
            }
            nav("/roi");
          }}
        >
          Next
        </button>
      </div>
    </WizardShell>
  );
}
