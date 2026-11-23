#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q5 figure: uniform capacity versus hotspot protection, same money, same city.

Reads q5_portfolio_grid.csv (uniform menu) and q5_selective_protection.csv (hotspot menu)
and draws the best benefit-cost ratio each menu can reach, so the comparison in the text is
visible rather than asserted.
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
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "grid.linestyle": ":"})

CITIES = ["Guangzhou", "Haikou", "Zhengzhou"]


def main() -> None:
    grid = pd.read_csv(C.RESULTS / "q5_portfolio_grid.csv")
    base = pd.read_csv(C.RESULTS / "q5_baselines.csv").set_index("city")
    sel = pd.read_csv(C.RESULTS / "q5_selective_protection.csv")

    # uniform: best ratio on the grid, using the no-investment EAD as the counterfactual
    rows = []
    for city in CITIES:
        sub = grid[grid["city"] == city]
        ead0 = float(base.loc[city, "baseline_ead_cny"])
        bcr = (ead0 - sub["ead_cny"]) / sub["annual_cost_cny"].clip(lower=1.0)
        rows.append({"city": city, "menu": "uniform", "bcr": float(bcr.max())})
        rows.append({"city": city, "menu": "hotspot",
                     "bcr": float(sel.loc[sel["city"] == city, "bcr"].max())})
    d = pd.DataFrame(rows).pivot(index="city", columns="menu", values="bcr").loc[CITIES]
    d.to_csv(C.RESULTS / "q5_menu_comparison.csv")

    fig, ax = plt.subplots(figsize=(4.6, 2.7))
    xs = np.arange(len(d))
    ax.bar(xs - 0.19, d["uniform"], width=0.36, color="#2f6f9f",
           label="uniform capacity (best of 126)")
    ax.bar(xs + 0.19, d["hotspot"], width=0.36, color="#b5342c",
           label="hotspot protection (best of 15)")
    ax.axhline(1.0, color="k", lw=0.8, ls="--")
    for i, (u, h) in enumerate(zip(d["uniform"], d["hotspot"])):
        ax.text(i - 0.19, u + 0.08, f"{u:.2f}", ha="center", fontsize=7)
        ax.text(i + 0.19, h + 0.08, f"{h:.2f}", ha="center", fontsize=7)
    ax.set_xticks(xs)
    ax.set_xticklabels(d.index, fontsize=8)
    ax.set_ylabel("Best benefit--cost ratio")
    ax.set_ylim(0, max(d["hotspot"].max(), 1.0) * 1.22)
    ax.set_title("Same city, same money: what each menu can reach")
    ax.legend(fontsize=7, loc="upper right")
    fig.savefig(C.FIGS / "fig21_bcr.png")
    plt.close(fig)
    print(d.round(3).to_string())


if __name__ == "__main__":
    main()
