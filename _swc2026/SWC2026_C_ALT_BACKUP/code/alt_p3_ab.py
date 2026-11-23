# -*- coding: utf-8 -*-
"""Official five-mapping sensitivity for Question 3 (SWC2026 C).

The statement (C_Problem3_Requirements.txt lines 71-73, 136-142) requires
validation for FIVE service-duration mappings p = alpha*d + beta:
    (1.0,0.5) nominal, (0.75,0.5), (1.5,0.5), (1.0,0.0), (1.0,1.0)
and "30 trials per case, 90 across cases, and 450 across five mappings".
The previous draft admitted this as an open gap; this script MEASURES it.

Design:
  * all 5 mappings x 3 cases x the 30 public seeds x 5 policies (the same five
    policies as Table~ref{tab:p3});
  * every mapping is run in the SAME process with the SAME residual bank and
    solver settings, so cross-mapping differences are paired (shared source
    assignments, exactly as required);
  * EDF / SLACK are the vendored official engine's simulate(), which itself
    applies alpha/beta to its scenarios and realized durations; the three
    CC-MIP policies are alt_p3_ccmip.run_episode() with the new alpha/beta
    parameters propagated to BOTH the MIP scenario durations and the realized
    duration (see _param_ab.py).
  * nominal (1.0,0.5) reproduces the published 30-seed main table up to CP-SAT
    time-limit nondeterminism; we cross-check the mean against tab:p3.

Output: data/alt_p3_ab.json, with per-mapping checkpoints written to
        data/alt_p3_ab.partial.json after each mapping completes.
Nothing in data/alt_p3.json (the main-table record) is touched.
"""
import os
import sys
import json
import time
import argparse
import multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import alt_p3_ccmip as M  # noqa: E402

MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]
POLICIES = ["edf_old", "slack_old", "ccmip_rolling", "ccmip_reserve", "ccmip_oneshot"]
BASE = ["edf_old", "slack_old"]
MIP = ["ccmip_rolling", "ccmip_reserve", "ccmip_oneshot"]
N_SCEN = 20
LAM = 0.01
EPS = 0.5
TIME_LIMIT = 1.0
WORKERS = 4

_G = {}


def _init(qbank):
    _G["qbank"] = qbank
    _G["mod"] = M.load_official_module()


def _cell(arg):
    case, seed, policy, alpha, beta = arg
    if policy in BASE:
        r = M.run_baseline(_G["mod"], case, seed, policy, alpha, beta)
    else:
        r = M.run_episode(case, seed, policy, _G["qbank"], N_SCEN,
                          EPS, LAM, TIME_LIMIT, WORKERS,
                          alpha=alpha, beta=beta)
    return dict(case=case, seed=int(seed), policy=policy,
                alpha=float(alpha), beta=float(beta),
                on_time=float(r["weighted_on_time_rate"]),
                completion=float(r["weighted_completion_rate"]),
                tardiness=float(r["weighted_tardiness_s"]),
                cost=float(r["cost"]),
                fallbacks=float(r.get("fallbacks", 0.0)),
                solve_calls=float(r.get("solve_calls", 0.0)))


def _aggregate(rows):
    """cells[(alpha,beta,case,policy)] -> means + paired-CI helper inputs."""
    import math
    groups = {}
    for r in rows:
        k = (r["alpha"], r["beta"], r["case"], r["policy"])
        groups.setdefault(k, []).append(r)
    cells = []
    for (a, b, case, pol), g in sorted(groups.items()):
        n = len(g)
        def m(f):
            v = [r[f] for r in g]
            return sum(v) / n
        on = [r["on_time"] for r in g]
        mean = sum(on) / n
        sd = math.sqrt(sum((x - mean) ** 2 for x in on) / (n - 1)) if n > 1 else 0.0
        cells.append(dict(alpha=a, beta=b, case=case, policy=pol, n=n,
                          on_time=m("on_time"), completion=m("completion"),
                          tardiness=m("tardiness"), cost=m("cost"),
                          fallbacks_mean=m("fallbacks"),
                          fallbacks_nonzero=sum(1 for r in g if r["fallbacks"] > 0),
                          on_time_sd=sd, on_time_ci95=1.96 * sd / math.sqrt(n) if n else 0.0))
    # ranking per mapping: best policy by mean on-time across the three cases
    rank = {}
    for (a, b) in MAPPINGS:
        key = "a%g_b%g" % (a, b)
        mo = {}
        for pol in POLICIES:
            vals = [c["on_time"] for c in cells
                    if (c["alpha"], c["beta"]) == (a, b) and c["policy"] == pol]
            if vals:
                mo[pol] = sum(vals) / len(vals)
        rank[key] = dict(mean_on_time=mo, best=max(mo, key=mo.get) if mo else None,
                         per_case={case: {pol: next((c["on_time"] for c in cells
                                    if (c["alpha"], c["beta"]) == (a, b)
                                    and c["case"] == case and c["policy"] == pol), None)
                                    for pol in POLICIES} for case in M.CASES})
    return cells, rank


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--procs", type=int, default=4)
    args = ap.parse_args()

    seeds = M.SEEDS[:args.seeds]
    t0 = time.time()
    qb_all, _, counts_all = M.build_residual_bank(N_SCEN, split="all")
    print("bank all (per prefix):", {("%.1f|%s" % k): v for k, v in counts_all.items()},
          flush=True)

    out_rows = []
    partial = os.path.join(ROOT, "data", "alt_p3_ab.partial.json")
    final = os.path.join(ROOT, "data", "alt_p3_ab.json")

    for (a, b) in MAPPINGS:
        tasks = [(case, seed, pol, a, b)
                 for case in M.CASES for seed in seeds for pol in POLICIES]
        tmap = time.time()
        with mp.get_context("spawn").Pool(args.procs, initializer=_init,
                                          initargs=(qb_all,)) as pool:
            for i, res in enumerate(pool.imap_unordered(_cell, tasks), 1):
                out_rows.append(res)
                if i % 100 == 0:
                    print("  a%.2f b%.2f  %d/%d  %.1fs" % (a, b, i, len(tasks),
                          time.time() - tmap), flush=True)
        cells, rank = _aggregate(out_rows)
        snap = dict(_meta=dict(seeds=len(seeds), mappings_done=[
                    list(x) for x in MAPPINGS[:MAPPINGS.index((a, b)) + 1]],
                    elapsed_s=round(time.time() - t0, 1)),
                    cells=cells, ranking=rank)
        with open(partial, "w", encoding="utf-8", newline="\n") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        print("  DONE a%.2f b%.2f in %.1fs -> %s" % (a, b, time.time() - tmap,
              snap["_meta"]["elapsed_s"]), flush=True)

    cells, rank = _aggregate(out_rows)
    out = dict(
        _meta=dict(
            title="Official five-mapping sensitivity, Question 3 (SWC2026 C, backup paper)",
            mappings=[list(x) for x in MAPPINGS],
            seeds=len(seeds), seeds_list=[int(s) for s in seeds],
            scenarios=N_SCEN, eps=EPS, lam=LAM,
            cp_time_limit_s=TIME_LIMIT, cp_workers=WORKERS,
            parallel_processes=args.procs,
            policies=POLICIES,
            residual_source="all 343 eligible segments, per family x prefix, 5%-95% quantile grid",
            note="Cross-mapping comparisons are paired: identical seeds, residual bank, "
                 "qbank and solver settings; only (alpha,beta) changes. EDF/SLACK are "
                 "the vendored official engine with the same mapping; CC-MIP policies "
                 "propagate (alpha,beta) to both MIP scenarios and realized duration.",
            official="C_Problem3_Requirements.txt: 5 mappings, 30 trials/case, "
                     "90 across cases, 450 across mappings; paired comparisons.",
            runtime_s=round(time.time() - t0, 1)),
        cells=cells, ranking=rank, trials=out_rows,
    )
    with open(final, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", final, "cells", len(cells), "trials", len(out_rows),
          "runtime", out["_meta"]["runtime_s"], flush=True)
    for key in rank:
        print("  rank", key, rank[key]["best"],
              {p: round(v, 4) for p, v in rank[key]["mean_on_time"].items()}, flush=True)


if __name__ == "__main__":
    main()
