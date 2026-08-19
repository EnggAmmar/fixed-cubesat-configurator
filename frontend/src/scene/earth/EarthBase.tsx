import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Mesh } from "three";
import * as THREE from "three";

type Props = {
  radius: number;
};

export function EarthBase({ radius }: Props) {
  const ref = useRef<Mesh>(null);

  useFrame((_, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * 0.05;
  });

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[radius, 128, 128]} />
      <meshStandardMaterial
        color={new THREE.Color("#02070d")}
        emissive={new THREE.Color("#07182b")}
        emissiveIntensity={0.22}
        roughness={0.98}
        metalness={0.02}
      />
    </mesh>
  );
}

