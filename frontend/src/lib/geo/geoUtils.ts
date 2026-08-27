import { Vector3 } from "three";

export function latLonToVec3(latDeg: number, lonDeg: number, radius: number) {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;
  const x = radius * Math.cos(lat) * Math.sin(lon);
  const y = radius * Math.sin(lat);
  const z = radius * Math.cos(lat) * Math.cos(lon);
  return new Vector3(x, y, z);
}

export function vec3ToLatLon(v: Vector3) {
  const r = Math.max(1e-6, v.length());
  const lat = Math.asin(v.y / r);
  const lon = Math.atan2(v.x, v.z);
  return { latDeg: (lat * 180) / Math.PI, lonDeg: (lon * 180) / Math.PI };
}

// New v1 helpers for a more “digital-earth” dots distribution and simple ROI work.
export function sphericalToCartesian(
  radius: number,
  latDeg: number,
  lonDeg: number,
): [number, number, number] {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;

  const x = radius * Math.cos(lat) * Math.sin(lon);
  const y = radius * Math.sin(lat);
  const z = radius * Math.cos(lat) * Math.cos(lon);

  return [x, y, z];
}

export function isApproxLand(lat: number, lon: number): boolean {
  const zones = [
    { latMin: -35, latMax: 37, lonMin: -20, lonMax: 55 }, // Africa + Europe part
    { latMin: 5, latMax: 55, lonMin: 55, lonMax: 150 }, // Asia
    { latMin: 15, latMax: 72, lonMin: -170, lonMax: -50 }, // North America
    { latMin: -55, latMax: 12, lonMin: -85, lonMax: -35 }, // South America
    { latMin: -45, latMax: -10, lonMin: 110, lonMax: 180 }, // Australia
    { latMin: 58, latMax: 84, lonMin: -75, lonMax: -10 }, // Greenland
  ];

  return zones.some(
    (z) => lat >= z.latMin && lat <= z.latMax && lon >= z.lonMin && lon <= z.lonMax,
  );
}
