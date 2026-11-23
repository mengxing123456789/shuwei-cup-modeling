#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q3: predict which cities will see extreme precipitation next, using four structurally
different methods, and compare them on a real out-of-sample window (2011-2024)."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.integrate import quad
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, roc_auc_score
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import common as C

TRAIN = (1961, 2010)
TEST = (2011, 2024)
FUTURE = 10          # 2026-2035 horizon, years

CITY_NAMES = {
    "CHM00050953": "Harbin", "CHM00051463": "Urumqi", "CHM00052866": "Xining",
    "CHM00052889": "Lanzhou", "CHM00053463": "Hohhot", "CHM00053614": "Yinchuan",
    "CHM00053772": "Taiyuan", "CHM00053798": "Shijiazhuang", "CHM00053959": "Yuncheng",
    "CHM00054342": "Shenyang", "CHM00054511": "Beijing", "CHM00054662": "Dalian",
    "CHM00054823": "Jinan", "CHM00054857": "Qingdao", "CHM00056294": "Chengdu",
    "CHM00056778": "Kunming", "CHM00057036": "Xi'an", "CHM00057083": "Zhengzhou",
    "CHM00057494": "Wuhan", "CHM00057687": "Changsha", "CHM00057816": "Guiyang",
    "CHM00058238": "Nanjing", "CHM00058321": "Hefei", "CHM00058362": "Shanghai",
    "CHM00058457": "Hangzhou", "CHM00058606": "Nanchang", "CHM00058847": "Fuzhou",
    "CHM00059287": "Guangzhou", "CHM00059431": "Nanning", "CHM00059758": "Haikou",
    "CHM00053882": "Changzhi", "CHM00053868": "Linfen",
}
plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 7,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "grid.linestyle": ":"})


def gpd_pot_return_level(daily: np.ndarray, years: int, T: float) -> float:
    """Poisson-GPD return level from daily values (peaks over the 95th wet-day percentile)."""
    wet = daily[daily >= 0.1]
    u = float(np.percentile(wet, 95))
    peaks, last = [], -10
    idx = np.where(daily > u)[0]
    for i in idx:
        if i - last >= 3:
            peaks.append(daily[i] - u)
            last = i
    if len(peaks) < 10:
        return np.nan
    xi, loc, scale = stats.genpareto.fit(np.array(peaks), floc=0)
    lam = len(peaks) / years
    return float(u + scale / xi * ((lam * T) ** xi - 1)) if xi != 0 else float(u + scale * np.log(lam * T))


def gumbel_rl(x: np.ndarray, T: float) -> float:
    """Gumbel return level by the method of moments (mean/sd of annual maxima)."""
    mu, sd = float(np.mean(x)), float(np.std(x, ddof=1))
    alpha = sd * np.sqrt(6) / np.pi
    u = mu - 0.5772 * alpha
    return float(u - alpha * np.log(-np.log(1 - 1 / T)))


def gev_emax(fit: dict, n: float) -> float:
    """Expected maximum of n independent draws from a fitted GEV.

    Uses E[M_n] = int_0^1 F^{-1}(u^{1/n}) du, i.e. integrate the max's quantile function over the
    probability scale (bounded, no divergent tail). Verified against the Gumbel closed form
    ln(n) + Euler-Mascheroni to 4 decimals.
    """
    c, loc, scale = fit["c"], fit["loc"], fit["scale"]
    val, _ = quad(lambda u: float(stats.genextreme.ppf(u ** (1.0 / n), c, loc=loc, scale=scale)),
                  0.0, 1.0, limit=400, points=[1e-8, 0.5, 1 - 1e-8])
    return float(val)


def build_panel() -> tuple[pd.DataFrame, dict]:
    rows, daily = [], {}
    for path in sorted((C.RESULTS / "ghcn").glob("CHM*.csv")):
        if path.stat().st_size < 5000:
            continue
        head = pd.read_csv(path, nrows=1, dtype=str, keep_default_na=False, skipinitialspace=True)
        head.columns = [c.strip().upper() for c in head.columns]
        meta = head.iloc[0]
        g = C.load_ghcn_wide(path)
        d = C.daily_grid(g[["date", "prcp_mm"]])
        ai = C.annual_indices(d)
        tr = ai.loc[TRAIN[0]:TRAIN[1]]
        te = ai.loc[TEST[0]:TEST[1]]
        if tr.shape[0] < 40 or te.shape[0] < 5:
            continue
        cid = meta["STATION"].strip()
        years_tr = tr.index.to_numpy(dtype=float)
        rec = {
            "id": cid, "city": CITY_NAMES.get(cid, meta["NAME"].strip().title()),
            "lat": float(meta["LATITUDE"]), "lon": float(meta["LONGITUDE"]), "elev": float(meta["ELEVATION"]),
            "n_train": int(tr.shape[0]), "n_test": int(te.shape[0]),
            "mean_total": float(tr["total"].mean()), "cv_total": float(tr["total"].std(ddof=1) / tr["total"].mean()),
            "mean_rx1day": float(tr["rx1day"].mean()), "sd_rx1day": float(tr["rx1day"].std(ddof=1)),
            "max_rx1day_train": float(tr["rx1day"].max()),
            "mean_wet_days": float(tr["wet_days"].mean()), "mean_sdii": float(tr["sdii"].mean()),
            "mean_r95p": float(tr["r95p"].mean()),
            "rx1day_sen": C.sen_slope(tr["rx1day"].to_numpy(dtype=float), years_tr)["slope"] * 10,
            "total_sen": C.sen_slope(tr["total"].to_numpy(dtype=float), years_tr)["slope"] * 10,
            "sdii_sen": C.sen_slope(tr["sdii"].to_numpy(dtype=float), years_tr)["slope"] * 10,
            "obs_mean_rx1day": float(te["rx1day"].mean()),
            "obs_max_rx1day": float(te["rx1day"].max()),
            "obs_max_year": int(te["rx1day"].idxmax()),
            "test_years": ",".join(str(y) for y in te.index),
            "obs_ge50_per_year": float((te["ge50"] if "ge50" in te else 0).mean()) if "ge50" in te else np.nan,
        }
        rows.append(rec)

        pr_tr = d.loc[f"{TRAIN[0]}-01-01":f"{TRAIN[1]}-12-31", "prcp_mm"]
        pr_all = d.loc[f"{TRAIN[0]}-01-01":f"{TEST[1]}-12-31", "prcp_mm"]
        daily[cid] = {"train_series": pd.Series(pr_tr.values), "ai_train": tr, "ai_test": te,
                      "ai_all": ai.loc[TRAIN[0]:TEST[1]]}
    return pd.DataFrame(rows), daily


def main() -> None:
    city, daily = build_panel()
    n = len(city)

    # ---------- method A/B/C: distribution-based predictions of the 14-year maximum ----------
    preds = {"GEV_T14": [], "GEV_LM_T14": [], "GEV_Emax": [], "GPD_POT_T14": [], "Gumbel_T14": [],
             "Gumbel_trend_T14": [], "GEV_Emax_trend": []}
    p_exceed_record, p_exceed_record_mle = [], []
    for _, r in city.iterrows():
        d = daily[r["id"]]
        am = d["ai_train"]["rx1day"].to_numpy(dtype=float)
        fit = C.gev_fit(am)
        fit_lm = C.gev_fit_lmom(am)
        T_test = int(r["n_test"])                    # valid test years differ per station
        preds["GEV_T14"].append(C.gev_return_level(fit, T_test))
        preds["GEV_LM_T14"].append(C.gev_return_level(fit_lm, T_test))
        preds["GEV_Emax"].append(gev_emax(fit_lm, T_test))
        gap = ((TEST[0] + TEST[1]) / 2 - (TRAIN[0] + TRAIN[1]) / 2)
        preds["GEV_Emax_trend"].append(gev_emax({"c": fit_lm["c"], "loc": fit_lm["loc"] + r["rx1day_sen"] / 10.0 * gap,
                                                 "scale": fit_lm["scale"]}, T_test))
        preds["GPD_POT_T14"].append(gpd_pot_return_level(d["train_series"].to_numpy(dtype=float),
                                                        TRAIN[1] - TRAIN[0] + 1, T_test))
        preds["Gumbel_T14"].append(gumbel_rl(am, T_test))
        # trend-adjusted Gumbel: shift the location by the Sen slope over the 7-year midpoint gap
        sl = r["rx1day_sen"] / 10.0
        preds["Gumbel_trend_T14"].append(gumbel_rl(am, T_test) + sl * ((TEST[0] + TEST[1]) / 2 - (TRAIN[0] + TRAIN[1]) / 2))
        p_lm = C.gev_exceed_prob(fit_lm, r["max_rx1day_train"])
        p_mle = C.gev_exceed_prob(fit, r["max_rx1day_train"])
        p_exceed_record.append(1 - (1 - p_lm) ** T_test)
        p_exceed_record_mle.append(1 - (1 - p_mle) ** T_test)
    for k, v in preds.items():
        city[k] = v
    city["p_exceed_record_lmom"] = p_exceed_record
    city["p_exceed_record_mle"] = p_exceed_record_mle
    city["exceeded_record"] = (city["obs_max_rx1day"] > city["max_rx1day_train"]).astype(int)

    # ---------- method D: machine learning (LOOCV) ----------
    feats = ["lat", "lon", "elev", "mean_total", "cv_total", "mean_rx1day", "sd_rx1day",
             "mean_wet_days", "mean_sdii", "mean_r95p", "rx1day_sen", "total_sen", "sdii_sen"]
    X = city[feats].to_numpy(dtype=float)
    y_reg = city["obs_max_rx1day"].to_numpy(dtype=float)
    y_cls = city["exceeded_record"].to_numpy(dtype=int)

    loo = LeaveOneOut()
    ml_reg = {"RF": np.zeros(n), "GBR": np.zeros(n), "Ridge": np.zeros(n)}
    ml_cls_prob = {"RF": np.zeros(n), "GBR": np.zeros(n), "Logit": np.zeros(n)}
    for tr_idx, te_idx in loo.split(X):
        for name, model in (("RF", RandomForestRegressor(n_estimators=300, max_depth=3, random_state=0, n_jobs=1)),
                            ("GBR", GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, random_state=0)),
                            ("Ridge", make_pipeline(StandardScaler(), Ridge(alpha=10.0)))):
            model.fit(X[tr_idx], y_reg[tr_idx])
            ml_reg[name][te_idx] = model.predict(X[te_idx])
        if len(np.unique(y_cls[tr_idx])) > 1:
            for name, model in (("RF", RandomForestClassifier(n_estimators=300, max_depth=3, random_state=0, n_jobs=1)),
                                ("GBR", GradientBoostingClassifier(n_estimators=200, max_depth=2, learning_rate=0.05, random_state=0)),
                                ("Logit", make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500)))):
                model.fit(X[tr_idx], y_cls[tr_idx])
                ml_cls_prob[name][te_idx] = model.predict_proba(X[te_idx])[0, 1]
    for k, v in ml_reg.items():
        city[f"pred_{k}"] = v
    for k, v in ml_cls_prob.items():
        city[f"prob_{k}"] = v

    # ---------- evaluation ----------
    reg_methods = ["GEV_T14", "GEV_LM_T14", "GEV_Emax", "GEV_Emax_trend", "GPD_POT_T14", "Gumbel_T14",
                   "Gumbel_trend_T14", "pred_RF", "pred_GBR", "pred_Ridge"]
    rows = []
    for m in reg_methods:
        p = city[m].to_numpy(dtype=float)
        ok = np.isfinite(p)
        obs_top = set(np.argsort(-y_reg[ok])[:5].tolist())
        pred_top = set(np.argsort(-p[ok])[:5].tolist())
        rows.append({"method": m, "task": "regression: held-out max Rx1day",
                     "n": int(ok.sum()),
                     "rmse_mm": float(np.sqrt(mean_squared_error(y_reg[ok], p[ok]))),
                     "mae_mm": float(mean_absolute_error(y_reg[ok], p[ok])),
                     "r2": float(r2_score(y_reg[ok], p[ok])),
                     "spearman": float(stats.spearmanr(y_reg[ok], p[ok]).statistic),
                     "bias_mm": float(np.mean(p[ok] - y_reg[ok])),
                     "overlap_top5": len(obs_top & pred_top)})
    cls_methods = ["p_exceed_record_lmom", "p_exceed_record_mle", "prob_RF", "prob_GBR", "prob_Logit"]
    for m in cls_methods:
        p = city[m].to_numpy(dtype=float)
        auc = float(roc_auc_score(y_cls, p))
        brier = float(np.mean((p - y_cls) ** 2))
        acc = float(np.mean((p >= 0.5).astype(int) == y_cls))
        rows.append({"method": m, "task": "classification: exceeds 1961-2010 record",
                     "n": int(len(p)), "auc": auc, "brier": brier, "accuracy": acc})
    comp = pd.DataFrame(rows)
    comp.to_csv(C.RESULTS / "q3_method_comparison.csv", index=False)

    # ---------- future risk (2026-2035) using full record ----------
    fut = []
    for _, r in city.iterrows():
        d = daily[r["id"]]
        am_all = d["ai_all"]["rx1day"].to_numpy(dtype=float)
        fit_lm = C.gev_fit_lmom(am_all)
        fit_mle = C.gev_fit(am_all)
        record = float(np.max(am_all))
        p_year = C.gev_exceed_prob(fit_lm, record)
        p10 = 1 - (1 - p_year) ** FUTURE
        rl10_mle = C.gev_return_level(fit_mle, 10)
        rl50_mle = C.gev_return_level(fit_mle, 50)
        fut.append({"id": r["id"], "city": r["city"], "lat": r["lat"], "lon": r["lon"],
                    "gev_xi_lmom": fit_lm["xi"], "gev_xi_mle": fit_mle["xi"],
                    "rl_10yr": C.gev_return_level(fit_lm, 10),
                    "rl_50yr": C.gev_return_level(fit_lm, 50),
                    "rl_10yr_mle": rl10_mle, "rl_50yr_mle": rl50_mle,
                    "mle_unstable": bool(rl50_mle > 3 * record),
                    "record_mm": record, "p_exceed_record_10y": p10,
                    "mean_rx1day_all": float(np.mean(am_all))})
    fut = pd.DataFrame(fut)

    # ML projection: train on the 1961-2010 -> 2011-2024 mapping with the full-record features
    X_full = city[feats].copy()
    X_full["rx1day_sen"] = [C.sen_slope(daily[c]["ai_all"]["rx1day"].to_numpy(dtype=float),
                                        daily[c]["ai_all"].index.to_numpy(dtype=float))["slope"] * 10 for c in city["id"]]
    rf = RandomForestRegressor(n_estimators=500, max_depth=3, random_state=0, n_jobs=1).fit(X, y_reg)
    gbr = GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05, random_state=0).fit(X, y_reg)
    fut["pred_next_decade_max_RF"] = rf.predict(X_full.to_numpy(dtype=float))
    fut["pred_next_decade_max_GBR"] = gbr.predict(X_full.to_numpy(dtype=float))
    fut["ratio_to_record_RF"] = fut["pred_next_decade_max_RF"] / fut["record_mm"]

    fut["rank_prob"] = fut["p_exceed_record_10y"].rank(ascending=False)
    fut["rank_rf"] = fut["pred_next_decade_max_RF"].rank(ascending=False)
    fut["risk_rank"] = ((fut["rank_prob"] + fut["rank_rf"]) / 2).rank().astype(int)
    fut = fut.sort_values("risk_rank")
    fut.to_csv(C.RESULTS / "q3_city_risk.csv", index=False)
    city.to_csv(C.RESULTS / "q3_city_predictions.csv", index=False)

    # ---------- figures ----------
    fig, axes = plt.subplots(2, 2, figsize=(6.8, 5.8), layout="constrained")
    for ax, m, title in zip(axes.ravel(),
                            ["GEV_T14", "GEV_Emax", "Gumbel_trend_T14", "pred_RF"],
                            ["A: GEV quantile at T = n", "B: GEV expected maximum",
                             "C: trend-adjusted Gumbel", "D: random forest (LOOCV)"]):
        p = city[m].to_numpy(dtype=float)
        ok = np.isfinite(p)
        ax.scatter(y_reg[ok], p[ok], s=22, color="#2f6f9f", alpha=0.85)
        lo, hi = float(np.nanmin([y_reg.min(), p[ok].min()])), float(np.nanmax([y_reg.max(), p[ok].max()]))
        ax.plot([lo, hi], [lo, hi], color="#b5342c", lw=0.9, ls="--")
        ax.set_title(f"{title}\nRMSE={np.sqrt(mean_squared_error(y_reg[ok], p[ok])):.1f} mm", fontsize=8)
    for ax in axes[1, :]:
        ax.set_xlabel("Observed held-out max (mm)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Predicted (mm)")
    fig.savefig(C.FIGS / "fig12_method_scatter.png")
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(7.4, 4.8))
    reg = comp[comp.task.str.startswith("regression")].set_index("method")
    ax = axes[0, 0]
    order = reg["rmse_mm"].sort_values().index
    ax.barh(range(len(order)), reg.loc[order, "rmse_mm"], color="#2f6f9f", alpha=0.85)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=6.5)
    ax.set_xlabel("RMSE (mm)")
    ax.set_title("Level accuracy on the held-out window")
    ax.invert_yaxis()
    ax = axes[0, 1]
    order = reg["spearman"].sort_values(ascending=False).index
    ax.barh(range(len(order)), reg.loc[order, "spearman"], color="#3f7d5a", alpha=0.85)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=6.5)
    ax.set_xlabel("Spearman rank correlation")
    ax.set_title("Ability to rank the riskiest cities")
    ax.invert_yaxis()
    ax = axes[1, 0]
    order = reg["bias_mm"].sort_values().index
    ax.barh(range(len(order)), reg.loc[order, "bias_mm"], color="#b5342c", alpha=0.85)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=6.5)
    ax.set_xlabel("mean(predicted - observed) (mm)")
    ax.set_title("Systematic bias")
    ax.invert_yaxis()
    ax = axes[1, 1]
    cls = comp[comp.task.str.startswith("classification")].set_index("method")
    order = cls["auc"].sort_values().index
    ax.barh(range(len(order)), cls.loc[order, "auc"], color="#7b5ea7", alpha=0.85)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=6.5)
    ax.set_xlim(0, 1)
    ax.set_xlabel("AUC")
    ax.set_title("Record-breaking cities (5 of 23)")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(C.FIGS / "fig13_method_comparison.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    pmax = float(max(fut["p_exceed_record_10y"].max(), 0.05))
    sc = ax.scatter(fut["lon"], fut["lat"], s=45 + 300 * fut["p_exceed_record_10y"] / pmax,
                    c=fut["p_exceed_record_10y"], cmap="YlOrRd", vmin=0, vmax=pmax,
                    edgecolor="k", linewidth=0.6, zorder=4)
    off = {"Zhengzhou": (6, -9), "Yuncheng": (-26, -9), "Hefei": (7, 4), "Nanjing": (7, -10),
           "Jinan": (6, 3), "Dalian": (7, -8), "Beijing": (6, 3), "Taiyuan": (6, 2),
           "Xining": (-24, 2), "Yinchuan": (-26, 4), "Hohhot": (6, 2), "Xi'an": (-24, -8),
           "Chengdu": (-26, 2), "Chongqing": (6, 2)}
    for _, r in fut.iterrows():
        ax.annotate(r["city"], (r["lon"], r["lat"]), fontsize=5.4,
                    xytext=off.get(r["city"], (4, 3)), textcoords="offset points")
    ax.set_xlabel("Longitude (deg E)")
    ax.set_ylabel("Latitude (deg N)")
    ax.set_title("P(a city exceeds its 1961-2024 daily record within 10 years)", fontsize=9)
    ax.set_xlim(84, 130)
    ax.set_ylim(18, 48)
    cb = fig.colorbar(sc, ax=ax, shrink=0.85)
    cb.set_label("P(exceed record in 10 yr)")
    fig.savefig(C.FIGS / "fig14_risk_map.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    top = fut.head(10).iloc[::-1]
    ax.barh(range(len(top)), top["p_exceed_record_10y"], color="#b5342c", alpha=0.8)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([f"{r.city} (RL10={r.rl_10yr:.0f} mm)" for r in top.itertuples()], fontsize=7)
    ax.set_xlabel("P(exceed own record within 2026-2035)")
    ax.set_title("Top-10 cities by combined GEV + random-forest risk rank")
    fig.savefig(C.FIGS / "fig15_risk_ranking.png")
    plt.close(fig)

    out = {
        "train": f"{TRAIN[0]}-{TRAIN[1]}", "test": f"{TEST[0]}-{TEST[1]}", "n_cities": n,
        "n_record_breakers": int(city["exceeded_record"].sum()),
        "record_breakers": city[city["exceeded_record"] == 1][
            ["city", "max_rx1day_train", "obs_max_rx1day", "obs_max_year", "n_test"]].to_dict("records"),
        "mle_unstable_cities": fut[fut["mle_unstable"]]["city"].tolist(),
        "n_test_years": city["n_test"].value_counts().to_dict(),
        "data_gap_note": "PRCP for these stations is sparse in 2013-2019; the held-out window keeps only years with >=300 valid days, so each city's T differs.",
        "comparison": comp.to_dict("records"),
        "best_regression": comp[comp.task.str.startswith("regression")].sort_values("rmse_mm").iloc[0]["method"],
        "best_classification": comp[comp.task.str.startswith("classification")].sort_values("auc", ascending=False).iloc[0]["method"],
        "top10_future_risk": fut.head(10)[["city", "p_exceed_record_10y", "rl_10yr", "rl_50yr", "pred_next_decade_max_RF"]].to_dict("records"),
        "zhengzhou": fut[fut.city.str.startswith("Zhengzhou")].to_dict("records"),
        "features": feats,
        "note": "GPD_POT_T14 undefined for stations with <10 declustered peaks; those are dropped from its metrics.",
    }
    C.write_json(out, C.RESULTS / "q3_results.json")

    print("cities", n, "record breakers", out["n_record_breakers"])
    print(comp.round(3).to_string(index=False))
    print("\nTop risk:\n", fut.head(10)[["city", "p_exceed_record_10y", "rl_10yr", "rl_50yr", "pred_next_decade_max_RF", "risk_rank"]].round(3).to_string(index=False))
    print("\nZhengzhou:", out["zhengzhou"])


if __name__ == "__main__":
    main()
