from __future__ import annotations

import pytest

from solver.orbit_mechanics import (
    orbit_assumptions_for_family,
    orbit_period_hr,
    worst_case_eclipse_fraction,
)


def test_leo_altitude_matches_previous_fixed_global_assumptions_closely() -> None:
    """Remote Sensing's 550 km reference altitude should reproduce the fixed globals
    (1.5h period, 38% eclipse) the LEO calibration was originally tuned against, within
    a small physically-expected margin - this is the regression guard that the F-07 fix
    does not disturb the well-tuned LEO case."""
    period_hr = orbit_period_hr(550.0)
    eclipse = worst_case_eclipse_fraction(550.0)
    assert period_hr == pytest.approx(1.5, rel=0.1)
    assert eclipse == pytest.approx(0.38, rel=0.1)


def test_navigation_meo_altitude_is_dramatically_different_from_leo_globals() -> None:
    """Navigation's 20,000 km MEO reference altitude must NOT reuse LEO-typical
    values - this is the actual bug (F-07) the fixed globals caused."""
    period_hr = orbit_period_hr(20000.0)
    eclipse = worst_case_eclipse_fraction(20000.0)
    assert period_hr > 10.0  # real MEO period is ~11.8h, nothing like the fixed 1.5h
    assert eclipse < 0.15  # real MEO worst-case eclipse is ~8%, nothing like fixed 38%


def test_orbit_assumptions_for_family_covers_all_three_families() -> None:
    for family in ("Remote Sensing", "IoT / Communication", "Navigation"):
        period_hr, f_sun, f_ecl = orbit_assumptions_for_family(family)
        assert period_hr > 0
        assert f_sun + f_ecl == pytest.approx(1.0)
        assert 0.0 <= f_ecl <= 1.0


def test_unknown_family_falls_back_to_leo_default_without_raising() -> None:
    period_hr, f_sun, f_ecl = orbit_assumptions_for_family("Some Future Family")
    assert period_hr == pytest.approx(orbit_period_hr(550.0))
