import { forwardRef, useRef } from "react";
import type { Group } from "three";
import { useSceneStore } from "../../store/sceneStore";
import { EarthBase } from "./EarthBase";
import { EarthDots } from "./EarthDots";
import { Atmosphere } from "./Atmosphere";
import { OrbitLayer } from "./OrbitLayer";
import { CountryPolygonOverlay } from "./CountryPolygonOverlay";
import { EarthRotationController } from "./EarthRotationController";

export const EarthSystem = forwardRef<Group>(function EarthSystem(_, ref) {
  const internalRef = useRef<Group>(null);
  const totalSatellites = useSceneStore((s) => s.constellationTotalSatellites);
  const orbitalPlanes = useSceneStore((s) => s.constellationPlanes);
  const satellitesPerPlane = useSceneStore((s) => s.constellationSatellitesPerPlane);

  return (
    <group ref={ref}>
      <group ref={internalRef}>
        <EarthBase radius={1} />
        <EarthDots radius={1.002} />
        <Atmosphere radius={1.04} />
        <OrbitLayer
          earthRadius={1}
          totalSatellites={totalSatellites}
          orbitalPlanes={orbitalPlanes}
          satellitesPerPlane={satellitesPerPlane}
        />
        <CountryPolygonOverlay radius={1.01} />
      </group>

      <EarthRotationController earthGroupRef={internalRef} />
    </group>
  );
});
