"""Regional frequency analysis (index-flood) for the 23-city daily-maximum panel.

Motivation: at-site GEV fits rest on 50 annual maxima per city, and the Task 3
hold-out window contains only 5-7 valid years, so at-site parameters are noisy.
Index-flood pooling borrows strength across sites under the assumption that the
growth curve is common after scaling by a site index.

Outputs
-------
q3_regional.json          regional growth curve, homogeneity tests H1/H2, Z
q3_regional_comparison.csv per-city at-site vs regional predictions
"""
import json

import numpy as np
import pandas as pd
from scipy.stats import genextreme

import common as C

TRAIN = (1961, 2010)
TEST = (2011, 2024)
HORIZON = 10
N_SIM = 400
SEED = 20210720


def ams_for(sid: str) -> pd.Series:
    g = C.load_ghcn_wide(C.RESULTS / "ghcn" / f"{sid}.csv")
    ai = C.annual_indices(C.daily_grid(g[["date", "prcp_mm"]]))
    return ai.loc[TRAIN[0]:TRAIN[1], "rx1day"].dropna()


def lmom(x: np.ndarray) -> tuple[float, float, float]:
    """Return (l1, l2, t3) by probability-weighted moments."""
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    i = np.arange(1, n + 1, dtype=float)
    b0 = float(np.mean(x))
    b1 = float(np.sum((i - 1) / (n - 1) * x) / n)
    b2 = float(np.sum((i - 1) * (i - 2) / ((n - 1) * (n - 2)) * x) / n)
    l1 = b0
    l2 = 2 * b1 - b0
    l3 = 6 * b2 - 6 * b1 + b0
    return l1, l2, l3 / l2


def regional_fit(scaled: np.ndarray) -> dict:
    l1, l2, t3 = lmom(scaled)
    cc = 2 / (3 + t3) - np.log(2) / np.log(3)
    k = 7.8590 * cc + 2.9554 * cc ** 2
    import math

    alpha = l2 * k / ((1 - 2 ** (-k)) * math.gamma(1 + k))
    u = l1 - alpha * (1 - math.gamma(1 + k)) / k
    return {"c": float(k), "xi": float(-k), "loc": float(u), "scale": float(alpha),
            "t3": float(t3), "l2": float(l2)}


def growth_quantile(fit: dict, T: float) -> float:
    return float(genextreme.ppf(1 - 1 / T, fit["c"], loc=fit["loc"], scale=fit["scale"]))


def expected_max(fit: dict, n: int) -> float:
    from scipy.integrate import quad

    f = lambda u: genextreme.ppf(u ** (1.0 / n), fit["c"], loc=fit["loc"], scale=fit["scale"])
    val, _ = quad(f, 1e-9, 1 - 1e-9, points=[0.5], limit=200)
    return float(val)


def heterogeneity(scaled_list: list[np.ndarray], fit: dict, n_sim: int = N_SIM, seed: int = SEED) -> dict:
    """Hosking-Wallis H1 (L-CV) and H2 (L-CV + L-skew) with Monte Carlo null."""
    rng = np.random.default_rng(seed)
    sizes = np.array([len(s) for s in scaled_list])
    n_sites = len(sizes)

    def stats_for(series_list):
        lcv, lsk, w = [], [], []
        for s in series_list:
            _, l2, t3 = lmom(s)
            l1 = float(np.mean(s))
            lcv.append(l2 / l1)
            lsk.append(t3)
            w.append(len(s))
        lcv, lsk, w = np.array(lcv), np.array(lsk), np.array(w)
        v1 = float(np.sum(w * (lcv - np.sum(w * lcv) / np.sum(w)) ** 2) / np.sum(w))
        v2 = float(np.sum(w * ((lcv - np.sum(w * lcv) / np.sum(w)) ** 2
                               + (lsk - np.sum(w * lsk) / np.sum(w)) ** 2)) / np.sum(w))
        return v1, v2

    v1_obs, v2_obs = stats_for(scaled_list)
    sims = []
    for _ in range(n_sim):
        sample = [genextreme.rvs(fit["c"], loc=fit["loc"], scale=fit["scale"], size=n, random_state=rng)
                  for n in sizes]
        sims.append(stats_for(sample))
    sims = np.array(sims)
    mu1, sd1 = sims[:, 0].mean(), sims[:, 0].std(ddof=1)
    mu2, sd2 = sims[:, 1].mean(), sims[:, 1].std(ddof=1)
    h1 = float((v1_obs - mu1) / sd1)
    h2 = float((v2_obs - mu2) / sd2)
    # Z statistic for the regional L-skew against the GEV expectation
    _, _, t3_reg = lmom(np.concatenate(scaled_list))
    z = float((t3_reg - 0.23) / np.sqrt(0.6 / np.sum(sizes)) * 1.0)
    return {"V1": v1_obs, "V2": v2_obs, "H1": h1, "H2": h2, "Z": z,
            "mu_V1": float(mu1), "sd_V1": float(sd1), "mu_V2": float(mu2), "sd_V2": float(sd2),
            "n_sim": n_sim, "sites": int(n_sites)}


def main() -> None:
    pred = pd.read_csv(C.RESULTS / "q3_city_predictions.csv")
    rows, scaled_list, indices, feats = [], [], [], []
    for rec in pred.itertuples(index=False):
        x = ams_for(rec.id).to_numpy(dtype=float)
        idx = float(np.mean(x))
        _, l2, t3 = lmom(x)
        scaled_list.append(x / idx)
        indices.append(idx)
        feats.append({"city": rec.city, "lcv": l2 / idx, "lskew": t3, "log_index": np.log(idx)})
        rows.append({"city": rec.city, "id": rec.id, "index_mm": idx, "n": len(x),
                     "at_site_lmom": C.gev_fit_lmom(x)})
    pooled = np.concatenate(scaled_list)
    fit = regional_fit(pooled)
    het = heterogeneity(scaled_list, fit)

    # Hydrologically similar pooling groups: k-means on (L-CV, L-skew, log index)
    fdf = pd.DataFrame(feats)
    z = (fdf[["lcv", "lskew", "log_index"]] - fdf[["lcv", "lskew", "log_index"]].mean()) / \
        fdf[["lcv", "lskew", "log_index"]].std(ddof=0)
    from sklearn.cluster import KMeans
    groups = {}
    for k in (2, 3):
        lab = KMeans(n_clusters=k, n_init=20, random_state=0).fit_predict(z.to_numpy())
        fdf[f"g{k}"] = lab
        info = []
        for g in range(k):
            members = fdf.index[fdf[f"g{k}"] == g].tolist()
            sc = [scaled_list[i] for i in members]
            fg = regional_fit(np.concatenate(sc))
            h = heterogeneity(sc, fg, n_sim=200)
            info.append({"group": g, "n_sites": len(members),
                         "cities": fdf.loc[members, "city"].tolist(),
                         "H1": h["H1"], "H2": h["H2"], "Z": h["Z"],
                         "growth_T10": growth_quantile(fg, 10), "growth_T50": growth_quantile(fg, 50),
                         "fit": fg})
        groups[f"k{k}"] = info

    # Pick the pooling partition with the most acceptable heterogeneity
    cand = []
    for k, info in groups.items():
        cand.append((max(g["H1"] for g in info), k))
    cand.sort()
    k_star = cand[0][1]
    kk = int(k_star[1])
    info_star = groups[k_star]

    out_rows = []
    from scipy.integrate import quad
    for i, (r, rec) in enumerate(zip(rows, pred.itertuples(index=False))):
        n_test = int(rec.n_test)
        f_at = r["at_site_lmom"]
        fq = lambda u: genextreme.ppf(u ** (1.0 / n_test), f_at["c"], loc=f_at["loc"], scale=f_at["scale"])
        at_emax = float(quad(fq, 1e-9, 1 - 1e-9, points=[0.5], limit=200)[0])
        reg_emax = expected_max(fit, n_test) * r["index_mm"]
        p10_at = 1 - (1 - C.gev_exceed_prob(f_at, rec.max_rx1day_train)) ** HORIZON
        p_annual_reg = float(genextreme.sf(rec.max_rx1day_train / r["index_mm"], fit["c"],
                                           loc=fit["loc"], scale=fit["scale"]))
        p10_reg = 1 - (1 - p_annual_reg) ** HORIZON
        gid = int(fdf.loc[i, f"g{kk}"])
        fg = info_star[gid]["fit"]
        grp_emax = expected_max(fg, n_test) * r["index_mm"]
        p_annual_grp = float(genextreme.sf(rec.max_rx1day_train / r["index_mm"], fg["c"],
                                           loc=fg["loc"], scale=fg["scale"]))
        p10_grp = 1 - (1 - p_annual_grp) ** HORIZON
        out_rows.append({
            "city": r["city"], "n_test": n_test, "group": gid,
            "obs_max": float(rec.obs_max_rx1day),
            "at_site_emax": at_emax, "regional_emax": reg_emax, "group_emax": grp_emax,
            "p10_at_site": p10_at, "p10_regional": p10_reg, "p10_group": p10_grp,
        })
    comp = pd.DataFrame(out_rows)
    comp["err_at_site"] = comp["at_site_emax"] - comp["obs_max"]
    comp["err_regional"] = comp["regional_emax"] - comp["obs_max"]
    comp["err_group"] = comp["group_emax"] - comp["obs_max"]

    def scores(col):
        e = comp[col].to_numpy()
        return {"rmse": float(np.sqrt(np.mean(e ** 2))), "mae": float(np.mean(np.abs(e))),
                "bias": float(np.mean(e))}

    def rho(a, b):
        return float(pd.Series(comp[a]).corr(pd.Series(comp[b]), method="spearman"))

    res = {
        "regional_fit": fit,
        "growth_curve": {f"T{T}": growth_quantile(fit, T) for T in (2, 5, 10, 20, 50, 100)},
        "homogeneity": het,
        "groups": {k: [{kk2: v for kk2, v in g.items()} for g in info] for k, info in groups.items()},
        "k_star": kk,
        "group_members": {int(g): fdf.loc[fdf[f"g{kk}"] == g, "city"].tolist() for g in range(kk)},
        "scores": {"at_site": scores("err_at_site"), "regional": scores("err_regional"),
                   "group": scores("err_group")},
        "rank_correlation_p10": {"at_vs_regional": rho("p10_at_site", "p10_regional"),
                                 "at_vs_group": rho("p10_at_site", "p10_group")},
        "n_cities": int(len(comp)),
        "note": "Index-flood: scaled annual maxima pooled, regional GEV by L-moments, site quantile = index x growth curve; groups from k-means on (L-CV, L-skew, log index).",
    }
    comp.to_csv(C.RESULTS / "q3_regional_comparison.csv", index=False)
    (C.RESULTS / "q3_regional.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("growth_curve", "homogeneity", "scores", "rank_correlation_p10", "k_star", "group_members")}, indent=2))
    for k, info in groups.items():
        print(k, [(g["group"], g["n_sites"], round(g["H1"], 2), round(g["growth_T10"], 3)) for g in info])


if __name__ == "__main__":
    main()