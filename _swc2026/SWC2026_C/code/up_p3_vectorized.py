# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p3_vectorized.py -- vectorised replay engine for the P3 restocking scheduler.

Why this file exists
--------------------
``code/p3_improved_verify.py`` replays one trial at a time: 30 seeds x 3 cases x
one policy costs ~12 s of pure Python, so a 600-1000 candidate x 15 (case,mapping)
nested search is out of reach.  This module keeps the *exact* arithmetic of that
reference implementation and batches the replay over (candidate x seed):

    for each (case, mapping) a batch of shape rows = candidates x seeds is
    advanced in lock-step through the same while-loop, with per-row state
    (t, zone, cost, started/done flags, prefix, ...).

Bit-exactness
-------------
1. Random draws: the unit for every job is drawn once per (case, seed) with
   ``random.Random(seed)`` and one ``randrange(len(pool))`` per job in
   ``job_id`` order -- identical to ``p3_improved_verify.configure``.  The draw
   depends only on (case, seed), so candidates share it.
2. ``np.quantile`` of a sorted residual array at an arbitrary q is reproduced
   bit-for-bit by :func:`quant_lerp`, which mirrors numpy's own ``_lerp``:
   ``b - (b-a)*(1-g)`` for ``g >= 0.5`` and ``a + (b-a)*g`` otherwise.
3. Every float expression is evaluated in the same association order as the
   Python reference (``s = (t + D) + 0.5``, ``c = (2.0 + 0.1*b) + 0.2*D``,
   ordered summation over jobs for ``rem`` / W / tardiness, ``max`` -> np.maximum,
   first-argmax tie breaking).
4. Review/VoI branch (only active when a candidate enables re-observation)
   mirrors ``p3_stochastic_schedule.simulate(..., reviews_allowed=True)``.

Public API
----------
build_spec(case)                    -> CaseSpec (static task data + zone matrix)
build_configs(spec, seeds)         -> sampled units / durations / predictions
simulate_batch(spec, cfg, alpha, beta, cand, n_seeds)
                                   -> dict of arrays shaped (n_candidates, n_seeds)
simulate_reference(case, seed, ...)-> the untouched p3_improved_verify replay
simulate_stochastic(case, seed,...)-> p3_stochastic_schedule replay (review arm)

CLI
---
    python up_p3_vectorized.py --check     # correctness gate + speed benchmark
"""
import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import p3_schedule as OLD                     # frozen ridge predictions / residuals
import p3_improved_verify as REF              # headline replay (gate target)
import p3_stochastic_schedule as STO          # review/VoI reference arm
from common import DATA, ATT, load_tasks, load_zones, write_json  # noqa: F401

EPS = 1e-9
CHANGEOVER = 0.5           # official movement.changeover_s
B_FLOOR = 0.2              # official service.reserve_min_s
PREFIX = (0.2, 0.6, 1.0)   # official observation.prefix_seconds
SCEN_Q = np.linspace(0.05, 0.95, 19)
Q_SLOPE = 0.55             # pressure -> chance-level slope (headline rule)
Q_KNEE = 0.75
Q_LO = 0.35
SLACK_COEF = 0.6           # slack reservation coefficient (baseline rule)
LATE_TOL_SLACK = 10.0
DROP_P = 1.05
DROP_ON = 0.15
REVIEW_BAR = 0.02          # VoI hurdle: 1 s delay + unit observation cost
MAX_ACTIONS = 200
DEFAULT_RISK = dict(Q_HI=0.60, GATE=0.5, LATE_TOL_RISK=12.0)

# candidate "reservation rule" codes
RULE_ABS = 0    # b = max(.2, alpha*(pred + Q_resid(qlevel)) + beta)   [headline]
RULE_ADD = 1    # b = max(.2, alpha*pred + beta + Q_resid(qlevel))
RULE_SLACK = 2  # b = max(.2, ph + 0.6*alpha*Q_resid(0.6))             [slack_old]
RULE_FIX = 3    # b = max(.2, alpha*(pred + Q_resid(Q_HI)) + beta)     [no pressure adapt.]


# --------------------------------------------------------------------------- #
# exact quantile (numpy 'linear' method, bit-for-bit)
# --------------------------------------------------------------------------- #
def quant_lerp(a, q):
    """np.quantile(a, q, method='linear') for sorted ``a``, vectorised over q."""
    a = np.asarray(a, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    n = a.size
    if n == 0:
        return np.full(q.shape, np.nan)
    if n == 1:
        return np.full(q.shape, a[0])
    idx = q * (n - 1)
    lo = np.floor(idx)
    lo_i = lo.astype(np.int64)
    hi_i = np.minimum(lo_i + 1, n - 1)
    g = idx - lo
    diff = a[hi_i] - a[lo_i]
    left = a[lo_i] + diff * g
    right = a[hi_i] - diff * (1.0 - g)
    return np.where(g >= 0.5, right, left)


# --------------------------------------------------------------------------- #
# static case data
# --------------------------------------------------------------------------- #
class CaseSpec(object):
    __slots__ = ("case", "H", "B", "K", "n", "jid", "release", "due", "w",
                 "zidx", "predcount", "succ", "zones", "ZD", "res0", "res1",
                 "res2", "q60", "ds")


_ZCACHE = {}


def _zone_table():
    if "t" in _ZCACHE:
        return _ZCACHE["t"]
    names = ["Z0"] + sorted(z for z in OLD.ZONES if z != "Z0")
    Z = {k: OLD.ZONES[k] for k in names}
    nz = len(names)
    ZD = np.zeros((nz, nz))
    for i, za in enumerate(names):
        for j, zb in enumerate(names):
            ZD[i, j] = math.hypot(Z[za][0] - Z[zb][0], Z[za][1] - Z[zb][1])
    _ZCACHE["t"] = (names, ZD)
    return names, ZD


def build_spec(case):
    conf = [c for c in STO.COND["cases"] if c["case_id"] == case][0]
    rows = STO.TASKS[STO.TASKS.case_id == case].sort_values("job_id").reset_index(drop=True)
    names, ZD = _zone_table()
    zi = {z: i for i, z in enumerate(names)}
    n = len(rows)
    sp = CaseSpec()
    sp.case = case
    sp.H = float(conf["horizon_s"])
    sp.B = float(conf["cost_budget"])
    sp.K = int(conf["observation_limit"])
    sp.n = n
    sp.jid = list(rows.job_id)
    sp.release = rows.release_s.astype(float).values
    sp.due = rows.due_s.astype(float).values
    sp.w = rows.priority_weight.astype(float).values
    sp.zidx = np.array([zi[z] for z in rows.zone_id], dtype=np.int64)
    sp.zones = names
    sp.ZD = ZD
    byid = {j: i for i, j in enumerate(sp.jid)}
    predcount = np.zeros(n, dtype=np.int16)
    succ = [[] for _ in range(n)]
    for i, p in enumerate(rows.predecessors):
        if isinstance(p, str) and p.strip() and p.strip().lower() != "nan":
            for q in p.split("|"):
                j = byid[q.strip()]
                predcount[i] += 1
                succ[j].append(i)
    sp.predcount = predcount
    sp.succ = succ
    sp.res0 = np.sort(np.asarray(OLD.RES[0.2], dtype=np.float64))
    sp.res1 = np.sort(np.asarray(OLD.RES[0.6], dtype=np.float64))
    sp.res2 = np.sort(np.asarray(OLD.RES[1.0], dtype=np.float64))
    sp.q60 = np.array([float(np.quantile(sp.res0, 0.6)),
                       float(np.quantile(sp.res1, 0.6)),
                       float(np.quantile(sp.res2, 0.6))])
    sp.ds = {p: np.quantile(sp.res0 if p == 0.2 else (sp.res1 if p == 0.6 else sp.res2), SCEN_Q)
             for p in PREFIX}
    return sp


def build_configs(spec, seeds):
    """Draw one validation unit per job with the reference RNG consumption order."""
    rows = STO.TASKS[STO.TASKS.case_id == spec.case].sort_values("job_id")
    S, n = len(seeds), spec.n
    d = np.zeros((S, n))
    p0 = np.zeros((S, n))
    p6 = np.zeros((S, n))
    p1 = np.zeros((S, n))
    for si, seed in enumerate(seeds):
        rng = random.Random(seed)
        for j, (_, row) in enumerate(rows.iterrows()):
            u = STO.sample_unit(row.family_id, rng)
            d[si, j] = float(u.duration_s)
            p0[si, j] = OLD.DHAT[(u.unit_id, 0.2)]
            p6[si, j] = OLD.DHAT[(u.unit_id, 0.6)]
            p1[si, j] = OLD.DHAT[(u.unit_id, 1.0)]
    return dict(d=d, pred0=p0, pred6=p6, pred1=p1, seeds=list(seeds))


def _scen(spec, cfg, alpha, beta):
    """SCEN[p][s, j, k] = alpha*max(prefix_p, pred_p(s,j)+Q_k(residual_p)) + beta."""
    out = np.empty((3, cfg["d"].shape[0], spec.n, SCEN_Q.size))
    pr = (cfg["pred0"], cfg["pred6"], cfg["pred1"])
    for p in range(3):
        ds = spec.ds[PREFIX[p]]
        out[p] = alpha * np.maximum(PREFIX[p], pr[p][:, :, None] + ds[None, None, :]) + beta
    return out


# --------------------------------------------------------------------------- #
# vectorised replay
# --------------------------------------------------------------------------- #
def simulate_batch(spec, cfg, alpha, beta, cand, n_seeds=None, scen=None):
    """Replay ``len(cand['q_hi']) * n_seeds`` trials in lock-step.

    ``cand`` holds per-candidate arrays: q_hi, gate, late_tol (float), rule,
    sel (0=risk selection, 1=slack selection), rev (bool).
    Row r = candidate c * n_seeds + seed s.
    """
    n = spec.n
    H, Bmax, K = spec.H, spec.B, spec.K
    nC = len(cand["q_hi"])
    S = n_seeds if n_seeds is not None else len(cfg["seeds"])
    B = nC * S
    Hp = H + EPS
    Bp = Bmax + EPS
    if scen is None:
        scen = _scen(spec, cfg, alpha, beta)
    sc0, sc1, sc2 = scen[0], scen[1], scen[2]

    seed_idx = np.tile(np.arange(S), nC)
    q_hi = np.repeat(np.asarray(cand["q_hi"], np.float64), S)
    gate = np.repeat(np.asarray(cand["gate"], np.float64), S)
    late = np.repeat(np.asarray(cand["late_tol"], np.float64), S)
    rule = np.repeat(np.asarray(cand["rule"], np.int8), S)
    sel = np.repeat(np.asarray(cand["sel"], np.int8), S)
    rev = np.repeat(np.asarray(cand["rev"], bool), S)
    any_rev_cand = bool(rev.any())

    started = np.zeros((B, n), bool)
    done = np.zeros((B, n), bool)
    dropped = np.zeros((B, n), bool)
    ontime = np.zeros((B, n), bool)
    Cmat = np.full((B, n), np.nan)
    pidx = np.zeros((B, n), np.int8)
    reviews = np.zeros((B, n), np.int8)
    prem = np.tile(spec.predcount.astype(np.int16), (B, 1))
    pred = np.tile(cfg["pred0"], (nC, 1))
    dtrue = np.tile(cfg["d"], (nC, 1))

    t = np.zeros(B)
    zone = np.zeros(B, np.int64)
    cost = np.zeros(B)
    steps = np.zeros(B, np.int64)
    nrev = np.zeros(B, np.int64)
    horizon_ok = np.ones(B, bool)
    budget_ok = np.ones(B, bool)
    overrun = np.zeros(B)
    idle = np.zeros(B)
    censored = np.zeros(B, bool)

    rel_j = spec.release[None, :]
    due_j = spec.due[None, :]
    w_j = spec.w[None, :]
    zidx = spec.zidx
    ZD = spec.ZD

    while True:
        act = (t < H - EPS) & (steps < MAX_ACTIONS)
        if not act.any():
            break
        steps[act] += 1

        feas = act[:, None] & (~started) & (rel_j <= (t[:, None] + EPS)) & (prem == 0)

        rem = np.zeros(B)
        for j in range(n):
            term = alpha * pred[:, j] + beta + 1.0
            rem = rem + np.where(started[:, j], 0.0, term)
        pressure = rem / np.maximum(H - t, 1e-6)
        qlevel = np.clip(q_hi - Q_SLOPE * np.maximum(0.0, pressure - Q_KNEE), Q_LO, q_hi)

        ph = alpha * pred + beta
        D = ZD[zone[:, None], zidx[None, :]]
        s = (t[:, None] + D) + CHANGEOVER

        qres0 = quant_lerp(spec.res0, qlevel)
        if pidx.any():
            qres1 = quant_lerp(spec.res1, qlevel)
            qres2 = quant_lerp(spec.res2, qlevel)
            qres = np.where(pidx == 0, qres0[:, None],
                            np.where(pidx == 1, qres1[:, None], qres2[:, None]))
        else:
            qres = qres0[:, None]

        b_abs = alpha * (pred + qres) + beta
        b_add = ph + qres
        b_slack = ph + SLACK_COEF * (alpha * spec.q60[pidx])
        if (rule == RULE_FIX).any():
            qfix0 = quant_lerp(spec.res0, q_hi)
            if pidx.any():
                qfix1 = quant_lerp(spec.res1, q_hi)
                qfix2 = quant_lerp(spec.res2, q_hi)
                qfix = np.where(pidx == 0, qfix0[:, None],
                                np.where(pidx == 1, qfix1[:, None], qfix2[:, None]))
            else:
                qfix = qfix0[:, None]
            b_fix = alpha * (pred + qfix) + beta
        else:
            b_fix = b_slack
        b = np.where(rule[:, None] == RULE_ABS, b_abs,
                     np.where(rule[:, None] == RULE_ADD, b_add,
                              np.where(rule[:, None] == RULE_SLACK, b_slack, b_fix)))
        b = np.maximum(B_FLOOR, b)
        c = (2.0 + 0.1 * b) + 0.2 * D
        valid = feas & ((s + b) <= Hp) & ((cost[:, None] + c) <= Bp)
        anyact = valid.any(1)

        # ---------------- paid re-observation (VoI), before the wait branch ----
        reviewed = np.zeros(B, bool)
        if any_rev_cand:
            rmask = act & rev & (nrev < K) & (cost + 1.0 <= Bmax) & (t + 1.0 < H)
            if rmask.any():
                rr = np.flatnonzero(rmask)
                elig = valid[rr] & (pidx[rr] < 2) & (reviews[rr] < 2)
                if elig.any():
                    nrr = rr.size
                    s_r = s[rr]
                    p_r = pidx[rr]
                    sidx = seed_idx[rr]
                    hasp = bool(p_r.any())
                    cnt0 = np.zeros((nrr, n))
                    cnt1 = np.zeros((nrr, n))
                    for k in range(SCEN_Q.size):
                        a0 = sc0[sidx, :, k]
                        if hasp:
                            a0 = np.where(p_r == 0, a0,
                                          np.where(p_r == 1, sc1[sidx, :, k], sc2[sidx, :, k]))
                            a1 = np.where(p_r == 0, sc1[sidx, :, k], sc2[sidx, :, k])
                        else:
                            a0 = sc0[sidx, :, k]
                            a1 = sc1[sidx, :, k]
                        cnt0 += (s_r + a0 <= due_j)
                        cnt1 += ((s_r + 1.0) + a1 <= due_j)
                    p0 = cnt0 / float(SCEN_Q.size)
                    p1 = cnt1 / float(SCEN_Q.size)
                    gain = w_j * (p1 - p0) - REVIEW_BAR
                    gain = np.where(elig, gain, -np.inf)
                    bj = gain.argmax(1)
                    bg = gain[np.arange(nrr), bj]
                    take = bg > 0.0
                    if take.any():
                        r2 = rr[take]
                        j2 = bj[take]
                        newp = pidx[r2, j2] + 1
                        pidx[r2, j2] = newp
                        reviews[r2, j2] += 1
                        nrev[r2] += 1
                        cost[r2] += 1.0
                        t[r2] += 1.0
                        sidx2 = seed_idx[r2]
                        pred[r2, j2] = np.where(newp == 1,
                                                cfg["pred6"][sidx2, j2],
                                                cfg["pred1"][sidx2, j2])
                        reviewed[r2] = True

        # ---------------- selection (risk / slack) -----------------------------
        sr = np.flatnonzero(act & (~reviewed) & anyact)
        if sr.size:
            ns = sr.size
            s_s = s[sr]
            ph_s = ph[sr]
            p_s = pidx[sr]
            sidx = seed_idx[sr]
            valid_s = valid[sr]
            cnt = np.zeros((ns, n))
            for k in range(SCEN_Q.size):
                sk = sc0[sidx, :, k]
                if p_s.any():
                    sk = np.where(p_s == 0, sk,
                                  np.where(p_s == 1, sc1[sidx, :, k], sc2[sidx, :, k]))
                cnt += (s_s + sk <= (due_j + EPS))
            onp = cnt / float(SCEN_Q.size)

            mx = np.maximum(0.5, ph_s)
            mw = np.maximum(0.03, onp)
            late_amt = np.maximum(0.0, (due_j - s_s) - ph_s)
            expo = np.exp(-(late_amt / late[sr][:, None]))
            score = ((w_j * mw) / mx) * expo
            onmask = valid_s & (onp >= gate[sr][:, None])
            has_on = onmask.any(1)
            pool = np.where(has_on[:, None], onmask, valid_s)
            score = np.where(pool, score, -np.inf)
            pick_risk = score.argmax(1)

            if (sel[sr] == 1).any():
                ok2 = valid_s & ((s_s + ph_s) <= (due_j + 0.5))
                has2 = ok2.any(1)
                sc_s = (w_j / mx) * np.exp(-(late_amt / LATE_TOL_SLACK))
                sc_s = np.where(ok2, sc_s, -np.inf)
                pick2 = sc_s.argmax(1)
                alt = ((s_s + ph_s) - due_j) / np.maximum(1.0, w_j)
                alt = np.where(valid_s, alt, np.inf)
                pick3 = alt.argmin(1)
                pick_slack = np.where(has2, pick2, pick3)
                pick = np.where(sel[sr] == 0, pick_risk, pick_slack)
            else:
                pick = pick_risk

            arow = np.arange(ns)
            onp_a = onp[arow, pick]
            keyd = (w_j * mw) / mx
            keyd = np.where(valid_s, keyd, np.inf)
            dropj = keyd.argmin(1)
            dropc = (pressure[sr] > DROP_P) & (onp_a < DROP_ON)

            # capacity relief: drop the lowest density job, t and cost unchanged
            dr = sr[dropc]
            if dr.size:
                dj = dropj[dropc]
                started[dr, dj] = True
                dropped[dr, dj] = True

            er = sr[~dropc]
            if er.size:
                ej = pick[~dropc]
                s_sel = s[er, ej]
                b_sel = b[er, ej]
                c_sel = c[er, ej]
                ptrue = alpha * dtrue[er, ej] + beta
                Cv = s_sel + ptrue
                Cmat[er, ej] = Cv
                cost[er] += c_sel
                started[er, ej] = True
                horizon_ok[er] &= ((s_sel + b_sel) <= Hp)
                over = Cv > Hp
                if over.any():
                    t[er[over]] = H
                ok = ~over
                # official measures: an overrun is service that exceeds its own
                # reservation; idle is the unused part of a reservation that did
                # finish inside the horizon; a job still running at H is censored.
                vis = np.minimum(ptrue, np.maximum(0.0, H - s_sel))
                overrun[er] += np.maximum(0.0, vis - b_sel)
                idle[er] += np.where(ok, np.maximum(0.0, b_sel - ptrue), 0.0)
                censored[er[over]] = True
                er2, ej2 = er[ok], ej[ok]
                if er2.size:
                    done[er2, ej2] = True
                    ontime[er2, ej2] = Cv[ok] <= (spec.due[ej2] + EPS)
                    t[er2] = s_sel[ok] + np.maximum(ptrue[ok], b_sel[ok])
                    zone[er2] = zidx[ej2]
                    newdone = np.zeros((B, n), bool)
                    newdone[er2, ej2] = True
                    for jj in range(n):
                        if not spec.succ[jj]:
                            continue
                        m = newdone[:, jj]
                        if m.any():
                            for j2 in spec.succ[jj]:
                                prem[m, j2] -= 1

        # ---------------- wait to the next release ----------------------------
        wr = np.flatnonzero(act & (~reviewed) & (~anyact))
        if wr.size:
            notstarted = ~started[wr]
            rel = np.where(notstarted & (rel_j > (t[wr][:, None] + EPS)), rel_j, np.inf)
            nxt = np.minimum(rel.min(1), H)
            stop = (nxt <= (t[wr] + EPS)) | (nxt >= H)
            go = ~stop
            if go.any():
                t[wr[go]] = nxt[go]

    budget_ok &= (cost <= Bp)

    W = float(sum(spec.w.tolist()))
    comp = np.zeros(B)
    ont = np.zeros(B)
    tard = np.zeros(B)
    fin = ~np.isnan(Cmat)
    Cval = np.where(fin, Cmat, H)
    for j in range(n):
        wj = spec.w[j]
        comp += wj * (done[:, j] & (~dropped[:, j]) & (Cmat[:, j] <= Hp))
        ont += wj * (done[:, j] & ontime[:, j])
        tard += wj * np.maximum(0.0, Cval[:, j] - spec.due[j])

    return dict(
        weighted_on_time_rate=(ont / W).reshape(nC, S),
        weighted_completion_rate=(comp / W).reshape(nC, S),
        weighted_tardiness_s=tard.reshape(nC, S),
        cost=cost.reshape(nC, S),
        elapsed_s=t.reshape(nC, S),
        n_done=done.sum(1).reshape(nC, S).astype(float),
        n_drop=dropped.sum(1).reshape(nC, S).astype(float),
        reviews=nrev.reshape(nC, S).astype(float),
        reserved_idle_s=idle.reshape(nC, S),
        observed_overrun_s=overrun.reshape(nC, S),
        censored_units=censored.reshape(nC, S).astype(float),
        budget_ok=budget_ok.reshape(nC, S),
        horizon_ok=horizon_ok.reshape(nC, S),
    )


# --------------------------------------------------------------------------- #
# reference wrappers (untouched engines)
# --------------------------------------------------------------------------- #
def simulate_reference(case, seed, policy="risk_old", params=None):
    r = REF.simulate(case, seed, policy, params=params)
    return {k: r[k] for k in ("weighted_on_time_rate", "weighted_completion_rate",
                              "weighted_tardiness_s", "cost", "elapsed_s",
                              "n_done", "n_drop")}


def simulate_stochastic(case, seed, policy="risk_old", reviews=False):
    r = STO.simulate(case, seed, policy, reviews_allowed=reviews)
    return {k: r[k] for k in ("weighted_on_time_rate", "weighted_completion_rate",
                              "weighted_tardiness_s", "cost", "elapsed_s",
                              "n_done", "n_drop")}


def _g(r, *names, default=None):
    for k in names:
        if k in r:
            return r[k]
    return default


def _cand_arrays(rows):
    """Normalise candidate dicts (accept both headline-style and lowercase keys)."""
    return dict(q_hi=np.array([_g(r, "Q_HI", "q_hi") for r in rows], float),
                gate=np.array([_g(r, "GATE", "gate") for r in rows], float),
                late_tol=np.array([_g(r, "LATE_TOL_RISK", "late_tol", default=12.0)
                                   for r in rows], float),
                rule=np.array([_g(r, "RULE", "rule", default=RULE_ABS) for r in rows], np.int8),
                sel=np.array([_g(r, "SEL", "sel", default=0) for r in rows], np.int8),
                rev=np.array([_g(r, "REVIEW", "rev", default=False) for r in rows], bool))


def run_vector(rows, cases, mapping=(1.0, 0.5), seeds=None, cfg_cache=None):
    """Run a candidate list on ``cases`` with one mapping; returns {case: arrays}."""
    alpha, beta = mapping
    out = {}
    for case in cases:
        sp = build_spec(case)
        cfg = (cfg_cache or {}).get((case, tuple(seeds))) if cfg_cache is not None else None
        if cfg is None:
            cfg = build_configs(sp, seeds)
            if cfg_cache is not None:
                cfg_cache[(case, tuple(seeds))] = cfg
        cand = _cand_arrays(rows)
        out[case] = simulate_batch(sp, cfg, alpha, beta, cand, n_seeds=len(seeds),
                                   scen=_scen(sp, cfg, alpha, beta))
    return out


# --------------------------------------------------------------------------- #
# correctness gate + speed benchmark
# --------------------------------------------------------------------------- #
SEEDS = list(range(2026111700, 2026111730))
CASES = ("S1", "S2", "S3")
METRICS = ("weighted_on_time_rate", "weighted_completion_rate", "weighted_tardiness_s",
           "cost", "elapsed_s", "n_done", "n_drop")
SELECTED = {"S2": dict(Q_HI=0.5, GATE=0.6, LATE_TOL_RISK=12.0),
            "S3": dict(Q_HI=0.6, GATE=0.5, LATE_TOL_RISK=20.0)}


def _compare(ref_rows, vec_rows, tag, store):
    """ref_rows / vec_rows: list aligned over seeds for one (case, arm)."""
    d = {}
    for m in METRICS:
        a = np.array([float(r[m]) for r in ref_rows], float)
        b = np.array(vec_rows[m], float)
        diff = np.abs(a - b)
        d[m] = dict(max_abs=float(diff.max()), mean_abs=float(diff.mean()),
                    n_exact=int((diff == 0).sum()), n=int(diff.size))
    store[tag] = d
    return max(v["max_abs"] for v in d.values())


def run_check(out_path=None):
    t_import = 0.0
    store = {}
    arms = []
    for case in CASES:
        arms.append((case, "slack_old", dict(SEL=1, RULE=RULE_SLACK, q_hi=0.6,
                                             gate=0.5, late_tol=12.0, REVIEW=False)))
    for case in CASES:
        arms.append((case, "risk_old_default", dict(SEL=0, RULE=RULE_ABS,
                                                    q_hi=DEFAULT_RISK["Q_HI"],
                                                    gate=DEFAULT_RISK["GATE"],
                                                    late_tol=DEFAULT_RISK["LATE_TOL_RISK"],
                                                    REVIEW=False)))
    for case in ("S2", "S3"):
        p = SELECTED[case]
        arms.append((case, "risk_old_selected", dict(SEL=0, RULE=RULE_ABS,
                                                     q_hi=p["Q_HI"], gate=p["GATE"],
                                                     late_tol=p["LATE_TOL_RISK"],
                                                     REVIEW=False)))

    t_ref = 0.0
    t_vec = 0.0
    gate_max = 0.0
    per_arm = {}
    for case, name, row in arms:
        sp = build_spec(case)
        cfg = build_configs(sp, SEEDS)
        sc = _scen(sp, cfg, 1.0, 0.5)
        t0 = time.time()
        vec = simulate_batch(sp, cfg, 1.0, 0.5, _cand_arrays([row]), n_seeds=len(SEEDS),
                             scen=sc)
        t_vec += time.time() - t0
        t0 = time.time()
        ref_rows = [REF.simulate(case, sd, "slack_old" if name == "slack_old" else "risk_old",
                                 params=None if name != "risk_old_selected" else
                                 dict(Q_HI=row["q_hi"], GATE=row["gate"],
                                      LATE_TOL_RISK=row["late_tol"]))
                    for sd in SEEDS]
        t_ref += time.time() - t0
        mx = _compare(ref_rows, vec, "%s|%s" % (case, name), per_arm)
        gate_max = max(gate_max, mx)

    # review/VoI branch against the stochastic engine (S2, S3).
    # NOTE: p3_stochastic_schedule hardcodes Q_HI=0.70 in its qlevel rule, so the
    # only faithful comparison is at Q_HI=0.70 (GATE .5, LATE_TOL_RISK 12, abs rule).
    rev_max = 0.0
    rev_arm = dict(SEL=0, RULE=RULE_ABS, q_hi=0.70, gate=0.5, late_tol=12.0, REVIEW=True)
    for case in ("S2", "S3"):
        sp = build_spec(case)
        cfg = build_configs(sp, SEEDS)
        vec = simulate_batch(sp, cfg, 1.0, 0.5, _cand_arrays([rev_arm]), n_seeds=len(SEEDS),
                             scen=_scen(sp, cfg, 1.0, 0.5))
        t0 = time.time()
        ref_rows = [STO.simulate(case, sd, "risk_old", reviews_allowed=True) for sd in SEEDS]
        t_ref += time.time() - t0
        mx = _compare(ref_rows, vec, "%s|risk_review_q70" % case, per_arm)
        rev_max = max(rev_max, mx)

    # ---- speed benchmark --------------------------------------------------- #
    sp = build_spec("S3")
    cfg = build_configs(sp, SEEDS)
    scen = _scen(sp, cfg, 1.0, 0.5)
    rows30 = [dict(SEL=0, RULE=RULE_ABS, q_hi=0.5 + 0.01 * i,
                   gate=0.4 + 0.01 * (i % 5), late_tol=12.0, REVIEW=False) for i in range(30)]
    t0 = time.time()
    simulate_batch(sp, cfg, 1.0, 0.5, _cand_arrays(rows30), n_seeds=len(SEEDS), scen=scen)
    t_vec30 = time.time() - t0
    t0 = time.time()
    for i in range(30):
        for sd in SEEDS:
            REF.simulate("S3", sd, "risk_old",
                         params=dict(Q_HI=0.5 + 0.01 * i,
                                     GATE=0.4 + 0.01 * (i % 5),
                                     LATE_TOL_RISK=12.0))
    t_ref30 = time.time() - t0

    # 960-candidate search unit (30 seeds).  Reference side extrapolated from the
    # measured per-trial cost above -- running 28 800 python trials is minutes.
    rows960 = [dict(SEL=0,
                    RULE=(RULE_ABS if i % 2 == 0 else RULE_ADD),
                    q_hi=0.40 + 0.01 * (i % 31), gate=0.40 + 0.005 * (i % 21),
                    late_tol=6.0 + 0.5 * (i % 33), REVIEW=bool(i % 2)) for i in range(960)]
    t0 = time.time()
    simulate_batch(sp, cfg, 1.0, 0.5, _cand_arrays(rows960), n_seeds=len(SEEDS), scen=scen)
    t_vec960 = time.time() - t0
    per_trial_ref = t_ref30 / (30 * len(SEEDS))

    out = dict(
        _meta=dict(purpose="bit-exact vectorised replay of code/p3_improved_verify.simulate",
                   seeds=SEEDS, cases=list(CASES),
                   reference="code/p3_improved_verify.py (slack_old / risk_old, no review)",
                   review_reference="code/p3_stochastic_schedule.simulate(risk_old, reviews_allowed=True)",
                   review_arm_params=dict(Q_HI=0.70, GATE=0.5, LATE_TOL_RISK=12.0,
                                          rule="abs", why="stochastic engine hardcodes Q_HI=0.70"),
                   row_layout="row = candidate * n_seeds + seed",
                   tolerance=1e-9),
        gate=dict(max_abs_diff_all=float(gate_max),
                  review_arm_max_abs_diff=float(rev_max),
                  passed=bool(gate_max <= 1e-9 and rev_max <= 1e-9),
                  metric_tolerance=1e-9,
                  per_arm=per_arm),
        timing=dict(
            # replay-only wall clock, setup (config draws, scenario tables) excluded
            single_candidate_30_seeds=dict(vector_seconds=float(t_vec),
                                           reference_seconds=float(t_ref),
                                           trials=int(len(arms) * len(SEEDS) + 2 * len(SEEDS)),
                                           speedup=float(t_ref / t_vec) if t_vec > 0 else None,
                                           note="vector side pays a fixed per-call overhead; this is the worst case"),
            batch_30cand_x_30seeds_s3=dict(vector_seconds=float(t_vec30),
                                          reference_seconds=float(t_ref30),
                                          trials=int(30 * len(SEEDS)),
                                          speedup=float(t_ref30 / t_vec30)),
            search_unit_960cand_x_30seeds_s3=dict(vector_seconds=float(t_vec960),
                                                  trials=int(960 * len(SEEDS)),
                                                  reference_per_trial_s=float(per_trial_ref),
                                                  reference_extrapolated_s=float(960 * len(SEEDS) * per_trial_ref),
                                                  speedup=float(960 * len(SEEDS) * per_trial_ref / t_vec960)),
        ),
    )
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=os.path.join(DATA, "up_p3_vec_check.json"))
    args = ap.parse_args()
    if args.check:
        t0 = time.time()
        out = run_check(args.out)
        print(json.dumps(dict(gate={k: out["gate"][k] for k in
                                 ("max_abs_diff_all", "review_arm_max_abs_diff", "passed")},
                             timing={k: out["timing"][k] for k in out["timing"]}),
                         indent=1, default=float))
        print("saved ->", args.out, " total %.1fs" % (time.time() - t0))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()