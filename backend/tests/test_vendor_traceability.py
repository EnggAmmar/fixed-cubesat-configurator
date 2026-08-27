from __future__ import annotations

from app.services.vendor_traceability import representative_product


def test_representative_product_covers_all_four_tiers() -> None:
    for domain in ("eps", "adcs", "comm", "obc", "thermal", "propulsion"):
        for tier in ("LOW", "MEDIUM", "HIGH", "EXTREME"):
            product = representative_product(domain, tier)
            assert product is not None, f"missing representative for {domain}/{tier}"
            assert product["item_id"]
            assert product["vendor"]
            assert product["product_name"]
            assert product["mass_kg"] > 0


def test_representative_product_is_case_insensitive_and_mass_ordered() -> None:
    low = representative_product("eps", "low")
    extreme = representative_product("eps", "EXTREME")
    assert low is not None and extreme is not None
    assert low["mass_kg"] <= extreme["mass_kg"]


def test_representative_product_unknown_domain_returns_none() -> None:
    assert representative_product("structure", "HIGH") is None
    assert representative_product("eps", "NOT_A_TIER") is None


def test_backend_solver_solution_carries_representative_product_metadata() -> None:
    from app.schemas.requirement_derivation import (
        DerivedSubsystemRequirements,
        DownlinkClass,
        OrbitFamily,
        ThermalMode,
    )
    from app.services.optimization.cubesat_engine_adapter import solve_subsystems_via_backend_solver

    class _Payload:
        type = "catalog"
        payload_id = "RS-EO-VIS-001"

    class _MissionInput:
        payload = _Payload()

    derived = DerivedSubsystemRequirements(
        required_bus_volume_u=6.0,
        estimated_total_mass_budget_kg=8.0,
        payload_power_avg_w=10.0,
        payload_power_peak_w=15.0,
        required_pointing_accuracy_deg=0.5,
        required_downlink_class=DownlinkClass.high,
        required_storage_gb=32.0,
        required_thermal_mode=ThermalMode.standard,
        required_eps_avg_generation_w=15.0,
        required_battery_wh=50.0,
        propulsion_recommended=False,
        recommended_orbit_family=OrbitFamily.sun_synchronous_leo,
    )

    ok, status, selected, optional, totals, margins, warnings, trace = (
        solve_subsystems_via_backend_solver(_MissionInput(), derived)
    )
    assert ok, status
    by_domain = {c.domain: c for c in selected}
    assert "representative_product" in by_domain["eps"].metadata
    assert "representative_product" not in by_domain["structure"].metadata
