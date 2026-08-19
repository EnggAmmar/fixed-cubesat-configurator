from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ortools.sat.python import cp_model


Tier = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
BUS_CLASSES: list[str] = ["1U", "1.5U", "2U", "3U", "6U", "12U", "16U", "27U", "50U+"]
TIERS: list[Tier] = ["LOW", "MEDIUM", "HIGH", "EXTREME"]


@dataclass(frozen=True)
class CubeSatVars:
    x_payload: dict[str, cp_model.IntVar]
    b_bus: dict[str, cp_model.IntVar]
    e_eps: dict[Tier, cp_model.IntVar]
    a_adcs: dict[Tier, cp_model.IntVar]
    c_comms: dict[Tier, cp_model.IntVar]
    o_obc: dict[Tier, cp_model.IntVar]
    t_thermal: dict[Tier, cp_model.IntVar]
    p_prop: dict[Tier, cp_model.IntVar]

    # Aggregates (scaled integer units)
    M_total_g: cp_model.IntVar
    P_avg_total_mw: cp_model.IntVar
    P_peak_total_mw: cp_model.IntVar
    U_total_mU: cp_model.IntVar
    Cost_total: cp_model.IntVar
    Risk_total: cp_model.IntVar
    BusOversize_mU: cp_model.IntVar


@dataclass(frozen=True)
class CubeSatModel:
    model: cp_model.CpModel
    vars: CubeSatVars


def build_cp_model(payload_ids: list[str]) -> CubeSatModel:
    m = cp_model.CpModel()

    x_payload: dict[str, cp_model.IntVar] = {}
    for pid in payload_ids:
        x_payload[pid] = m.new_bool_var(f"x_payload[{pid}]")

    b_bus: dict[str, cp_model.IntVar] = {}
    for u in BUS_CLASSES:
        b_bus[u] = m.new_bool_var(f"b_bus[{u}]")

    def _tier_vars(prefix: str) -> dict[Tier, cp_model.IntVar]:
        return {k: m.new_bool_var(f"{prefix}[{k}]") for k in TIERS}

    e_eps = _tier_vars("e_eps")
    a_adcs = _tier_vars("a_adcs")
    c_comms = _tier_vars("c_comms")
    o_obc = _tier_vars("o_obc")
    t_thermal = _tier_vars("t_thermal")
    p_prop = _tier_vars("p_prop")

    # Upper bounds are conservative and should not restrict feasible solutions.
    M_total_g = m.new_int_var(0, 200_000, "M_total_g")
    P_avg_total_mw = m.new_int_var(0, 2_000_000, "P_avg_total_mw")
    P_peak_total_mw = m.new_int_var(0, 5_000_000, "P_peak_total_mw")
    U_total_mU = m.new_int_var(0, 200_000, "U_total_mU")
    Cost_total = m.new_int_var(0, 5_000_000, "Cost_total_usd_proxy")
    Risk_total = m.new_int_var(0, 50_000, "Risk_total_points")
    BusOversize_mU = m.new_int_var(0, 200_000, "BusOversize_mU")

    return CubeSatModel(
        model=m,
        vars=CubeSatVars(
            x_payload=x_payload,
            b_bus=b_bus,
            e_eps=e_eps,
            a_adcs=a_adcs,
            c_comms=c_comms,
            o_obc=o_obc,
            t_thermal=t_thermal,
            p_prop=p_prop,
            M_total_g=M_total_g,
            P_avg_total_mw=P_avg_total_mw,
            P_peak_total_mw=P_peak_total_mw,
            U_total_mU=U_total_mU,
            Cost_total=Cost_total,
            Risk_total=Risk_total,
            BusOversize_mU=BusOversize_mU,
        ),
    )

