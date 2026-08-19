from __future__ import annotations

import math


def volume_cm3_from_mm(length_mm: float, width_mm: float, height_mm: float) -> float:
    return (length_mm * width_mm * height_mm) / 1000.0


def occupied_u_from_cm3(volume_cm3: float) -> float:
    return volume_cm3 / 1000.0


def ceil_div_mm_to_u(length_mm: float, u_mm: float = 100.0) -> int:
    return int(math.ceil(length_mm / u_mm))
