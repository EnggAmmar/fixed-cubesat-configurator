# Solver Readiness Report

Generated on: 2026-04-29

## Scope

- `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`
- `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`
- `backend/data_base/Navigation/MASTER_Navigation.json`
- `backend/data_base/global_engineering_assumptions.json`
- `backend/data_base/payload_compatibility_rules.json`

Validation checks performed:
1. JSON syntax parseability
2. Presence of all solver-facing engineering fields
3. Null-handling consistency for newly added fields
4. Duplicate payload_id detection across mission databases
5. Coverage: payload_compatibility_rules has an entry for every payload_id
6. Hierarchy integrity (root -> variants -> products)
7. Solver ingest risks (type variability, nullable numeric fields)

## Summary Metrics

- Total variants: 58
- Total products: 198
- payload_id total: 198
- payload_id unique: 198

## Readiness Score

- Score: 86 / 100

Scoring basis (simple heuristic):
- Start at 100
- Hard issues: -10 each (capped)
- Warnings: -2 each (capped)
- Ingest risks: -2 each (capped)

## Results By Check

### 1) Broken JSON Syntax
- PASS: all target JSON files parsed successfully.

### 2) Missing New Engineering Fields
- PASS: all products contain the full canonical product schema (base fields + solver-facing engineering fields).

### 3) Inconsistent Null Handling
- PASS: intended null-only fields remain null across all products:
  - `thermal_survival_heater_required`
  - `compression_ratio_assumed`
  - `onboard_storage_days`
- PASS: all inferred fields are non-null for all products.

### 4) Duplicate payload_id
- PASS: no duplicate payload IDs detected across the three master mission databases.

### 5) Missing Compatibility Metadata
- PASS: `payload_compatibility_rules.json` contains an entry for every mission payload_id (198/198).

### 6) Hierarchy Corruption
- PASS: mission file hierarchy is intact (root keys present; variants are arrays of objects; products are arrays of objects).

### 7) Solver Ingest Risks
- Non-blocking ingest risks detected (solver should normalize/handle these):
  - Field 'avg_power_w' mixes numeric types: ['float', 'int']
  - Field 'peak_power_w' mixes numeric types: ['float', 'int']
  - Field 'nominal_data_rate_mbps' mixes numeric types: ['float', 'int']
  - Field 'ground_resolution_m' mixes numeric types: ['float', 'int']
  - Field 'ground_resolution_m' is nullable (null_count=142); solver should treat null as N/A/unknown per domain
  - Field 'swath_km' mixes numeric types: ['float', 'int']
  - Field 'swath_km' is nullable (null_count=142); solver should treat null as N/A/unknown per domain

## Remaining Weaknesses / Recommendations

- Normalize numeric parsing to float internally for: `avg_power_w`, `peak_power_w`, `nominal_data_rate_mbps`, `ground_resolution_m`, `swath_km` (mixed int/float in JSON).
- Treat `ground_resolution_m` and `swath_km` nulls explicitly as domain-dependent N/A vs unknown; avoid assuming 0.
- Consider adding explicit solver semantics later for the still-null fields (`compression_ratio_assumed`, `onboard_storage_days`, `thermal_survival_heater_required`) once mission concepts constrain them.
- Consider future schema extension for product-level flattened classification fields if the solver needs product-only records without variant traversal.

## Can Backend Solver Coding Begin?

- YES
- No blocking validation issues were found. Proceed with solver implementation, with normalization safeguards for the ingest risks listed above.
