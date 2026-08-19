from __future__ import annotations

import math

from app.schemas.constellation_estimator import (
    ConstellationEstimateRequest,
    ConstellationEstimateV1,
    WalkerCandidate,
)
from app.schemas.requirement_derivation import OrbitFamily


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _range_pair_sorted(pair: tuple[float, float]) -> tuple[float, float]:
    a, b = pair
    return (a, b) if a <= b else (b, a)


def _pick_altitudes(lo_km: int, hi_km: int) -> list[int]:
    lo, hi = (lo_km, hi_km) if lo_km <= hi_km else (hi_km, lo_km)
    if lo == hi:
        return [lo]

    mids = sorted({lo, int(round((lo + hi) / 2)), hi, 500, 550, 600})
    out = [a for a in mids if lo <= a <= hi]
    if len(out) > 5:
        # keep endpoints + closest to 550
        out.sort(key=lambda x: (x not in (lo, hi), abs(x - 550)))
        out = sorted(set(out[:5]))
    return out


def _pick_inclinations(
    orbit_family: OrbitFamily, inclination_range_deg: tuple[float, float]
) -> list[float]:
    lo, hi = _range_pair_sorted(inclination_range_deg)

    base: list[float]
    if orbit_family == OrbitFamily.sun_synchronous_leo:
        base = [97.2, 97.6, 98.0]
    elif orbit_family == OrbitFamily.leo:
        base = [0.0, 53.0, 70.0, 90.0]
    else:
        base = [45.0, 56.0, 63.4]

    out = [x for x in base if lo <= x <= hi]
    if not out:
        # fallback to range midpoint
        out = [round((lo + hi) / 2, 1)]
    return out


def _default_swath_km(family: str) -> float:
    if family == "remote_sensing":
        return 50.0
    if family == "iot_communication":
        return 1200.0
    return 800.0


def _choose_orbit_family(req: ConstellationEstimateRequest, trace: list[str]) -> OrbitFamily:
    allowed = req.estimator.allowed_orbit_families
    family = req.input.family.value

    if allowed:
        # Prefer sun-synchronous for remote sensing if allowed; otherwise first allowed.
        if family == "remote_sensing" and OrbitFamily.sun_synchronous_leo in allowed:
            trace.append("Orbit family rule: remote_sensing prefers sun_synchronous_leo (allowed).")
            return OrbitFamily.sun_synchronous_leo
        trace.append(f"Orbit family rule: using first allowed `{allowed[0].value}`.")
        return allowed[0]

    # Default if not provided
    if family == "remote_sensing":
        trace.append("Orbit family rule: default remote_sensing => sun_synchronous_leo.")
        return OrbitFamily.sun_synchronous_leo
    if family == "iot_communication":
        trace.append("Orbit family rule: default iot_communication => leo.")
        return OrbitFamily.leo
    trace.append("Orbit family rule: default navigation => meo.")
    return OrbitFamily.meo


def _roi_multiplier(roi_type: str) -> float:
    return 2.0 if roi_type == "global" else 1.0


def _effective_swath_km(
    swath_km: float, field_of_regard_deg: float | None, trace: list[str]
) -> float:
    if field_of_regard_deg is None:
        trace.append(f"Swath rule: using swath_km={swath_km:g} (no FOR provided).")
        return swath_km
    for_deg = float(field_of_regard_deg)
    # v1 heuristic: FOR increases effective coverage width modestly.
    factor = 1.0 + _clamp(for_deg / 60.0, 0.0, 1.0) * 0.5
    eff = swath_km * factor
    trace.append(f"Swath rule: swath_km={swath_km:g}, FOR={for_deg:g} => effective_swath={eff:g}.")
    return eff


def _estimate_satellites(
    revisit_h: float,
    roi_mult: float,
    effective_swath_km: float,
    altitude_km: int,
    orbit_family: OrbitFamily,
    trace: list[str],
) -> int:
    # v1 explainable approximation:
    # - revisit drives base satellites ~ 24/revisit
    # - global coverage doubles the demand
    # - swath increases coverage, reducing satellites (relative to 50 km baseline)
    # - higher altitude increases footprint modestly (relative to 550 km baseline)
    base = (24.0 / revisit_h) * roi_mult
    swath_factor = 50.0 / max(10.0, effective_swath_km)
    alt_factor = 550.0 / float(max(300, altitude_km))
    orbit_factor = 1.0 if orbit_family != OrbitFamily.meo else 0.4

    raw = base * swath_factor * alt_factor * orbit_factor
    sats = max(1, int(math.ceil(raw)))

    trace.append(
        "Satellite count rule: "
        f"base(24/revisit*roi)={base:g}, swath_factor={swath_factor:g}, "
        f"alt_factor={alt_factor:g}, orbit_factor={orbit_factor:g} => N≈{raw:.2f} => {sats}."
    )
    return sats


def _walker_candidates(n_est: int, trace: list[str]) -> list[WalkerCandidate]:
    # Walker-delta style candidates: choose planes P and satellites/plane S with N=P*S >= n_est
    max_planes = min(8, max(1, n_est))
    candidates: list[WalkerCandidate] = []
    for planes in range(1, max_planes + 1):
        sats_per_plane = int(math.ceil(n_est / planes))
        total = planes * sats_per_plane
        # simple score: prefer fewer satellites and fewer planes
        score = 10_000.0 - total * 200.0 - planes * 25.0
        candidates.append(
            WalkerCandidate(
                total_satellites=total,
                planes=planes,
                satellites_per_plane=sats_per_plane,
                relative_phasing_f=1 if planes > 1 else 0,
                score=score,
                rationale=[
                    f"Walker candidate: planes={planes}, sats/plane={sats_per_plane} "
                    f"=> total={total}.",
                    "Score favors fewer satellites and fewer planes (v1 heuristic).",
                ],
            )
        )
    candidates.sort(key=lambda c: (-c.score, c.total_satellites, c.planes))
    trace.append(
        f"Walker generation: created {len(candidates)} candidates up to {max_planes} planes."
    )
    return candidates


def estimate_constellation_v1(req: ConstellationEstimateRequest) -> ConstellationEstimateV1:
    trace: list[str] = []
    warnings: list[str] = []
    assumptions: list[str] = []

    revisit_h = float(req.input.parameters.revisit_time_hours)
    if revisit_h <= 0:
        raise ValueError("revisit_time_hours must be > 0")

    orbit_family = _choose_orbit_family(req, trace)

    alt_lo, alt_hi = req.estimator.altitude_range_km
    altitudes = _pick_altitudes(int(alt_lo), int(alt_hi))
    if not altitudes:
        raise ValueError("altitude_range_km produced no candidates")

    inclinations = _pick_inclinations(orbit_family, req.estimator.inclination_range_deg)

    family = req.input.family.value
    swath_km = float(req.estimator.payload_swath_km or _default_swath_km(family))
    if req.estimator.payload_swath_km is None:
        assumptions.append(
            f"Swath proxy not provided; default swath_km={swath_km:g} by mission family `{family}`."
        )

    eff_swath = _effective_swath_km(swath_km, req.estimator.payload_field_of_regard_deg, trace)

    roi_mult = _roi_multiplier(req.input.roi.type)
    if req.input.roi.type == "global":
        assumptions.append("Global coverage increases revisit demand (roi_multiplier=2.0).")

    # Choose a representative altitude for N estimate (closest to 550 km in LEO; mid for others)
    if orbit_family in (OrbitFamily.leo, OrbitFamily.sun_synchronous_leo):
        alt_ref = min(altitudes, key=lambda x: abs(x - 550))
    else:
        alt_ref = altitudes[len(altitudes) // 2]
    trace.append(f"Reference altitude for sizing: {alt_ref} km.")

    n_est = _estimate_satellites(revisit_h, roi_mult, eff_swath, alt_ref, orbit_family, trace)

    # Data volume sanity (very rough)
    if (
        req.estimator.payload_data_volume_gb_per_day is not None
        and req.estimator.downlink_mbps_assumed is not None
    ):
        gb = float(req.estimator.payload_data_volume_gb_per_day)
        mbps = float(req.estimator.downlink_mbps_assumed)
        seconds_needed = (gb * 8 * 1024) / max(1e-6, mbps)
        minutes = seconds_needed / 60.0
        trace.append(
            f"Downlink sanity: {gb:g} GB/day at {mbps:g} Mbps needs ~{minutes:.1f} min/day contact."
        )
        if minutes > 120:
            warnings.append(
                "Downlink assumption suggests >120 min/day contact time; consider higher downlink, "
                "more ground stations, or lowering data volume."
            )
    else:
        assumptions.append("Downlink/data-volume sanity check skipped (inputs not provided).")

    candidates = _walker_candidates(n_est, trace)
    recommended = candidates[0]

    return ConstellationEstimateV1(
        recommended_orbit_family=orbit_family,
        candidate_altitudes_km=altitudes,
        candidate_inclinations_deg=inclinations,
        estimated_number_of_satellites=n_est,
        recommended_candidate=recommended,
        candidate_walker_constellations=candidates[: min(10, len(candidates))],
        assumptions=assumptions,
        trace=trace,
        warnings=warnings,
    )
