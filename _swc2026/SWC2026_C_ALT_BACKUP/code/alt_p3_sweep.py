# -*- coding: utf-8 -*-
"""Measured sensitivity experiments for the Question-3 scheduling layer.

Two things are measured here, both deliberately kept OUT of data/alt_p3.json
(which is the JSON of record behind Table~\\ref{tab:p3}):

  (1) an epsilon sweep on 8 paired seeds x 3 cases x 3 CC-MIP policies, with
      the two official priority rules evaluated once (they do not depend on
      epsilon), so the paper can report a measured curve instead of claiming
      an "earlier run" that never happened;
  (2) a train-only residual-bank replication at epsilon = 0.50, to check
      whether pooling all 343 eligible segments (including the test split)
      changes the ranking.  The main table keeps the all-split bank; this
      replication is reported as a robustness check.

Output: data/alt_p3_sweep.json.  Nothing in the paper's record JSON is touched.
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

EPS_GRID = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70]
BASE_POLICIES = ["edf_old", "slack_old"]
MIP_POLICIES = ["ccmip_reserve", "ccmip_rolling", "ccmip_oneshot"]
N_SCEN = 20
LAM = 0.01
TIME_LIMIT = 1.0
WORKERS = 4

_MOD = None


def _official():
    global _MOD
    if _MOD is None:
        _MOD = M.load_official_module()
    return _MOD


def _cell(arg):
    case, seed, policy, eps, split, qbank = arg
    if policy in BASE_POLICIES:
        r = M.run_baseline(_official(), case, seed, policy)
    else:
        r = M.run_episode(case, seed, policy, qbank, N_SCEN,
                          eps, LAM, TIME_LIMIT, WORKERS)
    return dict(case=case, seed=int(seed), policy=policy, eps=float(eps),
                split=split,
                on_time=float(r["weighted_on_time_rate"]),
                completion=float(r["weighted_completion_rate"]),
                tardiness=float(r["weighted_tardiness_s"]),
                cost=float(r["cost"]),
                fallbacks=int(r.get("fallbacks", 0)),
                solve_calls=int(r.get("solve_calls", 0)))


def _aggregate(rows):
    """Mean per (eps, split, case, policy) + paired best-policy ranking."""
    import collections
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["eps"], r["split"], r["case"], r["policy"])].append(r)
    cells = []
    for (eps, split, case, pol), g in sorted(groups.items()):
        n = len(g)
        cells.append(dict(eps=eps, split=split, case=case, policy=pol, n=n,
                          on_time=sum(x["on_time"] for x in g) / n,
                          completion=sum(x["completion"] for x in g) / n,
                          tardiness=sum(x["tardiness"] for x in g) / n,
                          cost=sum(x["cost"] for x in g) / n,
                          fallbacks_mean=sum(x["fallbacks"] for x in g) / n,
                          fallbacks_nonzero=sum(1 for x in g if x["fallbacks"] > 0)))
    rank = {}
    for eps in sorted({c["eps"] for c in cells}):
        for split in sorted({c["split"] for c in cells}):
            bypol = collections.defaultdict(list)
            for c in cells:
                if c["eps"] == eps and c["split"] == split:
                    bypol[c["policy"]].append(c["on_time"])
            key = "%s|%.2f" % (split, eps)
            rank[key] = dict(
                mean_on_time={p: sum(v) / len(v) for p, v in sorted(bypol.items())},
                best=max(bypol, key=lambda p: sum(bypol[p]) / len(bypol[p])),
            )
    return cells, rank


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    seeds = M.SEEDS[:1] if args.quick else M.SEEDS[:args.seeds]
    eps_grid = [0.50] if args.quick else EPS_GRID
    t0 = time.time()

    qb_all, _, counts_all = M.build_residual_bank(N_SCEN, split="all")
    qb_train, _, counts_train = M.build_residual_bank(N_SCEN, split="train")
    print("banks: all=%s train=%s" % (
        {("%.1f|%s" % k): v for k, v in counts_all.items()},
        {("%.1f|%s" % k): v for k, v in counts_train.items()}), flush=True)

    tasks = []
    # baselines: epsilon- and bank-independent, compute once
    for case in M.CASES:
        for seed in seeds:
            for pol in BASE_POLICIES:
                tasks.append((case, seed, pol, 0.50, "all", None))
    # epsilon sweep on the published (all-split) bank
    for eps in eps_grid:
        for case in M.CASES:
            for seed in seeds:
                for pol in MIP_POLICIES:
                    tasks.append((case, seed, pol, eps, "all", qb_all))
    # train-only replication at epsilon = 0.50
    if not args.quick:
        for case in M.CASES:
            for seed in seeds:
                for pol in MIP_POLICIES:
                    tasks.append((case, seed, pol, 0.50, "train", qb_train))

    print("cells=%d seeds=%d eps=%s" % (len(tasks), len(seeds), eps_grid), flush=True)
    rows = []
    if args.procs > 1:
        with mp.get_context("spawn").Pool(args.procs) as pool:
            for i, res in enumerate(pool.imap_unordered(_cell, tasks), 1):
                rows.append(res)
                if i % 40 == 0:
                    print("  %d/%d %.1fs" % (i, len(tasks), time.time() - t0), flush=True)
    else:
        for t in tasks:
            rows.append(_cell(t))

    # baselines are shared by every (eps, split) row in the ranking
    base_rows = [r for r in rows if r["policy"] in BASE_POLICIES]
    expanded = list(rows)
    for eps in eps_grid:
        for split in ("all", "train"):
            if split == "train" and args.quick:
                continue
            for r in base_rows:
                e = dict(r)
                e["eps"], e["split"] = eps, split
                expanded.append(e)
    cells, rank = _aggregate(expanded)

    out = dict(
        _meta=dict(
            title="Measured epsilon sweep and train-only residual-bank ablation (P3 backup)",
            seeds=len(seeds), seeds_list=[int(s) for s in seeds],
            eps_grid=eps_grid, scenarios=N_SCEN, lam=LAM,
            cp_time_limit_s=TIME_LIMIT, cp_workers=WORKERS,
            parallel_processes=args.procs,
            bank_all="all 343 eligible segments, per family x prefix, 5%-95% quantile grid",
            bank_train="train-split eligible segments only, same quantile grid",
            residual_counts_all={("%.1f|%s" % k): v for k, v in counts_all.items()},
            residual_counts_train={("%.1f|%s" % k): v for k, v in counts_train.items()},
            note="Baselines (edf_old/slack_old) do not depend on epsilon or on the residual bank; "
                 "they are evaluated once per seed and reused in every ranking row.",
            runtime_s=round(time.time() - t0, 1)),
        cells=cells, ranking=rank,
        trials=rows,
    )
    path = os.path.join(ROOT, "data", "alt_p3_sweep.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", path, "cells", len(cells), "runtime", out["_meta"]["runtime_s"], flush=True)
    for key in sorted(rank):
        print("  rank", key, rank[key]["best"],
              {p: round(v, 4) for p, v in rank[key]["mean_on_time"].items()}, flush=True)


if __name__ == "__main__":
    main()
