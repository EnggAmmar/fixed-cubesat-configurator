from __future__ import annotations

from solver.cubesat_solver_runner import run_cubesat_diagnostic, run_cubesat_solver


def test_navigation_and_remote_sensing_solve_with_family_specific_orbit_physics() -> None:
    """Both mission families must still solve to a feasible bus after F-07 threads
    altitude-derived orbit assumptions into the CP-SAT model, instead of raising or
    silently reusing another family's orbit period/eclipse fraction."""
    nav = run_cubesat_solver("NAV-RF-PNT-001")
    assert nav["status"] in {"OPTIMAL", "FEASIBLE"}

    rs = run_cubesat_solver("RS-EO-VIS-001")
    assert rs["status"] in {"OPTIMAL", "FEASIBLE"}


def test_diagnostic_re_verification_agrees_with_solver_for_navigation_payload() -> None:
    """run_cubesat_diagnostic's independent pure-Python re-evaluation (_eval_case) must
    use the same per-family orbit assumptions as the CP-SAT constraint injector, or the
    two would disagree about feasibility for MEO-altitude payloads."""
    result = run_cubesat_diagnostic("NAV-RF-PNT-001")
    solved_bus = run_cubesat_solver("NAV-RF-PNT-001")["selection"]["bus_class"]
    case = next(c for c in result["bus_cases"] if c["bus_class"] == solved_bus)
    assert case["status"] in {"OPTIMAL", "FEASIBLE"}
