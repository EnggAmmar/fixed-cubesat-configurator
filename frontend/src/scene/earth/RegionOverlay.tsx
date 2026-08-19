import { useMemo } from "react";
import * as THREE from "three";
import { useSceneStore } from "../../store/sceneStore";
import { sphericalToCartesian } from "../../lib/geo/geoUtils";

type Props = {
  radius: number;
};

type RegionVisual = {
  lat: number;
  lon: number;
  color: string;
  scale: number;
};

function getRegionVisual(regionName: string): RegionVisual {
  const map: Record<string, RegionVisual> = {
    Pakistan: { lat: 30, lon: 69, color: "#f1f6ff", scale: 1 },
    Germany: { lat: 51, lon: 10, color: "#f1f6ff", scale: 1 },
    USA: { lat: 39, lon: -98, color: "#f1f6ff", scale: 1 },
    "United States": { lat: 39, lon: -98, color: "#f1f6ff", scale: 1 },
    Europe: { lat: 54, lon: 15, color: "#f1f6ff", scale: 1 },
    Global: { lat: 0, lon: 0, color: "#b9d8ff", scale: 1.4 },
  };

  return map[regionName] ?? { lat: 20, lon: 20, color: "#f1f6ff", scale: 1 };
}

export function RegionOverlay({ radius }: Props) {
  const selectedRegion = useSceneStore((s) => s.selectedRegion);

  const region = useMemo(() => {
    if (!selectedRegion) return null;
    return getRegionVisual(selectedRegion.name);
  }, [selectedRegion]);

  if (!region) return null;

  const [x, y, z] = sphericalToCartesian(radius, region.lat, region.lon);

  return (
    <group position={[x, y, z]}>
      <mesh>
        <sphereGeometry args={[0.06 * region.scale, 20, 20]} />
        <meshBasicMaterial color={new THREE.Color(region.color)} transparent opacity={0.92} />
      </mesh>

      <mesh>
        <sphereGeometry args={[0.12 * region.scale, 20, 20]} />
        <meshBasicMaterial color={new THREE.Color("#7dc6ff")} transparent opacity={0.14} />
      </mesh>
    </group>
  );
}

