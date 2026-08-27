import { render, screen } from "@testing-library/react";
import { test, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { MissionProvider } from "../state/mission";
import PayloadPage from "../pages/PayloadPage";
import * as api from "../lib/api";
import type { TaxonomyResponse } from "../lib/api";

function renderAtPayload() {
  return render(
    <MemoryRouter initialEntries={["/payload"]}>
      <MissionProvider>
        <Routes>
          <Route path="/payload" element={<PayloadPage />} />
          <Route path="/" element={<div>home</div>} />
        </Routes>
      </MissionProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.spyOn(api, "getTaxonomy").mockResolvedValue({
    version: "v1",
    families: [
      {
        family_id: "remote_sensing",
        label: "Remote Sensing",
        description: "EO",
        payload_categories: [
          {
            category_id: "vhr_optical",
            label: "VHR Optical",
            description: "desc",
            payloads: [{ payload_id: "rs_vhr_optical_v1", label: "VHR Optical (v1)" }],
          },
          {
            category_id: "my_payload",
            label: "My Payload",
            description: "manual",
            payloads: [],
          },
        ],
      },
      {
        family_id: "iot_communication",
        label: "IoT",
        description: "IoT",
        payload_categories: [
          {
            category_id: "iot_store_and_forward",
            label: "IoT Store-and-Forward",
            description: "desc",
            payloads: [{ payload_id: "IOT-COM-BPT-001", label: "Bent-Pipe Transponder (v1)" }],
          },
          {
            category_id: "broadband_rf_comms",
            label: "Broadband RF Comms",
            description: "desc",
            payloads: [{ payload_id: "IOT-COM-SDT-001", label: "SD Transponder (v1)" }],
          },
          {
            category_id: "optical_laser_comms",
            label: "Optical / Laser Comms",
            description: "desc",
            payloads: [{ payload_id: "IOT-COM-LCT-001", label: "Laser Terminal (v1)" }],
          },
          {
            category_id: "quantum_secure_comms",
            label: "Quantum Secure Comms",
            description: "desc",
            payloads: [{ payload_id: "IOT-COM-QC-001", label: "Quantum Comms (v1)" }],
          },
          {
            category_id: "my_payload",
            label: "My Payload",
            description: "manual",
            payloads: [],
          },
        ],
      },
      {
        family_id: "navigation",
        label: "Navigation",
        description: "Nav",
        payload_categories: [
          {
            category_id: "my_payload",
            label: "My Payload",
            description: "manual",
            payloads: [],
          },
        ],
      },
    ],
  } as unknown as TaxonomyResponse);
});

afterEach(() => {
  localStorage.clear();
});

test("valid localStorage family renders payload cards", async () => {
  localStorage.setItem("mission_draft_v1", JSON.stringify({ family: "remote_sensing" }));
  renderAtPayload();

  expect(await screen.findByRole("heading", { name: "Select Payload" })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: /VHR Optical/i })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: /My Payload/i })).toBeInTheDocument();
});

test("invalid localStorage family falls back and still renders payload cards", async () => {
  localStorage.setItem("mission_draft_v1", JSON.stringify({ family: "bad_family" }));
  renderAtPayload();

  expect(await screen.findByRole("button", { name: /VHR Optical/i })).toBeInTheDocument();
});

test("iot_communication family renders mapped payload cards enabled", async () => {
  localStorage.setItem("mission_draft_v1", JSON.stringify({ family: "iot_communication" }));
  renderAtPayload();

  expect(await screen.findByRole("heading", { name: "Select Payload" })).toBeInTheDocument();

  const sof = await screen.findByRole("button", { name: /IoT Store-and-Forward/i });
  const rf = await screen.findByRole("button", { name: /Broadband RF Comms/i });
  const optical = await screen.findByRole("button", { name: "Optical / Laser Comms" });
  const quantum = await screen.findByRole("button", { name: /Quantum Secure Comms/i });
  const myPayload = await screen.findByRole("button", { name: /My Payload/i });

  for (const b of [sof, rf, optical, quantum, myPayload]) {
    expect(b).not.toBeDisabled();
    expect(b).toHaveTextContent("Select");
  }
});

test("taxonomy fetch failure shows visible error message", async () => {
  vi.spyOn(api, "getTaxonomy").mockRejectedValueOnce(new Error("network down"));

  localStorage.setItem("mission_draft_v1", JSON.stringify({ family: "remote_sensing" }));
  renderAtPayload();

  expect(await screen.findByText(/Could not load payload taxonomy/i)).toBeInTheDocument();
});
