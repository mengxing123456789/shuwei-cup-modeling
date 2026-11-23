#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q1: interannual variability of Zhengzhou precipitation, wet-year identification, and a
quantitative account of the July 2021 urban waterlogging event.

Primary trend source: GHCN-Daily CHM00057083 (1951-2025, 6.6% missing).
Event source: the official attachment station 57083099999 (GSOD), cross-checked with GHCN.
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

BASE = (1961, 2020)
GH_ID, GS_ID = "CHM00057083", "57083099999"
plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 7.5,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "grid.linestyle": ":"})
BLUE, ORANGE, RED, GREY, GREEN = "#2f6f9f", "#e08a1e", "#b5342c", "#6b6b6b", "#3f7d5a"


def ghcn_daily() -> pd.DataFrame:
    g = C.load_ghcn_wide(C.RESULTS / "ghcn" / f"{GH_ID}.csv")
    return C.daily_grid(g[["date", "prcp_mm", "tmax_c", "tmin_c"]])


def gsod_daily() -> pd.DataFrame:
    d = pd.read_csv(C.RESULTS / f"daily_{GS_ID}.csv", parse_dates=["date"]).set_index("date")
    return d.asfreq("D")


def window_total(d: pd.DataFrame, month: int, day: int) -> pd.Series:
    out = {}
    for year, g in d.groupby(d.index.year):
        end = pd.Timestamp(year=year, month=month, day=day)
        g = g.loc[:end]
        span = (end - pd.Timestamp(year=year, month=1, day=1)).days + 1
        if len(g) and g["prcp_mm"].notna().sum() >= 0.9 * span:
            out[year] = float(g["prcp_mm"].sum())
    return pd.Series(out).sort_index()


def annual_max_kday(series: pd.Series, k: int) -> pd.Series:
    r = series.rolling(k, min_periods=k).sum()
    return r.groupby(r.index.year).max().dropna()


def trend_row(name: str, x: np.ndarray, years: np.ndarray, period: str) -> dict:
    mk = C.mann_kendall(x)
    sen = C.sen_slope(x, years.astype(float))
    mean = float(np.nanmean(x))
    return {"index": name, "period": period, "n": mk["n"], "mean": mean,
            "mk_tau": mk["tau"], "mk_p": mk["p"], "z": mk["Z"],
            "sen_per_decade": sen["slope"] * 10, "sen_lo": sen["lo"] * 10, "sen_hi": sen["hi"] * 10,
            "change_pct": sen["slope"] * (years.max() - years.min()) / mean * 100 if mean else np.nan}


def main() -> None:
    gh, gs = ghcn_daily(), gsod_daily()
    ai, ai_gs = C.annual_indices(gh[["prcp_mm", "tmax_c", "tmin_c"]]), C.annual_indices(gs[["prcp_mm"]])
    ai.to_csv(C.RESULTS / "q1_annual_indices_ghcn.csv")
    ai_gs.to_csv(C.RESULTS / "q1_annual_indices_gsod.csv")

    lo, hi = BASE
    sub = ai.loc[lo:hi]
    years = sub.index.to_numpy(dtype=float)

    # ---------- trends ----------
    rows = [trend_row(c, sub[c].to_numpy(dtype=float), years, f"{lo}-{hi}")
            for c in ("total", "rx1day", "rx5day", "sdii", "wet_days", "r95p", "r99p", "max_dry_spell")]
    rows += [trend_row(c, ai.loc[1981:hi, c].to_numpy(dtype=float),
                       ai.loc[1981:hi].index.to_numpy(dtype=float), f"1981-{hi}")
             for c in ("total", "rx1day", "r95p")]
    rows += [trend_row(c, ai.loc[1951:2024, c].to_numpy(dtype=float),
                       ai.loc[1951:2024].index.to_numpy(dtype=float), "1951-2024")
             for c in ("total", "rx1day")]
    trends = pd.DataFrame(rows)

    # extreme-day counts + log-linear Poisson trend
    pr = gh["prcp_mm"]
    counts = pd.DataFrame({
        "ge25": pr.where(pr >= 25).groupby(pr.index.year).count(),
        "ge50": pr.where(pr >= 50).groupby(pr.index.year).count(),
        "ge100": pr.where(pr >= 100).groupby(pr.index.year).count()}).fillna(0).astype(int)
    counts.to_csv(C.RESULTS / "q1_extreme_day_counts.csv")
    poisson = {}
    for c in counts.columns:
        cc = counts.loc[lo:hi, c]
        poisson[c] = C.poisson_trend(cc.index.to_numpy(dtype=float), cc.to_numpy(dtype=float))
    trends.to_csv(C.RESULTS / "q1_trends.csv", index=False)

    # ---------- change points ----------
    cp_total = C.pettitt_change_point(sub["total"].to_numpy(dtype=float))
    cp_rx = C.pettitt_change_point(sub["rx1day"].to_numpy(dtype=float))
    cp_total["year"] = int(sub.index[cp_total["idx"] - 1]) if cp_total["idx"] else None
    cp_rx["year"] = int(sub.index[cp_rx["idx"] - 1]) if cp_rx["idx"] else None

    # ---------- GEV ----------
    am = sub["rx1day"].to_numpy(dtype=float)
    fit = C.gev_fit(am)
    rls = []
    for T in (2, 5, 10, 20, 50, 100):
        ci = C.gev_bootstrap_ci(am, T, n_boot=1000)
        rls.append({"T": T, "level_mm": ci["rl"], "lo95": ci["lo"], "hi95": ci["hi"]})
    rl = pd.DataFrame(rls)
    rl.to_csv(C.RESULTS / "q1_return_levels_daily.csv", index=False)

    m3 = annual_max_kday(gh.loc[f"{lo}-01-01":f"{hi}-12-31", "prcp_mm"], 3)
    fit3 = C.gev_fit(m3.to_numpy(dtype=float))
    rl3 = pd.DataFrame([{"T": T, "level_mm": C.gev_return_level(fit3, T)} for T in (2, 5, 10, 20, 50, 100)])
    rl3.to_csv(C.RESULTS / "q1_return_levels_3day.csv", index=False)

    # ---------- the 2021 event ----------
    ev = gh.loc["2021-07-15":"2021-07-25", "prcp_mm"]
    peak = float(ev.max())
    peak_date = ev.idxmax()
    tri = float(ev.rolling(3, min_periods=3).sum().max())
    tri_end = ev.rolling(3, min_periods=3).sum().idxmax()
    sev = float(ev.rolling(7, min_periods=7).sum().max())
    y21 = gh.loc["2021-01-01":"2021-11-05", "prcp_mm"]
    tot21 = float(y21.sum())
    win = window_total(gh, 11, 5).loc[lo:2020]
    z21 = float((tot21 - win.mean()) / win.std(ddof=1))
    pct21 = float((win < tot21).mean() * 100)

    all_daily = ai["rx1day"]
    rank_daily = int((all_daily > peak).sum() + 1)
    all_tri = annual_max_kday(gh["prcp_mm"], 3)
    rank_tri = int((all_tri > tri).sum() + 1)
    emp_rp = C.empirical_return_period(peak, am)
    rp_daily = C.gev_return_period_of_value(am, peak, n_boot=500)
    rp_tri = C.gev_return_period_of_value(m3.to_numpy(dtype=float), tri, n_boot=500)
    rp_official = C.gev_return_period_of_value(am, 449.0, n_boot=300)

    july = float(gh.loc["2021-07-01":"2021-07-31", "prcp_mm"].sum())
    july_clim = gh.loc["1991-01-01":"2020-12-31", "prcp_mm"]
    july_mean = float(july_clim[july_clim.index.month == 7].groupby(july_clim[july_clim.index.month == 7].index.year).sum().mean())
    aug_mean = float(july_clim[july_clim.index.month == 8].groupby(july_clim[july_clim.index.month == 8].index.year).sum().mean())

    # ---------- waterlogging quantification ----------
    area = 1180.0                      # built-up area, km2 (sensitivity 1000-1300)
    cn_grid = {cn: (lambda s, ia: (tri - ia) ** 2 / (tri + 0.8 * s) if tri > ia else 0.0)(25400 / cn - 254, 0.2 * (25400 / cn - 254))
               for cn in (75, 80, 85, 90, 95)}
    runoff = cn_grid[85]
    vol_m3 = runoff / 1000.0 * area * 1e6
    vol_official_m3 = (lambda s, ia: ((449 - ia) ** 2 / (449 + 0.8 * s) if 449 > ia else 0.0))(25400 / 85 - 254, 0.2 * (25400 / 85 - 254)) / 1000.0 * area * 1e6
    peak_hour = 201.9                  # official 16:00-17:00 record, quoted in the problem statement
    # The peak hour is routed through the same curve-number model as the event total, so the
    # excess is a runoff volume, not a depth-times-area shortcut (an earlier version applied a
    # 0.9 factor with no derivation; that value is superseded).
    s85 = 25400 / 85 - 254
    ia85 = 0.2 * s85
    q_peak = (peak_hour - ia85) ** 2 / (peak_hour + 0.8 * s85) if peak_hour > ia85 else 0.0
    drainage = {}
    for label, cap in (("design_1yr_36mmh", 36.0), ("design_2yr_43mmh", 43.0), ("design_3yr_50mmh", 50.0)):
        excess = max(q_peak - cap, 0.0) / 1000.0 * area * 1e6
        drainage[label] = {"capacity_mm_per_h": cap, "peak_ratio": peak_hour / cap,
                           "peak_runoff_mm": q_peak, "excess_volume_m3": excess,
                           # drainage time is quoted on the runoff that the network must remove,
                           # not on the rainfall depth (the difference is the curve-number loss)
                           "hours_to_drain_3day_runoff": runoff / cap,
                           "hours_to_drain_3day_rainfall": tri / cap}

    # ---------- wet years ----------
    mu, sd = float(sub["total"].mean()), float(sub["total"].std(ddof=1))
    q75 = float(sub["total"].quantile(0.75))
    wy = pd.DataFrame({"year": sub.index, "total": sub["total"].values, "z": (sub["total"].values - mu) / sd})
    wy["class"] = np.where(wy["total"] > mu + sd, "very wet", np.where(wy["total"] > q75, "wet", "normal"))
    wy.sort_values("total", ascending=False).to_csv(C.RESULTS / "q1_wet_years.csv", index=False)
    wet_years = wy.wy.sort_values if False else wy.sort_values("total", ascending=False)

    # ---------- figures ----------
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.bar(sub.index, sub["total"], color=BLUE, alpha=0.55, label="Annual total (GHCN 1961-2020)")
    sen = C.sen_slope(sub["total"].to_numpy(dtype=float), years)
    ax.plot(sub.index, sub["total"].iloc[0] + sen["slope"] * (sub.index - sub.index[0]), color=RED, lw=1.4,
            label=f"Sen slope {sen['slope']*10:+.0f} mm/decade (p={trends.loc[0,'mk_p']:.2f})")
    ax.axhline(mu, color=GREY, ls=":", lw=0.9)
    ax.errorbar([2021], [tot21], yerr=[[0], [0]], fmt="D", color=ORANGE, ms=5, zorder=6,
                label=f"2021 Jan 1-Nov 5 = {tot21:.0f} mm ({pct21:.0f}th pct)")
    ax.set_ylabel("Precipitation (mm)")
    ax.set_title("Zhengzhou annual precipitation: no significant monotonic trend, high interannual variability")
    ax.legend(loc="upper left", frameon=False, ncol=1)
    fig.savefig(C.FIGS / "fig01_annual_total.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]
    ax.plot(sub.index, sub["rx1day"], color=BLUE, lw=1.0, marker="o", ms=2.5, label="Annual Rx1day")
    ax.scatter([2021], [peak], color=ORANGE, marker="D", s=34, zorder=6, label=f"2021: {peak:.0f} mm")
    ax.annotate(f"{peak:.0f} mm on {peak_date.date()}\nrank {rank_daily} of {len(all_daily)} years",
                (2021, peak), xytext=(1994, 175), fontsize=7.2, color=ORANGE,
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=0.8))
    ax.set_ylabel("Rx1day (mm/day)")
    ax.set_title("Annual maximum daily precipitation")
    ax.legend(frameon=False, loc="lower left")
    ax = axes[1]
    Ts = np.logspace(np.log10(2), np.log10(200), 120)
    lev = np.array([C.gev_return_level(fit, T) for T in Ts])
    ax.plot(Ts, lev, color=RED, lw=1.3)
    band = rl.set_index("T")
    ax.fill_between(band.index, band["lo95"], band["hi95"], color=RED, alpha=0.18, label="95% bootstrap band")
    ax.scatter([rp_daily["rp_yr"]], [peak], color=ORANGE, zorder=5, s=26)
    ax.set_xscale("log")
    ax.set_xlabel("Return period (years)")
    ax.set_ylabel("Return level (mm/day)")
    ax.set_title(f"GEV fit (xi = {fit['xi']:+.2f})")
    ax.legend(frameon=False, loc="upper left")
    fig.savefig(C.FIGS / "fig02_rx1day_gev.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    months = np.arange(1, 13)
    clim = [float(july_clim[july_clim.index.month == m].groupby(july_clim[july_clim.index.month == m].index.year).sum().mean()) for m in months]
    m21 = gh.loc["2021-01-01":"2021-11-05", "prcp_mm"].groupby(gh.loc["2021-01-01":"2021-11-05"].index.month)
    m21 = [float(m21.get_group(m).sum()) if m in m21.groups else 0.0 for m in months]
    ax.bar(months - 0.18, clim, width=0.34, color=GREY, alpha=0.55, label="1991-2020 mean")
    ax.bar(months + 0.18, m21, width=0.34, color=BLUE, label="2021")
    ax.set_xticks(months)
    ax.set_xlabel("Month")
    ax.set_ylabel("Monthly total (mm)")
    ax.set_title(f"July 2021 = {m21[6]:.0f} mm, {m21[6]/clim[6]:.1f} x the 1991-2020 July mean ({clim[6]:.0f} mm)")
    ax.legend(frameon=False)
    fig.savefig(C.FIGS / "fig03_monthly_2021.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    dec = counts.loc[lo:hi].groupby((counts.loc[lo:hi].index // 10) * 10).sum()
    x = np.arange(len(dec))
    ax.bar(x - 0.2, dec["ge50"], width=0.36, color=BLUE, label="Days with P >= 50 mm")
    ax.bar(x + 0.2, dec["ge100"], width=0.36, color=RED, label="Days with P >= 100 mm")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{i}s" for i in dec.index])
    ax.set_ylabel("Days per decade")
    ax.set_title("Extreme precipitation days per decade (Poisson trend: {:+.0f}%/decade, p={:.3f})".format(
        poisson["ge50"]["pct_per_decade"], poisson["ge50"]["p"]))
    ax.legend(frameon=False)
    fig.savefig(C.FIGS / "fig04_extreme_days.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    seq = gh.loc["2021-06-01":"2021-09-30", "prcp_mm"]
    ax.bar(seq.index, seq.values, color=BLUE, width=0.9)
    p95w = float(np.percentile(gh.loc[f"{lo}-01-01":f"{hi}-12-31", "prcp_mm"].dropna().loc[lambda s: s >= 0.1], 95))
    ax.axhline(p95w, color=RED, ls="--", lw=1, label=f"wet-day P95 (1961-2020) = {p95w:.0f} mm")
    ax.axhline(50, color=GREY, ls=":", lw=0.9, label="50 mm heavy-rain threshold")
    ax.annotate(f"{peak:.0f} mm on {peak_date.date()}", (peak_date, peak), xytext=(pd.Timestamp("2021-08-12"), peak * 0.82),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.set_ylabel("Daily precipitation (mm)")
    ax.set_title("The July 2021 storm in the daily record")
    ax.legend(frameon=False, loc="upper right")
    fig.savefig(C.FIGS / "fig05_event_profile.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    labels = ["Daily peak\n(188.7 mm)", "3-day total\n(313.4 mm)", "Official 3-day\n(449 mm)"]
    vals = [rp_daily["rp_yr"], rp_tri["rp_yr"], rp_official["rp_yr"]]
    lo_err = [max(v - l, 0) for v, l in zip(vals, [rp_daily["lo95"], rp_tri["lo95"], rp_official["lo95"]])]
    hi_err = [h - v for v, h in zip(vals, [rp_daily["hi95"], rp_tri["hi95"], rp_official["hi95"]])]
    ax.bar(labels, vals, color=[BLUE, ORANGE, RED], alpha=0.8, width=0.55)
    ax.errorbar(labels, vals, yerr=[lo_err, hi_err], fmt="none", ecolor="k", capsize=4, lw=1)
    ax.set_yscale("log")
    ax.set_ylabel("GEV return period (years, log scale)")
    ax.set_title("Return periods of the July 2021 rainfall under the 1961-2020 GEV model")
    for i, v in enumerate(vals):
        ax.text(i, v * 1.35, f"{v:,.0f} yr", ha="center", fontsize=7.5)
    fig.savefig(C.FIGS / "fig06_event_return_periods.png")
    plt.close(fig)

    out = {
        "sources": {"trend": GH_ID, "event": GS_ID, "baseline": f"{lo}-{hi}"},
        "n_years": int(sub.shape[0]), "mean_total_mm": mu, "sd_total_mm": sd, "cv": sd / mu,
        "q75_mm": q75, "trends": trends.to_dict("records"), "poisson_counts": poisson,
        "pettitt_total": cp_total, "pettitt_rx1day": cp_rx,
        "gev_daily": fit, "return_levels_daily": rls,
        "gev_3day": fit3, "return_levels_3day": rl3.to_dict("records"),
        "event": {"peak_date": str(peak_date.date()), "peak_mm": peak, "peak_rank": rank_daily,
                  "years_in_record": int(len(all_daily)),
                  "three_day_mm": tri, "three_day_end": str(tri_end.date()), "three_day_rank": rank_tri,
                  "seven_day_mm": sev, "empirical_rp_daily_yr": emp_rp,
                  "gev_rp_daily": rp_daily, "gev_rp_3day": rp_tri, "gev_rp_official_449mm": rp_official,
                  "july_2021_mm": july, "july_climatology_mm": july_mean, "july_ratio": july / july_mean,
                  "august_climatology_mm": aug_mean, "annual_2021_jan_nov_mm": tot21,
                  "annual_2021_percentile": pct21, "annual_2021_z": z21,
                  "official_3day_mm": 449.0, "official_peak_hour_mm": peak_hour,
                  "station_vs_official_ratio": tri / 449.0},
        "waterlogging": {"area_km2": area, "three_day_mm": tri, "runoff_mm_by_cn": cn_grid,
                         "runoff_depth_mm_cn85": runoff, "runoff_volume_m3_cn85": vol_m3,
                         "runoff_volume_m3_official_449_cn85": vol_official_m3,
                         "peak_hour_mm": peak_hour, "drainage": drainage},
        "wet_years_top5": wet_years.head(5).to_dict("records"),
    }
    C.write_json(out, C.RESULTS / "q1_results.json")

    print("n", out["n_years"], "mean", round(mu, 1), "sd", round(sd, 1), "cv", round(sd / mu, 2))
    print(trends.round(3).to_string(index=False))
    print("poisson", {k: {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in poisson.items()})
    print("pettitt total", cp_total, "\npettitt rx1", cp_rx)
    print(rl.round(1).to_string(index=False))
    print("event", {k: (v if not isinstance(v, float) else round(v, 2)) for k, v in out["event"].items()})
    print("waterlogging", out["waterlogging"])
    print("wet5", out["wet_years_top5"])


if __name__ == "__main__":
    main()