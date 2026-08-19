import { OrbitControls } from '@react-three/drei';
import { useEffect, useMemo, useRef } from 'react';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { Vector3 } from 'three';
import { useSceneStore } from '../../store/sceneStore';
import { registerSceneControls } from './controlsRegistry';

function getDefaultTarget(step: string) {
  void step;
  return new Vector3(0, 0, 0);
}

export function SceneControls() {
  const step = useSceneStore((s) => s.step);
  const setEarthAutoRotate = useSceneStore((s) => s.setEarthAutoRotate);
  const earthFocused = useSceneStore((s) => s.earthFocused);
  const selectedRegion = useSceneStore((s) => s.selectedRegion);

  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const resumeEarthRotateRef = useRef<boolean>(false);

  useEffect(() => {
    registerSceneControls(controlsRef.current);
    return () => registerSceneControls(null);
  }, []);

  const cfg = useMemo(() => {
    const isROI = step === 'roi';
    const isPayload = step === 'payloadSelection';
    const isMission = step === 'missionType';
    const isResults = step === 'results';
    const isMissionParams = step === 'missionParameters';

    let minDistance = 4.4;
    let maxDistance = 8.5;
    let rotateSpeed = 0.45;
    let zoomSpeed = 0.7;
    let minPolarAngle = Math.PI / 2 - 0.7;
    let maxPolarAngle = Math.PI / 2 + 0.7;

    if (isMission) {
      minDistance = 5.0;
      maxDistance = 8.5;
      rotateSpeed = 0.38;
      zoomSpeed = 0.55;
      minPolarAngle = Math.PI / 2 - 0.45;
      maxPolarAngle = Math.PI / 2 + 0.45;
    }

    if (isPayload) {
      minDistance = 4.2;
      maxDistance = 7.4;
      rotateSpeed = 0.5;
      zoomSpeed = 0.75;
      minPolarAngle = Math.PI / 2 - 0.55;
      maxPolarAngle = Math.PI / 2 + 0.55;
    }

    if (isROI) {
      minDistance = 2.5;
      maxDistance = 6.5;
      rotateSpeed = 0.7;
      zoomSpeed = 0.85;
      minPolarAngle = 0.25;
      maxPolarAngle = Math.PI - 0.25;
    }

    if (isMissionParams) {
      minDistance = 3.8;
      maxDistance = 7.0;
      rotateSpeed = 0.45;
      zoomSpeed = 0.7;
      minPolarAngle = Math.PI / 2 - 0.6;
      maxPolarAngle = Math.PI / 2 + 0.6;
    }

    if (isResults) {
      minDistance = 4.0;
      maxDistance = 8.0;
      rotateSpeed = 0.5;
      zoomSpeed = 0.7;
      minPolarAngle = Math.PI / 2 - 0.7;
      maxPolarAngle = Math.PI / 2 + 0.7;
    }

    return {
      isROI,
      minDistance,
      maxDistance,
      rotateSpeed,
      zoomSpeed,
      minPolarAngle,
      maxPolarAngle,
    };
  }, [step]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    controls.target.copy(getDefaultTarget(step));
    controls.update();
  }, [step]);

  return (
    <OrbitControls
      ref={(c) => {
        controlsRef.current = c as unknown as OrbitControlsImpl | null;
      }}
      enableRotate
      enableZoom
      enablePan={false}
      enableDamping
      dampingFactor={0.08}
      rotateSpeed={cfg.rotateSpeed}
      zoomSpeed={cfg.zoomSpeed}
      minDistance={cfg.minDistance}
      maxDistance={cfg.maxDistance}
      minPolarAngle={cfg.minPolarAngle}
      maxPolarAngle={cfg.maxPolarAngle}
      screenSpacePanning={false}
      onStart={() => {
        if (!cfg.isROI) return;
        // Pause earth auto-rotation while user is interacting (but don't override focus).
        if (!earthFocused && !selectedRegion) {
          resumeEarthRotateRef.current = true;
          setEarthAutoRotate(false);
        }
      }}
      onEnd={() => {
        if (!cfg.isROI) return;
        if (resumeEarthRotateRef.current) {
          resumeEarthRotateRef.current = false;
          setEarthAutoRotate(true);
        }
      }}
    />
  );
}

export default SceneControls;
