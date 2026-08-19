import { useMemo } from "react";
import worldCountries from "../../data/world-countries.geo.json";
import { pointInGeometry } from "../../lib/geo/pointInCountry";
import { latLonToVector3 } from "../../lib/geo/globeProjection";

type Props = {
  radius: number;
};

type FeatureEntry = {
  geometry: any;
  bbox: { minLon: number; minLat: number; maxLon: number; maxLat: number };
};

function computeBBox(geometry: any): FeatureEntry["bbox"] | null {
  if (!geometry) return null;

  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  const visit = (pos: any) => {
    if (!Array.isArray(pos) || pos.length < 2) return;
    const lon = Number(pos[0]);
    const lat = Number(pos[1]);
    if (Number.isNaN(lon) || Number.isNaN(lat)) return;
    minLon = Math.min(minLon, lon);
    minLat = Math.min(minLat, lat);
    maxLon = Math.max(maxLon, lon);
    maxLat = Math.max(maxLat, lat);
  };

  const walk = (node: any) => {
    if (!Array.isArray(node)) return;
    if (typeof node[0] === "number" && typeof node[1] === "number") {
      visit(node);
      return;
    }
    for (const child of node) walk(child);
  };

  walk(geometry.coordinates);

  if (!Number.isFinite(minLon)) return null;
  return { minLon, minLat, maxLon, maxLat };
}

function inBBox(lon: number, lat: number, b: FeatureEntry["bbox"]) {
  return lon >= b.minLon && lon <= b.maxLon && lat >= b.minLat && lat <= b.maxLat;
}

export function EarthDots({ radius }: Props) {
  const positions = useMemo(() => {
    const pts: number[] = [];
    const featuresRaw = ((worldCountries as any).features ?? []) as Array<{ geometry?: any }>;

    const features: FeatureEntry[] = [];
    for (const f of featuresRaw) {
      const g = f.geometry;
      const bbox = computeBBox(g);
      if (!bbox) continue;
      features.push({ geometry: g, bbox });
    }

    // Dense land-dot distribution using point-in-polygon against country geometries.
    // Note: this is a v1 approach; later we can replace with a proper raster land mask for speed.
    for (let lat = -80; lat <= 80; lat += 1.8) {
      for (let lon = -180; lon <= 180; lon += 1.8) {
        const jitterLat = lat + (Math.random() - 0.5) * 0.5;
        const jitterLon = lon + (Math.random() - 0.5) * 0.5;

        let onLand = false;
        for (const f of features) {
          if (!inBBox(jitterLon, jitterLat, f.bbox)) continue;
          if (pointInGeometry([jitterLon, jitterLat], f.geometry)) {
            onLand = true;
            break;
          }
        }
        if (!onLand) continue;

        const v = latLonToVector3(radius, jitterLat, jitterLon);
        pts.push(v.x, v.y, v.z);
      }
    }

    return new Float32Array(pts);
  }, [radius]);

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.012}
        color="#ffffff"
        transparent
        opacity={1.0}
        depthWrite={false}
      />
    </points>
  );
}
