import { useEffect, useMemo } from "react";
import * as THREE from "three";
import worldCountries from "../../data/world-countries.geo.json";
import { useSceneStore } from "../../store/sceneStore";
import { ringToSpherePoints } from "../../lib/geo/globeProjection";

type Props = {
  radius: number;
};

type AnyFeature = {
  properties?: any;
  geometry?: any;
};

function getCode(props: any): string {
  return props.ISO_A3 ?? props.iso_a3 ?? "";
}

function sanitizeRing(ring: [number, number][]) {
  if (ring.length < 2) return ring;
  const a = ring[0];
  const b = ring[ring.length - 1];
  if (a[0] === b[0] && a[1] === b[1]) return ring.slice(0, -1);
  return ring;
}

function PolygonLine({
  ring,
  radius,
  glow = false,
}: {
  ring: [number, number][];
  radius: number;
  glow?: boolean;
}) {
  const line = useMemo(() => {
    const pts = ringToSpherePoints([...sanitizeRing(ring), ring[0]], radius);
    const geometry = new THREE.BufferGeometry().setFromPoints(pts);
    const material = new THREE.LineBasicMaterial({
      color: new THREE.Color(glow ? "#67cfff" : "#f3f8ff"),
      transparent: true,
      opacity: glow ? 0.25 : 0.95,
    });
    const l = new THREE.Line(geometry, material);
    l.frustumCulled = false;
    l.renderOrder = glow ? 10 : 11;
    return { l, geometry, material };
  }, [glow, ring, radius]);

  useEffect(() => {
    return () => {
      line.geometry.dispose();
      line.material.dispose();
    };
  }, [line]);

  return <primitive object={line.l} />;
}

export function CountryPolygonOverlay({ radius }: Props) {
  const step = useSceneStore((s) => s.step);
  const selectedRegion = useSceneStore((s) => s.selectedRegion);

  const feature = useMemo(() => {
    if (step !== "roi") return null;
    if (!selectedRegion?.id) return null;
    const id = selectedRegion.id.toUpperCase();
    const fc = worldCountries as any;
    return (fc.features as AnyFeature[]).find((f) => getCode(f.properties ?? {}).toUpperCase() === id) ?? null;
  }, [selectedRegion?.id, step]);

  if (!feature) return null;
  const geometry = (feature as AnyFeature).geometry;
  if (!geometry) return null;

  if (geometry.type === "Polygon") {
    const outerRing = geometry.coordinates[0] as [number, number][];
    return (
      <group>
        <PolygonLine ring={outerRing} radius={radius * 1.003} glow />
        <PolygonLine ring={outerRing} radius={radius} />
      </group>
    );
  }

  if (geometry.type === "MultiPolygon") {
    return (
      <group>
        {geometry.coordinates.map((poly: [number, number][][], idx: number) => (
          <group key={idx}>
            <PolygonLine ring={poly[0]} radius={radius * 1.003} glow />
            <PolygonLine ring={poly[0]} radius={radius} />
          </group>
        ))}
      </group>
    );
  }

  return null;
}
