import { forwardRef, useLayoutEffect, useMemo } from 'react';
import { useGLTF } from '@react-three/drei';
import type { Group, Material, Mesh, Object3D } from 'three';
import { useSceneStore } from '../../store/sceneStore';
import * as THREE from 'three';

const NASA_CUBESAT_1RU_GLB_URL = '/assets/models/nasa-cubesat-1ru-generic.glb';

function PayloadModule() {
  const payloadType = useSceneStore((s) => s.payloadType);

  switch (payloadType) {
    case 'hyperspectral':
      return (
        <mesh position={[0, 0, -0.45]}>
          <cylinderGeometry args={[0.16, 0.16, 0.35, 24]} />
          <meshStandardMaterial color="#0e1824" emissive="#1ea7ff" emissiveIntensity={0.7} />
        </mesh>
      );

    case 'sar':
      return (
        <mesh position={[0, -0.15, -0.5]}>
          <coneGeometry args={[0.28, 0.35, 24, 1, true]} />
          <meshStandardMaterial color="#0e1824" emissive="#1ea7ff" emissiveIntensity={0.6} />
        </mesh>
      );

    case 'thermal':
      return (
        <mesh position={[0, 0, -0.42]}>
          <boxGeometry args={[0.25, 0.18, 0.18]} />
          <meshStandardMaterial color="#111826" emissive="#18a2ff" emissiveIntensity={0.5} />
        </mesh>
      );

    default:
      return (
        <mesh position={[0, 0, -0.42]}>
          <boxGeometry args={[0.22, 0.22, 0.16]} />
          <meshStandardMaterial color="#111826" emissive="#18a2ff" emissiveIntensity={0.4} />
        </mesh>
      );
  }
}

function tweakMaterial(m: Material) {
  const mat = m as any;
  if (mat && typeof mat === 'object') {
    if ('roughness' in mat) mat.roughness = Math.min(1, Math.max(0, 0.9));
    if ('metalness' in mat) mat.metalness = Math.min(1, Math.max(0, 0.1));
  }
}

function NasaCubesatBus({ targetMaxDim = 0.9 }: { targetMaxDim?: number }) {
  const gltf = useGLTF(NASA_CUBESAT_1RU_GLB_URL) as any;

  // Clone to keep per-instance transforms safe even with GLTF cache.
  const model = useMemo(() => gltf.scene.clone(true), [gltf.scene]);

  useLayoutEffect(() => {
    // Normalize the model so it behaves consistently with our scene poses.
    const box = new THREE.Box3().setFromObject(model);
    const size = new THREE.Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z, 1e-6);
    const scale = targetMaxDim / maxDim;
    model.scale.setScalar(scale);

    // Recompute after scaling, then center at origin.
    box.setFromObject(model);
    const center = new THREE.Vector3();
    box.getCenter(center);
    model.position.sub(center);

    // Small material tweak to match our premium dark-space palette.
    model.traverse((obj: Object3D) => {
      const o = obj as any;
      if (!o.isMesh) return;
      const mesh = o as Mesh;
      const mat = mesh.material as any;
      if (Array.isArray(mat)) mat.forEach(tweakMaterial);
      else if (mat) tweakMaterial(mat);
    });
  }, [model, targetMaxDim]);

  return <primitive object={model} />;
}

function SolarPanels() {
  // Keep a subtle, premium hero silhouette even with a 1U body model.
  return (
    <>
      <mesh position={[-0.95, 0, 0]}>
        <boxGeometry args={[1.1, 0.06, 0.4]} />
        <meshStandardMaterial color="#0d2d52" emissive="#1d8fff" emissiveIntensity={0.35} />
      </mesh>

      <mesh position={[0.95, 0, 0]}>
        <boxGeometry args={[1.1, 0.06, 0.4]} />
        <meshStandardMaterial color="#0d2d52" emissive="#1d8fff" emissiveIntensity={0.35} />
      </mesh>
    </>
  );
}

export const SatelliteHero = forwardRef<Group>(function SatelliteHero(_, ref) {
  return (
    <group ref={ref}>
      <NasaCubesatBus targetMaxDim={0.85} />
      <SolarPanels />

      <PayloadModule />
    </group>
  );
});

useGLTF.preload(NASA_CUBESAT_1RU_GLB_URL);
