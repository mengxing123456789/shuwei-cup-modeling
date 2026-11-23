#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q5: long-term construction plan for extreme-rainfall resilience.

Everything is expressed on the three-day event scale, which is the scale at which
urban flooding and the 2021 disaster actually happened:
  hazard   : annual maximum three-day rainfall, GEV (L-moments)
  capacity : design storm depth for return period T plus storage depth
  damage   : SCS-CN runoff minus capacity, priced at a density calibrated on 2021
  objective: annualised investment + expected annual damage + value of expected deaths
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import common as C

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 7,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "grid.linestyle": ":"})

CITIES = {
    "Zhengzhou": {"id": "CHM00057083", "area_km2": 1180.0, "cn": 85.0, "pop": 12.60e6,
                  "deaths_ref": 380.0},
    "Haikou": {"id": "CHM00059758", "area_km2": 230.0, "cn": 82.0, "pop": 2.87e6,
               "deaths_ref": 380.0 * 2.87e6 / 12.60e6},
    "Guangzhou": {"id": "CHM00059287", "area_km2": 1400.0, "cn": 85.0, "pop": 18.68e6,
                  "deaths_ref": 380.0 * 18.68e6 / 12.60e6},
}

P = {
    "damage_per_m3": 120.0,        # CNY per m3 of overflow; recalibrated in main()
    "pipe_cost_per_mm_km2": 1.0e9 / 1180.0,  # CNY per mm of added three-day design depth per km2
    "storage_cost_per_m3": 800.0,  # CNY per m3 of storage
    "green_cost_per_km2": 1.5e8,   # CNY per km2 of full sponge-city retrofit
    "green_cn_drop": 40.0,
    "vsl_cny": 5.0e6,              # value of a statistical life
    "discount": 0.04,
    "horizon": 30,
    "om_share": 0.02,
    "deaths_elasticity": 1.5,
    "damage_exponent": 1.5,
    "risk_aversion": 0.5,
}

T_PIPE = [2, 3, 5, 10, 20, 50, 100]
S_DEPTH = [0, 5, 10, 20, 40, 80]
GREEN = [0.0, 0.15, 0.30]
REF_RAIN = 449.0      # Zhengzhou 2021 three-day areal total (mm)
OFFICIAL_LOSS = 409.0e8


def crf(r: float, n: int) -> float:
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def scs_runoff(p_mm, cn: float):
    s = 25400.0 / cn - 254.0
    ia = 0.2 * s
    p = np.asarray(p_mm, dtype=float)
    return np.where(p > ia, (p - ia) ** 2 / (p + 0.8 * s), 0.0)


def overflow_depth(rain, cn: float, cap_mm: float):
    return np.maximum(0.0, scs_runoff(rain, cn) - cap_mm)


def volume_m3(depth_mm, area_km2: float):
    return np.asarray(depth_mm, dtype=float) * area_km2 * 1e3


def city_loss_scale(area_km2: float, gamma: float) -> float:
    """Loss anchor for a city whose built-up area differs from Zhengzhou's.

    Damage is a power law in overflow volume, so at equal overflow depth a city of area A
    loses (A / A_Zhengzhou)^gamma times what Zhengzhou loses. Using a linear area factor
    here would silently disagree with evaluate(), which works on volumes.
    """
    return OFFICIAL_LOSS * (area_km2 / CITIES["Zhengzhou"]["area_km2"]) ** gamma


def load_annual(id_: str) -> pd.DataFrame:
    g = C.load_ghcn_wide(C.RESULTS / "ghcn" / f"{id_}.csv")
    d = C.daily_grid(g[["date", "prcp_mm"]])["prcp_mm"]
    valid = d.groupby(d.index.year).apply(lambda z: int(z.notna().sum()))
    df = pd.DataFrame({"rx1day": d.groupby(d.index.year).max(),
                       "rx3day": d.rolling(3, min_periods=3).sum().groupby(d.index.year).max()})
    return df[valid >= 300].loc[1961:2020]


def rl3(fit, t: float) -> float:
    return float(C.gev_return_level(fit, t))


def evaluate(rain3, cn, cap_mm, area, ref_loss, over_ref_mm, gamma, deaths_ref, elasticity,
             v_ref_m3=None):
    """Damage is a convex power law in overflow *volume*, anchored on the 2021 event.

    Volume, not depth, is the physical carrier: a 230 km2 city cannot lose the same
    absolute amount as a 1180 km2 city at the same overflow depth. The anchor is
    V_ref = over_ref x area_Zhengzhou, so Zhengzhou reproduces the official loss exactly
    and every other city is scaled by its own built-up area.
    """
    over = overflow_depth(rain3, cn, cap_mm)
    if over_ref_mm <= 0:
        over_ref_mm = 1.0
    if v_ref_m3 is None:
        v_ref_m3 = float(volume_m3(over_ref_mm, CITIES["Zhengzhou"]["area_km2"]))
    vol = volume_m3(over, area)
    dmg = ref_loss * np.power(np.clip(vol / v_ref_m3, 0.0, None), gamma)
    ead = float(np.mean(dmg))
    k = max(1, int(np.ceil(0.05 * len(dmg))))
    cvar = float(np.mean(np.sort(dmg)[-k:]))
    deaths = float(np.mean(deaths_ref * (over / over_ref_mm) ** elasticity))
    return ead, cvar, deaths, over


def main() -> None:
    # ---- calibrate damage density: the 2021 Zhengzhou event must reproduce 40.9 bn CNY ----
    zc = CITIES["Zhengzhou"]
    am_z = load_annual(zc["id"])
    fit_z = C.gev_fit_lmom(am_z["rx3day"].to_numpy(dtype=float))
    cap_ref = rl3(fit_z, 2)
    over_ref = float(overflow_depth(np.array([REF_RAIN]), zc["cn"], cap_ref)[0])
    v_ref = float(volume_m3(over_ref, zc["area_km2"]))
    P["damage_per_m3"] = OFFICIAL_LOSS / v_ref
    print(f"[calibration] 2021 overflow {over_ref:.1f} mm ({v_ref / 1e6:.1f} Mm3), "
          f"damage density {P['damage_per_m3']:.1f} CNY/m3, design depth {cap_ref:.1f} mm")
    rows, scen = [], []
    for city, cfg in CITIES.items():
        am = load_annual(cfg["id"])
        rain3 = am["rx3day"].to_numpy(dtype=float)
        area, cn0 = cfg["area_km2"], cfg["cn"]
        fit = C.gev_fit_lmom(rain3)
        rl = {t: rl3(fit, t) for t in T_PIPE}
        o2021 = float(overflow_depth(np.array([REF_RAIN]), cn0, rl[2])[0])
        v2021 = float(volume_m3(o2021, area))
        for g in GREEN:
            cn = cn0 - P["green_cn_drop"] * (g / 0.30)
            green_cap = P["green_cost_per_km2"] * area * (g / 0.30)
            for t in T_PIPE:
                for s_mm in S_DEPTH:
                    cap = rl[t] + s_mm
                    ead, cvar, deaths, over = evaluate(rain3, cn, cap, area, OFFICIAL_LOSS, over_ref,
                                                       P["damage_exponent"], cfg["deaths_ref"],
                                                       P["deaths_elasticity"], v_ref)
                    capex = (P["pipe_cost_per_mm_km2"] * area * max(0.0, rl[t] - rl[2])
                             + P["storage_cost_per_m3"] * s_mm * area * 1e3 + green_cap)
                    annual = (crf(P["discount"], P["horizon"]) + P["om_share"]) * capex
                    rows.append({"city": city, "green": g, "T_pipe": t, "storage_mm": s_mm,
                                 "capacity_mm": cap, "ead_cny": ead, "cvar95_cny": cvar,
                                 "exp_deaths": deaths,
                                 "capex_cny": capex, "annual_cost_cny": annual,
                                 "total_econ_cny": annual + ead,
                                 "total_social_cny": (annual + ead
                                                      + P["risk_aversion"] * cvar
                                                      + deaths * P["vsl_cny"])})
        base_ead, base_cvar, base_deaths, base_over = evaluate(
            rain3, cn0, rl[2], area, OFFICIAL_LOSS, over_ref, P["damage_exponent"],
            cfg["deaths_ref"], P["deaths_elasticity"], v_ref)
        scen.append({"city": city, "area_km2": area, "cn": cn0, "pop": cfg["pop"],
                     "rl2": rl[2], "rl10": rl[10], "rl50": rl[50], "rl100": rl[100],
                     "mean_rx3day": float(rain3.mean()),
                     "baseline_ead_cny": base_ead, "baseline_cvar95_cny": base_cvar, "baseline_deaths": base_deaths,
                     "stress2021_overflow_mm": o2021, "stress2021_volume_m3": v2021,
                     "deaths_ref": cfg["deaths_ref"], "deaths_calibrated": bool(v2021 > 0)})

    grid = pd.DataFrame(rows)
    base = pd.DataFrame(scen).set_index("city")
    grid.to_csv(C.RESULTS / "q5_portfolio_grid.csv", index=False)

    best_econ = grid.sort_values("total_econ_cny").groupby("city").head(1).set_index("city")
    best_soc = grid.sort_values("total_social_cny").groupby("city").head(1).set_index("city")
    keep = ["green", "T_pipe", "storage_mm", "capacity_mm", "ead_cny", "exp_deaths",
            "capex_cny", "annual_cost_cny", "total_econ_cny", "total_social_cny"]
    best_econ[keep].to_csv(C.RESULTS / "q5_optimal_economic.csv")
    best_soc[keep].to_csv(C.RESULTS / "q5_optimal_social.csv")

    base = base.join(best_econ[keep].add_suffix("_econ")).join(best_soc[keep].add_suffix("_soc"))
    base["ead_cut_econ_pct"] = (1 - base["ead_cny_econ"] / base["baseline_ead_cny"].clip(lower=1)) * 100
    base["ead_cut_soc_pct"] = (1 - base["ead_cny_soc"] / base["baseline_ead_cny"].clip(lower=1)) * 100
    base["deaths_cut_soc_pct"] = (1 - base["exp_deaths_soc"]
                                  / base["baseline_deaths"].clip(lower=1e-9)) * 100
    base["bcr_econ"] = ((base["baseline_ead_cny"] - base["ead_cny_econ"])
                        / base["annual_cost_cny_econ"].clip(lower=1))
    base["bcr_soc"] = ((base["baseline_ead_cny"] - base["ead_cny_soc"]
                        + (base["baseline_deaths"] - base["exp_deaths_soc"]) * P["vsl_cny"])
                       / base["annual_cost_cny_soc"].clip(lower=1))
    base.to_csv(C.RESULTS / "q5_baselines.csv")

    # ---------- figures ----------
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9), layout="constrained")
    for ax, city in zip(axes, ["Zhengzhou", "Haikou"]):
        sub = grid[grid["city"] == city]
        for g, mk in zip(GREEN, ["o", "s", "^"]):
            s2 = sub[sub["green"] == g].sort_values("annual_cost_cny")
            ax.plot(s2["annual_cost_cny"] / 1e8, s2["total_social_cny"] / 1e8, marker=mk, ms=2.5,
                    lw=0.9, label=f"{int(g * 100)}% source control")
        r = best_soc.loc[city]
        ax.scatter(r["annual_cost_cny"] / 1e8, r["total_social_cny"] / 1e8, marker="*", s=90,
                   color="#b5342c", zorder=5, label="social optimum")
        ax.set_xlabel("Annualised investment (100 million CNY/yr)")
        ax.set_ylabel("Total annual cost (damage + lives)")
        ax.set_title(f"{city}: total-cost frontier")
        ax.legend(fontsize=6)
    fig.savefig(C.FIGS / "fig20_cost_damage_frontier.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.8, 2.9))
    xs = np.arange(len(base))
    ax.bar(xs - 0.2, base["bcr_econ"], width=0.36, color="#2f6f9f", label="economic only")
    ax.bar(xs + 0.2, base["bcr_soc"], width=0.36, color="#b5342c", label="incl. value of life")
    ax.axhline(1.0, color="k", lw=0.8, ls="--")
    ax.set_xticks(xs)
    ax.set_xticklabels(base.index, fontsize=7.5)
    ax.set_ylabel("Benefit-cost ratio at the optimum")
    ax.set_title("Does protection pay for itself?")
    ax.legend(fontsize=7)
    fig.savefig(C.FIGS / "fig21_bcr.png")
    plt.close(fig)

    # sensitivity on Zhengzhou: damage density x storage cost -> optimal design return period
    dmg_grid = [40, 80, 120, 250, 500]
    stor_grid = [300, 500, 800, 1500, 3000]
    heat = np.zeros((len(dmg_grid), len(stor_grid)))
    heat_s = np.zeros_like(heat)
    fitz = C.gev_fit_lmom(am_z["rx3day"].to_numpy(dtype=float))
    rainz = am_z["rx3day"].to_numpy(dtype=float)
    rlz = {t: rl3(fitz, t) for t in T_PIPE}
    area_z = zc["area_km2"]
    v2021_z = float(volume_m3(overflow_depth(np.array([REF_RAIN]), zc["cn"], rlz[2])[0], area_z))
    for i, d in enumerate(dmg_grid):
        for j, sc in enumerate(stor_grid):
            best_t, best_s_t, best_tot, best_s = np.nan, np.nan, np.inf, np.inf
            for t in T_PIPE:
                for s_mm in S_DEPTH:
                    ead, cvar, deaths, _ = evaluate(rainz, zc["cn"], rlz[t] + s_mm, area_z,
                                                    OFFICIAL_LOSS * d, over_ref,
                                                    P["damage_exponent"], zc["deaths_ref"],
                                                    P["deaths_elasticity"], v_ref)
                    capex = (P["pipe_cost_per_mm_km2"] * area_z * max(0.0, rlz[t] - rlz[2])
                             + sc * s_mm * area_z * 1e3)
                    annual = (crf(P["discount"], P["horizon"]) + P["om_share"]) * capex
                    if annual + ead < best_tot:
                        best_tot, best_t = annual + ead, t
                    social = annual + ead + P["risk_aversion"] * cvar + deaths * P["vsl_cny"]
                    if social < best_s:
                        best_s = social
                        best_s_t = t
            heat[i, j] = best_t
            heat_s[i, j] = best_s_t

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), layout="constrained")
    for ax, mat, title in ((axes[0], heat, "Economic objective"),
                           (axes[1], heat_s, "Including value of life")):
        im = ax.imshow(mat, cmap="YlGnBu", aspect="auto", origin="lower")
        ax.set_xticks(range(len(stor_grid)))
        ax.set_xticklabels(stor_grid, fontsize=6.5)
        ax.set_yticks(range(len(dmg_grid)))
        ax.set_yticklabels(dmg_grid, fontsize=6.5)
        ax.set_xlabel("Storage cost (CNY/m3)")
        ax.set_ylabel("Damage density (CNY/m3)")
        ax.set_title(title)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center", fontsize=6.5)
    fig.colorbar(im, ax=axes, shrink=0.85, label="optimal design return period (years)")
    fig.savefig(C.FIGS / "fig22_sensitivity_tpipe.png")
    plt.close(fig)

    out = {"parameters": P, "cities": CITIES,
           "calibration": {"event_rain_mm": REF_RAIN, "design_depth_mm": cap_ref,
                           "overflow_mm": over_ref, "overflow_Mm3": v_ref / 1e6,
                           "official_loss_cny": OFFICIAL_LOSS},
           "baselines": base.reset_index().to_dict("records"),
           "optimal_economic": best_econ[keep].reset_index().to_dict("records"),
           "optimal_social": best_soc[keep].reset_index().to_dict("records"),
           "sensitivity": {"damage_density": dmg_grid, "storage_cost": stor_grid,
                           "optimal_T_econ": heat.tolist(), "optimal_T_social": heat_s.tolist()},
           "note": "Hazard, capacity and damage all live on the three-day event scale. Damage density "
                   "is calibrated so that the modelled 2021 overflow reproduces the official loss of "
                   "40.9 bn CNY. EAD and expected deaths are historical-simulation means over the "
                   "1961-2020 annual maxima, with no GEV tail extrapolation."}
    C.write_json(out, C.RESULTS / "q5_results.json")

    cols = ["rl2", "rl10", "rl50", "baseline_ead_cny", "baseline_deaths", "stress2021_volume_m3",
            "T_pipe_econ", "storage_mm_econ", "green_econ", "ead_cut_econ_pct", "bcr_econ",
            "T_pipe_soc", "storage_mm_soc", "green_soc", "ead_cut_soc_pct", "deaths_cut_soc_pct",
            "bcr_soc"]
    print(base[cols].round(2).to_string())
    print("\nbcr>1 (econ)?", bool((base["bcr_econ"] > 1).any()),
          "(social)?", bool((base["bcr_soc"] > 1).any()))


if __name__ == "__main__":
    main()