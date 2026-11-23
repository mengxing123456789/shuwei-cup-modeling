#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q4: are the Zhengzhou July 2021 and Shanxi October 2021 rainstorms the same phenomenon,
and why do their losses differ by an order of magnitude?

Data: GHCN-Daily station series (same source as Q1-Q3) plus officially reported loss figures
(State Council investigation report for Henan; Shanxi provincial government press conference,
both cited in the paper)."""
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

EVENTS = {
    "Zhengzhou": {"id": "CHM00057083", "start": "2021-07-17", "end": "2021-07-23", "core": True},
    "Taiyuan": {"id": "CHM00053772", "start": "2021-10-01", "end": "2021-10-07", "core": True},
    "Yuncheng": {"id": "CHM00053959", "start": "2021-10-01", "end": "2021-10-07", "core": False},
    "Station53975": {"id": "53975099999", "start": "2021-10-01", "end": "2021-10-07", "core": False},
}

# Officially reported impact, cited in the paper (losses in 1e8 CNY, areas in km2).
OFFICIAL = {
    "Zhengzhou city": {"deaths": 380, "affected": np.nan, "loss": 409.0, "area": 7567.0,
                       "pop": 12.60e6, "rain_mm": 449.0, "rain_note": "3-day city areal total (official)"},
    "Henan province": {"deaths": 398, "affected": 1478.6e4, "loss": 1200.6, "area": 167000.0,
                       "pop": 99.37e6, "rain_mm": 449.0, "rain_note": "3-day city areal total (official)"},
    "Shanxi province": {"deaths": 18, "affected": 175.71e4, "loss": 50.29, "area": 156700.0,
                        "pop": 34.80e6, "rain_mm": 120.0, "rain_note": "4-day provincial mean, 109 stations"},
}


def load_daily(sid: str) -> pd.Series:
    if sid.startswith("CHM"):
        g = C.load_ghcn_wide(C.RESULTS / "ghcn" / f"{sid}.csv")
        return C.daily_grid(g[["date", "prcp_mm"]])["prcp_mm"]
    att = pd.read_csv(C.RESULTS / "attachment_daily_tidy.csv", parse_dates=["date"])
    return C.daily_grid(att.loc[att["station"].astype(str) == sid, ["date", "prcp_mm"]])["prcp_mm"]


def window_metrics(s: pd.Series, start: str, end: str) -> dict:
    win = s.loc[start:end]
    x = win.dropna()
    v = x.to_numpy(dtype=float)
    tot = float(v.sum())
    roll = {f"max{k}d": float(pd.Series(v).rolling(k, min_periods=k).sum().max()) for k in (1, 2, 3, 5, 7)}
    run, best = 0, 0
    for z in v:
        run = run + 1 if z >= 0.1 else 0
        best = max(best, run)
    return {"days_in_window": int(len(win)), "days_with_data": int(len(v)), "total_mm": tot, **roll,
            "wet_days": int((v >= 0.1).sum()), "days_ge25": int((v >= 25).sum()),
            "days_ge50": int((v >= 50).sum()), "max_wet_run": best,
            "mean_wet_day_mm": float(v[v >= 0.1].mean()) if (v >= 0.1).any() else np.nan,
            "ratio_1d_3d": roll["max1d"] / roll["max3d"] if roll["max3d"] else np.nan,
            "share_top_day": roll["max1d"] / tot if tot else np.nan}


def annual_max_series(s: pd.Series, k: int) -> pd.Series:
    roll = s.rolling(k, min_periods=k).sum()
    out = roll.groupby(roll.index.year).max()
    valid = s.groupby(s.index.year).apply(lambda z: int(z.notna().sum()))
    return out[valid >= 300]


def climatological_shape(s: pd.Series) -> pd.DataFrame:
    """Concentration / duration of the wettest 7-day window of every year with enough data."""
    roll = s.rolling(7, min_periods=7).sum()
    rows = []
    for year, g in roll.groupby(roll.index.year):
        if s.loc[str(year)].notna().sum() < 300 or g.isna().all():
            continue
        end = g.idxmax()
        win = s.loc[end - pd.Timedelta(days=6):end]
        if win.isna().sum() > 0 or win.sum() < 50:
            continue
        rows.append({"year": year, "total": float(win.sum()), "max1d": float(win.max()),
                     "concentration": float(win.max() / win.sum()),
                     "ratio_1d_3d": float(win.max() / win.rolling(3, min_periods=3).sum().max()),
                     "wet_days": int((win >= 0.1).sum())})
    return pd.DataFrame(rows)


def main() -> None:
    rows, series = [], {}
    for name, ev in EVENTS.items():
        s = load_daily(ev["id"])
        series[name] = s
        m = {"event": name, "station": ev["id"], "in_core_belt": ev["core"],
             "window": f'{ev["start"]}..{ev["end"]}'}
        m.update(window_metrics(s, ev["start"], ev["end"]))
        clim = climatological_shape(s)
        for k in (1, 3):
            am = annual_max_series(s, k).dropna().to_numpy(dtype=float)
            fit = C.gev_fit_lmom(am)
            p = C.gev_exceed_prob(fit, m[f"max{k}d"])
            m[f"rp{k}d_years"] = float(1 / p) if p > 0 else np.inf
            m[f"rl10_{k}d"] = C.gev_return_level(fit, 10)
        m["clim_ratio_1d_3d_median"] = float(clim["ratio_1d_3d"].median())
        m["pct_ratio_1d_3d"] = float((clim["ratio_1d_3d"] <= m["ratio_1d_3d"]).mean() * 100)
        m["clim_concentration_median"] = float(clim["concentration"].median())
        m["pct_concentration"] = float((clim["concentration"] <= m["share_top_day"]).mean() * 100)
        m["clim_wet_days_median"] = float(clim["wet_days"].median())
        m["pct_wet_days"] = float((clim["wet_days"] <= m["wet_days"]).mean() * 100)
        rows.append(m)
    idx = pd.DataFrame(rows).set_index("event")
    idx.to_csv(C.RESULTS / "q4_event_indices.csv")

    # ---------- loss comparison ----------
    loss = pd.DataFrame([{"event": k, **v} for k, v in OFFICIAL.items()]).set_index("event")
    loss["loss_per_mm_1e4cny"] = loss["loss"] * 1e4 / loss["rain_mm"]
    loss["loss_per_affected_cny"] = loss["loss"] * 1e8 / loss["affected"]
    loss["deaths_per_million_affected"] = loss["deaths"] / (loss["affected"] / 1e6)
    loss["loss_per_km2_1e4cny"] = loss["loss"] * 1e4 / loss["area"]
    loss["pop_density_per_km2"] = loss["pop"] / loss["area"]
    loss["affected_share"] = loss["affected"] / loss["pop"]
    loss["loss_per_capita_cny"] = loss["loss"] * 1e8 / loss["pop"]
    loss.to_csv(C.RESULTS / "q4_loss_table.csv")

    # ---------- figures ----------
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9))
    ax = axes[0]
    wz = series["Zhengzhou"].loc["2021-07-17":"2021-07-23"]
    ax.bar(range(len(wz)), wz.values, color="#b5342c", width=0.65)
    ax.axhline(50, color="k", lw=0.7, ls="--")
    ax.set_xticks(range(len(wz)))
    ax.set_xticklabels([d.strftime("%m-%d") for d in wz.index], fontsize=6.5, rotation=45)
    ax.set_ylabel("Daily precipitation (mm)")
    ax.set_title("A: Zhengzhou, 17-23 July 2021")
    ax.annotate("peak hour 201.9 mm\n(20 Jul, 16-17 h)", xy=(3, 188.7), xytext=(0.3, 160),
                fontsize=7, arrowprops=dict(arrowstyle="->", lw=0.7))
    ax = axes[1]
    for name, color, ls in (("Taiyuan", "#2f6f9f", "-"), ("Yuncheng", "#3f7d5a", "--"),
                            ("Station53975", "#7b5ea7", ":")):
        w = series[name].loc["2021-10-01":"2021-10-07"]
        ax.plot(range(len(w)), w.values, marker="o", ms=3, lw=1.2, color=color, ls=ls, label=name)
    ax.axhline(50, color="k", lw=0.7, ls="--")
    ax.set_xticks(range(7))
    ax.set_xticklabels(["10-01", "10-02", "10-03", "10-04", "10-05", "10-06", "10-07"], fontsize=6.5, rotation=45)
    ax.set_ylabel("Daily precipitation (mm)")
    ax.set_title("B: Shanxi stations, 1-7 October 2021")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(C.FIGS / "fig16_hyetograph.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.4, 2.9))
    for name, color, ls in (("Zhengzhou", "#b5342c", "-"), ("Taiyuan", "#2f6f9f", "-"),
                            ("Yuncheng", "#3f7d5a", "--"), ("Station53975", "#7b5ea7", ":")):
        w = series[name].loc[EVENTS[name]["start"]:EVENTS[name]["end"]].dropna()
        ax.plot(range(1, len(w) + 1), np.cumsum(w.values) / w.sum(), marker="o", ms=3, lw=1.2,
                color=color, ls=ls, label=f"{name} ({w.sum():.0f} mm)")
    ax.plot([1, 7], [1 / 7, 1.0], color="grey", ls=":", lw=0.9, label="perfectly uniform")
    ax.set_xlabel("Day of the event")
    ax.set_ylabel("Cumulative share of event rainfall")
    ax.set_title("How concentrated was each storm?")
    ax.legend(loc="lower right", fontsize=6.5)
    fig.savefig(C.FIGS / "fig17_concentration.png")
    plt.close(fig)

    # return-period ladder: station daily maxima of the event vs the 10-year level
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    core = idx.loc[["Zhengzhou", "Taiyuan"]]
    ax.bar([0, 1], core["rp1d_years"], width=0.55, color=["#b5342c", "#2f6f9f"])
    for i, (name, r) in enumerate(core.iterrows()):
        ax.text(i, r["rp1d_years"] * 1.15, f'{r["max1d"]:.1f} mm\nRP={r["rp1d_years"]:.1f} yr',
                ha="center", fontsize=7)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(core.index, fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("Return period of the largest daily total (years)")
    ax.set_title("Daily intensity: a 1-in-100 year day vs a 1-in-10 year day")
    ax.set_ylim(1, 400)
    fig.savefig(C.FIGS / "fig18_return_period_ladder.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), layout="constrained")
    prov = loss.loc[["Henan province", "Shanxi province"]]
    xpos = np.arange(len(prov))
    ax = axes[0]
    ax.bar(xpos - 0.2, prov["loss_per_km2_1e4cny"], width=0.38, color="#2f6f9f",
           label="loss per km2 (1e4 CNY)")
    ax.bar(xpos + 0.2, prov["loss_per_affected_cny"] / 1e2, width=0.38, color="#b5342c",
           label="loss per affected person (1e2 CNY)")
    ax.set_xticks(xpos)
    ax.set_xticklabels(prov.index, fontsize=7.5)
    ax.set_yscale("log")
    ax.set_title("Economic loss, two normalisations")
    ax.legend(fontsize=6.5)
    ax = axes[1]
    ax.bar(xpos - 0.2, prov["deaths_per_million_affected"], width=0.38, color="#3f7d5a",
           label="deaths per million affected")
    ax.bar(xpos + 0.2, prov["loss_per_mm_1e4cny"], width=0.38, color="#7b5ea7",
           label="loss per mm of event rain (1e4 CNY)")
    ax.set_xticks(xpos)
    ax.set_xticklabels(prov.index, fontsize=7.5)
    ax.set_yscale("log")
    ax.set_title("Human cost and rainfall efficiency")
    ax.legend(fontsize=6.5)
    fig.savefig(C.FIGS / "fig19_loss_normalised.png")
    plt.close(fig)

    # ---------- explicit "same storm type?" decision ----------
    zc = idx.loc["Zhengzhou"]
    ty = idx.loc["Taiyuan"]
    criteria = {
        "rp1d_ratio": float(zc["rp1d_years"] / ty["rp1d_years"]),
        "ratio_1d_3d_gap": float(abs(zc["ratio_1d_3d"] - ty["ratio_1d_3d"])),
        "wet_run_gap_days": float(abs(zc["max_wet_run"] - ty["max_wet_run"])),
    }
    same_type = bool(criteria["rp1d_ratio"] < 3 and criteria["ratio_1d_3d_gap"] < 0.1
                     and criteria["wet_run_gap_days"] <= 1)
    loss_ratios = {
        "henan_vs_shanxi_loss": float(loss.loc["Henan province", "loss"] / loss.loc["Shanxi province", "loss"]),
        "henan_vs_shanxi_loss_per_km2": float(loss.loc["Henan province", "loss_per_km2_1e4cny"]
                                              / loss.loc["Shanxi province", "loss_per_km2_1e4cny"]),
        "henan_vs_shanxi_loss_per_affected": float(loss.loc["Henan province", "loss_per_affected_cny"]
                                                   / loss.loc["Shanxi province", "loss_per_affected_cny"]),
        "henan_vs_shanxi_deaths_per_million": float(loss.loc["Henan province", "deaths_per_million_affected"]
                                                    / loss.loc["Shanxi province", "deaths_per_million_affected"]),
        "henan_vs_shanxi_pop_density": float(loss.loc["Henan province", "pop_density_per_km2"]
                                             / loss.loc["Shanxi province", "pop_density_per_km2"]),
    }
    out = {
        "event_indices": idx.reset_index().to_dict("records"),
        "loss_table": loss.to_dict("records"),
        "official_inputs": OFFICIAL,
        "provincial_note": "Shanxi 4-day provincial mean 120 mm over 109 stations; core belt 100-250 mm "
                           "(Che et al. 2021); Zhengzhou city 3-day areal total 449 mm, peak hour 201.9 mm "
                           "(China Meteorological Administration).",
        "type_criteria": criteria,
        "same_storm_type": same_type,
        "loss_ratios": loss_ratios,
        "decomposition_note": "Loss difference is driven by exposure (population density ratio "
                              f"{loss_ratios['henan_vs_shanxi_pop_density']:.1f}x) and by vulnerability "
                              "(urban underground space, emergency response), not by rainfall volume alone.",
        "decomposition": {
            "density": float(loss.loc["Henan province", "pop_density_per_km2"] / loss.loc["Shanxi province", "pop_density_per_km2"]),
            "affected_share": float(loss.loc["Henan province", "affected_share"] / loss.loc["Shanxi province", "affected_share"]),
            "loss_per_affected": float(loss.loc["Henan province", "loss_per_affected_cny"] / loss.loc["Shanxi province", "loss_per_affected_cny"]),
            "loss_per_capita": float(loss.loc["Henan province", "loss_per_capita_cny"] / loss.loc["Shanxi province", "loss_per_capita_cny"]),
            "identity": "loss/km2 = population density x affected share x loss per affected person",
            "check_product": float(loss.loc["Henan province", "pop_density_per_km2"] / loss.loc["Shanxi province", "pop_density_per_km2"]
                                   * loss.loc["Henan province", "affected_share"] / loss.loc["Shanxi province", "affected_share"]
                                   * loss.loc["Henan province", "loss_per_affected_cny"] / loss.loc["Shanxi province", "loss_per_affected_cny"]),
        },
    }
    C.write_json(out, C.RESULTS / "q4_results.json")

    cols = ["in_core_belt", "days_with_data", "total_mm", "max1d", "max3d", "max_wet_run",
            "ratio_1d_3d", "pct_ratio_1d_3d", "rp1d_years", "rp3d_years", "share_top_day"]
    print(idx[cols].round(2).to_string())
    print()
    print(loss.reset_index()[["event", "loss_per_mm_1e4cny", "loss_per_affected_cny",
                          "deaths_per_million_affected", "loss_per_km2_1e4cny",
                          "pop_density_per_km2"]].round(1).to_string(index=False))
    print("\nsame type?", same_type, "| criteria", {k: round(v, 3) for k, v in criteria.items()})
    print("loss ratios", {k: round(v, 2) for k, v in loss_ratios.items()})


if __name__ == "__main__":
    main()