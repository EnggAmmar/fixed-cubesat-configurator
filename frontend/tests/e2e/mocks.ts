import type { Page } from "@playwright/test";

export const TAXONOMY_MOCK = {
  version: "v1",
  families: [
    {
      family_id: "remote_sensing",
      label: "Remote Sensing",
      description: "Earth observation missions (optical, hyperspectral, thermal, SAR).",
      payload_categories: [
        {
          category_id: "vhr_optical",
          label: "VHR Optical",
          description: "Very high resolution optical imaging payload.",
          payloads: [{ payload_id: "rs_vhr_optical_v1", label: "VHR Optical v1" }],
        },
        {
          category_id: "hyperspectral",
          label: "Hyperspectral",
          description: "Hyperspectral imaging payload.",
          payloads: [{ payload_id: "rs_hyperspec_v1", label: "Hyperspectral v1" }],
        },
        {
          category_id: "my_payload",
          label: "My Payload",
          description: "Confidential synthetic payload inputs.",
          payloads: [],
        },
      ],
    },
    {
      family_id: "iot_communication",
      label: "IoT / Communication",
      description: "Store-and-forward IoT and communications missions.",
      payload_categories: [
        {
          category_id: "my_payload",
          label: "My Payload",
          description: "Confidential synthetic payload inputs.",
          payloads: [],
        },
      ],
    },
    {
      family_id: "navigation",
      label: "Navigation",
      description: "Navigation-related missions and timing experiments.",
      payload_categories: [
        {
          category_id: "my_payload",
          label: "My Payload",
          description: "Confidential synthetic payload inputs.",
          payloads: [],
        },
      ],
    },
  ],
} as const;

export const SOLVE_MOCK = {
  constellation: { satellites: 2, planes: 2, orbit_type: "Sun-synchronous" },
  solution: {
    platform: { name: "8U Platform", bus_size_u: 8 },
    budgets: { total_cost_kusd: 600, total_mass_kg: 12.3 },
    subsystems: [
      { domain: "structure", name: "8U Platform" },
      { domain: "comm", name: "X-band Downlink" },
    ],
    warnings: ["Tight mass margin (< 0.5 kg)."],
  },
} as const;

export async function mockTaxonomy(page: Page) {
  await page.route("**/api/v1/taxonomy", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(TAXONOMY_MOCK),
    });
  });
}

export async function mockSolve(page: Page) {
  await page.route("**/api/v1/mission/solve", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SOLVE_MOCK),
    });
  });
}

