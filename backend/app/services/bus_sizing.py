from __future__ import annotations

import itertools
import json
from functools import lru_cache
from pathlib import Path

from app.schemas.bus_sizing import (
    BusCandidate,
    BusCandidateConstraints,
    BusCandidatesRequest,
    BusCandidatesResponse,
    StructureCatalog,
    StructureSize,
)
from app.services.catalog import get_catalog
from app.services.payload_resolver import resolve_payload_for_requirements
from app.services.units import occupied_u_from_cm3, volume_cm3_from_mm


def _structures_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "structures.json"


@lru_cache(maxsize=1)
def get_structure_catalog() -> StructureCatalog:
    raw = json.loads(_structures_path().read_text(encoding="utf-8"))
    return StructureCatalog.model_validate(raw)


def _payload_box_mm(req: BusCandidatesRequest) -> tuple[float, float, float]:
    payload = req.input.payload
    if payload.type == "my_payload":
        return (float(payload.length_mm), float(payload.width_mm), float(payload.height_mm))

    catalog = get_catalog()
    p = resolve_payload_for_requirements(payload.payload_id, catalog)
    if not p:
        raise ValueError(f"Unknown catalog payload_id: {payload.payload_id}")
    return (float(p.length_mm), float(p.width_mm), float(p.height_mm))


def _payload_volume_u(req: BusCandidatesRequest) -> float:
    a, b, c = _payload_box_mm(req)
    cm3 = volume_cm3_from_mm(a, b, c)
    return occupied_u_from_cm3(cm3)


def _envelope_fit(
    payload_mm: tuple[float, float, float],
    structure: StructureSize,
    clearance_mm: float,
) -> tuple[bool, dict[str, float] | None, list[str]]:
    reasons: list[str] = []
    px, py = structure.cross_section_mm
    pz = structure.max_length_mm

    inner_x = max(0.0, float(px) - 2 * clearance_mm)
    inner_y = max(0.0, float(py) - 2 * clearance_mm)
    inner_z = max(0.0, float(pz) - 2 * clearance_mm)

    reasons.append(
        f"Envelope: inner {inner_x:g}x{inner_y:g}x{inner_z:g} mm (clearance {clearance_mm:g} mm)."
    )

    best: dict[str, float] | None = None
    for a, b, c in set(itertools.permutations(payload_mm, 3)):
        if a <= inner_x and b <= inner_y and c <= inner_z:
            best = {"x_mm": a, "y_mm": b, "z_mm": c}
            break
        if b <= inner_x and a <= inner_y and c <= inner_z:
            best = {"x_mm": b, "y_mm": a, "z_mm": c}
            break

    if best is None:
        reasons.append(
            "Envelope fit: no orientation fits within internal cross-section and length."
        )
        return (False, None, reasons)

    reasons.append(
        f"Envelope fit: orientation {best['x_mm']:g}x{best['y_mm']:g}x{best['z_mm']:g} mm fits."
    )
    return (True, best, reasons)


def evaluate_bus_candidates(req: BusCandidatesRequest) -> BusCandidatesResponse:
    constraints = req.constraints or BusCandidateConstraints()
    catalog = get_structure_catalog()
    family = req.input.family

    # Reserve margin tuning by family (transparent v1 knobs)
    reserve_multiplier = (
        1.10
        if family.value == "remote_sensing"
        else 1.00
        if family.value == "iot_communication"
        else 1.05
    )
    integration_margin = 1.12 if family.value == "remote_sensing" else 1.08
    clearance_mm = 4.0

    payload_mm = _payload_box_mm(req)
    payload_occupied_u = _payload_volume_u(req)
    payload_with_margin_u = payload_occupied_u * integration_margin

    candidates: list[BusCandidate] = []
    for s in catalog.structures:
        if not constraints.include_commercial_sizes and not s.official:
            continue
        if constraints.max_bus_size_u is not None and s.size_u > constraints.max_bus_size_u:
            continue

        nominal_u = float(s.size_u)
        reserve_u = nominal_u * float(s.subsystem_reserve_fraction) * reserve_multiplier
        usable_payload_u = max(0.0, nominal_u - reserve_u)

        reasoning: list[str] = []
        reasoning.append(f"Nominal total volume: {nominal_u:g} U.")
        reasoning.append(
            "Subsystem reserve margin: "
            f"{s.subsystem_reserve_fraction:g} * "
            f"family_multiplier({reserve_multiplier:g}) => {reserve_u:g} U."
        )
        reasoning.append(f"Usable payload volume: {usable_payload_u:g} U.")

        reasoning.append(
            f"Payload occupied volume: {payload_occupied_u:g} U; "
            f"integration margin {integration_margin:g} => {payload_with_margin_u:g} U."
        )

        volume_fit = payload_with_margin_u <= usable_payload_u
        reasoning.append(f"Volume fit: {volume_fit}.")

        envelope_ok, orientation, env_reasons = _envelope_fit(payload_mm, s, clearance_mm)
        reasoning.extend(env_reasons)

        overall_fit = bool(volume_fit and envelope_ok)

        waste_u = max(0.0, usable_payload_u - payload_with_margin_u)
        # Fitness: prefer smaller buses that fit with less wasted usable payload volume.
        fitness = (
            10_000.0 - (nominal_u * 120.0) - (waste_u * 900.0)
            if overall_fit
            else 1_000.0 - nominal_u * 50.0
        )

        if orientation:
            reasoning.append(
                "Selected orientation (mm): "
                f"{orientation['x_mm']:g}x{orientation['y_mm']:g}x{orientation['z_mm']:g}."
            )

        if not overall_fit:
            if not envelope_ok:
                reasoning.append("Overall fit: failed envelope packaging.")
            elif not volume_fit:
                reasoning.append("Overall fit: failed usable payload volume.")
        else:
            reasoning.append(f"Overall fit: OK. Usable payload waste: {waste_u:g} U.")

        candidates.append(
            BusCandidate(
                size_u=float(s.size_u),
                label=s.label,
                official=s.official,
                nominal_total_volume_u=nominal_u,
                subsystem_reserve_margin_u=reserve_u,
                usable_payload_volume_u=usable_payload_u,
                payload_occupied_volume_u=payload_occupied_u,
                payload_volume_with_margin_u=payload_with_margin_u,
                envelope_fit=envelope_ok,
                volume_fit=volume_fit,
                overall_fit=overall_fit,
                fitness_score=float(fitness),
                reasoning=reasoning + list(s.notes),
            )
        )

    candidates.sort(
        key=lambda c: (
            not c.overall_fit,
            -c.fitness_score,
            c.size_u,
        )
    )

    return BusCandidatesResponse(mission_family=req.input.family, candidates=candidates)
