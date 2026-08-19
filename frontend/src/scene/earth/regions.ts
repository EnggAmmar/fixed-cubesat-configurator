export type RegionDef = {
  id: string;
  name: string;
  // closed polygon [lat, lon] points (approximate bounding shapes)
  polygon?: Array<[number, number]>;
  centroid?: [number, number];
};

// v1 coarse regions only; later swap with real GeoJSON.
export const REGION_DEFS: Record<string, RegionDef> = {
  pakistan: {
    id: "pakistan",
    name: "Pakistan",
    polygon: [
      [37.1, 61.0],
      [37.1, 77.6],
      [23.5, 77.6],
      [23.5, 61.0],
      [37.1, 61.0],
    ],
    centroid: [30.3, 69.3],
  },
  europe: {
    id: "europe",
    name: "Europe",
    polygon: [
      [71.0, -10.0],
      [71.0, 40.0],
      [36.0, 40.0],
      [36.0, -10.0],
      [71.0, -10.0],
    ],
    centroid: [54.0, 15.0],
  },
  usa: {
    id: "usa",
    name: "United States",
    polygon: [
      [49.5, -125.0],
      [49.5, -66.5],
      [24.0, -66.5],
      [24.0, -125.0],
      [49.5, -125.0],
    ],
    centroid: [39.0, -98.0],
  },
};

export function matchRegionFromQuery(query: string | null) {
  if (!query) return null;
  const q = query.trim().toLowerCase();
  if (!q) return null;
  if (q.includes("pakistan") || q === "pk") return REGION_DEFS.pakistan;
  if (q.includes("europe") || q === "eu") return REGION_DEFS.europe;
  if (q.includes("usa") || q.includes("united states") || q === "us") return REGION_DEFS.usa;
  return null;
}

export function regionHitTest(latDeg: number, lonDeg: number) {
  for (const r of Object.values(REGION_DEFS)) {
    if (!r.polygon) continue;
    const lats = r.polygon.map((p) => p[0]);
    const lons = r.polygon.map((p) => p[1]);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    if (latDeg >= minLat && latDeg <= maxLat && lonDeg >= minLon && lonDeg <= maxLon) return r.id;
  }
  return null;
}

