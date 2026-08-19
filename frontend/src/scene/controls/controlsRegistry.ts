import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

let controls: OrbitControlsImpl | null = null;

export function registerSceneControls(next: OrbitControlsImpl | null) {
  controls = next;
}

export function getSceneControls() {
  return controls;
}

