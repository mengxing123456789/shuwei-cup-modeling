#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared IO, climate indices, trend tests and GEV utilities for the 2021 ShuWei Cup B practice.

Units convention used everywhere downstream:
  precipitation  -> mm/day
  temperature    -> degC
All functions are pure and deterministic (bootstrap uses fixed seeds).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall")
PROBLEM = ROOT / "00_problem"
RESULTS = ROOT / "03_results"
FIGS = ROOT / "02_figures"
for _d in (RESULTS, FIGS):
    _d.mkdir(parents=True, exist_ok=True)

GSOD_MISSING = {999.9, 9999.9, 99.99, 999.0}
INCH_MM = 25.4
WET_THRESHOLD = 0.1  # mm/day, WMO wet-day threshold


# --------------------------------------------------------------------------- #
# Raw readers
# --------------------------------------------------------------------------- #
def load_gsod_workbook(path: Path) -> pd.DataFrame:
    """Read the three GSOD sheets from the official attachment.

    Returns a tidy frame: station, date, prcp_mm, tmax_c, tmin_c, temp_c, dewp_c,
    slp, wdsp, visib, frshtt. Missing sentinels become NaN.
    """
    frames = []
    for sheet in ("station1", "station2", "station3"):
        df = pd.read_excel(path, sheet_name=sheet)
        df.columns = [str(c).strip().upper() for c in df.columns]
        df["DATE"] = pd.to_datetime(df["DATE"])
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)

    def clean(col, sentinels):
        s = pd.to_numeric(raw[col], errors="coerce")
        return s.mask(s.isin(sentinels))

    out = pd.DataFrame({
        "station": raw["STATION"].astype(str),
        "date": raw["DATE"],
        "prcp_mm": clean("PRCP", {99.99, 999.99}) * INCH_MM,
        "tmax_c": (clean("MAX", {999.9}) - 32.0) * 5.0 / 9.0,
        "tmin_c": (clean("MIN", {999.9}) - 32.0) * 5.0 / 9.0,
        "temp_c": (clean("TEMP", {999.9}) - 32.0) * 5.0 / 9.0,
        "dewp_c": (clean("DEWP", {999.9}) - 32.0) * 5.0 / 9.0,
        "slp": clean("SLP", {9999.9, 999.9}),
        "wdsp": clean("WDSP", {999.9}),
        "visib": clean("VISIB", {999.9}),
        "frshtt": raw.get("FRSHTT"),
    })
    out["prcp_mm"] = out["prcp_mm"].clip(lower=0)
    return out.sort_values(["station", "date"]).reset_index(drop=True)


def load_ghcn_wide(path: Path) -> pd.DataFrame:
    """Read one GHCN-Daily station CSV (wide daily format) into mm / degC.

    GHCN stores PRCP in tenths of mm, TMAX/TMIN in tenths of degC; blanks are missing.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False, skipinitialspace=True)
    df.columns = [c.strip().upper() for c in df.columns]
    num = lambda col: pd.to_numeric(df.get(col, pd.Series(index=df.index, dtype=str)).str.strip(), errors="coerce")
    out = pd.DataFrame({
        "station": df["STATION"].str.strip(),
        "date": pd.to_datetime(df["DATE"].str.strip(), errors="coerce"),
        "prcp_mm": num("PRCP") / 10.0,
        "tmax_c": num("TMAX") / 10.0,
        "tmin_c": num("TMIN") / 10.0,
        "name": df.get("NAME", pd.Series([""] * len(df))).str.strip(),
    })
    out["prcp_mm"] = out["prcp_mm"].where(out["prcp_mm"] >= 0)
    return out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def daily_grid(df: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    """Reindex a station series onto a continuous daily calendar and flag gaps."""
    s = df.set_index("date").sort_index()
    start = start or s.index.min()
    end = end or s.index.max()
    idx = pd.date_range(start, end, freq="D")
    s = s.reindex(idx)
    s.index.name = "date"
    return s


# --------------------------------------------------------------------------- #
# Climate indices
# --------------------------------------------------------------------------- #
def annual_indices(daily: pd.DataFrame, min_valid_days: int = 300) -> pd.DataFrame:
    """Annual precipitation indices for one station.

    daily must have columns date, prcp_mm (mm/day, NaN = missing).
    Returns one row per hydrological year (calendar year) with coverage flags.
    """
    d = daily.copy()
    d["year"] = d.index.year
    d["valid"] = d["prcp_mm"].notna()
    d["wet"] = d["prcp_mm"] >= WET_THRESHOLD

    recs = []
    for year, g in d.groupby("year"):
        pr = g["prcp_mm"]
        if pr.notna().sum() < min_valid_days:
            continue
        wet = pr[pr >= WET_THRESHOLD]
        p95 = np.percentile(wet, 95) if len(wet) >= 20 else np.nan
        recs.append({
            "year": year,
            "n_valid": int(pr.notna().sum()),
            "total": float(pr.sum()),
            "wet_days": int((pr >= WET_THRESHOLD).sum()),
            "rx1day": float(pr.max()),
            "rx5day": float(pr.rolling(5, min_periods=5).sum().max()),
            "sdii": float(wet.sum() / len(wet)) if len(wet) else np.nan,
            "r95p": float(wet[wet > p95].sum()) if len(wet) >= 20 else np.nan,
            "r99p": float(wet[wet > np.percentile(wet, 99)].sum()) if len(wet) >= 20 else np.nan,
            "max_dry_spell": int(_max_run(pr.fillna(0) < WET_THRESHOLD)),
            "max_wet_spell": int(_max_run(pr.fillna(0) >= WET_THRESHOLD)),
        })
    return pd.DataFrame(recs).set_index("year")


def _max_run(mask: pd.Series) -> int:
    best = cur = 0
    for v in mask.to_numpy():
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


# --------------------------------------------------------------------------- #
# Trend tests
# --------------------------------------------------------------------------- #
def mann_kendall(x: np.ndarray) -> dict:
    """Two-sided Mann-Kendall trend test with tie correction (normal approximation)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return {"n": n, "S": np.nan, "Z": np.nan, "p": np.nan, "tau": np.nan}
    s = 0
    for i in range(n - 1):
        s += np.sign(x[i + 1:] - x[i]).sum()
    _, counts = np.unique(x, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - np.sum(counts * (counts - 1) * (2 * counts + 5))) / 18.0
    if s > 0:
        z = (s - 1) / math.sqrt(var)
    elif s < 0:
        z = (s + 1) / math.sqrt(var)
    else:
        z = 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    tau = s / (0.5 * n * (n - 1))
    return {"n": n, "S": int(s), "Z": float(z), "p": float(p), "tau": float(tau)}


def sen_slope(x: np.ndarray, t: np.ndarray | None = None) -> dict:
    """Sen's slope with a 95% confidence interval from the ranked pairwise slopes."""
    x = np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    x = x[ok]
    t = np.arange(len(ok))[ok] if t is None else np.asarray(t, dtype=float)[ok]
    n = len(x)
    slopes = []
    for i in range(n - 1):
        slopes.extend((x[i + 1:] - x[i]) / (t[i + 1:] - t[i]))
    slopes = np.array(slopes)
    b = np.median(slopes)
    alpha = 0.05
    var = n * (n - 1) * (2 * n + 5) / 18.0
    z = stats.norm.ppf(1 - alpha / 2)
    c = z * math.sqrt(var)
    rank = np.sort(slopes)
    lo_idx = int((len(rank) - c) / 2)
    hi_idx = int((len(rank) + c) / 2) + 1
    lo = rank[max(lo_idx, 0)]
    hi = rank[min(hi_idx, len(rank) - 1)]
    return {"slope": float(b), "lo": float(lo), "hi": float(hi), "n_pairs": len(rank)}


def pettitt_change_point(x: np.ndarray) -> dict:
    """Pettitt (1979) single change-point test on the sign statistic U_t.

    U_t = sum_{i<=t} sum_{j>t} sign(x_i - x_j);  K = max_t |U_t|;
    p ~= 2 exp(-6 K^2 / (n^3 + n^2)).  The sign form (not the rank-sum form) keeps the
    statistic bounded at the series edges, which the rank version does not.
    """
    x = np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    x = x[ok]
    n = len(x)
    if n < 10:
        return {"n": n, "K": np.nan, "p": np.nan, "idx": None}
    s = np.sign(x[:, None] - x[None, :])
    U = np.array([s[:t, t:].sum() for t in range(1, n)])
    aU = np.abs(U)
    kmax = float(aU.max())
    tstar = int(np.argmax(aU) + 1)
    p = 2 * math.exp(-6 * kmax ** 2 / (n ** 3 + n ** 2))
    return {"n": n, "K": kmax, "idx": tstar, "p": float(min(1.0, p)),
            "mean_before": float(np.mean(x[:tstar])), "mean_after": float(np.mean(x[tstar:]))}


def poisson_trend(years: np.ndarray, counts: np.ndarray) -> dict:
    """Log-linear Poisson trend for event counts; returns %/decade and p-value."""
    import statsmodels.api as sm

    years = np.asarray(years, dtype=float)
    counts = np.asarray(counts, dtype=float)
    X = sm.add_constant(years - years.min())
    m = sm.GLM(counts, X, family=sm.families.Poisson()).fit()
    b = float(m.params[1])
    return {"beta_per_year": b, "pct_per_decade": float((math.exp(10 * b) - 1) * 100),
            "p": float(m.pvalues[1])}


def gev_return_period_of_value(x: np.ndarray, value: float, n_boot: int = 500,
                               seed: int = 20210720) -> dict:
    """Return period of an observed value under the fitted GEV, with bootstrap CI."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    fit = gev_fit(x)
    rp = 1.0 / max(1e-12, 1.0 - stats.genextreme.cdf(value, fit["c"], loc=fit["loc"], scale=fit["scale"]))
    rng = np.random.default_rng(seed)
    sims = stats.genextreme.rvs(fit["c"], loc=fit["loc"], scale=fit["scale"],
                                size=(n_boot, len(x)), random_state=rng)
    vals = []
    for row in sims:
        try:
            f = gev_fit(row)
            vals.append(1.0 / max(1e-12, 1.0 - stats.genextreme.cdf(value, f["c"], loc=f["loc"], scale=f["scale"])))
        except Exception:
            continue
    vals = np.array(vals)
    return {"value": value, "rp_yr": float(rp),
            "lo95": float(np.percentile(vals, 2.5)), "hi95": float(np.percentile(vals, 97.5)),
            "n_boot": int(len(vals))}


# --------------------------------------------------------------------------- #
# Extreme value analysis
# --------------------------------------------------------------------------- #
def gev_fit(x: np.ndarray) -> dict:
    """GEV MLE fit; returns scipy shape c (c = -xi), loc, scale, AIC and diagnostics."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    c, loc, scale = stats.genextreme.fit(x)
    ll = np.sum(stats.genextreme.logpdf(x, c, loc=loc, scale=scale))
    k = 3
    return {"c": float(c), "xi": float(-c), "loc": float(loc), "scale": float(scale),
            "loglik": float(ll), "aic": float(2 * k - 2 * ll), "n": int(len(x))}


def gev_fit_lmom(x: np.ndarray) -> dict:
    """GEV fit by L-moments (Hosking & Wallis). Returns scipy-compatible c, loc, scale.

    L-moments are far more stable than MLE for 50-70 year annual-maxima samples, where the
    MLE shape can drift into a heavy tail and give non-physical 50-year return levels.
    """
    x = np.sort(np.asarray(x, dtype=float)[~np.isnan(np.asarray(x, dtype=float))])
    n = len(x)
    b0 = float(np.mean(x))
    i = np.arange(1, n + 1, dtype=float)
    b1 = float(np.sum((i - 1) / (n - 1) * x) / n)
    b2 = float(np.sum((i - 1) * (i - 2) / ((n - 1) * (n - 2)) * x) / n)
    l1 = b0
    l2 = 2 * b1 - b0
    l3 = 6 * b2 - 6 * b1 + b0
    t3 = l3 / l2
    cc = 2 / (3 + t3) - np.log(2) / np.log(3)
    k = 7.8590 * cc + 2.9554 * cc ** 2
    alpha = l2 * k / ((1 - 2 ** (-k)) * math.gamma(1 + k))
    u = l1 - alpha * (1 - math.gamma(1 + k)) / k
    return {"c": float(k), "xi": float(-k), "loc": float(u), "scale": float(alpha),
            "t3": float(t3), "l2": float(l2), "method": "lm", "n": int(n)}


def gev_exceed_prob(fit: dict, value: float) -> float:
    """Annual probability that a GEV variable exceeds `value`."""
    return float(stats.genextreme.sf(value, fit["c"], loc=fit["loc"], scale=fit["scale"]))


def gev_return_level(fit: dict, T: float) -> float:
    return float(stats.genextreme.ppf(1 - 1 / T, fit["c"], loc=fit["loc"], scale=fit["scale"]))


def gev_bootstrap_ci(x: np.ndarray, T: float, n_boot: int = 1000, seed: int = 20210720) -> dict:
    """Parametric bootstrap CI for a return level (resample from the fitted GEV)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    fit = gev_fit(x)
    rng = np.random.default_rng(seed)
    sims = stats.genextreme.rvs(fit["c"], loc=fit["loc"], scale=fit["scale"], size=(n_boot, len(x)), random_state=rng)
    levels = []
    for row in sims:
        try:
            f = gev_fit(row)
            levels.append(gev_return_level(f, T))
        except Exception:
            continue
    levels = np.array(levels)
    return {"T": T, "rl": gev_return_level(fit, T),
            "lo": float(np.percentile(levels, 2.5)), "hi": float(np.percentile(levels, 97.5)),
            "n_boot": int(len(levels))}


def empirical_return_period(value: float, annual_max: np.ndarray) -> float:
    """Weibull plotting-position return period of a value against annual maxima."""
    am = np.sort(np.asarray(annual_max, dtype=float)[~np.isnan(annual_max)])[::-1]
    n = len(am)
    rank = np.sum(am >= value)
    return float((n + 1) / rank) if rank else float("inf")


def write_json(obj, path: Path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))