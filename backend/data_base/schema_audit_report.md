# Schema Audit Report - MASTER Payload Databases

Generated on: 2026-04-29

## Scope

Target files audited (read-only):

- `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`
- `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`
- `backend/data_base/Navigation/MASTER_Navigation.json`

Audit method:

- Inspected every `variants[].products[]` product object in each file.
- Enumerated all existing keys at top-level, variant-level, product-level, and within `dimensions_mm`.
- Checked for: missing/extra keys, naming inconsistencies, `null` handling differences, datatype mismatches, and key ordering mismatches.

## Inventory Summary

| File | mission_family | schema_version | Variants | Products |
|---|---|---:|---:|---:|
| `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json` | `Remote Sensing` | `ONE_V3_PAYLOAD_DB_2.1` | 35 | 104 |
| `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json` | `IoT / Communication` | `ONE_V3_PAYLOAD_DB_3.1` | 18 | 74 |
| `backend/data_base/Navigation/MASTER_Navigation.json` | `Navigation` | `ONE_V3_PAYLOAD_DB_4.0` | 5 | 20 |

---

## A) Common Fields Present In All Three Files

### A1) Top-Level (root JSON object)

Present in all three files:

- `mission_family` (string)
- `block` (string)
- `schema_version` (string)
- `dimension_convention` (object; documentation strings)
  - `length_x` (string)
  - `width_y` (string)
  - `height_z` (string)
- `variants` (array of variant objects)

### A2) Variant Objects (`variants[]`)

Each variant object contains:

- `payload_group` (string)
- `payload_type` (string)
- `payload_variant` (string)
- `products` (array of product objects)

### A3) Product Objects (`variants[].products[]`)

Every product object in all three files contains exactly these fields:

- `payload_id` (string)
- `vendor` (string)
- `product_name` (string)
- `mass_kg` (number)
- `dimensions_mm` (object)
  - `length_x` (number)
  - `width_y` (number)
  - `height_z` (number)
- `payload_envelope_u` (number)
- `mounting_face` (string)
- `avg_power_w` (number)
- `peak_power_w` (number)
- `nominal_data_rate_mbps` (number)
- `spectral_band` (string)
- `ground_resolution_m` (number or `null`)
- `swath_km` (number or `null`)
- `pointing_requirement_deg` (number)
- `estimated_cost_usd` (integer-number)

---

## B) Fields Inconsistently Present (Missing Keys / Extra Keys)

Result: **none found**.

- No product objects were missing any keys (all products across all three files share the same 15 product fields).
- No product objects contained additional unexpected keys.
- Variant objects are consistent across files (same 4 keys), with no missing or extra keys.

---

## C) Fields Missing For Solver-Readiness

No "hard missing" fields were found for a minimal payload-selection solver that only needs:
`mass_kg`, `dimensions_mm`, `avg_power_w`, `peak_power_w`, `nominal_data_rate_mbps`, and `estimated_cost_usd` (plus identifiers).

However, for practical solver-readiness (robust filtering/optimization without needing parent-context traversal or external lookups), these fields are currently **not present as product-level keys** and are commonly needed:

1. **Product self-containment (flattened classification)**
   - `mission_family` (currently only at file top-level)
   - `schema_version` (currently only at file top-level)
   - `payload_group` (currently only at variant-level)
   - `payload_type` (currently only at variant-level)
   - `payload_variant` (currently only at variant-level)

2. **Explicit applicability / "N/A vs unknown" signaling**
   - A field to disambiguate `null` meaning for `ground_resolution_m` and `swath_km` (e.g., `performance_applicability` or per-domain performance objects), so the solver can distinguish:
     - "not applicable for this payload class" vs
     - "unknown / missing data".

3. **Constraints that typically become solver inputs**
   - `mounting_constraints` / `mounting_interface` (current `mounting_face` is a start, but does not encode interfaces, keep-outs, deployables, etc.)
   - `data_interface` / `downlink_assumption` (to interpret `nominal_data_rate_mbps` consistently across mission families)

Note: Items (2) and (3) are "missing for robustness", not required for simply parsing the current databases.

---

## D) Recommended Canonical Field Ordering

### D1) Top-Level Key Order

Recommended (matches current ordering in all three files):

1. `mission_family`
2. `block`
3. `schema_version`
4. `dimension_convention`
5. `variants`

### D2) Variant Key Order

Recommended (matches current ordering in all three files):

1. `payload_group`
2. `payload_type`
3. `payload_variant`
4. `products`

### D3) Product Key Order

Recommended (matches current ordering in all three files):

1. `payload_id`
2. `vendor`
3. `product_name`
4. `mass_kg`
5. `dimensions_mm` (with keys ordered: `length_x`, `width_y`, `height_z`)
6. `payload_envelope_u`
7. `mounting_face`
8. `avg_power_w`
9. `peak_power_w`
10. `nominal_data_rate_mbps`
11. `spectral_band`
12. `ground_resolution_m`
13. `swath_km`
14. `pointing_requirement_deg`
15. `estimated_cost_usd`

---

## Observed Inconsistencies (Datatype / Null Handling)

Even though key presence and naming are consistent, a solver will still need to normalize or account for these:

1. **Datatype variability (`int` vs `float`)**
   - `avg_power_w` / `peak_power_w`:
     - `Remote_Sensing`: mix of integer and float values
     - `IoT_Comm`, `Navigation`: float values only
   - `nominal_data_rate_mbps`:
     - `Remote_Sensing`: integer values only
     - `IoT_Comm`: mostly integers, but some fractional Mbps values exist (e.g., quantum/low-rate entries)
     - `Navigation`: mixed integers and fractional values are common
   - `dimensions_mm.length_x/width_y/height_z`:
     - Mostly integers across all files, but at least one `Remote_Sensing` product uses decimal millimeter values.

2. **Null handling differences**
   - `ground_resolution_m` / `swath_km` are always present but `null` frequency differs by mission family:
     - `Remote_Sensing`: mix of numeric and `null`
     - `IoT_Comm`: always `null`
     - `Navigation`: always `null`

3. **Ordering mismatches**
   - None found (top-level, variant-level, product-level, and `dimensions_mm` key ordering are consistent within and across files).
