from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    # backend/solver/<this_file>.py -> backend/solver -> backend -> repo_root
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected dict JSON at {path}, got {type(obj).__name__}")
    return obj


@dataclass(frozen=True)
class PayloadRecord:
    payload_id: str
    mission_family: str
    payload_group: str
    payload_type: str
    payload_variant: str
    product: dict[str, Any]
    source_file: str


@dataclass(frozen=True)
class CubeSatData:
    payloads: dict[str, PayloadRecord]
    compatibility: dict[str, dict[str, Any]]
    assumptions: dict[str, Any]

    bus_library: dict[str, dict[str, Any]]
    eps_library: dict[str, dict[str, Any]]
    adcs_library: dict[str, dict[str, Any]]
    comms_library: dict[str, dict[str, Any]]
    obc_library: dict[str, dict[str, Any]]
    thermal_library: dict[str, dict[str, Any]]
    propulsion_library: dict[str, dict[str, Any]]


def load_payload_catalog() -> dict[str, PayloadRecord]:
    root = _repo_root()
    mission_files = [
        root / "backend" / "data_base" / "Remote_Sensing" / "MASTER_Remote_Sensing.json",
        root / "backend" / "data_base" / "IoT_Comm" / "MASTER_IoT_Comm.json",
        root / "backend" / "data_base" / "Navigation" / "MASTER_Navigation.json",
    ]

    payloads: dict[str, PayloadRecord] = {}
    for path in mission_files:
        db = _load_json(path)
        mission_family = str(db.get("mission_family") or "")
        for variant in db.get("variants", []):
            if not isinstance(variant, dict):
                continue
            payload_group = str(variant.get("payload_group") or "")
            payload_type = str(variant.get("payload_type") or "")
            payload_variant = str(variant.get("payload_variant") or "")
            for prod in variant.get("products", []):
                if not isinstance(prod, dict):
                    continue
                pid = str(prod.get("payload_id") or "")
                if not pid:
                    raise ValueError(f"Missing payload_id in {path}")
                if pid in payloads:
                    raise ValueError(f"Duplicate payload_id detected across mission files: {pid}")
                payloads[pid] = PayloadRecord(
                    payload_id=pid,
                    mission_family=mission_family,
                    payload_group=payload_group,
                    payload_type=payload_type,
                    payload_variant=payload_variant,
                    product=prod,
                    source_file=str(path.as_posix()),
                )

    if not payloads:
        raise ValueError("No payloads loaded from master mission files.")
    return payloads


def load_compatibility_map() -> dict[str, dict[str, Any]]:
    root = _repo_root()
    path = root / "backend" / "data_base" / "payload_compatibility_rules.json"
    obj = _load_json(path)
    compat_list = obj.get("compatibility", [])
    if not isinstance(compat_list, list):
        raise ValueError("payload_compatibility_rules.json: expected 'compatibility' list.")

    m: dict[str, dict[str, Any]] = {}
    for entry in compat_list:
        if not isinstance(entry, dict):
            continue
        pid = str(entry.get("payload_id") or "")
        if not pid:
            raise ValueError("payload_compatibility_rules.json: entry missing payload_id")
        if pid in m:
            raise ValueError(f"payload_compatibility_rules.json: duplicate payload_id {pid}")
        m[pid] = entry
    return m


def load_global_assumptions() -> dict[str, Any]:
    root = _repo_root()
    path = root / "backend" / "data_base" / "global_engineering_assumptions.json"
    return _load_json(path)


def _index_library_by_key(
    lib_path: Path, list_key: str, key_field: str
) -> dict[str, dict[str, Any]]:
    obj = _load_json(lib_path)
    items = obj.get(list_key, [])
    if not isinstance(items, list):
        raise ValueError(f"{lib_path}: expected list at '{list_key}'")
    out: dict[str, dict[str, Any]] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        k = str(it.get(key_field) or "")
        if not k:
            raise ValueError(f"{lib_path}: item missing '{key_field}'")
        if k in out:
            raise ValueError(f"{lib_path}: duplicate key '{k}'")
        out[k] = it
    return out


def load_capacity_libraries() -> dict[str, dict[str, dict[str, Any]]]:
    root = _repo_root()
    libs = root / "backend" / "solver_libs"

    bus = _index_library_by_key(libs / "bus_capacity_library.json", "bus_classes", "bus_class")
    eps = _index_library_by_key(libs / "eps_capacity_library.json", "eps_tiers", "eps_tier")
    adcs = _index_library_by_key(libs / "adcs_capacity_library.json", "adcs_tiers", "adcs_tier")
    comms = _index_library_by_key(
        libs / "comms_capacity_library.json", "comms_tiers", "comms_tier"
    )
    obc = _index_library_by_key(libs / "obc_capacity_library.json", "obc_tiers", "obc_tier")
    thermal = _index_library_by_key(
        libs / "thermal_capacity_library.json", "thermal_tiers", "thermal_tier"
    )
    prop = _index_library_by_key(
        libs / "propulsion_capacity_library.json", "propulsion_tiers", "propulsion_tier"
    )

    return {
        "bus": bus,
        "eps": eps,
        "adcs": adcs,
        "comms": comms,
        "obc": obc,
        "thermal": thermal,
        "propulsion": prop,
    }


def load_all_data() -> CubeSatData:
    payloads = load_payload_catalog()
    compatibility = load_compatibility_map()
    assumptions = load_global_assumptions()
    libs = load_capacity_libraries()

    # Cross-check coverage (zero-trust).
    missing = [pid for pid in payloads.keys() if pid not in compatibility]
    if missing:
        raise ValueError(
            f"Compatibility map missing {len(missing)} payload_ids. Example: {missing[:5]}"
        )
    orphan = [pid for pid in compatibility.keys() if pid not in payloads]
    if orphan:
        raise ValueError(
            f"Compatibility map has {len(orphan)} orphan payload_ids. Example: {orphan[:5]}"
        )

    return CubeSatData(
        payloads=payloads,
        compatibility=compatibility,
        assumptions=assumptions,
        bus_library=libs["bus"],
        eps_library=libs["eps"],
        adcs_library=libs["adcs"],
        comms_library=libs["comms"],
        obc_library=libs["obc"],
        thermal_library=libs["thermal"],
        propulsion_library=libs["propulsion"],
    )
