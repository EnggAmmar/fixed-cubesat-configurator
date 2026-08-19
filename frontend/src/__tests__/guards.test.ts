import { describe, expect, it } from "vitest";
import { firstMissingStep } from "../lib/guards";

describe("wizard guards", () => {
  it("returns first missing step in order", () => {
    expect(firstMissingStep({})).toBe("/");
    expect(firstMissingStep({ family: "remote_sensing" })).toBe("/payload");
    expect(
      firstMissingStep({
        family: "remote_sensing",
        payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
      }),
    ).toBe("/roi");
    expect(
      firstMissingStep({
        family: "remote_sensing",
        payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
        roi: { type: "global" },
      }),
    ).toBe("/parameters");
    expect(
      firstMissingStep({
        family: "remote_sensing",
        payload: { type: "catalog", payload_id: "rs_vhr_optical_v1" },
        roi: { type: "global" },
        parameters: { revisit_time_hours: 24 },
      }),
    ).toBeNull();
  });
});

