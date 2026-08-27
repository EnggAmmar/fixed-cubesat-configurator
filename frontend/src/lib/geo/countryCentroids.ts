import type { Geometry, Position as GeoPosition } from "geojson";

type Position = [number, number];

function toPositions(ring: GeoPosition[]): Position[] {
  return ring.map((p): Position => [p[0], p[1]]);
}

function averagePositions(points: Position[]): Position {
  if (!points.length) return [0, 0];

  let lon = 0;
  let lat = 0;

  for (const [x, y] of points) {
    lon += x;
    lat += y;
  }

  return [lon / points.length, lat / points.length];
}

function polygonCentroid(ring: Position[]): Position {
  return averagePositions(ring);
}

function multiPolygonCentroid(polygons: Position[][][]): Position {
  const pts: Position[] = [];

  for (const poly of polygons) {
    if (poly[0]?.length) pts.push(polygonCentroid(poly[0]));
  }

  return averagePositions(pts);
}

export function featureCentroid(geometry: Geometry | null | undefined): Position {
  if (!geometry) return [0, 0];

  if (geometry.type === "Polygon") {
    return polygonCentroid(toPositions(geometry.coordinates[0] ?? []));
  }

  if (geometry.type === "MultiPolygon") {
    return multiPolygonCentroid(geometry.coordinates.map((poly) => poly.map(toPositions)));
  }

  return [0, 0];
}
