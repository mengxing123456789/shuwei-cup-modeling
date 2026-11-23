#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q2: multi-city precipitation trends from GHCN-Daily (25 stations, 1961-2020),
including FDR-controlled significance, regional aggregation and data-driven clustering."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import common as C

BASE = (1961, 2020)
MIN_YEARS = 45
plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 7.5,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "grid.linestyle": ":"})
INDICES = ["total", "rx1day", "r95p", "sdii", "wet_days"]

# Frozen station list. The GHCN folder is allowed to grow (extra stations were fetched
# later for other checks), so the panel is defined here rather than by whatever happens
# to sit in the directory: 30 of the 35 downloaded files carry data, 26 clear 45 valid
# years in 1961-2020, and Yan'an (CHM00053845) is excluded on purpose because it belongs
# to neither the Zhengzhou nor the Shanxi comparison.
PANEL_IDS = [
    "CHM00050953", "CHM00051463", "CHM00052866", "CHM00052889", "CHM00053463",
    "CHM00053614", "CHM00053772", "CHM00053959", "CHM00054342", "CHM00054511",
    "CHM00054662", "CHM00054823", "CHM00056778", "CHM00057036", "CHM00057083",
    "CHM00057494", "CHM00057816", "CHM00058238", "CHM00058321", "CHM00058457",
    "CHM00058606", "CHM00058847", "CHM00059287", "CHM00059431", "CHM00059758",
]


def station_meta(path: Path) -> dict:
    head = pd.read_csv(path, nrows=1, dtype=str, keep_default_na=False, skipinitialspace=True)
    head.columns = [c.strip().upper() for c in head.columns]
    row = head.iloc[0]
    return {"id": row["STATION"].strip(), "name": row["NAME"].strip().title(),
            "lat": float(row["LATITUDE"]), "lon": float(row["LONGITUDE"]),
            "elev": float(row["ELEVATION"])}


def bh_fdr(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for rank, idx in enumerate(order[::-1], start=1):
        val = min(prev, p[idx] * n / (n - rank + 1))
        q[idx] = val
        prev = val
    return q


def belt(lat: float, lon: float) -> str:
    if lat < 25:
        return "South"
    if lon < 108:
        return "Southwest" if lat < 32 else "Northwest"
    if lat >= 40 and lon >= 118:
        return "Northeast"
    if lat >= 35:
        return "North China"
    if lat >= 28:
        return "Yangtze"
    return "South"


def main() -> None:
    rows, series = [], {}
    for sid in PANEL_IDS:
        path = C.RESULTS / "ghcn" / f"{sid}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        meta = station_meta(path)
        g = C.load_ghcn_wide(path)
        d = C.daily_grid(g[["date", "prcp_mm"]])
        ai = C.annual_indices(d)
        sub = ai.loc[BASE[0]:BASE[1]]
        if sub.shape[0] < MIN_YEARS:
            continue
        years = sub.index.to_numpy(dtype=float)
        rec = {"id": meta["id"], "city": meta["name"], "lat": meta["lat"], "lon": meta["lon"],
               "elev": meta["elev"], "belt": belt(meta["lat"], meta["lon"]), "n_years": int(sub.shape[0]),
               "mean_total": float(sub["total"].mean()), "cv_total": float(sub["total"].std(ddof=1) / sub["total"].mean()),
               "mean_rx1day": float(sub["rx1day"].mean()), "max_rx1day": float(sub["rx1day"].max()),
               "mean_ge50_days": float(sub["ge50"].mean() if "ge50" in sub else np.nan)}
        for c in INDICES:
            mk = C.mann_kendall(sub[c].to_numpy(dtype=float))
            sen = C.sen_slope(sub[c].to_numpy(dtype=float), years)
            rec[f"{c}_sen"] = sen["slope"] * 10
            rec[f"{c}_sen_lo"] = sen["lo"] * 10
            rec[f"{c}_sen_hi"] = sen["hi"] * 10
            rec[f"{c}_p"] = mk["p"]
            rec[f"{c}_tau"] = mk["tau"]
        pr = d.loc[f"{BASE[0]}-01-01":f"{BASE[1]}-12-31", "prcp_mm"]
        ge50 = pr.where(pr >= 50).groupby(pr.index.year).count().reindex(sub.index).fillna(0)
        ge100 = pr.where(pr >= 100).groupby(pr.index.year).count().reindex(sub.index).fillna(0)
        po = C.poisson_trend(years, ge50.to_numpy(dtype=float))
        rec["ge50_mean"] = float(ge50.mean())
        rec["ge50_pct_per_decade"] = po["pct_per_decade"] if ge50.mean() >= 0.5 else np.nan
        rec["ge50_p"] = po["p"] if ge50.mean() >= 0.5 else np.nan
        rec["ge100_mean"] = float(ge100.mean())
        rows.append(rec)
        series[meta["id"]] = sub

    city = pd.DataFrame(rows).sort_values("lat", ascending=False).reset_index(drop=True)

    # FDR across all city-index tests
    pcols = [f"{c}_p" for c in INDICES] + ["ge50_p"]
    flat = city[pcols].to_numpy(dtype=float).ravel()
    qflat = bh_fdr(flat)
    city_q = pd.DataFrame(qflat.reshape(city[pcols].shape), columns=[c.replace("_p", "_q") for c in pcols],
                         index=city.index)
    city = pd.concat([city, city_q], axis=1)
    for c in INDICES:
        city[f"{c}_sig"] = city[f"{c}_q"] < 0.05
    city["ge50_sig"] = city["ge50_q"] < 0.05
    city.to_csv(C.RESULTS / "q2_city_trends.csv", index=False)

    # regional aggregation: area-free simple mean of standardised anomalies
    region_rows = []
    for belt_name, g in city.groupby("belt"):
        for c in INDICES:
            region_rows.append({"belt": belt_name, "index": c, "n_cities": int(len(g)),
                                "mean_sen_per_decade": float(g[f"{c}_sen"].mean()),
                                "median_sen": float(g[f"{c}_sen"].median()),
                                "n_sig": int(g[f"{c}_sig"].sum())})
    region = pd.DataFrame(region_rows)
    region.to_csv(C.RESULTS / "q2_region_summary.csv", index=False)

    # regional mean anomaly series (z-score per city then average)
    anom = {}
    for belt_name, g in city.groupby("belt"):
        frames = []
        for cid in g["id"]:
            s = series[cid]
            z = (s["rx1day"] - s["rx1day"].mean()) / s["rx1day"].std(ddof=1)
            frames.append(z.rename(cid))
        anom[belt_name] = pd.concat(frames, axis=1).mean(axis=1)
    anom = pd.DataFrame(anom)

    # clustering on standardised trend/mean features
    feats = ["rx1day_sen", "total_sen", "r95p_sen", "sdii_sen", "ge50_pct_per_decade",
             "mean_rx1day", "cv_total", "mean_total"]
    Xdf = city[feats].astype(float)
    X = StandardScaler().fit_transform(Xdf.fillna(Xdf.median()).to_numpy(dtype=float))
    sil, inert = {}, {}
    for k in (2, 3, 4, 5):
        km = KMeans(n_clusters=k, n_init=50, random_state=0).fit(X)
        sil[k] = float(silhouette_score(X, km.labels_))
        inert[k] = float(km.inertia_)
    k_best = max(sil, key=sil.get)
    km = KMeans(n_clusters=k_best, n_init=100, random_state=0).fit(X)
    city["cluster"] = km.labels_
    city["cluster_name"] = city["cluster"].map(
        lambda c: f"C{c}: " + ", ".join(city.loc[city.cluster == c, "city"].head(3)))
    city.to_csv(C.RESULTS / "q2_city_clusters.csv", index=False)

    cluster_profile = city.groupby("cluster")[feats + ["lat", "lon"]].mean()
    cluster_profile["n"] = city.groupby("cluster").size()
    cluster_profile.to_csv(C.RESULTS / "q2_cluster_profile.csv")

    # ---------- figures ----------
    for idx, fname, title in (("rx1day", "fig07_trend_map_rx1day.png", "Trend in annual maximum daily precipitation"),
                              ("r95p", "fig08_trend_map_r95p.png", "Trend in R95p (very wet day total)")):
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        v = city[f"{idx}_sen"].to_numpy()
        sig = city[f"{idx}_sig"].to_numpy()
        sc = ax.scatter(city["lon"], city["lat"], s=18 + 12 * np.abs(v), c=v, cmap="RdBu_r",
                        vmin=-np.nanmax(np.abs(v)), vmax=np.nanmax(np.abs(v)),
                        edgecolor=np.where(sig, "k", "none"), linewidth=0.8, zorder=4)
        for _, r in city.iterrows():
            ax.annotate(r["city"].split(",")[0], (r["lon"], r["lat"]), fontsize=5.6,
                        xytext=(3, 3), textcoords="offset points", color="#333333")
        ax.set_xlabel("Longitude (deg E)")
        ax.set_ylabel("Latitude (deg N)")
        ax.set_title(f"{title} (Sen slope, mm/decade; black edge = FDR-significant)")
        cb = fig.colorbar(sc, ax=ax, shrink=0.85)
        cb.set_label("mm/decade")
        fig.savefig(C.FIGS / fname)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    mat = city.set_index("city")[[f"{c}_sen" for c in INDICES]].copy()
    mat.columns = INDICES
    lim = np.nanmax(np.abs(mat.to_numpy()))
    im = ax.imshow(mat.to_numpy(), cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(len(INDICES)))
    ax.set_xticklabels(["Total", "Rx1day", "R95p", "SDII", "Wet days"])
    ax.set_yticks(range(len(mat)))
    ax.set_yticklabels([c.split(",")[0] for c in mat.index], fontsize=6)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{mat.iat[i, j]:+.1f}", ha="center", va="center", fontsize=5.2,
                    color="white" if abs(mat.iat[i, j]) > 0.6 * lim else "black")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Sen slope (per decade)")
    ax.set_title("Per-city precipitation trends, 1961-2020")
    fig.savefig(C.FIGS / "fig09_trend_heatmap.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    for c in sorted(city["cluster"].unique()):
        g = city[city.cluster == c]
        ax.scatter(g["rx1day_sen"], g["r95p_sen"], s=34, label=f"Cluster {c} (n={len(g)})", alpha=0.85)
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("Rx1day trend (mm/decade)")
    ax.set_ylabel("R95p trend (mm/decade)")
    ax.set_title("Cities in trend space")
    ax.legend(frameon=False, fontsize=6.5)
    ax = axes[1]
    ks = list(sil)
    ax.plot(ks, [sil[k] for k in ks], marker="o", color="#2f6f9f")
    ax.set_xlabel("Number of clusters k")
    ax.set_ylabel("Silhouette score")
    ax.set_title(f"Cluster selection (k = {k_best})")
    fig.savefig(C.FIGS / "fig10_clusters.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for belt_name in anom.columns:
        ax.plot(anom.index, anom[belt_name].rolling(9, min_periods=5).mean(), lw=1.2, label=belt_name)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("Standardised Rx1day anomaly")
    ax.set_title("Regional mean extreme-precipitation anomaly (9-year moving average)")
    ax.legend(frameon=False, ncol=3, fontsize=7)
    fig.savefig(C.FIGS / "fig11_regional_anomaly.png")
    plt.close(fig)

    out = {
        "n_cities": int(len(city)), "period": f"{BASE[0]}-{BASE[1]}", "min_years": MIN_YEARS,
        "fdr_alpha": 0.05,
        "n_sig_by_index": {c: int(city[f"{c}_sig"].sum()) for c in INDICES},
        "n_sig_ge50": int(city["ge50_sig"].sum()),
        "median_sen_by_index": {c: float(city[f"{c}_sen"].median()) for c in INDICES},
        "mean_sen_by_index": {c: float(city[f"{c}_sen"].mean()) for c in INDICES},
        "range_sen_rx1day": [float(city["rx1day_sen"].min()), float(city["rx1day_sen"].max())],
        "top5_wet_rx1day_trend": city.nlargest(5, "rx1day_sen")[["city", "rx1day_sen", "rx1day_q"]].to_dict("records"),
        "top5_dry_rx1day_trend": city.nsmallest(5, "rx1day_sen")[["city", "rx1day_sen", "rx1day_q"]].to_dict("records"),
        "silhouette": sil, "k_best": k_best,
        "cluster_profile": cluster_profile.reset_index().to_dict("records"),
        "regional": region.to_dict("records"),
        "data_source": "NOAA GHCN-Daily, https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/ (accessed 2026-11-17)",
    }
    C.write_json(out, C.RESULTS / "q2_results.json")

    print("cities", len(city), "k_best", k_best, "sil", {k: round(v, 3) for k, v in sil.items()})
    print("sig counts", out["n_sig_by_index"], "ge50", out["n_sig_ge50"])
    print("median sen", {k: round(v, 2) for k, v in out["median_sen_by_index"].items()})
    print(city[["city", "belt", "lat", "lon", "rx1day_sen", "rx1day_q", "r95p_sen", "ge50_pct_per_decade"]].round(2).to_string(index=False))
    print(region.round(2).to_string(index=False))


if __name__ == "__main__":
    main()