from __future__ import annotations

import math

# Circular-orbit approximations used to replace backend/solver/'s previously-fixed
# LEO-only orbit_assumptions (nominal_orbit_period_hr=1.5, eclipse_fraction=0.38,
# sunlight_fraction=0.62 in data_base/global_engineering_assumptions.json) with values
# derived from the mission's actual altitude. Those fixed constants were tuned for a
# ~550 km sun-synchronous LEO mission and are close to correct there, but silently wrong
# for Navigation-family payloads that fly at ~20,000 km MEO (real period ~11.8 h vs the
# fixed 1.5 h; real worst-case eclipse ~8% vs the fixed 38%).

_EARTH_RADIUS_KM = 6378.0
_EARTH_MU_KM3_S2 = 398600.4418  # standard gravitational parameter of Earth

# backend/solver/ has no per-payload altitude field (see cubesat_data_loader.py's
# PayloadRecord); these mirror app/services/constellation.py's existing per-family
# defaults so both pipelines agree on a reference altitude absent a real one.
DEFAULT_ALTITUDE_KM_BY_FAMILY = {
    "Remote Sensing": 550.0,
    "IoT / Communication": 600.0,
    "Navigation": 20000.0,
}
_FALLBACK_ALTITUDE_KM = 550.0


def orbit_period_hr(altitude_km: float) -> float:
    """Kepler's third law for a circular orbit at the given altitude above Earth's
    mean radius."""
    semi_major_axis_km = _EARTH_RADIUS_KM + altitude_km
    period_s = 2.0 * math.pi * math.sqrt(semi_major_axis_km**3 / _EARTH_MU_KM3_S2)
    return period_s / 3600.0


def worst_case_eclipse_fraction(altitude_km: float) -> float:
    """Fraction of the orbit spent in Earth's shadow for the worst-case beta angle of
    zero (orbit plane containing the sun direction) - a cylindrical-shadow
    approximation, conservative but standard for preliminary sizing."""
    r_km = _EARTH_RADIUS_KM + altitude_km
    cos_half_angle = math.sqrt(max(r_km**2 - _EARTH_RADIUS_KM**2, 0.0)) / r_km
    cos_half_angle = max(-1.0, min(1.0, cos_half_angle))
    return (1.0 / math.pi) * math.acos(cos_half_angle)


def orbit_assumptions_for_family(mission_family: str) -> tuple[float, float, float]:
    """Returns (nominal_orbit_period_hr, sunlight_fraction, eclipse_fraction) computed
    from the mission family's reference altitude, replacing the fixed global
    orbit_assumptions/power_assumptions values with altitude-appropriate ones."""
    altitude_km = DEFAULT_ALTITUDE_KM_BY_FAMILY.get(mission_family, _FALLBACK_ALTITUDE_KM)
    period_hr = orbit_period_hr(altitude_km)
    eclipse_fraction = worst_case_eclipse_fraction(altitude_km)
    return period_hr, 1.0 - eclipse_fraction, eclipse_fraction
