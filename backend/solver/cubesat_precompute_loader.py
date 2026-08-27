from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected dict JSON at {path}, got {type(obj).__name__}")
    return obj


@dataclass(frozen=True)
class PayloadPrecompute:
    payloads: dict[str, dict[str, Any]]
    assumptions_used: dict[str, Any]
    engineering_thresholds: dict[str, Any]


@dataclass(frozen=True)
class ObjectiveCoefficients:
    cost_proxy_tables: dict[str, dict[str, int]]
    risk_proxy_tables: dict[str, dict[str, int]]
    weights_percent: dict[str, int]
    normalization_scales: dict[str, Any]
    integer_objective: dict[str, Any]


def load_payload_precompute() -> PayloadPrecompute:
    root = _repo_root()
    path = root / "backend" / "solver_precompute" / "payload_precompute_constants.json"
    obj = _load_json(path)
    payloads = obj.get("payloads", {})
    if not isinstance(payloads, dict):
        raise ValueError("payload_precompute_constants.json: expected 'payloads' dict")
    return PayloadPrecompute(
        payloads=payloads,
        assumptions_used=obj.get("assumptions_used", {}),
        engineering_thresholds=obj.get("engineering_thresholds", {}),
    )


def load_objective_coefficients() -> ObjectiveCoefficients:
    root = _repo_root()
    path = root / "backend" / "solver_precompute" / "objective_function_coefficients.json"
    obj = _load_json(path)
    od = obj.get("objective_definition", {})
    if not isinstance(od, dict):
        raise ValueError(
            "objective_function_coefficients.json: expected 'objective_definition' dict"
        )

    rec = od.get("recommended_integer_objective", {})
    if not isinstance(rec, dict):
        raise ValueError(
            "objective_function_coefficients.json: missing recommended_integer_objective"
        )

    return ObjectiveCoefficients(
        cost_proxy_tables=obj.get("cost_proxy_tables", {}),
        risk_proxy_tables=obj.get("risk_proxy_tables", {}),
        weights_percent=od.get("weights_percent", {}),
        normalization_scales=rec.get("normalization_scales_in_scaled_units", {}),
        integer_objective=rec,
    )


@dataclass(frozen=True)
class CubeSatPrecompute:
    payload_precompute: PayloadPrecompute
    objective: ObjectiveCoefficients


def load_all_precompute() -> CubeSatPrecompute:
    payload_precompute = load_payload_precompute()
    objective = load_objective_coefficients()
    return CubeSatPrecompute(payload_precompute=payload_precompute, objective=objective)

