#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q5 upgrade: scenario-based stochastic programme with an explicit CVaR constraint.

The discrete (T, S) grid of s06_q5.py answers "which menu item is cheapest". This
script answers the planning question a city actually faces: choose a continuous
conveyance depth C and storage depth S (and a source-control share g) so that the
annualised cost plus expected annual damage is minimal *subject to* a cap on the
95% conditional tail expectation of damage.

Scenarios are the observed 1961-2020 annual maximum three-day depths (equal
weights), so no tail extrapolation is involved in the risk measure; the GEV is used
only to convert the chosen depth C into an equivalent design return period.

Outputs
-------
q5_sp_grid.csv        every candidate design with cost, EAD, CVaR, BCR
q5_sp_frontier.csv    cost-minimal design for each CVaR cap (efficient frontier)
q5_sp_summary.json    headline numbers
fig23_q5_pareto.png   frontier: annualised cost against CVaR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import common as C
from s06_q5 import CITIES, P, REF_RAIN, OFFICIAL_LOSS, crf, load_annual, scs_runoff, rl3

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 7,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "grid.linestyle": ":"})

C_GRID = np.arange(0.0, 450.0 + 1e-9, 2.5)      # ADDITIONAL conveyance depth beyond the 2-yr design
S_GRID = np.arange(0.0, 150.0 + 1e-9, 2.5)      # storage depth (mm over the city area)
GREEN = [0.0, 0.15, 0.30]
ALPHA = 0.95
BUDGET_Q = [0.9, 0.75, 0.5, 0.25]               # fractions of the no-investment CVaR


def damage(over_mm, ref_loss, over_ref, gamma):
    return ref_loss * np.power(np.clip(over_mm / over_ref, 0.0, None), gamma)


def evaluate(rain3, cn, cap_mm, ref_loss, over_ref, gamma):
    over = np.maximum(0.0, scs_runoff(rain3, cn) - cap_mm)
    d = damage(over, ref_loss, over_ref, gamma)
    ead = float(np.mean(d))
    k = max(1, int(round((1 - ALPHA) * len(d))))
    cvar = float(np.mean(np.sort(d)[-k:]))
    return ead, cvar


def equivalent_return_period(fit, depth_mm: float) -> float:
    """Smallest T with RL3d(T) >= depth; 2.0 if depth is below the 2-year level."""
    for t in (2, 3, 5, 10, 20, 50, 100, 200, 500):
        if rl3(fit, t) >= depth_mm:
            return float(t)
    return float("inf")


def main() -> None:
    zc = CITIES["Zhengzhou"]
    am_z = load_annual(zc["id"])
    fit_z = C.gev_fit_lmom(am_z["rx3day"].to_numpy(dtype=float))
    cap_ref = rl3(fit_z, 2)
    over_ref = float(max(0.0, scs_runoff(np.array([REF_RAIN]), zc["cn"])[0] - cap_ref))
    v_ref = over_ref * zc["area_km2"] * 1e3
    density = OFFICIAL_LOSS / v_ref
    print(f"[calibration] overflow {over_ref:.2f} mm ({v_ref / 1e6:.1f} Mm3), "
          f"{density:.1f} CNY/m3")

    rows, frontier, summary = [], [], {}
    for city, cfg in CITIES.items():
        am = load_annual(cfg["id"])
        rain3 = am["rx3day"].to_numpy(dtype=float)
        fit = C.gev_fit_lmom(rain3)
        area, cn0 = cfg["area_km2"], cfg["cn"]
        design_2 = rl3(fit, 2)
        # Damage is carried by overflow volume: the Zhengzhou anchor scales with
        # (built-up area)^gamma, consistent with s06_q5.evaluate.
        loss_city = OFFICIAL_LOSS * (area / CITIES["Zhengzhou"]["area_km2"]) ** P["damage_exponent"]
        base_ead, base_cvar = evaluate(rain3, cn0, design_2, loss_city, over_ref,
                                       P["damage_exponent"])
        print(f"{city}: baseline EAD {base_ead / 1e8:.2f} bn, CVaR95 {base_cvar / 1e8:.2f} bn, "
              f"RL3d(2) {design_2:.1f} mm")

        city_rows = []
        for g in GREEN:
            cn = cn0 - P["green_cn_drop"] * (g / 0.30)
            green_capex = P["green_cost_per_km2"] * area * (g / 0.30)
            for cadd in C_GRID:
                for sv in S_GRID:
                    cap = design_2 + cadd + sv
                    ead, cvar = evaluate(rain3, cn, cap, loss_city, over_ref, P["damage_exponent"])
                    capex = (P["pipe_cost_per_mm_km2"] * area * cadd
                             + P["storage_cost_per_m3"] * sv * area * 1e3 + green_capex)
                    annual = (crf(P["discount"], P["horizon"]) + P["om_share"]) * capex
                    city_rows.append((g, cadd, sv, cap, annual, ead, cvar))
        df = pd.DataFrame(city_rows, columns=["green", "C_add_mm", "S_mm", "capacity_mm",
                                              "annual_cost_cny", "ead_cny", "cvar95_cny"])
        df["city"] = city
        df["bcr"] = (base_ead - df["ead_cny"]) / df["annual_cost_cny"].clip(lower=1.0)
        df["total_cny"] = df["annual_cost_cny"] + df["ead_cny"]
        rows.append(df)

        # cost-minimal design for each CVaR cap: the epsilon-constraint frontier
        for q in BUDGET_Q:
            cap_b = q * base_cvar
            feas = df[df["cvar95_cny"] <= cap_b]
            if feas.empty:
                continue
            r = feas.sort_values("annual_cost_cny").iloc[0]
            frontier.append({"city": city, "budget_frac": q, "cvar_cap_cny": cap_b,
                             "green": r["green"], "C_add_mm": r["C_add_mm"], "S_mm": r["S_mm"],
                             "capacity_mm": r["capacity_mm"],
                             "T_equivalent_yr": equivalent_return_period(fit, design_2 + r["C_add_mm"]),
                             "annual_cost_cny": r["annual_cost_cny"], "ead_cny": r["ead_cny"],
                             "cvar95_cny": r["cvar95_cny"], "bcr": r["bcr"]})
        best = df.sort_values("total_cny").iloc[0]
        summary[city] = {
            "baseline_ead_cny": base_ead, "baseline_cvar95_cny": base_cvar,
            "design_depth_2yr_mm": design_2,
            "unconstrained": {"green": float(best["green"]), "C_add_mm": float(best["C_add_mm"]),
                              "S_mm": float(best["S_mm"]), "capacity_mm": float(best["capacity_mm"]),
                              "annual_cost_cny": float(best["annual_cost_cny"]),
                              "ead_cny": float(best["ead_cny"]), "cvar95_cny": float(best["cvar95_cny"]),
                              "bcr": float(best["bcr"])},
        }

    grid = pd.concat(rows, ignore_index=True)
    fr = pd.DataFrame(frontier)
    grid.to_csv(C.RESULTS / "q5_sp_grid.csv", index=False)
    fr.to_csv(C.RESULTS / "q5_sp_frontier.csv", index=False)

    out = {"parameters": {**P, "alpha": ALPHA, "C_grid": [float(C_GRID[0]), float(C_GRID[-1]), 2.5],
                          "S_grid": [float(S_GRID[0]), float(S_GRID[-1]), 2.5]},
           "calibration": {"event_rain_mm": REF_RAIN, "design_depth_mm": cap_ref,
                           "overflow_mm": over_ref, "damage_density_cny_m3": density},
           "cities": summary,
           "frontier": fr.to_dict("records"),
           "note": "Scenario-based programme: 60 annual maxima 1961-2020 with equal weights; "
                   "risk measure CVaR95 of damage; designs enumerated on a 2.5 mm lattice "
                   "in conveyance and storage depth; frontier = cost-minimal design per CVaR cap."}
    (C.RESULTS / "q5_sp_summary.json").write_text(json.dumps(out, indent=2, default=float),
                                                  encoding="utf-8")

    # ---------------- figure: cost vs CVaR frontier ----------------
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.7), layout="constrained", sharey=False)
    for ax, city in zip(axes, CITIES):
        sub = grid[grid["city"] == city]
        for g, mk in zip(GREEN, ["o", "s", "^"]):
            s2 = sub[sub["green"] == g].sort_values("annual_cost_cny")
            cost = s2["annual_cost_cny"].to_numpy() / 1e8
            cvar = s2["cvar95_cny"].to_numpy() / 1e8
            # keep only the non-dominated part: cost rising, CVaR at a new low
            keep, best = [], np.inf
            for i in range(len(cvar)):
                if cvar[i] < best - 1e-12:
                    best = cvar[i]
                    keep.append(i)
            ax.plot(cost[keep], cvar[keep], marker=mk, ms=2.0, lw=0.9,
                    label=f"{int(g * 100)}% source control")
        f2 = fr[fr["city"] == city]
        ax.scatter(f2["annual_cost_cny"] / 1e8, f2["cvar95_cny"] / 1e8, s=40, marker="*",
                   color="#b5342c", zorder=5, label="risk-capped optimum")
        ax.set_xlabel("Annualised cost (100 million CNY/yr)")
        ax.set_title(city, fontsize=9)
        ax.legend(fontsize=6, loc="upper right")
    axes[0].set_ylabel("CVaR$_{95}$ of annual damage (100 million CNY)")
    fig.savefig(C.FIGS / "fig23_q5_pareto.png")
    plt.close(fig)

    print(fr.round(3).to_string(index=False))
    print(json.dumps({c: {k: round(v, 2) if isinstance(v, float) else v
                          for k, v in s["unconstrained"].items()}
                      for c, s in summary.items()}, indent=1))


if __name__ == "__main__":
    main()