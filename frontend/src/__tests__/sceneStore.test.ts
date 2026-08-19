import { describe, expect, it } from "vitest";
import { useSceneStore } from "../store/sceneStore";

describe("scene store", () => {
  it("toggles ROI interaction on roi step", () => {
    const { setStep } = useSceneStore.getState();
    setStep("missionType");
    expect(useSceneStore.getState().roiInteractionEnabled).toBe(false);
    setStep("roi");
    expect(useSceneStore.getState().roiInteractionEnabled).toBe(true);
    setStep("results");
    expect(useSceneStore.getState().roiInteractionEnabled).toBe(false);
  });
});
