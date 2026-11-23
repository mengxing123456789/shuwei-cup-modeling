
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Regret decomposition for the final P3 policy.

total regret of the deployed policy (unit_resid distribution + online alpha)
against the stored fixed-alpha risk_fusion baseline splits into three terms:

  implementation gap  M1 - risk_fusion   (same distribution, same known alpha)
  distribution swap   M2 - M1            (calibrated distribution instead of the
                                          deployment table's own residual quantiles)
  alpha estimation    B  - M2            (online Bayes alpha instead of the true one)

M1: info=model_quant, alpha known      M2: info=unit_resid, alpha known
M3: info=model_quant, alpha estimated  B : info=unit_resid, alpha estimated (p3_adaptive)
"""
import json, os, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p3_adaptive as A
from common import DATA, write_json

t0 = time.time()
base = json.load(open(os.path.join(DATA, "p3_stochastic_schedule.json"), encoding="utf-8"))
sens = base["mapping_sensitivity"]


def matrix(info, mode):
    rows = []
    for alpha, beta in A.old.MAPPINGS:
        for case in ("S1", "S2", "S3"):
            for seed in A.SEEDS:
                rows.append(A.simulate(case, seed, info, alpha, beta, alpha_mode=mode))
    return pd.DataFrame(rows)


CACHE = {("model_quant", "fixed"): "p3_adaptive_m1.csv",
         (A.CAL_INFO, "fixed"): "p3_adaptive_m2.csv",
         ("model_quant", "bayes"): "p3_adaptive_m3.csv",
         (A.CAL_INFO, "bayes"): "p3_adaptive_b.csv"}


def load_matrix(info, mode):
    """Reuse the cached trial table when the earlier run already wrote it."""
    f = os.path.join(DATA, CACHE.get((info, mode), ""))
    if CACHE.get((info, mode)) and os.path.exists(f):
        return pd.read_csv(f)
    df = matrix(info, mode)
    if (info, mode) in CACHE:
        df.to_csv(f, index=False)
    return df


M1 = load_matrix("model_quant", "fixed")
M2 = load_matrix(A.CAL_INFO, "fixed")
M3 = load_matrix("model_quant", "bayes")
B = load_matrix(A.CAL_INFO, "bayes")


def cell(df, alpha, beta, case):
    g = df[(df.alpha == alpha) & (df.beta == beta) & (df.case == case)]
    return float(g.weighted_on_time_rate.mean())


SK = {(r["policy"], r["alpha"], r["beta"], r["case"]): float(r["eta"]) for r in sens}
BASE3 = ("slack_old", "slack_fusion", "risk_fusion")
rows = []
for alpha, beta in A.old.MAPPINGS:
    for case in ("S1", "S2", "S3"):
        cand = {p: SK[(p, alpha, beta, case)] for p in BASE3}
        best_p = max(cand, key=cand.get)
        b_m1 = cell(M1, alpha, beta, case); b_m2 = cell(M2, alpha, beta, case)
        b_b = cell(B, alpha, beta, case); b_m3 = cell(M3, alpha, beta, case)
        rows.append(dict(alpha=alpha, beta=beta, case=case, best_policy=best_p, best=cand[best_p],
                         risk_fusion=cand["risk_fusion"], slack_old=cand["slack_old"],
                         m1_model_quant_fixed=b_m1, m2_cal_fixed=b_m2,
                         m3_model_quant_bayes=b_m3, final_bayes=b_b,
                         impl_gap=b_m1 - cand["risk_fusion"],
                         dist_swap=b_m2 - b_m1,
                         alpha_cost=b_b - b_m2,
                         total=b_b - cand["risk_fusion"],
                         regret=cand[best_p] - b_b,
                         alpha_sep_cost=b_b - b_m2, alpha_cost_at_model=b_m3 - b_m1))
df = pd.DataFrame(rows)
df.to_csv(os.path.join(DATA, "p3_adaptive_decomp.csv"), index=False)
out = dict(_meta=dict(design="one-factor-at-a-time regret decomposition on the same 30 seeds",
                      columns=dict(m1="deployment quantiles + known alpha (my re-implementation of risk_fusion)",
                                   m2="unit_resid quantiles + known alpha",
                                   m3="deployment quantiles + online Bayes alpha",
                                   final="unit_resid quantiles + online Bayes alpha")),
           cells=rows,
           summary=dict(
               impl_gap_mean=float(df.impl_gap.mean()), impl_gap_max=float(np.max(np.abs(df.impl_gap))),
               dist_swap_mean=float(df.dist_swap.mean()), dist_swap_min=float(df.dist_swap.min()),
               dist_swap_max=float(df.dist_swap.max()),
               alpha_cost_mean=float(df.alpha_cost.mean()), alpha_cost_max=float(df.alpha_cost.max()),
               total_mean=float(df.total.mean()), total_max=float(df.total.max()),
               regret_max=float(df.regret.max()),
               regret_max_cells=df.loc[df.regret > 0.02, ["alpha", "beta", "case", "regret"]].to_dict("records")),
           seconds=time.time() - t0)
write_json("p3_adaptive_decomp.json", out)
print(json.dumps(out["summary"], ensure_ascii=False, indent=1))
print("seconds", round(out["seconds"], 1))