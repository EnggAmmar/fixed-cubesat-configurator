# Database Merge Validation Report

Generated on: 2026-04-27 01:59:53

## Scope

- Task: Database consolidation only (merge block files into 1 master JSON per mission family).
- Source files left untouched; only new MASTER JSON files and this report were created.

## IoT_Comm

Output: `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`

| Source file | Variants | Products | Payload IDs |
|---|---:|---:|---:|
| `backend/data_base/IoT_Comm/Block_A_pt1.json` | 4 | 17 | 17 |
| `backend/data_base/IoT_Comm/Block_A_pt2.json` | 5 | 20 | 20 |
| `backend/data_base/IoT_Comm/Block_B_pt1.json` | 3 | 12 | 12 |
| `backend/data_base/IoT_Comm/Block_B_pt2.json` | 3 | 13 | 13 |
| `backend/data_base/IoT_Comm/Block_C.json` | 3 | 12 | 12 |

- Mission family: `IoT / Communication`
- Schema versions seen: `ONE_V3_PAYLOAD_DB_3.1`, `ONE_V3_PAYLOAD_DB_3.1`, `ONE_V3_PAYLOAD_DB_3.1`
- MASTER schema_version used: `ONE_V3_PAYLOAD_DB_3.1`
- Final merged totals: variants=18, products=74, payload_ids=74 (unique=74)

- Duplicate payload_id detected: 0

- Validation:
  - Merged variant count equals exact sum of source variant counts.
  - Merged product count equals exact sum of source product counts.
  - No payload_id loss introduced by merge (payload_ids_total equals sum of per-source payload IDs).

## Navigation

Output: `backend/data_base/Navigation/MASTER_Navigation.json`

| Source file | Variants | Products | Payload IDs |
|---|---:|---:|---:|
| `backend/data_base/Navigation/Block_A.json` | 0 | 0 | 0 |
| `backend/data_base/Navigation/Block_B.json` | 0 | 0 | 0 |
| `backend/data_base/Navigation/Block_C.json` | 5 | 20 | 20 |

- Mission family: `Navigation`
- Schema versions seen: `ONE_V3_PAYLOAD_DB_4.0`
- MASTER schema_version used: `ONE_V3_PAYLOAD_DB_4.0`
- Final merged totals: variants=5, products=20, payload_ids=20 (unique=20)

- Duplicate payload_id detected: 0

- Validation:
  - Merged variant count equals exact sum of source variant counts.
  - Merged product count equals exact sum of source product counts.
  - No payload_id loss introduced by merge (payload_ids_total equals sum of per-source payload IDs).

## Remote_Sensing

Output: `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`

| Source file | Variants | Products | Payload IDs |
|---|---:|---:|---:|
| `backend/data_base/Remote_Sensing/Block_A_pt1.json` | 4 | 25 | 25 |
| `backend/data_base/Remote_Sensing/Block_A_pt2.json` | 5 | 20 | 20 |
| `backend/data_base/Remote_Sensing/Block_A_pt3.json` | 3 | 8 | 8 |
| `backend/data_base/Remote_Sensing/Block_B.json` | 8 | 18 | 18 |
| `backend/data_base/Remote_Sensing/Block_C.json` | 11 | 19 | 19 |
| `backend/data_base/Remote_Sensing/Block_D.json` | 2 | 8 | 8 |
| `backend/data_base/Remote_Sensing/Block_E.json` | 2 | 6 | 6 |

- Mission family: `Remote Sensing`
- Schema versions seen: `ONE_V3_PAYLOAD_DB_2.0`, `ONE_V3_PAYLOAD_DB_2.0`, `ONE_V3_PAYLOAD_DB_2.0`, `ONE_V3_PAYLOAD_DB_2.0`, `ONE_V3_PAYLOAD_DB_2.1`, `ONE_V3_PAYLOAD_DB_2.1`, `ONE_V3_PAYLOAD_DB_2.1`
- MASTER schema_version used: `ONE_V3_PAYLOAD_DB_2.1`
- Final merged totals: variants=35, products=104, payload_ids=104 (unique=104)

- Duplicate payload_id detected: 0

- Validation:
  - Merged variant count equals exact sum of source variant counts.
  - Merged product count equals exact sum of source product counts.
  - No payload_id loss introduced by merge (payload_ids_total equals sum of per-source payload IDs).

## Source File Notes

- `backend/data_base/Navigation/Block_A.json` and `backend/data_base/Navigation/Block_B.json` were empty (0 bytes), so they contributed 0 variants/products to the Navigation master.
- Some IoT_Comm block files contained non-strict JSON formatting (e.g., line comments and/or variants-array fragments without the root wrapper). The merge process parsed these without modifying the source files, and preserved all payload content verbatim in the MASTER output.

## Confirmation

- Source files were not edited or deleted.
- Only the following new files were created:
  - `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`
  - `backend/data_base/Navigation/MASTER_Navigation.json`
  - `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`
  - `backend/data_base/MERGE_VALIDATION_REPORT.md`

