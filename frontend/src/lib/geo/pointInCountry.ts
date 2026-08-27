import type { Geometry, Position as GeoPosition } from "geojson";

type Position = [number, number]; // [lon, lat]

function toPositions(ring: GeoPosition[]): Position[] {
  return ring.map((p): Position => [p[0], p[1]]);
}

function pointInRing(point: Position, ring: Position[]): boolean {
  const [x, y] = point;
  let inside = false;

  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];

    const intersect =
      yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-12) + xi;

    if (intersect) inside = !inside;
  }

  return inside;
}

function pointInPolygon(point: Position, polygon: Position[][]): boolean {
  if (!polygon.length) return false;

  // outer ring must contain the point
  if (!pointInRing(point, polygon[0])) return false;

  // if point is inside any hole, reject it
  for (let i = 1; i < polygon.length; i += 1) {
    if (pointInRing(point, polygon[i])) return false;
  }

  return true;
}

export function pointInGeometry(point: Position, geometry: Geometry | null | undefined): boolean {
  if (!geometry) return false;

  if (geometry.type === "Polygon") {
    return pointInPolygon(point, geometry.coordinates.map(toPositions));
  }

  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .map((polygon) => polygon.map(toPositions))
      .some((polygon) => pointInPolygon(point, polygon));
  }

  return false;
}

