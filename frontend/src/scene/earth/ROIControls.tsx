import { OrbitControls } from "@react-three/drei";
import { useSceneStore } from "../../store/sceneStore";

export function ROIControls() {
  const enabled = useSceneStore((s) => s.roiInteractionEnabled);

  if (!enabled) return null;

  return (
    <OrbitControls
      enablePan={false}
      enableRotate
      enableZoom
      enableDamping
      dampingFactor={0.08}
      rotateSpeed={0.65}
      zoomSpeed={0.8}
      minDistance={2.4}
      maxDistance={6.2}
    />
  );
}
