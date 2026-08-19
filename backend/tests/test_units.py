from __future__ import annotations

from app.services.units import ceil_div_mm_to_u, occupied_u_from_cm3, volume_cm3_from_mm


def test_volume_cm3_from_mm() -> None:
    assert volume_cm3_from_mm(100, 100, 100) == 1000.0
    assert volume_cm3_from_mm(200, 100, 50) == 1000.0


def test_occupied_u_from_cm3() -> None:
    assert occupied_u_from_cm3(0) == 0
    assert occupied_u_from_cm3(1000) == 1.0
    assert occupied_u_from_cm3(2500) == 2.5


def test_ceil_div_mm_to_u_defaults_to_100mm() -> None:
    assert ceil_div_mm_to_u(1) == 1
    assert ceil_div_mm_to_u(100) == 1
    assert ceil_div_mm_to_u(101) == 2
    assert ceil_div_mm_to_u(250) == 3
