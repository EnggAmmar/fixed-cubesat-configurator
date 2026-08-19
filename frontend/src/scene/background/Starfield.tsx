import { useMemo, useRef } from "react";
import type { Points } from "three";
import { useFrame, useThree } from "@react-three/fiber";

function createStars(count: number, radius: number) {
  const pts: number[] = [];

  for (let i = 0; i < count; i += 1) {
    const r = radius * (0.7 + Math.random() * 0.3);
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);

    const x = r * Math.sin(phi) * Math.cos(theta);
    const y = r * Math.cos(phi);
    const z = r * Math.sin(phi) * Math.sin(theta);

    pts.push(x, y, z);
  }

  return new Float32Array(pts);
}

export function Starfield() {
  const rootRef = useRef<Points>(null);
  const { camera } = useThree();

  const far = useMemo(() => createStars(1800, 28), []);
  const mid = useMemo(() => createStars(1000, 18), []);
  const near = useMemo(() => createStars(450, 12), []);

  useFrame((state, delta) => {
    if (!rootRef.current) return;

    rootRef.current.rotation.y += delta * 0.0025;
    rootRef.current.rotation.x += delta * 0.0008;

    rootRef.current.position.x = camera.position.x * 0.025;
    rootRef.current.position.y = camera.position.y * 0.025;

    const mat = rootRef.current.material as any;
    if (mat) {
      mat.opacity = 0.82 + Math.sin(state.clock.getElapsedTime() * 1.8) * 0.08;
    }
  });

  return (
    <group>
      <points ref={rootRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={far.length / 3}
            array={far}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial size={0.022} color="#ffffff" transparent opacity={0.86} depthWrite={false} />
      </points>

      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={mid.length / 3}
            array={mid}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial size={0.03} color="#eef6ff" transparent opacity={0.75} depthWrite={false} />
      </points>

      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={near.length / 3}
            array={near}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial size={0.04} color="#ffffff" transparent opacity={0.58} depthWrite={false} />
      </points>
    </group>
  );
}

