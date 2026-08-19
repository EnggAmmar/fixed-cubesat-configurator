import * as THREE from "three";

export function DeepSpaceBackdrop() {
  return (
    <mesh>
      <sphereGeometry args={[20, 64, 64]} />
      <meshBasicMaterial side={THREE.BackSide} transparent opacity={0.12} color="#0b3d91" />
    </mesh>
  );
}
