#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q5 (continued): is targeted protection of the damage hotspots cost-effective where a
city-wide uniform upgrade is not?

A hotspot is a small share h of the built-up area that produces a disproportionate share of
the damage (subway stations, underpasses, low-lying districts). Storage is installed only there."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import common as C
from s06_q5 import (CITIES, P, T_PIPE, S_DEPTH, OFFICIAL_LOSS, REF_RAIN, crf,
                    scs_runoff, overflow_depth, load_annual, rl3)

H_SHARE = [0.02, 0.05, 0.10]
MULT = [5.0, 10.0, 20.0]


def reference_overflow() -> float:
    """The damage anchor is shared with s06_q5: the 2021 Zhengzhou event."""
    cfg = CITIES["Zhengzhou"]
    am = load_annual(cfg["id"])
    fit = C.gev_fit_lmom(am["rx3day"].to_numpy(dtype=float))
    return float(overflow_depth(np.array([REF_RAIN]), cfg["cn"], rl3(fit, 2))[0])


def city_ref_loss(area_km2: float, area_z: float, gamma: float) -> float:
    """Loss scale for a city: the Zhengzhou anchor scaled by built-up area.

    Damage is a power law in overflow volume, so at equal overflow depth a city of area A
    loses (A/A_Z)^gamma times what Zhengzhou loses; a linear factor would disagree with
    s06_q5.evaluate, which integrates volumes.
    """
    return OFFICIAL_LOSS * (area_km2 / area_z) ** gamma


def main() -> None:
    rows = []
    over_ref = reference_overflow()
    area_z = CITIES["Zhengzhou"]["area_km2"]
    print(f"[anchor] shared over_ref = {over_ref:.2f} mm")
    for city, cfg in CITIES.items():
        am = load_annual(cfg["id"])
        rain3 = am["rx3day"].to_numpy(dtype=float)
        area = cfg["area_km2"]
        loss_city = city_ref_loss(area, area_z, P["damage_exponent"])
        fit = C.gev_fit_lmom(rain3)
        rl = {t: rl3(fit, t) for t in T_PIPE}
        runoff = scs_runoff(rain3, cfg["cn"])
        over0 = np.maximum(0.0, runoff - rl[2])
        dmg_year = loss_city * (over0 / over_ref) ** P["damage_exponent"]
        ead_total = float(np.mean(dmg_year))
        for h in H_SHARE:
            for m in MULT:
                w = m * h / (m * h + (1 - h))          # share of city damage inside the hotspot
                hot_ead = ead_total * w
                for s_mm in S_DEPTH:
                    reduced = loss_city * w * np.power(
                        np.clip((runoff - (rl[2] + s_mm)) / over_ref, 0.0, None),
                        P["damage_exponent"])
                    hot_after = float(np.mean(reduced))
                    capex = P["storage_cost_per_m3"] * s_mm * h * area * 1e3
                    annual = (crf(P["discount"], P["horizon"]) + P["om_share"]) * capex
                    avoided = hot_ead - hot_after
                    rows.append({"city": city, "hotspot_share": h, "damage_multiplier": m,
                                 "storage_mm": s_mm, "hotspot_ead_cny": hot_ead,
                                 "ead_after_cny": hot_after, "capex_cny": capex,
                                 "annual_cost_cny": annual,
                                 "bcr": avoided / annual if annual > 0 else np.nan,
                                 "avoided_cny": avoided})
    df = pd.DataFrame(rows)
    df.to_csv(C.RESULTS / "q5_selective_protection.csv", index=False)
    best = df.sort_values("bcr", ascending=False).groupby(["city", "hotspot_share",
                                                           "damage_multiplier"]).head(1)
    print(best[["city", "hotspot_share", "damage_multiplier", "storage_mm", "bcr",
                "caption"] if "caption" in best.columns else
         ["city", "hotspot_share", "damage_multiplier", "storage_mm", "bcr"]]
          .round(2).to_string(index=False))
    print("\nany bcr>1?", bool((df["bcr"] > 1).any()), "max", round(float(df["bcr"].max()), 2))


if __name__ == "__main__":
    main()