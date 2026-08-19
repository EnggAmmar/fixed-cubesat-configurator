import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import { SceneDirector } from "./SceneDirector";
import { CursorGlow } from "./effects/CursorGlow";
import { Starfield } from "./background/Starfield";
import { DeepSpaceBackdrop } from "./background/DeepSpaceBackdrop";
import { SceneErrorBoundary } from "./SceneErrorBoundary";
import { SceneControls } from "./controls/SceneControls";

export function SceneCanvas() {
  const isAutomation = typeof navigator !== "undefined" && Boolean((navigator as any).webdriver);
  return (
    <div className="scene-root sceneLayer" aria-hidden>
      <SceneErrorBoundary fallback={null}>
        <Canvas
          frameloop={isAutomation ? "demand" : "always"}
          camera={{ position: [0, 0.3, 7], fov: 35 }}
          gl={{ antialias: true, alpha: true }}
          dpr={[1, 2]}
        >
          <color attach="background" args={["#02060d"]} />
          <fog attach="fog" args={["#02060d", 10, 38]} />

          <ambientLight intensity={0.3} />
          <directionalLight position={[5, 3, 5]} intensity={1.15} color="#7ac6ff" />
          <pointLight position={[-6, 2, 4]} intensity={0.45} color="#2e8bff" />

          <Suspense fallback={null}>
          <DeepSpaceBackdrop />
          <Starfield />
          <SceneDirector />
          <SceneControls />
        </Suspense>
      </Canvas>
    </SceneErrorBoundary>

      <CursorGlow />
    </div>
  );
}

export default SceneCanvas;
