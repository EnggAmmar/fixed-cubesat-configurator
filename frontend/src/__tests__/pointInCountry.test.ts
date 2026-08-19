import { describe, expect, it } from "vitest";
import { pointInGeometry } from "../lib/geo/pointInCountry";

describe("pointInGeometry", () => {
  it("detects point inside polygon and outside polygon", () => {
    const square = {
      type: "Polygon",
      coordinates: [
        [
          [0, 0],
          [10, 0],
          [10, 10],
          [0, 10],
          [0, 0],
        ],
      ],
    };

    expect(pointInGeometry([5, 5], square)).toBe(true);
    expect(pointInGeometry([-1, 5], square)).toBe(false);
  });

  it("respects holes in polygon", () => {
    const donut = {
      type: "Polygon",
      coordinates: [
        [
          [0, 0],
          [10, 0],
          [10, 10],
          [0, 10],
          [0, 0],
        ],
        [
          [4, 4],
          [6, 4],
          [6, 6],
          [4, 6],
          [4, 4],
        ],
      ],
    };

    expect(pointInGeometry([2, 2], donut)).toBe(true);
    expect(pointInGeometry([5, 5], donut)).toBe(false);
  });
});

