import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { gsap } from "gsap";
import type { Group } from "three";
import { Vector3 } from "three";
import { useSceneStore } from "../store/sceneStore";
import type { ScenePose, SceneStep } from "../types/scene";
import { EarthSystem } from "./earth/EarthSystem";
import { getSceneControls } from "./controls/controlsRegistry";

function getPose(step: SceneStep): ScenePose {
  switch (step) {
    case "missionType":
      return {
        cameraPosition: [0, 0.4, 7],
        cameraTarget: [0, 0, 0],
        earthPosition: [0, 0, 0],
        earthScale: 1.2,
        satellitePosition: [0, 0, 0],
        satelliteRotation: [0, 0, 0],
        satelliteVisible: false,
      };
    case "payloadSelection":
      return {
        cameraPosition: [0, 0.2, 6.2],
        cameraTarget: [0, 0, 0],
        earthPosition: [0, 0, 0],
        earthScale: 1.05,
        satellitePosition: [0, 0, 0],
        satelliteRotation: [0, 0, 0],
        satelliteVisible: false,
      };
    case "roi":
      return {
        cameraPosition: [0, 0, 3.7],
        cameraTarget: [0, 0, 0],
        earthPosition: [0, 0, 0],
        earthScale: 1.5,
        satellitePosition: [0, 0, 0],
        satelliteRotation: [0, 0, 0],
        satelliteVisible: false,
      };
    case "missionParameters":
      return {
        cameraPosition: [0, 0.2, 5.2],
        cameraTarget: [0, 0, 0],
        earthPosition: [0, 0, 0],
        earthScale: 1.2,
        satellitePosition: [0, 0, 0],
        satelliteRotation: [0, 0, 0],
        satelliteVisible: false,
      };
    case "results":
      return {
        cameraPosition: [0, 0.1, 6.4],
        cameraTarget: [0, 0, 0],
        earthPosition: [0, 0, 0],
        earthScale: 1.1,
        satellitePosition: [0, 0, 0],
        satelliteRotation: [0, 0, 0],
        satelliteVisible: false,
      };
  }
}

export function SceneDirector() {
  const { camera } = useThree();
  const step = useSceneStore((s) => s.step);
  const earthRef = useRef<Group>(null);

  const pose = useMemo(() => getPose(step), [step]);

  useEffect(() => {
    const controls = getSceneControls();
    if (controls) {
      controls.target.set(pose.cameraTarget[0], pose.cameraTarget[1], pose.cameraTarget[2]);
      controls.update();
    } else {
      camera.lookAt(new Vector3(...pose.cameraTarget));
    }

    gsap.killTweensOf(camera.position);
    gsap.to(camera.position, {
      x: pose.cameraPosition[0],
      y: pose.cameraPosition[1],
      z: pose.cameraPosition[2],
      duration: 1.2,
      ease: "power3.inOut",
      onUpdate: () => controls?.update(),
      onComplete: () => controls?.update(),
    });
  }, [camera, pose]);

  useFrame(() => {
    if (earthRef.current) {
      earthRef.current.position.lerp(new Vector3(...pose.earthPosition), 0.08);
      earthRef.current.scale.lerp(new Vector3(pose.earthScale, pose.earthScale, pose.earthScale), 0.08);
    }
  });

  return (
    <>
      <EarthSystem ref={earthRef} />
      {/* Satellite temporarily hidden for centered-globe UX pass. */}
    </>
  );
}
