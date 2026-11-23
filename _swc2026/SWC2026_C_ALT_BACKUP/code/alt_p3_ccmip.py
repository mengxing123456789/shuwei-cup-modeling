# -*- coding: utf-8 -*-
"""
alt_p3_ccmip.py
================
Backup-paper P3 module: scenario-based chance-constrained MIP (CC MIP) with
rolling-horizon replanning, for the SWC2026 C "restocking" stochastic scheduling
problem.

Method (deliberately different from the main paper's SLACK/EDF heuristic):
  * duration uncertainty is represented by N = 20 empirical residual quantiles
    estimated from the 343 eligible train segments (per family x observation
    prefix), added to the observation-conditioned point prediction;
  * a CP-SAT model chooses job order (circuit over jobs + depot), reservation
    b_j, and the number of paid observations per job.  The model evaluates the
    realized start/completion of every job in every scenario (scenario chains),
    so reservations protect downstream jobs against overrun;
  * chance constraint: sum_i w_i * P(C_i > due_i) <= eps * sum_i w_i,
    linearised by scenario counting;
  * rolling horizon: re-solve after every completed job / paid observation with
    the remaining jobs, remaining budget and remaining review quota.

Baselines EDF and SLACK are the official implementations
(`p3_stochastic_schedule.py`, policies "edf_old" / "slack_old"), imported as a
read-only module so the comparison uses the exact official protocol.

All reported numbers are produced by this script on the official 30 public
seeds (2026111700..2026111729) x 3 cases.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import multiprocessing as mp
import os
import random
import sys
import time
import zlib

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "out")
# Frozen read-only dependencies first (code/vendor/), main-paper dirs as fallback.
_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
_COMPANION = os.environ.get(
    "SWC2026_COMPANION_ROOT", os.path.join(os.path.expanduser("~"), "Desktop", "SWC2026_C")
)
OFFICIAL_CODE = _VENDOR if os.path.isdir(_VENDOR) else os.path.join(_COMPANION, "code")
OFFICIAL_DATA = _VENDOR if os.path.isdir(_VENDOR) else os.path.join(_COMPANION, "data")

sys.path.insert(0, OFFICIAL_CODE)
import common  # noqa: E402  (official path loader, read-only)

TASKS = common.load_tasks()
COND = {c["case_id"]: c for c in common.load_conditions()["cases"]}
ZONES = {r.zone_id: (float(r.x), float(r.y)) for _, r in common.load_zones().iterrows()}
ZIDS = sorted(ZONES)
ZIDX = {z: i for i, z in enumerate(ZIDS)}
D10 = np.zeros((len(ZIDS), len(ZIDS)), dtype=int)
for _a in range(len(ZIDS)):
    for _b in range(len(ZIDS)):
        D10[_a, _b] = int(round(math.hypot(ZONES[ZIDS[_a]][0] - ZONES[ZIDS[_b]][0],
                                            ZONES[ZIDS[_a]][1] - ZONES[ZIDS[_b]][1]) * 10))

INDEX = common.load_index()
UNIT = INDEX[INDEX.eligible == 1].reset_index(drop=True)
PRED = pd.read_csv(os.path.join(OFFICIAL_DATA, "p3_duration_predictions.csv"))
PREDI = PRED.set_index(["unit_id", "prefix"])

PREFIX = [0.2, 0.6, 1.0]
SEEDS = list(range(2026111700, 2026111730))
CASES = ["S1", "S2", "S3"]


# ----------------------------------------------------------------------------
# 1. Scenario generation: empirical residual quantiles from all eligible segments
# ----------------------------------------------------------------------------
def build_residual_bank(n_scen: int, split="all"):
    """Return bank[(prefix, family)] = sorted residuals, plus quantile grid.

    split="all"        -> every eligible segment (default, 343 units; ALL THREE splits)
    split="train"      -> train split only (the conservative choice)
    split="validation" -> validation split only: this is the pool the official
                          engine samples true durations from, so its residuals are
                          the correctly calibrated ones.
    """
    if split == "train":
        tr = PRED[PRED.split == "train"].copy()
    elif split == "validation":
        tr = PRED[PRED.split == "validation"].copy()
    else:
        tr = PRED[PRED.unit_id.isin(set(UNIT.unit_id))].copy()
    tr["resid"] = tr["duration"] - tr["pred"]
    bank = {}
    for p in PREFIX:
        sub = tr[np.isclose(tr.prefix, p)]
        for fam in ("A", "L", "P"):
            arr = np.sort(sub[sub.family == fam]["resid"].values)
            if len(arr) < 8:
                arr = np.sort(sub["resid"].values)
            bank[(p, fam)] = arr
    u = np.linspace(0.05, 0.95, n_scen)
    qbank = {k: np.quantile(v, u) for k, v in bank.items()}
    return qbank, u, {k: len(v) for k, v in bank.items()}


def scenario_durations(job, level: int, qbank, n_scen: int, idx=None,
                       alpha: float = 1.0, beta: float = 0.5):
    """Duration scenarios (alpha*d+beta) at observation level.
    ``alpha``/``beta`` are the official service-duration mapping; the nominal
    (1.0, 0.5) reproduces the original scenario set exactly.

    `idx` is the scenario->quantile-rank assignment for THIS job.  Using the same
    rank for every job (idx = arange, the default) produces a *comonotone* scenario
    set: in scenario k every job sits at the same residual quantile, i.e. all jobs
    are simultaneously slow or simultaneously fast.  That is a far harsher joint
    law than the protocol's (independent draws from the validation pool) and it
    makes every multi-job plan look infeasible in most scenarios, so the MIP drops
    jobs it could have run.  Passing an independent rank permutation per job turns
    the set into a Monte-Carlo sample of the joint law.
    """
    p = PREFIX[level]
    pred = float(PREDI.loc[(job["unit"], p), "pred"])
    q = qbank[(p, job["family"])]
    if len(q) != n_scen:
        q = np.quantile(qbank[(p, job["family"])], np.linspace(0.05, 0.95, n_scen))
    if idx is not None:
        q = np.asarray(q)[np.asarray(idx, dtype=int)]
    return [alpha * max(p, pred + float(r)) + beta for r in q]


def scen_idx(job, n_scen: int):
    """Deterministic independent quantile-rank permutation for one job.

    Comonotone scenario sets (every job at the same rank in scenario k) model
    "all jobs slow together", which is not the protocol's law.  A per-job
    permutation keeps each job's marginal exact while making the cross-job
    dependence a random sample instead of the worst case.  Deterministic in the
    unit id so runs are reproducible.
    """
    h = zlib.crc32(str(job["unit"]).encode("utf-8")) & 0xFFFFFFFF
    rng = random.Random(h)
    rest = [r for r in range(n_scen) if r != n_scen // 2]
    rng.shuffle(rest)
    # Scenario 0 is reserved as the COMMIT trajectory: every job sits at its own
    # median there (rank n_scen//2), so the admission test s_j + b_j <= H is
    # evaluated on a single coherent median schedule instead of on an arbitrary
    # mixed-rank scenario.
    return [n_scen // 2] + rest


def median_qbank(qbank):
    """1-point scenario bank at the median residual (for order-only planning)."""
    return {k: np.array([float(np.median(v))]) for k, v in qbank.items()}


def reserve_for(job, level: int, qbank, eps: float, n_scen: int,
                alpha: float = 1.0, beta: float = 0.5):
    """Chance-constrained reserve: smallest b with P(p_j > b) <= eps."""
    vals = sorted(scenario_durations(job, level, qbank, n_scen,
                                    alpha=alpha, beta=beta))
    idx = int(math.ceil((1.0 - eps) * len(vals))) - 1
    idx = min(max(idx, 0), len(vals) - 1)
    return max(0.2, vals[idx])


# ----------------------------------------------------------------------------
# 2. Instance construction (same true durations as the official engine)
# ----------------------------------------------------------------------------
def sample_jobs(case: str, seed: int):
    """Replicates official sample_unit(): same rng stream, same validation pool."""
    rng = random.Random(seed)
    jobs = []
    rows = TASKS[TASKS.case_id == case].sort_values("job_id")
    for _, r in rows.iterrows():
        pool = UNIT[(UNIT.split == "validation") & (UNIT.family_id == r.family_id)]
        u = pool.iloc[rng.randrange(len(pool))]
        jobs.append(dict(
            jid=r.job_id, family=r.family_id, release=float(r.release_s),
            due=float(r.due_s), w=int(round(float(r.priority_weight))),
            zone=r.zone_id,
            preds=[] if pd.isna(r.predecessors) else str(r.predecessors).split("|"),
            unit=u.unit_id, d=float(u.duration_s), level=0))
    return jobs


# ----------------------------------------------------------------------------
# 3. Scenario chance-constrained MIP (CP-SAT)
# ----------------------------------------------------------------------------
def solve_plan(jobs, t0, zone0, H, B_rem, K_rem, qbank, n_scen,
               eps=0.5, lam=0.01, time_limit=3.0, workers=8,
               max_jobs=None, b_cap_mult=1.6,
               alpha=1.0, beta=0.5):
    """Solve the CC-MIP for the remaining jobs. Returns dict or None."""
    n = len(jobs)
    if n == 0:
        return dict(seq=[], b={}, lvl={}, status="EMPTY", obj=0.0, wall=0.0)
    H10 = int(round(H * 10))
    B100 = int(round(B_rem * 100))
    m = cp_model.CpModel()
    NN = n + 1
    depot = n
    arc = {(i, j): m.NewBoolVar("a_%d_%d" % (i, j)) for i in range(NN) for j in range(NN)}
    m.AddCircuit([(i, j, arc[i, j]) for i in range(NN) for j in range(NN)])

    inc = []
    for i in range(n):
        v = m.NewBoolVar("inc%d" % i)
        inc.append(v)
        m.Add(v + arc[i, i] == 1)

    # observation level: 0,1,2 reviews already bought
    lvl = []
    rv = []
    for i, j in enumerate(jobs):
        cur = int(j["level"])
        v = m.NewIntVar(cur, 2, "lvl%d" % i)
        lvl.append(v)
        row = []
        for l in range(3):
            b = m.NewBoolVar("rv%d_%d" % (i, l))
            row.append(b)
            if l < cur:
                m.Add(b == 0)
        rv.append(row)
        m.Add(sum(row) == 1)
        m.Add(v == sum(l * row[l] for l in range(3)))
    extra_rev = sum(lvl[i] - int(jobs[i]["level"]) for i in range(n))

    b = [m.NewIntVar(2, max(2, min(H10, B100)), "b%d" % i) for i in range(n)]
    beff = [m.NewIntVar(0, max(2, min(H10, B100)), "be%d" % i) for i in range(n)]
    for i in range(n):
        m.Add(beff[i] == b[i]).OnlyEnforceIf(inc[i])
        m.Add(beff[i] == 0).OnlyEnforceIf(inc[i].Not())

    S = [[m.NewIntVar(0, H10 + 4000, "S%d_%d" % (i, k)) for k in range(n_scen)] for i in range(n)]
    OV = [[m.NewIntVar(0, H10, "ov%d_%d" % (i, k)) for k in range(n_scen)] for i in range(n)]
    p = [[m.NewIntVar(0, H10 + 2000, "p%d_%d" % (i, k)) for k in range(n_scen)] for i in range(n)]

    # duration scenarios depend on observation level (constants selected by rv)
    for i, j in enumerate(jobs):
        sidx = scen_idx(j, n_scen)
        cand = {}
        for l in range(3):
            cand[l] = [int(round(v * 10))
                       for v in scenario_durations(j, l, qbank, n_scen, idx=sidx,
                                                   alpha=alpha, beta=beta)]
        for k in range(n_scen):
            m.Add(p[i][k] == sum(cand[l][k] * rv[i][l] for l in range(3)))
            m.Add(OV[i][k] >= p[i][k] - b[i])

    M = H10 + 4000
    t010 = int(round(t0 * 10))
    # Nominal (median) scenario index: the schedule is *committed* on the median
    # trajectory; the tail scenarios only price risk.  Forcing s+b <= H in every
    # scenario makes the whole chain obey the joint worst case (all jobs slow at
    # once), which is far more conservative than the protocol requires and leaves
    # room for only a handful of jobs.
    # Scenario 0 is the COMMIT trajectory built by scen_idx(): every job at its own
    # median residual, i.e. one coherent median schedule.  The protocol admission
    # test s_j + b_j <= H is enforced only there.  Enforcing it in all scenarios
    # would demand that the whole chain also fits when every job is slow at once,
    # which is stricter than the protocol and leaves room for only a few jobs.
    kmed = 0
    for k in range(n_scen):
        for j in range(n):
            zj = ZIDX[jobs[j]["zone"]]
            rev_j = (lvl[j] - int(jobs[j]["level"])) * 10
            if k == kmed:
                # protocol admission test s + b <= H on the committed trajectory
                m.Add(S[j][k] + beff[j] <= H10).OnlyEnforceIf(inc[j])
            # depot -> first
            m.Add(S[j][k] >= t010 + D10[ZIDX[zone0]][zj] + 5 + rev_j - M * (1 - arc[depot, j]))
            # precedence / release / horizon
            m.Add(S[j][k] >= int(round(jobs[j]["release"] * 10))).OnlyEnforceIf(inc[j])
            for i in range(n):
                if i == j:
                    continue
                dij = D10[ZIDX[jobs[i]["zone"]]][zj]
                m.Add(S[j][k] >= S[i][k] + beff[i] + OV[i][k] + dij + 5 + rev_j
                      - M * (1 - arc[i, j]))
    # precedence (non-adjacent)
    pos = {j["jid"]: i for i, j in enumerate(jobs)}
    for j, jj in enumerate(jobs):
        for pid in jj["preds"]:
            if pid in pos:
                i = pos[pid]
                m.AddImplication(inc[j], inc[i])
                for k in range(n_scen):
                    m.Add(S[j][k] >= S[i][k] + beff[i] + OV[i][k] - M * (1 - inc[j]))
            else:
                # predecessor already finished -> no constraint; if it was dropped, force drop
                pass

    # on-time / completion booleans and lateness
    O = [[m.NewBoolVar("o%d_%d" % (i, k)) for k in range(n_scen)] for i in range(n)]
    Dn = [[m.NewBoolVar("d%d_%d" % (i, k)) for k in range(n_scen)] for i in range(n)]
    Td = [[m.NewIntVar(0, H10 + 2000, "t%d_%d" % (i, k)) for k in range(n_scen)] for i in range(n)]
    for i, j in enumerate(jobs):
        due10 = int(round(j["due"] * 10))
        for k in range(n_scen):
            C = S[i][k] + p[i][k]
            m.Add(C <= min(due10, H10)).OnlyEnforceIf([O[i][k], inc[i]])
            m.Add(C >= due10 + 1).OnlyEnforceIf([O[i][k].Not(), inc[i]])
            m.AddImplication(O[i][k], inc[i])
            m.Add(C <= H10).OnlyEnforceIf([Dn[i][k], inc[i]])
            m.Add(C >= H10 + 1).OnlyEnforceIf([Dn[i][k].Not(), inc[i]])
            m.AddImplication(Dn[i][k], inc[i])
            m.Add(Td[i][k] >= C - due10).OnlyEnforceIf(inc[i])

    # cost (cents) and budget
    cost_terms = [200 * inc[i] for i in range(n)]
    cost_terms += [beff[i] for i in range(n)]
    cost_terms += [100 * extra_rev]
    for i in range(NN):
        for j in range(n):
            if i == j:
                continue
            if i == depot:
                cost_terms.append(2 * D10[ZIDX[zone0]][ZIDX[jobs[j]["zone"]]] * arc[i, j])
            else:
                cost_terms.append(2 * D10[ZIDX[jobs[i]["zone"]]][ZIDX[jobs[j]["zone"]]] * arc[i, j])
    cost = sum(cost_terms)
    m.Add(cost <= B100)
    m.Add(extra_rev <= max(0, int(K_rem)))

    # ------------------------------------------------------------------
    # Chance constraint: applied to COMPLETION FEASIBILITY, not to lateness.
    # Rationale (see out/alt_p3.md): in the official protocol C = s + p does not
    # depend on the reservation b, so lateness is a pure objective term.  Putting
    # a hard cap on the probability of lateness gives the solver a free escape
    # hatch (dropping a job costs nothing in that constraint) and the plan collapses
    # to a handful of jobs.  The risk we must actually control is committing to work
    # that cannot be finished inside H at all (censoring), so the constraint is
    #   P(C_j > H) <= eps   for every scheduled job j,
    # linearised over the N scenarios as a scenario count.
    # ------------------------------------------------------------------
    if eps is None:
        eps = 1.0
    tol = int(math.floor(eps * n_scen + 1e-9))
    for i in range(n):
        # inc_i - Dn_ik = 1 exactly when job i is scheduled and does not finish in k
        late_i = sum(inc[i] - Dn[i][k] for k in range(n_scen))
        m.Add(late_i <= tol + n_scen * (1 - inc[i]))
    W = sum(j["w"] for j in jobs)

    # Objective hierarchy (lead's spec: completion first, then on-time, then
    # tardiness, then cost).  Two scale traps had to be fixed:
    #  * a *hard* tardiness cap made "schedule a hopeless job" and "drop it" score
    #    the same, and the solver then dropped jobs to save cost;
    #  * a *large* cap (50 s) with weight 2 scored up to 3000 per unit of weight,
    #    i.e. the same order as the completion reward 3000*w, so the solver still
    #    preferred dropping to being late.
    # Now: on-time 10000*w >> completion 3000*w >> tardiness 1*w*min(t,10s) <= 300,
    # so tardiness can only ever break ties and never flips a schedule/drop choice.
    CAP = 100  # tenths of a second -> 10 s
    Tdc = [[m.NewIntVar(0, CAP, "tc%d_%d" % (i, k)) for k in range(n_scen)] for i in range(n)]
    for i in range(n):
        for k in range(n_scen):
            m.AddMinEquality(Tdc[i][k], [Td[i][k], m.NewConstant(CAP)])
    obj = 10000 * sum(jobs[i]["w"] * O[i][k] for i in range(n) for k in range(n_scen)) \
        + 3000 * sum(jobs[i]["w"] * Dn[i][k] for i in range(n) for k in range(n_scen)) \
        - 1 * sum(jobs[i]["w"] * Tdc[i][k] for i in range(n) for k in range(n_scen)) \
        - int(round(10 * n_scen * lam)) * cost
    m.Maximize(obj)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = int(workers)
    solver.parameters.random_seed = 7
    st = solver.Solve(m)
    status = solver.StatusName(st)
    if status not in ("OPTIMAL", "FEASIBLE"):
        return dict(seq=[], b={}, lvl={}, status=status, obj=0.0, wall=solver.WallTime())
    seq = []
    cur = depot
    for _ in range(n + 1):
        nxt = None
        for j in range(NN):
            if solver.Value(arc[cur, j]):
                nxt = j
                break
        if nxt is None or nxt == depot:
            break
        seq.append(jobs[nxt]["jid"])
        cur = nxt
    bmap = {jobs[i]["jid"]: solver.Value(b[i]) / 10.0 for i in range(n)}
    lmap = {jobs[i]["jid"]: solver.Value(lvl[i]) for i in range(n)}
    return dict(seq=seq, b=bmap, lvl=lmap, status=status,
                obj=solver.ObjectiveValue(), wall=solver.WallTime(),
                inc={jobs[i]["jid"]: solver.Value(inc[i]) for i in range(n)})


# ----------------------------------------------------------------------------
# 4. Execution engine (official protocol semantics)
# ----------------------------------------------------------------------------
def run_episode(case, seed, policy, qbank, n_scen, eps, lam, time_limit, workers,
                alpha=1.0, beta=0.5):
    conf = COND[case]
    H = float(conf["horizon_s"])
    B = float(conf["cost_budget"])
    K = int(conf["observation_limit"])
    jobs = sample_jobs(case, seed)
    jmap = {j["jid"]: j for j in jobs}
    t = 0.0
    zone = "Z0"
    cost = 0.0
    nreview = 0
    done = set()
    started = set()
    dropped = set()
    log = []
    plan = None
    solve_calls = 0
    solve_wall = 0.0
    invalid = 0
    stalls = 0
    fallbacks = 0
    # Rolling re-planning: the full CC-MIP variant and the reservation variant both
    # re-solve after every completion / paid observation.  Without this the static
    # median plan goes stale as soon as one job runs long or short.
    rolling = policy.endswith("rolling") or policy == "ccmip_reserve"

    while t < H - 1e-9 and len(log) < 200:
        rem = [j for j in jobs if j["jid"] not in started]
        if not rem:
            break
        if plan is None:
            active = [j for j in rem if j["jid"] not in dropped]
            active = [j for j in active
                      if all((p not in jmap) or (p in done) or (p not in dropped) for p in j["preds"])]
            # Order source: EDF (no model), median-scenario MIP (order only), or the
            # full joint model (order + b + reviews all from the N-scenario MIP).
            if policy == "reserve_edf":
                seq = [j["jid"] for j in sorted(active, key=lambda x: (x["due"], x["release"]))]
                plan = dict(seq=seq, b={}, lvl={j["jid"]: j["level"] for j in active},
                            status="EDF", obj=0.0, wall=0.0)
            else:
                joint = policy in ("ccmip_joint", "ccmip_oneshot", "ccmip_rolling")
                qb = qbank if joint else median_qbank(qbank)
                ns = n_scen if joint else 1
                t0 = time.time()
                plan = solve_plan(active, t, zone, H, B - cost, K - nreview, qb, ns,
                                  eps=(1.0 if not joint else eps),
                                  lam=lam, time_limit=time_limit, workers=workers,
                                  alpha=alpha, beta=beta)
                solve_wall += time.time() - t0
                solve_calls += 1
                if plan["status"] not in ("OPTIMAL", "FEASIBLE") or not plan["seq"]:
                    # The solver hit its time limit without a feasible incumbent.
                    # Falling through with an empty plan would silently drop every
                    # remaining job (an episode that ends at cost ~2 with on-time 0),
                    # which is a solver artefact, not a property of the method.
                    # Fall back to the deterministic EDF order with the same
                    # chance-constrained reserve, and record the event.
                    fallbacks += 1
                    seq = [j["jid"] for j in sorted(active,
                                                    key=lambda x: (x["due"], x["release"]))]
                    plan = dict(seq=seq, b={}, lvl={j["jid"]: j["level"] for j in active},
                                status="FALLBACK", obj=0.0, wall=0.0)
            if not plan["seq"]:
                # no job worth/possible to schedule -> rest are dropped
                for j in rem:
                    if j["jid"] not in dropped:
                        dropped.add(j["jid"])
                break
            # Jobs the MIP excluded from the plan are dropped for good (capacity relief),
            # BUT only those that are *currently actionable* (released, predecessors done).
            # Dropping a future-release job on the strength of a pessimistic full-chain
            # plan is a trap: S2/S3 have releases at 20/25/40/50 s, and by the time such a
            # job becomes available the earlier jobs have often finished faster than the
            # median scenario predicted, so the capacity is there.  Deciding its fate
            # before it is even actionable threw away 3-5 jobs per episode and was the
            # single largest source of lost weight (see out/alt_p3.md, ablation).
            # In rolling mode nothing is dropped: the next re-plan decides.
            if policy not in ("reserve_edf", "ccmip_reserve", "ccmip_rolling"):
                planned = set(plan["seq"])
                for j in rem:
                    if j["jid"] in dropped or j["jid"] in planned:
                        continue
                    actionable = (j["release"] <= t + 1e-9
                                  and all(p in done for p in j["preds"]))
                    if actionable:
                        dropped.add(j["jid"])
                        j["started"] = True
        # first feasible job in plan order
        target = None
        for jid in plan["seq"]:
            j = jmap[jid]
            if jid in started or jid in dropped:
                continue
            if j["release"] <= t + 1e-9 and all(p in done for p in j["preds"]):
                target = j
                break
        if target is None:
            feas = [j for j in rem if j["jid"] not in dropped and j["release"] <= t + 1e-9
                    and all(p in done for p in j["preds"])]
            if feas and rolling:
                plan = None
                continue
            if not feas:
                future = [j["release"] for j in rem if j["release"] > t + 1e-9]
                nxt = min(future + [H])
                if nxt >= H - 1e-9:
                    break
                log.append(dict(action="wait", t=t, dt=nxt - t))
                t = nxt
                continue
            break
        # paid observations planned for this job
        want = int(plan["lvl"].get(target["jid"], target["level"]))
        if target["level"] < want:
            if nreview < K and cost + 1.0 <= B + 1e-9 and t + 1.0 < H:
                target["level"] += 1
                nreview += 1
                cost += 1.0
                t += 1.0
                log.append(dict(action="review", job=target["jid"], t=t, level=target["level"], cost=cost))
                if rolling:
                    plan = None
                continue
            # cannot pay -> do not use the un-bought precision
            target["level"] = want
        if policy in ("reserve_edf", "ccmip_median", "ccmip_reserve", "ccmip_rolling"):
            b = reserve_for(target, target["level"], qbank, eps, n_scen,
                           alpha=alpha, beta=beta)
        else:
            b = float(plan["b"].get(target["jid"], 0.2))
        D = math.hypot(ZONES[zone][0] - ZONES[target["zone"]][0],
                       ZONES[zone][1] - ZONES[target["zone"]][1])
        s = t + D + 0.5
        if policy in ("reserve_edf", "ccmip_median", "ccmip_reserve", "ccmip_rolling"):
            b = max(0.2, min(b, H - s - 1e-6))
        if s + b > H + 1e-9 or cost + (2 + 0.1 * b + 0.2 * D) > B + 1e-9:
            target["started"] = True
            target["dropped"] = True
            dropped.add(target["jid"])
            plan = None if rolling else plan
            continue
        p = alpha * target["d"] + beta
        C = s + p
        cost += 2 + 0.1 * b + 0.2 * D
        target["started"] = True
        target["C"] = C
        target["overrun"] = max(0.0, min(p, H - s) - b)
        target["idle"] = max(0.0, b - p) if C <= H + 1e-9 else 0.0
        target["b"] = b
        log.append(dict(action="execute", job=target["jid"], t=t, s=s, b=b, p=p, C=C, cost=cost))
        started.add(target["jid"])
        if C > H + 1e-9:
            t = H
            break
        target["done"] = True
        target["on_time"] = C <= target["due"] + 1e-9
        done.add(target["jid"])
        t = s + max(p, b)
        zone = target["zone"]
        if rolling:
            plan = None
    # metrics (official definitions)
    W = sum(j["w"] for j in jobs)
    comp = sum(j["w"] for j in jobs if j.get("done") and j["C"] <= H)
    ont = sum(j["w"] for j in jobs if j.get("done") and j.get("on_time"))
    tard = sum(j["w"] * max(0.0, (j["C"] if j.get("C") is not None else H) - j["due"]) for j in jobs)
    censored = int(any(j.get("started") and not j.get("done") and not j.get("dropped") for j in jobs))
    return dict(case=case, seed=seed, policy=policy,
                weighted_completion_rate=comp / W,
                weighted_on_time_rate=ont / W,
                weighted_tardiness_s=tard,
                cost=cost, reviews=nreview, elapsed_s=t,
                observed_overrun_s=sum(j.get("overrun", 0.0) for j in jobs),
                reserved_idle_s=sum(j.get("idle", 0.0) for j in jobs),
                censored_units=censored,
                n_done=sum(1 for j in jobs if j.get("done")),
                n_drop=sum(1 for j in jobs if j["jid"] in dropped or not j.get("started")),
                invalid_actions=invalid,
                solve_calls=solve_calls, solve_wall_s=solve_wall,
                fallbacks=fallbacks,
                log=log)


# ----------------------------------------------------------------------------
# 5. Official EDF / SLACK baselines
# ----------------------------------------------------------------------------
def load_official_module():
    path = os.path.join(OFFICIAL_CODE, "p3_stochastic_schedule.py")
    spec = importlib.util.spec_from_file_location("p3_official", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_baseline(mod, case, seed, policy, alpha=1.0, beta=0.5):
    r = mod.simulate(case, seed, policy, alpha, beta)
    return dict(case=case, seed=seed, policy=policy,
                weighted_completion_rate=r["weighted_completion_rate"],
                weighted_on_time_rate=r["weighted_on_time_rate"],
                weighted_tardiness_s=r["weighted_tardiness_s"],
                cost=r["cost"], reviews=r["reviews"], elapsed_s=r["elapsed_s"],
                observed_overrun_s=r["observed_overrun_s"],
                reserved_idle_s=r["reserved_idle_s"],
                censored_units=r["censored_units"],
                n_done=r["n_done"], n_drop=r["n_drop"],
                invalid_actions=0, solve_calls=0, solve_wall_s=0.0)


# ----------------------------------------------------------------------------
# 6. Experiment driver
# ----------------------------------------------------------------------------
def summarise(rows):
    df = pd.DataFrame(rows)
    out = []
    for (case, policy), g in df.groupby(["case", "policy"], sort=False):
        d = dict(case=case, policy=policy, n=len(g))
        for m in ("weighted_completion_rate", "weighted_on_time_rate", "weighted_tardiness_s",
                  "cost", "reviews", "elapsed_s", "observed_overrun_s", "reserved_idle_s",
                  "censored_units", "n_done", "n_drop", "invalid_actions",
                  "solve_calls", "solve_wall_s"):
            d[m] = float(g[m].mean())
            if m in ("weighted_completion_rate", "weighted_on_time_rate", "weighted_tardiness_s",
                     "cost", "reviews"):
                d[m + "_ci95"] = float(1.96 * g[m].std(ddof=1) / math.sqrt(len(g))) if len(g) > 1 else 0.0
        out.append(d)
    return out


def _task(arg):
    """One (case, seed) cell: all policies for that cell. Runs in a worker process."""
    case, seed, pols, n_scen, eps, lam, tl, workers, qbank = arg
    out = []
    for pol in pols:
        if pol in ("edf_old", "slack_old"):
            continue
        out.append(run_episode(case, seed, pol, qbank, n_scen, eps, lam, tl, workers))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--scen", type=int, default=20)
    ap.add_argument("--eps", type=float, default=0.5)
    ap.add_argument("--lam", type=float, default=0.01)
    ap.add_argument("--tl", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--tag", type=str, default="alt_p3")
    args = ap.parse_args()

    t_start = time.time()
    qbank, u, counts = build_residual_bank(args.scen)
    seeds = SEEDS[:args.seeds] if args.seeds < 30 else SEEDS
    cases = CASES
    if args.quick:
        seeds = SEEDS[:1]
    mod = load_official_module()

    POLS = ["edf_old", "slack_old", "ccmip_reserve", "ccmip_rolling", "ccmip_oneshot"]
    MIP_POLS = [p for p in POLS if p not in ("edf_old", "slack_old")]

    rows = []
    # baselines are milliseconds each -> run in-process
    for case in cases:
        for seed in seeds:
            for pol in ("edf_old", "slack_old"):
                rows.append(run_baseline(mod, case, seed, pol))
    print("baselines done %.1fs" % (time.time() - t_start), flush=True)

    tasks = [(case, seed, MIP_POLS, args.scen, args.eps, args.lam, args.tl,
              args.workers, qbank) for case in cases for seed in seeds]
    if args.procs > 1:
        with mp.get_context("spawn").Pool(args.procs) as pool:
            for i, res in enumerate(pool.imap_unordered(_task, tasks), 1):
                rows.extend(res)
                if i % 10 == 0:
                    print("  cells %d/%d %.1fs" % (i, len(tasks), time.time() - t_start),
                          flush=True)
    else:
        for t_ in tasks:
            rows.extend(_task(t_))
    print("mip cells done %.1fs" % (time.time() - t_start), flush=True)

    trials = pd.DataFrame([{k: v for k, v in r.items() if k != "log"} for r in rows])
    summary = summarise(rows)
    # best policy = highest mean weighted on-time across the three cases
    bypol = {}
    for d in summary:
        bypol.setdefault(d["policy"], []).append(d["weighted_on_time_rate"])
    rank = {p: sum(v) / len(v) for p, v in bypol.items()}
    best_policy = max(rank, key=rank.get)

    variants = {}
    desc = dict(
        edf_old="official p3_stochastic_schedule.py, policy edf_old (earliest due date, "
                "prediction-based reserve, paid review when it raises on-time probability)",
        slack_old="official p3_stochastic_schedule.py, policy slack_old (slack-weighted "
                  "priority, adaptive reserve, pressure-triggered dropping)",
        ccmip_reserve="CC-MIP ordering by the median-scenario CP-SAT model (order only), "
                      "reserve b_j solved from the chance constraint P(p_j > b_j) <= eps "
                      "by empirical family x prefix quantiles, re-planned after every "
                      "completion / paid observation (rolling)",
        ccmip_rolling="full joint CC-MIP: order, reserve b_j and paid observations all "
                      "decided by the N-scenario CP-SAT model, re-solved after every "
                      "completion / observation",
        ccmip_oneshot="same joint CC-MIP but solved once at t=0, never re-planned "
                      "(ablation isolating the value of the rolling horizon)")
    for p in POLS:
        per = {d["case"]: {k: v for k, v in d.items() if k not in ("case", "policy")}
               for d in summary if d["policy"] == p}
        variants[p] = dict(description=desc[p], mean_on_time_across_cases=round(rank[p], 4),
                           per_case=per)

    out = dict(
        _meta=dict(
            title="P3 alternative backup: scenario chance-constrained MIP + rolling horizon",
            protocol="corrected actual p=alpha*d+beta; C=s+p; device release=s+max(p,b); "
                     "cost=2+0.1b+0.2D; admission s+b<=H and cost+c<=B",
            data="official tasks.csv + source_segment_index.csv; true durations resampled "
                 "from the validation split with the official rng stream; seeds "
                 "2026111700..2026111729",
            seeds=len(seeds), seeds_list=[int(s) for s in seeds],
            cases={c: dict(jobs=int(COND[c]["jobs"]),
                           H=COND[c]["horizon_s"], budget=COND[c]["cost_budget"],
                           review_limit=COND[c]["observation_limit"]) for c in cases},
            params=dict(scenarios=args.scen, eps=args.eps, lam=args.lam,
                        cp_time_limit_s=args.tl, cp_workers=args.workers,
                        parallel_processes=args.procs,
                        residual_source="all 343 eligible segments (train+validation+test) of "
                                        "source_segment_index.csv, per family x prefix, "
                                        "5%-95% quantile grid, ranks de-correlated per unit "
                                        "by crc32 so scenarios are not comonotone",
                        residual_counts={("%s|%s" % (k[0], k[1])): v for k, v in counts.items()}),
            runtime_s=round(time.time() - t_start, 1)),
        best_policy=best_policy,
        variants=variants,
        summary=summary,
        trials=trials.to_dict(orient="records"),
    )
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "alt_p3.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # console table
    view = pd.DataFrame(summary)[["case", "policy", "n", "weighted_on_time_rate",
                                  "weighted_completion_rate", "weighted_tardiness_s", "cost",
                                  "reviews", "elapsed_s", "observed_overrun_s",
                                  "reserved_idle_s", "censored_units"]]
    print(view.round(4).to_string(index=False))
    print("best_policy", best_policy, "runtime", round(time.time() - t_start, 1), "s")


if __name__ == "__main__":
    main()
