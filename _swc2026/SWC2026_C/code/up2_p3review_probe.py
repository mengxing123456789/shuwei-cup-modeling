# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p3review_probe.py -- information headroom probe for the paid review arm.

Question: how much weighted on-time could *any* paid re-observation buy?
Bound used here: a policy that starts with the sharper prefix for free, at t=0,
with no 1 s delay and no observation cost, is an information superset of every
paid-review policy restricted to the same rule family (reserve b =
max(.2, alpha*(pred + Q_resid(qlevel)) + beta)).  If even that free-information
arm moves the on-time rate by < 1 point, no paid policy can reach 1 point.

Arms (all REVIEW=False, same seeds, same rule, same qlevel rule):
  base  : pred0 / res0                      (what the no-review arm sees)
  free6 : pred6 / res1  -- perfect 0.6-prefix observation, free, at t=0
  free10: pred1 / res2  -- perfect 1.0-prefix observation, free, at t=0
  true  : d     / {0}   -- full duration knowledge (oracle, same rule)

CLI:  python up2_p3review_probe.py
"""
import copy
import json
import math
import os
import sys
import time

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V          # noqa: E402

DATA = os.path.join(os.path.dirname(HERE), "data")
LOGS = os.path.join(os.path.dirname(HERE), "logs")
SEEDS = list(V.SEEDS)
CASES = ("S1", "S2", "S3")
Q_GRID = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
ALPHA, BETA = 1.0, 0.5
METRIC = "weighted_on_time_rate"


def paired(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = d.size
    m = float(d.mean())
    sd = float(d.std(ddof=1))
    se = sd / math.sqrt(n)
    tc = float(stats.t.ppf(0.975, n - 1))
    return dict(mean=m, ci95=[m - tc * se, m + tc * se], se=se, sd=sd, n=n,
                n_pos=int((d > 0).sum()), n_neg=int((d < 0).sum()),
                n_zero=int((d == 0).sum()))


def shift_arm(sp, cfg, kind):
    """Return (spec2, cfg2) where the arm starts with sharper information for free."""
    sp2 = copy.copy(sp)
    cfg2 = dict(cfg)
    if kind == "free6":
        pred, res = cfg["pred6"], sp.res1
    elif kind == "free10":
        pred, res = cfg["pred1"], sp.res2
    elif kind == "true":
        pred, res = cfg["d"], np.array([0.0])
    else:
        return sp, cfg
    cfg2["pred0"] = pred
    sp2.res0 = np.sort(np.asarray(res, float))
    sp2.q60 = np.array([float(np.quantile(sp2.res0, 0.6)), sp.q60[1], sp.q60[2]])
    sp2.ds = dict(sp.ds)
    sp2.ds[0.2] = np.quantile(sp2.res0, V.SCEN_Q)
    return sp2, cfg2


def run_arm(sp, cfg, q, kind):
    sp2, cfg2 = shift_arm(sp, cfg, kind)
    row = dict(SEL=0, RULE=V.RULE_ABS, q_hi=q, gate=0.5, late_tol=12.0, REVIEW=False)
    sc = V._scen(sp2, cfg2, ALPHA, BETA)
    r = V.simulate_batch(sp2, cfg2, ALPHA, BETA, V._cand_arrays([row]),
                         n_seeds=len(SEEDS), scen=sc)
    return np.asarray(r[METRIC], float)[0], np.asarray(r["cost"], float)[0]


def main():
    t0 = time.time()
    store = dict(_meta=dict(script="code/up2_p3review_probe.py",
                            purpose="information headroom of the paid review arm",
                            seeds=SEEDS, q_grid=Q_GRID, alpha=ALPHA, beta=BETA,
                            arms=["base", "free6", "free10", "true"],
                            rule="b=max(.2, alpha*(pred+Q_resid(qlevel))+beta), risk selection"),
                 cells={}, best={}, resid={})
    for case in CASES:
        sp = V.build_spec(case)
        cfg = V.build_configs(sp, SEEDS)
        store["resid"][case] = dict(
            sd0=float(np.std(sp.res0)), sd1=float(np.std(sp.res1)),
            sd2=float(np.std(sp.res2)),
            p90_abs_res0=float(np.percentile(np.abs(sp.res0), 90)),
            p90_abs_res1=float(np.percentile(np.abs(sp.res1), 90)),
            p90_abs_res2=float(np.percentile(np.abs(sp.res2), 90)))
        for q in Q_GRID:
            base, cbase = run_arm(sp, cfg, q, "base")
            cell = dict(q=q, base=float(base.mean()), cost_base=float(cbase.mean()), arms={})
            for kind in ("free6", "free10", "true"):
                y, c = run_arm(sp, cfg, q, kind)
                st = paired(y, base)
                cell["arms"][kind] = dict(
                    on_time=float(y.mean()), cost=float(c.mean()),
                    delta_pt=float(st["mean"] * 100.0),
                    ci95_pt=[float(x * 100.0) for x in st["ci95"]],
                    se_pt=float(st["se"] * 100.0),
                    n_pos=st["n_pos"], n_neg=st["n_neg"], n_zero=st["n_zero"])
            store["cells"]["%s|q%.2f" % (case, q)] = cell
            print("[%s q=%.2f] base=%.4f free6=%+.2fpt free10=%+.2fpt true=%+.2fpt"
                  % (case, q, cell["base"],
                     cell["arms"]["free6"]["delta_pt"],
                     cell["arms"]["free10"]["delta_pt"],
                     cell["arms"]["true"]["delta_pt"]), flush=True)
        keys = [k for k in store["cells"] if k.startswith(case + "|")]
        store["best"][case] = {
            kind: dict(max_delta_pt=float(max(store["cells"][k]["arms"][kind]["delta_pt"]
                                              for k in keys)),
                       at_q=float(max(keys, key=lambda k: store["cells"][k]["arms"][kind]["delta_pt"])
                                  .split("q")[1]))
            for kind in ("free6", "free10", "true")}
    store["_meta"]["seconds"] = float(time.time() - t0)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "up2_p3review_probe.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)
    print("[probe] best free10:", json.dumps(store["best"], ensure_ascii=False))
    print("[probe] seconds %.1f" % store["_meta"]["seconds"])


if __name__ == "__main__":
    main()