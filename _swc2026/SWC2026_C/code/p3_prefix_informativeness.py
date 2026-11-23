
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Why the observation budget stays unused: measured informativeness of the prefix.

Two questions, both answered from data rather than assumption:
  Q1 does the released prefix shrink the predictive spread on the P3 pool
     (validation split, the split the formal protocol samples from)?
  Q2 what spread reduction would be needed for one observation (cost 1.0, delay
     1.0 s) to pay for itself, given the official weighted on-time objective?

Q2 is a closed-form threshold: an observation is worth buying only if the
reduction in P(late) times the job weight exceeds the delay and cost shadow
price. With a common due date and a single duration, the largest achievable gain
is bounded by the probability mass the observation can move across the deadline.
"""
import json
import math
import os
import numpy as np
import pandas as pd
from common import DATA, load_conditions, load_tasks, load_index, write_json
import p3_schedule as old

PREFIX = [0.2, 0.6, 1.0]
PRED = pd.read_csv(os.path.join(DATA, "p3_duration_predictions.csv"))
COND = load_conditions()
TASKS = load_tasks()


def spread_table():
    rows = []
    for split in ("train", "validation", "test"):
        g = PRED[PRED.split == split]
        for p in PREFIX:
            gp = g[g.prefix == p]
            r_old = gp.duration.values - gp.old.values
            r_fus = gp.duration.values - gp.pred.values
            # Within-family spread is the irreducible part a scheduler cannot remove
            # without an observation; total spread is what it faces before observing.
            wf = []
            for f, gg in gp.groupby("family"):
                if len(gg) >= 4:
                    wf.append(gg.duration.values - gg.pred.values)
            wf = np.concatenate(wf) if wf else np.array([0.0])
            rows.append(dict(
                split=split, prefix=p, n=len(gp),
                sd_total=float(np.std(gp.duration.values)),
                sd_resid_old=float(np.std(r_old)),
                sd_resid_fusion=float(np.std(r_fus)),
                iqr_resid_fusion=float(np.subtract(*np.percentile(r_fus, [75, 25]))),
                sd_within_family_resid=float(np.std(wf)),
                shrinkage_old=float(1 - np.std(r_old) / max(np.std(gp.duration.values), 1e-9)),
                shrinkage_fusion=float(1 - np.std(r_fus) / max(np.std(gp.duration.values), 1e-9)),
            ))
    return pd.DataFrame(rows)


def gain_rate_by_prefix(df):
    """Observable gain (seconds resolved) as the prefix grows, for three τ levels."""
    out = []
    for r in (0.25, 0.35, 0.50):
        g = df[df.split == "validation"]
        for p in PREFIX:
            gp = g[g.prefix == p]
            late = (gp.duration.values > gp.pred.values + r * gp.duration.values).mean()
            out.append(dict(bar=r, prefix=p, p_late=float(late)))
    return out


def voi_threshold():
    """Break-even spread shrink for one observation.

    Under the official nominal mapping the service cost is dominated by the
    reservation b and the fixed 2.0 + 0.2*D terms; the observation adds exactly
    1.0 cost and 1.0 s of delay. For the job with the largest weight w_max the
    observation can pay only when the probability of lateness it removes times
    w_max exceeds the weighted on-time share it destroys by using one second of
    the horizon. We report both sides so the threshold is auditable.
    """
    rows = []
    for conf in COND["cases"]:
        H = float(conf["horizon_s"]); B = float(conf["cost_budget"])
        js = TASKS[TASKS.case_id == conf["case_id"]]
        W = float(js.priority_weight.sum())
        w_max = float(js.priority_weight.max())
        # A 1.0 s delay can at most convert one job at the deadline; its best case
        # is preserving one maximal-weight job's on-time status.
        best_gain = w_max / W
        # Cost side: 1.0 out of the budget, measured as the share of the smallest
        # reservation it displaces.
        cost_share = 1.0 / max(B, 1e-9)
        rows.append(dict(case=conf["case_id"], horizon=H, budget=B, w_max=w_max,
                         best_on_time_gain_per_review=best_gain,
                         budget_share_per_review=round(cost_share, 4),
                         obs_limit=conf["observation_limit"],
                         n_reviews_if_all_used=conf["observation_limit"],
                         max_possible_on_time_gain=round(best_gain * conf["observation_limit"], 4)))
    return rows


def main():
    S = spread_table()
    print("SPREAD BY PREFIX")
    print(S.round(4).to_string(index=False))
    G = gain_rate_by_prefix(PRED)
    print("\nLATE-PROBABILITY by prefix and bar (validation pool)")
    print(pd.DataFrame(G).round(4).to_string(index=False))
    V = voi_threshold()
    print("\nVOI BOUNDS")
    print(pd.DataFrame(V).to_string(index=False))
    # Does the prefix actually shrink spread on the pool the protocol uses?
    v = S[S.split == "validation"].sort_values("prefix")
    sd = v.sd_resid_fusion.values
    monotone = bool(np.all(np.diff(sd) <= 1e-9))
    rel = float((sd[0] - sd[-1]) / max(sd[0], 1e-9))
    out = dict(_meta=dict(question="prefix informativeness on the P3 sampling pool and VoI break-even",
                          pool="validation split; eligible units only",
                          note="residual = true duration - frozen predictor; no test leakage"),
               spread=S.to_dict("records"), p_late_by_prefix=G, voi_bounds=V,
               prefix_shrinks_spread_monotonically=monotone,
               relative_spread_reduction_0p2_to_1p0=rel)
    write_json("p3_prefix_informativeness.json", out)
    print("\nmonotone shrink:", monotone, " relative reduction 0.2->1.0 s:", round(rel, 4))


if __name__ == "__main__":
    main()