import { useEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";
import { useNavigate } from "react-router-dom";
import WizardShell from "../components/WizardShell";
import { getDefaultEngineeringPreferences, useMission } from "../state/mission";
import type {
  DownlinkRatePreference,
  OptimizationPriority,
  OrbitType,
  PointingPrecisionPreference,
  PropulsionPreference,
} from "../lib/api";

export default function ParametersPage() {
  const nav = useNavigate();
  const { draft, setEngineeringPreferences, setRevisitHours } = useMission();
  const [hours, setHours] = useState<number>(() => draft.parameters?.revisit_time_hours ?? 48);

  const initialPrefs = useMemo(() => {
    const defaults = getDefaultEngineeringPreferences();
    return { ...defaults, ...(draft.parameters?.engineering_preferences ?? {}) };
  }, [draft.parameters?.engineering_preferences]);

  const [altitudeKm, setAltitudeKm] = useState<number>(() => initialPrefs.altitude_km ?? 500);
  const [orbitType, setOrbitType] = useState<OrbitType>(() => initialPrefs.orbit_type ?? "leo");
  const [lifetimeYears, setLifetimeYears] = useState<number>(() => initialPrefs.lifetime_years ?? 2);
  const [propulsionPreference, setPropulsionPreference] = useState<PropulsionPreference>(
    () => initialPrefs.propulsion_preference ?? "no_preference",
  );
  const [pointingPreference, setPointingPreference] = useState<PointingPrecisionPreference>(
    () => initialPrefs.pointing_precision_preference ?? "no_preference",
  );
  const [downlinkPreference, setDownlinkPreference] = useState<DownlinkRatePreference>(
    () => initialPrefs.downlink_rate_preference ?? "no_preference",
  );
  const [optimizationPriority, setOptimizationPriority] = useState<OptimizationPriority>(
    () => initialPrefs.optimization_priority ?? "balanced",
  );
  const [maxBudgetUsd, setMaxBudgetUsd] = useState<string>(() =>
    initialPrefs.max_budget_usd != null ? String(initialPrefs.max_budget_usd) : "",
  );
  const [maxBusU, setMaxBusU] = useState<string>(() =>
    initialPrefs.max_bus_u != null ? String(initialPrefs.max_bus_u) : "any",
  );

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
    }
  }, [draft.family, draft.payload, draft.roi, nav]);

  return (
    <WizardShell
      title="Mission Parameters"
      subtitle="Define the key mission needs used to estimate the constellation and guide system choices."
      backTo="/roi"
      testId="page-parameters"
    >
      <div className="form">
        <label>
          Revisit Time (hours)
          <input
            type="range"
            min={2}
            max={168}
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
          />
        </label>
        <div className="kpi">
          <div className="kpiLabel">Revisit Hours</div>
          <input
            aria-label="Revisit Hours"
            className="kpiInput"
            type="number"
            min={1}
            max={720}
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
          />
        </div>

        <div className="formSection">
          <div className="kpi">
            <div className="kpiLabel">Advanced Engineering Preferences</div>
            <div className="muted">optional</div>
          </div>

          <div className="preferencesGrid">
            <label>
              Orbit Altitude (km)
              <input
                aria-label="Orbit Altitude (km)"
                type="range"
                min={300}
                max={1000}
                step={10}
                value={altitudeKm}
                onChange={(e) => setAltitudeKm(Number(e.target.value))}
              />
            </label>

            <div className="kpi">
              <div className="kpiLabel">Altitude</div>
              <input
                aria-label="Orbit Altitude Numeric"
                className="kpiInput"
                type="number"
                min={300}
                max={20000}
                step={10}
                value={altitudeKm}
                onChange={(e) => setAltitudeKm(Number(e.target.value))}
              />
            </div>

            <label>
              Orbit Type
              <select
                aria-label="Orbit Type"
                value={orbitType}
                onChange={(e) => setOrbitType(e.target.value as OrbitType)}
              >
                <option value="leo">LEO</option>
                <option value="sso">SSO</option>
                <option value="polar">Polar</option>
                <option value="equatorial">Equatorial</option>
                <option value="custom">Custom</option>
              </select>
            </label>

            <label>
              Mission Lifetime (years)
              <select
                aria-label="Mission Lifetime (years)"
                value={String(lifetimeYears)}
                onChange={(e) => setLifetimeYears(Number(e.target.value))}
              >
                <option value="0.5">0.5</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="5">5</option>
              </select>
            </label>

            <label>
              Propulsion Preference
              <select
                aria-label="Propulsion Preference"
                value={propulsionPreference}
                onChange={(e) => setPropulsionPreference(e.target.value as PropulsionPreference)}
              >
                <option value="no_preference">No preference</option>
                <option value="none">No propulsion</option>
                <option value="cold_gas">Cold gas</option>
                <option value="electric">Electric</option>
                <option value="chemical">Chemical</option>
                <option value="green_monoprop">Green monoprop</option>
              </select>
            </label>

            <label>
              Pointing Precision
              <select
                aria-label="Pointing Precision"
                value={pointingPreference}
                onChange={(e) =>
                  setPointingPreference(e.target.value as PointingPrecisionPreference)
                }
              >
                <option value="no_preference">No preference</option>
                <option value="coarse">Coarse</option>
                <option value="medium">Medium</option>
                <option value="fine">Fine</option>
                <option value="ultra_fine">Ultra-fine</option>
              </select>
            </label>

            <label>
              Downlink Rate Preference
              <select
                aria-label="Downlink Rate Preference"
                value={downlinkPreference}
                onChange={(e) => setDownlinkPreference(e.target.value as DownlinkRatePreference)}
              >
                <option value="no_preference">No preference</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="optical_extreme">Optical / extreme</option>
              </select>
            </label>

            <label>
              Optimization Priority
              <select
                aria-label="Optimization Priority"
                value={optimizationPriority}
                onChange={(e) => setOptimizationPriority(e.target.value as OptimizationPriority)}
              >
                <option value="balanced">Balanced</option>
                <option value="lowest_cost">Lowest cost</option>
                <option value="lowest_mass">Lowest mass</option>
                <option value="highest_performance">Highest performance</option>
                <option value="lowest_risk">Lowest risk</option>
              </select>
            </label>

            <label>
              Max Budget (USD)
              <input
                aria-label="Max Budget (USD)"
                type="number"
                inputMode="numeric"
                placeholder="e.g. 500000"
                value={maxBudgetUsd}
                onChange={(e) => setMaxBudgetUsd(e.target.value)}
              />
            </label>

            <label>
              Max Bus Size
              <select
                aria-label="Max Bus Size"
                value={maxBusU}
                onChange={(e) => setMaxBusU(e.target.value)}
              >
                <option value="any">Any</option>
                <option value="1">1U</option>
                <option value="1.5">1.5U</option>
                <option value="2">2U</option>
                <option value="3">3U</option>
                <option value="6">6U</option>
                <option value="12">12U</option>
                <option value="16">16U</option>
                <option value="27">27U</option>
                <option value="50">50U+</option>
              </select>
            </label>
          </div>
        </div>
      </div>

      <div className="actions">
        <button
          className="btn btnPrimary"
          type="button"
          onClick={() => {
            const maxBudget = maxBudgetUsd.trim() === "" ? undefined : Number(maxBudgetUsd);
            const maxBus = maxBusU === "any" ? undefined : Number(maxBusU);

            const nextPrefs = {
              altitude_km: altitudeKm,
              orbit_type: orbitType,
              lifetime_years: lifetimeYears,
              propulsion_preference: propulsionPreference,
              pointing_precision_preference: pointingPreference,
              downlink_rate_preference: downlinkPreference,
              optimization_priority: optimizationPriority,
              max_budget_usd: Number.isFinite(maxBudget as number) ? maxBudget : undefined,
              max_bus_u: Number.isFinite(maxBus as number) ? maxBus : undefined,
            };

            flushSync(() => {
              setRevisitHours(hours);
              setEngineeringPreferences(nextPrefs);
            });
            nav("/result");
          }}
        >
          Finish
        </button>
      </div>
    </WizardShell>
  );
}
