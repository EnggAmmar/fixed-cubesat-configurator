from __future__ import annotations

from app.schemas.radiation import RadClass, RadiationComponent, VerificationStatus
from app.schemas.radiation_screening import (
    RadiationFlag,
    RadiationMissionProfile,
    RadiationScreenResponse,
)
from app.schemas.requirement_derivation import OrbitFamily
from app.schemas.subsystem_selection import SelectedComponent
from app.services.radiation_db import radiation_index_by_component_id


def _env_tid_krad_per_year(orbit_family: OrbitFamily) -> float:
    # Explainable v1 constants (not a high-fidelity environment model):
    # LEO and SSO tend to be lower TID than MEO; MEO can be substantially harsher.
    if orbit_family == OrbitFamily.sun_synchronous_leo:
        return 7.0
    if orbit_family == OrbitFamily.leo:
        return 5.0
    return 30.0


def _shielding_factor(mm_al: float) -> float:
    # Very rough: more shielding reduces TID; diminishing returns.
    # Normalize to 2mm Al baseline.
    if mm_al <= 0:
        return 1.5
    return max(0.35, 2.0 / mm_al)


def _required_tid_krad(profile: RadiationMissionProfile) -> float:
    years = profile.mission_duration_months / 12.0
    base = _env_tid_krad_per_year(profile.orbit_family) * years
    factor = _shielding_factor(profile.shielding_assumption_mm_al)
    # Add 50% margin for v1 screening.
    return base * factor * 1.5


def _rad_class_rank(rad_class: RadClass) -> int:
    return {
        RadClass.cots: 0,
        RadClass.screened_cots: 1,
        RadClass.rad_tolerant: 2,
        RadClass.rad_hard: 3,
    }[rad_class]


def _verification_rank(status: VerificationStatus) -> int:
    return {
        VerificationStatus.unverified: 0,
        VerificationStatus.vendor_claim: 1,
        VerificationStatus.test_report: 2,
        VerificationStatus.flight_heritage: 3,
    }[status]


def _severity(score: float) -> str:
    if score >= 0.9:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def screen_architecture_radiation(
    mission: RadiationMissionProfile,
    selected: list[SelectedComponent],
    optional_selected: list[SelectedComponent] | None = None,
) -> RadiationScreenResponse:
    optional_selected = optional_selected or []
    idx = radiation_index_by_component_id()

    assumptions: list[str] = [
        "v1 screening uses a simple TID proxy model (not a high-fidelity environment simulation).",
        "TID requirement = environment_rate(orbit_family)*duration*shielding_factor*margin(1.5).",
    ]
    trace: list[str] = []

    required_tid = _required_tid_krad(mission)
    trace.append(
        "TID screening: "
        f"orbit_family={mission.orbit_family.value}, "
        f"duration={mission.mission_duration_months:g} months, "
        f"shielding={mission.shielding_assumption_mm_al:g} mm Al => "
        f"required_tid~{required_tid:.1f} krad."
    )

    flags: list[RadiationFlag] = []

    def check(component: SelectedComponent, db: RadiationComponent | None) -> None:
        if db is None:
            flags.append(
                RadiationFlag(
                    component_id=None,
                    item_id=component.item_id,
                    domain=component.domain,
                    component_name=component.name,
                    severity="low",
                    message="No radiation record found for component; screening incomplete.",
                    mitigations=[
                        "Add radiation metadata (TID/SEE) for this component.",
                        (
                            "Consider ECC/EDAC, watchdogs, and latchup protection as baseline "
                            "mitigations."
                        ),
                    ],
                )
            )
            return

        tid = float(db.tid_krad)
        class_rank = _rad_class_rank(db.rad_class)
        ver_rank = _verification_rank(db.verification_status)

        # Score: deficit dominates; low class/verification increases severity.
        deficit = max(0.0, required_tid - tid)
        deficit_ratio = deficit / max(1.0, required_tid)
        class_penalty = 0.15 * (
            2 - min(2, class_rank)
        )  # penalize cots/screened_cots vs rad_tolerant+
        ver_penalty = 0.10 * (2 - min(2, ver_rank))  # penalize unverified/vendor_claim vs test+
        score = min(1.0, deficit_ratio + class_penalty + ver_penalty)

        if score < 0.35:
            return

        message = (
            f"Radiation risk: tid_krad={tid:g} vs required~{required_tid:.1f}; "
            f"class={db.rad_class.value}, verification={db.verification_status.value}."
        )
        mitigations = [
            "Consider adding EDAC/ECC memory and periodic scrubbing for SEU resilience.",
            "Add latchup protection (current limiting) on sensitive rails.",
        ]
        if deficit > 0:
            mitigations.append(
                "Increase shielding, choose higher rad-class parts, or reduce mission duration/"
                "environment severity."
            )

        flags.append(
            RadiationFlag(
                component_id=db.component_id,
                item_id=component.item_id,
                domain=component.domain,
                component_name=db.component_name,
                severity=_severity(score),
                message=message,
                mitigations=mitigations,
            )
        )

    for c in selected:
        check(c, idx.get(c.item_id))

    for c in optional_selected:
        # Optional components usually mitigate risk; still record missing metadata.
        check(c, idx.get(c.item_id))

    flags.sort(key=lambda f: {"high": 0, "medium": 1, "low": 2}[f.severity])
    trace.append(
        f"Screened {len(selected) + len(optional_selected)} components; flags={len(flags)}."
    )

    return RadiationScreenResponse(
        mission=mission, flags=flags, assumptions=assumptions, trace=trace
    )
