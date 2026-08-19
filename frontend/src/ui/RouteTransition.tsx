import type { ReactNode } from "react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useMission } from "../state/mission";
import { useSceneStore } from "../store/sceneStore";
import type { PayloadType, SceneStep } from "../types/scene";
import { resolveCountry } from "../lib/geo/countrySearch";
import LeftDock from "./LeftDock";

function stepFromPath(pathname: string): SceneStep {
  if (pathname === "/") return "missionType";
  if (pathname.startsWith("/payload")) return "payloadSelection";
  if (pathname.startsWith("/roi")) return "roi";
  if (pathname.startsWith("/parameters")) return "missionParameters";
  if (pathname.startsWith("/result")) return "results";
  return "missionType";
}

function payloadTypeFromDraft(draft: ReturnType<typeof useMission>["draft"]): PayloadType {
  const payload = draft.payload;
  if (!payload) return null;
  if (payload.type === "my_payload") return "my_payload";

  const id = payload.payload_id.toLowerCase();
  if (id.includes("hyperspec")) return "hyperspectral";
  if (id.includes("multispec") || id.includes("multi")) return "multispectral";
  if (id.includes("nir") || id.includes("swir")) return "multispectral";
  if (id.includes("vhr")) return "vhr_optical";
  if (id.includes("thermal")) return "thermal";
  if (id.includes("sar")) return "sar";
  if (id.includes("ais")) return "ais";
  if (id.includes("adsb") || id.includes("adsb")) return "adsb";
  if (id.includes("broadband")) return "broadband";
  if (id.includes("store") || id.includes("forward")) return "store_and_forward";
  if (id.includes("sigint") || id.includes("secure")) return "sigint";
  return null;
}

export default function RouteTransition({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const { draft } = useMission();
  const setStep = useSceneStore((s) => s.setStep);
  const setMissionFamily = useSceneStore((s) => s.setMissionFamily);
  const setPayloadType = useSceneStore((s) => s.setPayloadType);
  const setSelectedRegion = useSceneStore((s) => s.setSelectedRegion);
  const setRegionQuery = useSceneStore((s) => s.setRegionQuery);

  useEffect(() => {
    setStep(stepFromPath(loc.pathname));
  }, [loc.pathname, setStep]);

  useEffect(() => {
    setMissionFamily(draft.family ?? null);
    setPayloadType(payloadTypeFromDraft(draft));

    if (!draft.roi || draft.roi.type === "global") {
      setRegionQuery("");
      setSelectedRegion(null);
      return;
    }

    const q = draft.roi.query?.trim() ?? "";
    if (!q) {
      setRegionQuery("");
      setSelectedRegion(null);
      return;
    }
    setRegionQuery(q);

    const match = resolveCountry(q);
    setSelectedRegion(match ? { id: match.id, name: match.name, lat: match.lat, lon: match.lon } : null);
  }, [draft.family, draft.payload, draft.roi, setMissionFamily, setPayloadType, setRegionQuery, setSelectedRegion]);

  return (
    <div className="uiView">
      <LeftDock>
        <div key={loc.pathname} className="dockRoute">
          {children}
        </div>
      </LeftDock>
    </div>
  );
}
