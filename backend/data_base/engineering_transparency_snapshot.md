# Engineering Transparency Snapshot (Prompt 7.6)

Generated on: 2026-04-29

Evidence sources inspected:
- `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`
- `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`
- `backend/data_base/Navigation/MASTER_Navigation.json`
- `backend/data_base/payload_compatibility_rules.json`
- `backend/data_base/final_engineering_fidelity_report.md`

This snapshot reconstructs Prompt 7.6 changes by comparing current databases against the pre-7.6 inference/compatibility rules documented in `backend/data_base/engineering_inference_rules.md`.

## SECTION A - Exact Patched payload_id Log (by patch type)

### A1) Bus sizing upward patches

Total: 39

- `IOT-DEF-CI-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.625 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-CI-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.25 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-CI-003`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.875 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-CI-004`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.45 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-EAS-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-EAS-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-EAS-003`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-EAS-004`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-SIG-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.5 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-SIG-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.125 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-SIG-003`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.75 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-DEF-SIG-004`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.3 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-EDGE-GPU-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `IOT-EDGE-GPU-003`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-LWIR-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.75 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-LWIR-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.5 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-LWIR-003`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.0 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-LWIR-004`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.625 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-LWIR-005`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.25 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-NIR-004`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-NIR-005`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-PAN-004`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.25 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-PAN-005`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-VIS-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-VIS-005`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.5 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-VIS-006`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-VIS-007`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-VIS-008`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-VIS-009`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-EO-VIS-010`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SCI-ATM-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SCI-ATM-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SCI-OPSPEC-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SCI-OPSPEC-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SCI-OPSPEC-003`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SCI-UVSPEC-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.5 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SCI-UVSPEC-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 5.0 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SPC-HED-001`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)
- `RS-SPC-HED-002`: `recommended_bus_min_u` 3 -> 6, `recommended_bus_min_mass_kg` 4.2 -> 8.4 (Downlink burden guardrail: required_downlink_class=high drove minimum bus size increase for comms/EPS practicality.)

### A2) Bus sizing downward patches

Total: 4

- `NAV-RF-BEACON-001`: `recommended_bus_min_u` 6 -> 3, `recommended_bus_min_mass_kg` 8.4 -> 4.2 (Beacon/externally mounted but low-burden payload: reduced bus size to avoid structurally over-constraining solver.)
- `NAV-RF-BEACON-002`: `recommended_bus_min_u` 6 -> 3, `recommended_bus_min_mass_kg` 8.4 -> 4.2 (Beacon/externally mounted but low-burden payload: reduced bus size to avoid structurally over-constraining solver.)
- `NAV-RF-BEACON-003`: `recommended_bus_min_u` 6 -> 3, `recommended_bus_min_mass_kg` 8.4 -> 4.2 (Beacon/externally mounted but low-burden payload: reduced bus size to avoid structurally over-constraining solver.)
- `NAV-RF-BEACON-004`: `recommended_bus_min_u` 6 -> 3, `recommended_bus_min_mass_kg` 8.4 -> 4.2 (Beacon/externally mounted but low-burden payload: reduced bus size to avoid structurally over-constraining solver.)

### A3) radiation_sensitivity rebalances

Total: 92

- `IOT-COM-LCT-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-COM-LCT-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-COM-LCT-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-COM-LCT-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-COM-OL-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-COM-OL-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-COM-OL-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-COM-OL-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-CI-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-CI-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-CI-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-CI-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-EAS-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-EAS-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-EAS-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-EAS-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-SIG-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-SIG-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-SIG-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `IOT-DEF-SIG-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-BEACON-001`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-BEACON-002`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-BEACON-003`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-BEACON-004`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-TIME-001`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-TIME-002`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-TIME-003`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `NAV-RF-TIME-004`: `radiation_sensitivity` medium -> low (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-DEF-MWIR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-DEF-MWIR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-DEF-MWIR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-DEF-UV-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-CSAR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-CSAR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-HSI-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-HSI-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-HSI-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-HSI-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-HSI-005`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LSAR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LSAR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LSAR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LWIR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LWIR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LWIR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LWIR-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-LWIR-005`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-MWIR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-MWIR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-MWIR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-MWIR-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-MWIR-005`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-NIR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-NIR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-NIR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-NIR-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-NIR-005`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-PAN-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-PAN-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-PAN-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-PAN-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-PAN-005`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-PSAR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-PSAR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-SWIR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-SWIR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-SWIR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-SWIR-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-SWIR-005`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-004`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-005`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-006`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-007`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-008`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-009`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-VIS-010`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-WXR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-WXR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-WXR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-XSAR-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-XSAR-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-EO-XSAR-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-SCI-ATM-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-SCI-ATM-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-SCI-OPSPEC-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-SCI-OPSPEC-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-SCI-OPSPEC-003`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-SCI-UVSPEC-001`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)
- `RS-SCI-UVSPEC-002`: `radiation_sensitivity` medium -> high (Radiation sensitivity made burden-sensitive (edge/compute/high-energy -> high; very low-power low-compute -> low; else medium).)

### A4) Other engineering field corrections

No other solver-facing engineering fields were changed in Prompt 7.6 beyond:
- `dimensions_mm` key standardization (`length_x/width_y/height_z` -> `length_mm/width_mm/height_mm`) for 198/198 payloads
- `dimension_convention` key standardization at the file root for all three masters

### A5) Compatibility map patches (driven by 7.6 payload changes)

Total payload_ids with compatibility diffs vs pre-7.6 derivation: 15

- `IOT-DEF-CI-001`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-DEF-CI-002`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-DEF-CI-003`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-DEF-CI-004`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-DEF-EAS-001`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-DEF-EAS-002`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-DEF-EAS-003`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-DEF-EAS-004`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-EDGE-GPU-002`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `IOT-EDGE-GPU-003`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `RS-SCI-ATM-001`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `RS-SCI-ATM-002`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `RS-SCI-OPSPEC-001`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `RS-SCI-OPSPEC-002`: structure_class_required MEDIUM->HIGH (Reason: structure class shifted after bus size plausibility patch)
- `RS-SCI-OPSPEC-003`: structure_class_required LOW->HIGH (Reason: structure class shifted after bus size plausibility patch)

## SECTION B - Before/After Class Distribution Tables (all 198 payloads)

### B1) Payload engineering class fields (mapped to LOW/MEDIUM/HIGH/EXTREME for comparability)

### cg_sensitivity_class

| Class | Before | After |
|---|---:|---:|
| LOW | 112 | 112 |
| MEDIUM | 37 | 37 |
| HIGH | 49 | 49 |
| EXTREME | 0 | 0 |

### compute_load_class

| Class | Before | After |
|---|---:|---:|
| LOW | 17 | 17 |
| MEDIUM | 70 | 70 |
| HIGH | 111 | 111 |
| EXTREME | 0 | 0 |

### required_downlink_class

| Class | Before | After |
|---|---:|---:|
| LOW | 12 | 12 |
| MEDIUM | 97 | 97 |
| HIGH | 81 | 81 |
| EXTREME | 8 | 8 |

### thermal_control_class

| Class | Before | After |
|---|---:|---:|
| LOW | 73 | 73 |
| MEDIUM | 73 | 73 |
| HIGH | 52 | 52 |
| EXTREME | 0 | 0 |

### radiation_sensitivity

| Class | Before | After |
|---|---:|---:|
| LOW | 0 | 8 |
| MEDIUM | 163 | 71 |
| HIGH | 35 | 119 |
| EXTREME | 0 | 0 |

### B2) Compatibility classes (already LOW/MEDIUM/HIGH/EXTREME)

### adcs_class_required

| Class | Before | After |
|---|---:|---:|
| LOW | 62 | 62 |
| MEDIUM | 50 | 50 |
| HIGH | 37 | 37 |
| EXTREME | 49 | 49 |

### comms_class_required

| Class | Before | After |
|---|---:|---:|
| LOW | 8 | 8 |
| MEDIUM | 101 | 101 |
| HIGH | 81 | 81 |
| EXTREME | 8 | 8 |

### eps_class_required

| Class | Before | After |
|---|---:|---:|
| LOW | 93 | 93 |
| MEDIUM | 61 | 61 |
| HIGH | 30 | 30 |
| EXTREME | 14 | 14 |

### thermal_class_required

| Class | Before | After |
|---|---:|---:|
| LOW | 73 | 73 |
| MEDIUM | 49 | 49 |
| HIGH | 27 | 27 |
| EXTREME | 49 | 49 |

### obc_class_required

| Class | Before | After |
|---|---:|---:|
| LOW | 5 | 5 |
| MEDIUM | 82 | 82 |
| HIGH | 91 | 91 |
| EXTREME | 20 | 20 |

### structure_class_required

| Class | Before | After |
|---|---:|---:|
| LOW | 53 | 52 |
| MEDIUM | 40 | 26 |
| HIGH | 73 | 88 |
| EXTREME | 32 | 32 |

### propulsion_need_class

| Class | Before | After |
|---|---:|---:|
| LOW | 148 | 148 |
| MEDIUM | 37 | 37 |
| HIGH | 13 | 13 |
| EXTREME | 0 | 0 |

## SECTION C - Five Representative Before/After Payload Case Studies

Case studies are selected to show different mission families and burden regimes, and to highlight where Prompt 7.6 changed solver semantics (bus sizing plausibility + radiation_sensitivity discrimination + standardized dimensions schema).

### RS-EO-VIS-001 - Remote Sensing | Optical Imaging | Visible Light Cameras

A. Key engineering fields before Prompt 7.6 (pre-7.6 inference rules):
- dimensions_mm keys: ['length_x', 'width_y', 'height_z']
- recommended_bus_min_u: 3
- recommended_bus_min_mass_kg: 4.2
- daily_data_generation_gb: 256.5 (required_downlink_class=high)
- radiation_sensitivity: medium
- integration_risk: high | trl: 6 | mission_value_score: 3

B. Patched engineering fields after Prompt 7.6 (current DB):
- dimensions_mm keys: ['length_mm', 'width_mm', 'height_mm']
- recommended_bus_min_u: 6
- recommended_bus_min_mass_kg: 8.4
- daily_data_generation_gb: 256.5 (required_downlink_class=high)
- radiation_sensitivity: high
- integration_risk: high | trl: 6 | mission_value_score: 3

C. Compatibility object before/after (pre-7.6 derivation vs current map):
- before: adcs=HIGH comms=HIGH eps=LOW thermal=LOW obc=HIGH structure=HIGH prop=LOW
- after:  adcs=HIGH comms=HIGH eps=LOW thermal=LOW obc=HIGH structure=HIGH prop=LOW

D. Why this improves mathematical sizing meaning:
- Bus sizing was raised to avoid an infeasible optimization choice (high downlink burden with an undersized bus), which directly improves comms/EPS/structure sizing realism.
- Radiation sensitivity was made burden-sensitive (compute/high-energy payloads drive rad-hard needs; low-power simple payloads can remain low), improving component-class discrimination in optimization.

### NAV-RF-BEACON-002 - Navigation | Navigation Beacons | Navigation Beacons

A. Key engineering fields before Prompt 7.6 (pre-7.6 inference rules):
- dimensions_mm keys: ['length_x', 'width_y', 'height_z']
- recommended_bus_min_u: 6
- recommended_bus_min_mass_kg: 8.4
- daily_data_generation_gb: 0.311 (required_downlink_class=low)
- radiation_sensitivity: medium
- integration_risk: high | trl: 7 | mission_value_score: 4

B. Patched engineering fields after Prompt 7.6 (current DB):
- dimensions_mm keys: ['length_mm', 'width_mm', 'height_mm']
- recommended_bus_min_u: 3
- recommended_bus_min_mass_kg: 4.2
- daily_data_generation_gb: 0.311 (required_downlink_class=low)
- radiation_sensitivity: low
- integration_risk: high | trl: 7 | mission_value_score: 4

C. Compatibility object before/after (pre-7.6 derivation vs current map):
- before: adcs=EXTREME comms=LOW eps=HIGH thermal=HIGH obc=MEDIUM structure=HIGH prop=LOW
- after:  adcs=EXTREME comms=LOW eps=HIGH thermal=HIGH obc=MEDIUM structure=HIGH prop=LOW

D. Why this improves mathematical sizing meaning:
- Bus sizing was reduced to prevent an external-mount heuristic from forcing an unrealistically large bus for a low-burden payload, improving solver freedom and trade realism.
- Radiation sensitivity was made burden-sensitive (compute/high-energy payloads drive rad-hard needs; low-power simple payloads can remain low), improving component-class discrimination in optimization.

### IOT-COM-LCT-003 - IoT / Communication | Optical Communication | Laser Communication Terminals

A. Key engineering fields before Prompt 7.6 (pre-7.6 inference rules):
- dimensions_mm keys: ['length_x', 'width_y', 'height_z']
- recommended_bus_min_u: 12
- recommended_bus_min_mass_kg: 16.8
- daily_data_generation_gb: 1080.0 (required_downlink_class=very_high)
- radiation_sensitivity: medium
- integration_risk: high | trl: 7 | mission_value_score: 3

B. Patched engineering fields after Prompt 7.6 (current DB):
- dimensions_mm keys: ['length_mm', 'width_mm', 'height_mm']
- recommended_bus_min_u: 12
- recommended_bus_min_mass_kg: 16.8
- daily_data_generation_gb: 1080.0 (required_downlink_class=very_high)
- radiation_sensitivity: high
- integration_risk: high | trl: 7 | mission_value_score: 3

C. Compatibility object before/after (pre-7.6 derivation vs current map):
- before: adcs=EXTREME comms=EXTREME eps=EXTREME thermal=HIGH obc=EXTREME structure=EXTREME prop=MEDIUM
- after:  adcs=EXTREME comms=EXTREME eps=EXTREME thermal=HIGH obc=EXTREME structure=EXTREME prop=MEDIUM

D. Why this improves mathematical sizing meaning:
- Dimension schema standardization removes schema ambiguity for structural sizing and packaging constraints (solver can consume length_mm/width_mm/height_mm directly).
- Radiation sensitivity was made burden-sensitive (compute/high-energy payloads drive rad-hard needs; low-power simple payloads can remain low), improving component-class discrimination in optimization.

### RS-SPC-OPT-004 - Remote Sensing | Telescopes | Optical Telescopes

A. Key engineering fields before Prompt 7.6 (pre-7.6 inference rules):
- dimensions_mm keys: ['length_x', 'width_y', 'height_z']
- recommended_bus_min_u: 6
- recommended_bus_min_mass_kg: 8.4
- daily_data_generation_gb: 22.68 (required_downlink_class=medium)
- radiation_sensitivity: medium
- integration_risk: high | trl: 7 | mission_value_score: 3

B. Patched engineering fields after Prompt 7.6 (current DB):
- dimensions_mm keys: ['length_mm', 'width_mm', 'height_mm']
- recommended_bus_min_u: 6
- recommended_bus_min_mass_kg: 8.4
- daily_data_generation_gb: 22.68 (required_downlink_class=medium)
- radiation_sensitivity: medium
- integration_risk: high | trl: 7 | mission_value_score: 3

C. Compatibility object before/after (pre-7.6 derivation vs current map):
- before: adcs=EXTREME comms=MEDIUM eps=LOW thermal=EXTREME obc=MEDIUM structure=HIGH prop=MEDIUM
- after:  adcs=EXTREME comms=MEDIUM eps=LOW thermal=EXTREME obc=MEDIUM structure=HIGH prop=MEDIUM

D. Why this improves mathematical sizing meaning:
- Dimension schema standardization removes schema ambiguity for structural sizing and packaging constraints (solver can consume length_mm/width_mm/height_mm directly).

### RS-EO-PSAR-001 - Remote Sensing | Synthetic Aperture Radar | P-Band SAR

A. Key engineering fields before Prompt 7.6 (pre-7.6 inference rules):
- dimensions_mm keys: ['length_x', 'width_y', 'height_z']
- recommended_bus_min_u: 27
- recommended_bus_min_mass_kg: 85.0
- daily_data_generation_gb: 907.2 (required_downlink_class=high)
- radiation_sensitivity: medium
- integration_risk: high | trl: 7 | mission_value_score: 4

B. Patched engineering fields after Prompt 7.6 (current DB):
- dimensions_mm keys: ['length_mm', 'width_mm', 'height_mm']
- recommended_bus_min_u: 27
- recommended_bus_min_mass_kg: 85.0
- daily_data_generation_gb: 907.2 (required_downlink_class=high)
- radiation_sensitivity: high
- integration_risk: high | trl: 7 | mission_value_score: 4

C. Compatibility object before/after (pre-7.6 derivation vs current map):
- before: adcs=EXTREME comms=HIGH eps=EXTREME thermal=EXTREME obc=EXTREME structure=EXTREME prop=HIGH
- after:  adcs=EXTREME comms=HIGH eps=EXTREME thermal=EXTREME obc=EXTREME structure=EXTREME prop=HIGH

D. Why this improves mathematical sizing meaning:
- Dimension schema standardization removes schema ambiguity for structural sizing and packaging constraints (solver can consume length_mm/width_mm/height_mm directly).
- Radiation sensitivity was made burden-sensitive (compute/high-energy payloads drive rad-hard needs; low-power simple payloads can remain low), improving component-class discrimination in optimization.

## SECTION D - Mock CP-SAT Ingest Sanity (semantic evidence)

Below are three payloads (one per mission family) showing exactly what a CP-SAT loader could read as discrete subsystem burdens after Prompt 7.6.

### RS-EO-VIS-001 - Remote Sensing | Optical Imaging | Visible Light Cameras

1) Burdens the solver can read:
- Bus burden: mass_kg=1.1, payload_envelope_u=1.5, recommended_bus_min_u=6, recommended_bus_min_mass_kg=8.4, structure_class_required=HIGH
- EPS burden: avg_power_w=2.5, peak_power_w=5.8, duty=25%, eclipse_required=False, battery_sensitivity=low, eps_class_required=LOW
- ADCS burden: pointing_requirement_deg=0.1, cg_sensitivity_class=medium, deployment_clearance_needed=True, adcs_class_required=HIGH
- Comms burden: nominal_data_rate_mbps=95, daily_data_generation_gb=256.5, required_downlink_class=high, comms_class_required=HIGH
- Thermal burden: heat_dissipation_fraction=0.9, thermal_control_class=passive, temperature_stability_requirement=medium, thermal_class_required=LOW
- OBC burden: compute_load_class=high, daily_data_generation_gb=256.5, latency_tolerance=delay_tolerant, obc_class_required=HIGH

2) Why this is optimization-meaningful now:
- These burdens are discrete and comparable across payloads (classes + normalized units), enabling integer decision variables for subsystem class selection.
- Prompt 7.6 removed a key ambiguity (dimension key naming) and corrected infeasible bus/downlink combinations, preventing solver choices that would be structurally/comms impossible.

### IOT-COM-LCT-003 - IoT / Communication | Optical Communication | Laser Communication Terminals

1) Burdens the solver can read:
- Bus burden: mass_kg=1.8, payload_envelope_u=2.0, recommended_bus_min_u=12, recommended_bus_min_mass_kg=16.8, structure_class_required=EXTREME
- EPS burden: avg_power_w=15.0, peak_power_w=24.0, duty=40%, eclipse_required=False, battery_sensitivity=high, eps_class_required=EXTREME
- ADCS burden: pointing_requirement_deg=0.004, cg_sensitivity_class=high, deployment_clearance_needed=True, adcs_class_required=EXTREME
- Comms burden: nominal_data_rate_mbps=2500, daily_data_generation_gb=1080.0, required_downlink_class=very_high, comms_class_required=EXTREME
- Thermal burden: heat_dissipation_fraction=0.85, thermal_control_class=active, temperature_stability_requirement=low, thermal_class_required=HIGH
- OBC burden: compute_load_class=high, daily_data_generation_gb=1080.0, latency_tolerance=near_real_time, obc_class_required=EXTREME

2) Why this is optimization-meaningful now:
- These burdens are discrete and comparable across payloads (classes + normalized units), enabling integer decision variables for subsystem class selection.
- Prompt 7.6 removed a key ambiguity (dimension key naming) and corrected infeasible bus/downlink combinations, preventing solver choices that would be structurally/comms impossible.

### NAV-RF-TIME-001 - Navigation | Timing Payloads | Timing Payloads

1) Burdens the solver can read:
- Bus burden: mass_kg=0.82, payload_envelope_u=0.5, recommended_bus_min_u=2, recommended_bus_min_mass_kg=2.8, structure_class_required=LOW
- EPS burden: avg_power_w=3.8, peak_power_w=5.5, duty=90%, eclipse_required=True, battery_sensitivity=high, eps_class_required=HIGH
- ADCS burden: pointing_requirement_deg=0.3, cg_sensitivity_class=low, deployment_clearance_needed=False, adcs_class_required=LOW
- Comms burden: nominal_data_rate_mbps=4, daily_data_generation_gb=0.389, required_downlink_class=low, comms_class_required=LOW
- Thermal burden: heat_dissipation_fraction=0.9, thermal_control_class=passive_plus, temperature_stability_requirement=high, thermal_class_required=HIGH
- OBC burden: compute_load_class=low, daily_data_generation_gb=0.389, latency_tolerance=real_time, obc_class_required=MEDIUM

2) Why this is optimization-meaningful now:
- These burdens are discrete and comparable across payloads (classes + normalized units), enabling integer decision variables for subsystem class selection.
- Prompt 7.6 removed a key ambiguity (dimension key naming) and corrected infeasible bus/downlink combinations, preventing solver choices that would be structurally/comms impossible.

## SECTION E - Final Statement

IS THE DATABASE NOW READY TO ENTER CP-SAT BACKEND IMPLEMENTATION?

- YES (for first-pass CP-SAT backend implementation), with the caveat that some fields remain modeled estimates (e.g., daily_data_generation_gb) and should be refined when mission/network assumptions are finalized.
