import { useEffect, useMemo, useRef } from "react";
import type { Group, Mesh, Vector3 } from "three";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

type OrbitPlaneInput = {
  tiltX: number;
  tiltZ: number;
  radiusOffset: number;
  speed: number;
  satelliteCount: number;
  phaseOffset?: number;
};

type Props = {
  earthRadius: number;
  totalSatellites?: number;
  orbitalPlanes?: number;
  satellitesPerPlane?: number;
  planes?: OrbitPlaneInput[];
  maxVisiblePlanes?: number;
};

type ResolvedPlane = {
  radius: number;
  tiltX: number;
  tiltZ: number;
  speed: number;
  satelliteCount: number;
  phaseOffset: number;
};

function buildOrbitPoints(radius: number, segments = 256) {
  const points: Vector3[] = [];

  for (let i = 0; i <= segments; i += 1) {
    const a = (i / segments) * Math.PI * 2;
    const x = Math.cos(a) * radius;
    const y = 0;
    const z = Math.sin(a) * radius;
    points.push(new THREE.Vector3(x, y, z));
  }

  return points;
}

function distributePlanes(
  earthRadius: number,
  orbitalPlanes: number,
  satellitesPerPlane: number,
  maxVisiblePlanes: number,
): ResolvedPlane[] {
  const visiblePlanes = Math.min(Math.max(orbitalPlanes, 1), maxVisiblePlanes);
  const planes: ResolvedPlane[] = [];

  for (let i = 0; i < visiblePlanes; i += 1) {
    const t = visiblePlanes === 1 ? 0.5 : i / visiblePlanes;

    const tiltX = -0.8 + t * 1.6;
    const tiltZ = (i / visiblePlanes) * Math.PI * 0.9;
    const radiusOffset = 0.08 + (i % 3) * 0.05;
    const speed = 0.38 + (i % 4) * 0.08;

    planes.push({
      radius: earthRadius + radiusOffset,
      tiltX,
      tiltZ,
      speed,
      satelliteCount: satellitesPerPlane,
      phaseOffset: (i / visiblePlanes) * Math.PI * 2,
    });
  }

  return planes;
}

function resolvePlanes({
  earthRadius,
  totalSatellites = 3,
  orbitalPlanes = 3,
  satellitesPerPlane,
  planes,
  maxVisiblePlanes = 6,
}: Props): ResolvedPlane[] {
  if (planes && planes.length > 0) {
    return planes.slice(0, maxVisiblePlanes).map((p, idx) => ({
      radius: earthRadius + p.radiusOffset,
      tiltX: p.tiltX,
      tiltZ: p.tiltZ,
      speed: p.speed,
      satelliteCount: Math.max(1, p.satelliteCount),
      phaseOffset: p.phaseOffset ?? idx * 0.8,
    }));
  }

  const safePlanes = Math.max(1, orbitalPlanes);
  const safeTotal = Math.max(1, totalSatellites);
  const derivedSatellitesPerPlane = satellitesPerPlane ?? Math.max(1, Math.ceil(safeTotal / safePlanes));

  return distributePlanes(earthRadius, safePlanes, derivedSatellitesPerPlane, maxVisiblePlanes);
}

function OrbitTrack({ radius, tiltX, tiltZ }: { radius: number; tiltX: number; tiltZ: number }) {
  const line = useMemo(() => {
    const points = buildOrbitPoints(radius, 256);
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({ color: new THREE.Color("#2f8df6"), transparent: true, opacity: 0.28 });
    const l = new THREE.Line(geometry, material);
    const g = new THREE.Group();
    g.rotation.set(tiltX, 0, tiltZ);
    g.add(l);
    return { g, l, geometry, material };
  }, [radius, tiltX, tiltZ]);

  useEffect(() => {
    return () => {
      line.geometry.dispose();
      line.material.dispose();
    };
  }, [line]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const opacity = 0.2 + ((Math.sin(t * 1.5 + radius * 3) + 1) / 2) * 0.18;
    const material = (line.l.material as THREE.LineBasicMaterial);
    material.opacity = opacity;
  });

  return <primitive object={line.g} />;
}

function OrbitSatelliteMarker({ plane, index }: { plane: ResolvedPlane; index: number }) {
  const markerRef = useRef<Mesh>(null);
  const haloRef = useRef<Mesh>(null);

  const basePhase = plane.phaseOffset + (index / plane.satelliteCount) * Math.PI * 2;

  useFrame((state) => {
    const marker = markerRef.current;
    const halo = haloRef.current;
    if (!marker || !halo) return;

    const t = state.clock.getElapsedTime() * plane.speed + basePhase;
    const x = Math.cos(t) * plane.radius;
    const y = 0;
    const z = Math.sin(t) * plane.radius;

    marker.position.set(x, y, z);
    halo.position.set(x, y, z);

    const pulse = 1 + 0.18 * Math.sin(state.clock.getElapsedTime() * 4 + index);
    halo.scale.setScalar(pulse);

    marker.parent?.rotation.set(plane.tiltX, 0, plane.tiltZ);
    halo.parent?.rotation.set(plane.tiltX, 0, plane.tiltZ);
  });

  return (
    <>
      <group>
        <mesh ref={haloRef}>
          <sphereGeometry args={[0.045, 16, 16]} />
          <meshBasicMaterial color="#7fc8ff" transparent opacity={0.12} depthWrite={false} />
        </mesh>
      </group>

      <group>
        <mesh ref={markerRef}>
          <sphereGeometry args={[0.016, 14, 14]} />
          <meshBasicMaterial color="#e5f4ff" />
        </mesh>
      </group>
    </>
  );
}

export function OrbitLayer({
  earthRadius,
  totalSatellites = 3,
  orbitalPlanes = 3,
  satellitesPerPlane,
  planes,
  maxVisiblePlanes = 6,
}: Props) {
  const rootRef = useRef<Group>(null);

  const resolvedPlanes = useMemo(
    () =>
      resolvePlanes({
        earthRadius,
        totalSatellites,
        orbitalPlanes,
        satellitesPerPlane,
        planes,
        maxVisiblePlanes,
      }),
    [earthRadius, totalSatellites, orbitalPlanes, satellitesPerPlane, planes, maxVisiblePlanes],
  );

  useFrame((_, delta) => {
    if (!rootRef.current) return;
    // Keep orbit layer attached to earth and gently alive
    rootRef.current.rotation.y += delta * 0.02;
  });

  return (
    <group ref={rootRef}>
      {resolvedPlanes.map((plane, planeIdx) => (
        <group key={`plane-${planeIdx}`}>
          <OrbitTrack radius={plane.radius} tiltX={plane.tiltX} tiltZ={plane.tiltZ} />

          {Array.from({ length: plane.satelliteCount }).map((_, satIdx) => (
            <OrbitSatelliteMarker key={`plane-${planeIdx}-sat-${satIdx}`} plane={plane} index={satIdx} />
          ))}
        </group>
      ))}
    </group>
  );
}
