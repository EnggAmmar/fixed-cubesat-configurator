import * as THREE from "three";

type Props = {
  radius: number;
};

export function Atmosphere({ radius }: Props) {
  return (
    <mesh>
      <sphereGeometry args={[radius, 96, 96]} />
      <meshBasicMaterial
        color={new THREE.Color("#3fa7ff")}
        transparent
        opacity={0.1}
        side={THREE.BackSide}
        depthWrite={false}
      />
    </mesh>
  );
}

