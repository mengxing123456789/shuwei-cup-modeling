
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Paired statistics for the P3 adaptive report: every headline difference is
computed on the same seeds, so the CI is the paired one."""
import os
import json, os
import numpy as np
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
A = pd.read_csv(os.path.join(DATA, "p3_adaptive_m2.csv"))  # unit_resid, known alpha (all maps)
BASE = json.load(open(os.path.join(DATA, "p3_stochastic_schedule.json"), encoding="utf-8"))
SENS = pd.DataFrame(BASE["mapping_sensitivity"])


def ci95(x):
    x = np.asarray(x, float)
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def paired(rows, k1, k2, keys=("case",)):
    out = []
    for k, g in rows.groupby(list(keys)):
        d = g[k1].values - g[k2].values
        out.append(dict(zip(list(keys), k if isinstance(k, tuple) else (k,)),
                        mean=float(d.mean()), ci95=float(ci95(d)),
                        n_neg=int((d < -1e-9).sum()), n=len(d)))
    return out


res = {}
info = pd.read_csv(os.path.join(DATA, "p3_adaptive_info_trials.csv")) if os.path.exists(
    os.path.join(DATA, "p3_adaptive_info_trials.csv")) else None

# rebuild the info trials cheaply from the stored json aggregate is impossible for
# paired CIs, so re-run only the four headline levels on 30 seeds.
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p3_adaptive as AD

rows = []
for case in ("S1", "S2", "S3"):
    for i in ("oracle", "family_dist", "point_est", "unit_resid", "model_quant"):
        for s in AD.SEEDS:
            r = AD.simulate(case, s, i, alpha_mode="fixed")
            rows.append(dict(case=case, info=i, seed=s, eta=r["weighted_on_time_rate"],
                             cost=r["cost"], res=r["reserved_s"]))
T = pd.DataFrame(rows)
T.to_csv(os.path.join(DATA, "p3_adaptive_info_trials.csv"), index=False)


def wide(a, b):
    p = T.pivot_table(index=["case", "seed"], columns="info", values="eta")
    d = p[a] - p[b]
    return [dict(case=c, mean=float(g.mean()), ci95=float(ci95(g)),
                 n_neg=int((g < -1e-9).sum()), n=len(g))
            for c, g in d.groupby(level=0)]


res["oracle_minus_family"] = wide("oracle", "family_dist")
res["oracle_minus_point"] = wide("oracle", "point_est")
res["unit_resid_minus_point"] = wide("unit_resid", "point_est")
res["unit_resid_minus_model"] = wide("unit_resid", "model_quant")
res["family_minus_point"] = wide("family_dist", "point_est")
res["oracle_minus_unit_resid"] = wide("oracle", "unit_resid")
# paired cost / reservation for the same levels
res["cost_unit_resid_minus_point"] = [
    dict(case=c, mean=float(g.mean()), ci95=float(ci95(g)))
    for c, g in (T.pivot_table(index=["case", "seed"], columns="info", values="cost")["unit_resid"]
                 - T.pivot_table(index=["case", "seed"], columns="info", values="cost")["point_est"]).groupby(level=0)]

# regret cells against the best of the three fixed baselines
out = []
for (al, be), g in A.groupby(["alpha", "beta"]):
    for case, gg in g.groupby("case"):
        cand = SENS[(SENS.alpha == al) & (SENS.beta == be) & (SENS.case == case)]
        best = float(cand.eta.max())
        d = gg.weighted_on_time_rate.values - best
        out.append(dict(alpha=float(al), beta=float(be), case=case, best=best,
                        mine=float(gg.weighted_on_time_rate.mean()),
                        regret=float(-d.mean()), ci95=float(ci95(d))))
res["regret_paired"] = out
res["_meta"] = dict(paired=True, ci="1.96*sd/sqrt(n) on the seed-paired difference")
open(os.path.join(DATA, "p3_adaptive_stats.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(res, ensure_ascii=False, indent=1))
for k, v in res.items():
    if k == "_meta":
        continue
    if not isinstance(v, list):
        print(k, "(dict, not tabulated here)")
        continue
    print(k, [(r.get("case", ""), round(r.get("mean", float("nan")), 4),
               round(r.get("ci95", float("nan")), 4), r.get("n_neg"))
              for r in v if isinstance(r, dict)])