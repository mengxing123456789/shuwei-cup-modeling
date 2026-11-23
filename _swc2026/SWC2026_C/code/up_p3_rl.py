# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p3_rl.py -- P3 deep-RL reservation policy (NEW script).

Scope discipline
----------------
NEW file.  Does not touch ``main.tex``, ``slots.tex`` or
``code/up_p3_vectorized.py``.  Imports the vectorised engine's ``build_spec`` /
``build_configs`` / ``_scen`` / ``quant_lerp`` so all arithmetic comes from the
frozen engine, and writes only ``data/up_p3_rl.json`` (+ a temporary ckpt).

What is learned
---------------
At every dispatch step the online scheduler decides *which* job to run and *how
much reserve* ``b`` to declare.  The existing policies fix both.  Here the
selection rule is held FIXED (per arm) and a 2x128 MLP chooses ``b`` from the
official 13-level grid ``{q0.30,...,q0.90}``, where level ``q`` means
``b = max(0.2, alpha*(pred + Q_resid(q)) + beta)`` -- the same mapping the rule
family uses, so the action set contains the rule's own choice.

Arms (identical training procedure, different fixed selector):
  A  slack selection  -> isolates the reserve decision against ``slack_old``
  B  risk  selection  -> isolates it against the strongest searched rule
Arm A is the pre-registered primary arm (it is the comparison named by the
baseline definition: EDF/slack selection + family-residual-quantile reserve).

Reward
------
The weighted on-time rate decomposes exactly additively: dispatching job ``j``
earns ``r_t = w_j * 1[C_j <= due_j] / W`` (0 if dropped / overruns / never
started), so ``sum_t r_t`` IS ``weighted_on_time_rate``.

Gate
----
The stepper must reproduce ``up_p3_vectorized.simulate_batch`` on the fixed
reference rules: max |dwotr| < 1e-6 over 3 cases x 30 seeds x 3 rule configs.

CLI
---
    python up_p3_rl.py --stage gate
    python up_p3_rl.py --stage diag
    python up_p3_rl.py --stage train
    python up_p3_rl.py --stage final
    python up_p3_rl.py --stage all
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V  # noqa: E402

EPS = V.EPS
H_FLOOR = V.B_FLOOR
CHANGEOVER = V.CHANGEOVER
SCEN_Q = V.SCEN_Q
NQ = SCEN_Q.size
Q_SLOPE, Q_KNEE, Q_LO = V.Q_SLOPE, V.Q_KNEE, V.Q_LO
DROP_P, DROP_ON = V.DROP_P, V.DROP_ON
ALPHA, BETA = 1.0, 0.5

Q_GRID = np.round(np.arange(0.30, 0.905, 0.05), 2)
assert Q_GRID.size == 13
NA = Q_GRID.size            # number of discrete reserve actions (13)
QRES_GRID = V.quant_lerp(np.sort(V.build_spec("S1").res0), Q_GRID)  # case-independent

SEED_ALL = list(range(2026111700, 2026111730))
SEED_TRAIN = SEED_ALL[:15]
SEED_VAL = SEED_ALL[15:25]
SEED_TEST = SEED_ALL[25:]
SEED_POOL = SEED_TRAIN + SEED_VAL          # diagnostics only; test stays clean
CASES = ["S1", "S2", "S3"]

# strongest existing rule per case (chosen on published 30-seed numbers)
CASE_CFG = {
    "S1": dict(sel="slack", q_hi=0.60, gate=0.5, late=10.0),
    "S2": dict(sel="risk", q_hi=0.50, gate=0.60, late=12.0),
    "S3": dict(sel="risk", q_hi=0.60, gate=0.5, late=20.0),
}
RISK_DEFAULT = dict(q_hi=0.60, gate=0.5, late=12.0)
SLACK_CFG = dict(q_hi=0.60, gate=0.5, late=10.0)

DATA_DIR = V.DATA
OUT_JSON = os.path.join(DATA_DIR, "up_p3_rl.json")

PROTOCOL = dict(
    script="code/up_p3_rl.py",
    algorithm="REINFORCE with learned baseline (A2C critic); one policy net per arm",
    seed=20261121,
    train_seeds=SEED_TRAIN,
    val_seeds=SEED_VAL,
    test_seeds=SEED_TEST,
    alpha=ALPHA, beta=BETA,
    action_grid=[float(q) for q in Q_GRID],
    action_rule="b = max(0.2, alpha*(pred + Q_resid(q)) + beta)",
    reward="r_t = w_j*1[C_j<=due_j]/W per dispatch; sum = weighted on-time rate",
    selector="held fixed per arm (A slack, B risk); only the reserve b is learned",
    net="MLP 36-128-128 -> 13 logits + 1 value; tanh; Adam",
    budget_gpu_minutes=25,
    gate="max |dwotr| vs up_p3_vectorized.simulate_batch < 1e-6",
    primary_arm="A (slack selection, baseline slack_old)",
    pass_rule="mean of S2,S3 test delta vs baseline >= 0.020 AND both paired 95% CI lower > 0",
    test_once="test seeds evaluated exactly once, after both arms are frozen",
)


# --------------------------------------------------------------------------- #
# stats helpers
# --------------------------------------------------------------------------- #
def t_crit(df):
    tab = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
           8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
           14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
           20: 2.086, 24: 2.064, 29: 2.045, 30: 2.042}
    if df <= 0:
        return 0.0
    if df in tab:
        return tab[df]
    if df > 30:
        return 1.96 + 2.4 / df
    lo = max(k for k in tab if k < df)
    hi = min(k for k in tab if k > df)
    return tab[lo] + (tab[hi] - tab[lo]) * (df - lo) / (hi - lo)


def summarize(x):
    x = np.asarray(x, float)
    n = x.size
    m = float(x.mean()) if n else float("nan")
    sd = float(x.std(ddof=1)) if n > 1 else 0.0
    half = t_crit(n - 1) * sd / math.sqrt(n) if n > 1 else 0.0
    npos = int((x > 0).sum()) if n else 0
    p = 1.0 if n else float("nan")
    if n:
        p = sum(math.comb(n, k) for k in range(npos, n + 1)) / 2.0 ** n
    return dict(n=n, delta_mean=m, sd=sd, ci95=half, lower=m - half, upper=m + half,
                n_pos=npos, n_neg=int((x < 0).sum()) if n else 0, sign_p=p,
                per_seed=[float(v) for v in x])


def paired(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    out = summarize(a - b)
    out["a_mean"] = float(a.mean())
    out["b_mean"] = float(b.mean())
    return out


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def base_doc(stage):
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "_meta": dict(PROTOCOL, stage=stage, written_at=now, gpu_train_seconds=None),
        "gate": {"alignment_max_abs_diff": None, "passed": False},
        "baseline": {}, "rl": {}, "paired": {}, 
        "verdict": {"passes": False, "reason": "not evaluated yet"},
        "_progress": {"stage": stage},
    }


# --------------------------------------------------------------------------- #
# case plumbing
# --------------------------------------------------------------------------- #
_SPEC, _CFG, _FAM = {}, {}, {}


def get_case(case, seeds):
    key = (case, len(seeds), tuple(seeds))
    sp = _SPEC.get(case)
    if sp is None:
        sp = V.build_spec(case)
        _SPEC[case] = sp
        rows = V.STO.TASKS[V.STO.TASKS.case_id == case].sort_values("job_id")
        names = ["A", "L", "P"]
        f1 = np.zeros((3, sp.n))
        for i, f in enumerate(list(rows.family_id)):
            f1[names.index(f), i] = 1.0
        _FAM[case] = f1
    if key not in _CFG:
        cfg = V.build_configs(sp, list(seeds))
        cfg["scen"] = V._scen(sp, cfg, ALPHA, BETA)
        cfg["fam1h"] = _FAM[case]
        _CFG[key] = cfg
    return sp, _CFG[key]


def model_arm(case, bmode):
    """Fixed-selector arm descriptor.  bmode: 'slack' | 'risk'."""
    if bmode == "slack":
        return dict(sel="slack", params=SLACK_CFG)
    return dict(sel="risk", params=CASE_CFG[case])


# --------------------------------------------------------------------------- #
# stepper
# --------------------------------------------------------------------------- #
def collect(traj, step, rows, feats, mask, act, rew):
    traj["feat"].append(feats)
    traj["mask"].append(mask)
    traj["act"].append(act)
    traj["row"].append(rows)
    traj["rew"].append(rew)


def traj_to_batch(traj):
    if not traj["feat"]:
        return None
    feats = np.concatenate(traj["feat"], 0)
    masks = np.concatenate(traj["mask"], 0)
    acts = np.concatenate(traj["act"], 0)
    rows = np.concatenate(traj["row"], 0)
    rews = np.concatenate(traj["rew"], 0)
    g = np.zeros(rows.size)
    for r in np.unique(rows):
        idx = np.flatnonzero(rows == r)
        g[idx] = np.cumsum(rews[idx][::-1])[::-1]
    return feats, masks, acts, g


def rollout(sp, cfg, arm, actor=None, greedy=False, bmode="rule", fixed_q=None,
            do_collect=False):
    n, H, Bmax = sp.n, sp.H, sp.B
    S = cfg["d"].shape[0]
    Hp, Bp = H + EPS, Bmax + EPS
    pred, dtrue = cfg["pred0"], cfg["d"]
    sel, par = arm["sel"], arm["params"]
    q_hi, gate, late = par["q_hi"], par["gate"], par["late"]

    started = np.zeros((S, n), bool)
    done = np.zeros((S, n), bool)
    dropped = np.zeros((S, n), bool)
    ontime = np.zeros((S, n), bool)
    Cmat = np.full((S, n), np.nan)
    prem = np.tile(sp.predcount.astype(np.int16), (S, 1))
    t = np.zeros(S)
    zone = np.zeros(S, np.int64)
    cost = np.zeros(S)
    steps = np.zeros(S, np.int64)
    frozen = np.zeros(S, bool)
    horizon_ok = np.ones(S, bool)

    rel_j = sp.release[None, :]
    due_j = sp.due[None, :]
    w_j = sp.w[None, :]
    W = float(sum(sp.w.tolist()))
    zidx, ZD = sp.zidx, sp.ZD
    nz = ZD.shape[0] - 1.0
    fam1h, q60 = cfg["fam1h"], sp.q60[0]
    sc0 = cfg["scen"][0]
    traj = dict(feat=[], mask=[], act=[], row=[], rew=[]) if do_collect else None

    while True:
        actv = (t < H - EPS) & (steps < V.MAX_ACTIONS) & (~frozen)
        if not actv.any():
            break
        steps[actv] += 1

        feas = actv[:, None] & (~started) & (rel_j <= (t[:, None] + EPS)) & (prem == 0)
        rem = np.zeros(S)
        for j in range(n):
            rem = rem + np.where(started[:, j], 0.0, ALPHA * pred[:, j] + BETA + 1.0)
        pressure = rem / np.maximum(H - t, 1e-6)
        qlevel = np.clip(q_hi - Q_SLOPE * np.maximum(0.0, pressure - Q_KNEE), Q_LO, q_hi)

        ph = ALPHA * pred + BETA
        D = ZD[zone[:, None], zidx[None, :]]
        s = (t[:, None] + D) + CHANGEOVER

        if bmode == "slack":
            b_rule = np.maximum(H_FLOOR, ph + V.SLACK_COEF * (ALPHA * q60))
        else:
            qres = V.quant_lerp(sp.res0, qlevel)
            b_rule = np.maximum(H_FLOOR, ALPHA * (pred + qres[:, None]) + BETA)
        c_rule = (2.0 + 0.1 * b_rule) + 0.2 * D
        valid = feas & ((s + b_rule) <= Hp) & ((cost[:, None] + c_rule) <= Bp)
        anyact = valid.any(1)

        sr = np.flatnonzero(actv & anyact)
        onp_s = None
        pick = None
        if sr.size:
            s_s, ph_s, v_s = s[sr], ph[sr], valid[sr]
            cnt = np.zeros((sr.size, n))
            for k in range(NQ):
                cnt += (s_s + sc0[sr, :, k] <= (due_j + EPS))
            onp_s = cnt / float(NQ)
            pick = np.full(S, -1, np.int64)
            pick[sr] = _select(sel, s_s, ph_s, v_s, onp_s, w_j, due_j, late, gate)

        # drop branch (identical to engine: drop wins, t and cost unchanged)
        er, ej = None, None
        if sr.size:
            onp_a = onp_s[np.arange(sr.size), pick[sr]]
            keyd = np.where(valid[sr],
                            (w_j * np.maximum(0.03, onp_s)) / np.maximum(0.5, ph[sr]),
                            np.inf)
            dropj = keyd.argmin(1)
            dropc = (pressure[sr] > DROP_P) & (onp_a < DROP_ON)
            if dropc.any():
                dr = sr[dropc]
                started[dr, dropj[dropc]] = True
                dropped[dr, dropj[dropc]] = True
            keep = ~dropc
            er = sr[keep]
            ej = pick[er]

        rw_vec = None
        if er is not None and er.size:
            s_e, D_e = s[er, ej], D[er, ej]
            pred_e, ph_e = pred[er, ej], ph[er, ej]
            if bmode in ("rule", "slack", "grid"):
                if bmode == "grid":
                    qq = float(Q_GRID[int(fixed_q)])
                    b_sel = np.maximum(H_FLOOR, ALPHA * (pred_e + QRES_GRID[int(fixed_q)]) + BETA)
                    c_sel = (2.0 + 0.1 * b_sel) + 0.2 * D_e
                else:
                    b_sel, c_sel = b_rule[er, ej], c_rule[er, ej]
            else:
                pos = np.searchsorted(sr, er)
                onp_sel = onp_s[pos, ej]
                b_lvl = np.maximum(H_FLOOR, ALPHA * (pred_e[:, None] + QRES_GRID[None, :]) + BETA)
                c_lvl = (2.0 + 0.1 * b_lvl) + 0.2 * D_e[:, None]
                mask = ((s_e[:, None] + b_lvl) <= Hp) & \
                       ((cost[er][:, None] + c_lvl) <= Bp)
                # the rule's own b may be larger than every grid level; q0.30 is
                # the smallest reserve and the rule's b dominated it, so a valid
                # dispatch always admits at least level 0 (asserted below).
                bad = ~mask.any(1)
                if bad.any():
                    raise RuntimeError("no feasible grid level on dispatchable job")
                feats = _features(sp, par, er, ej, t, pressure, cost, started,
                                  valid, s_e, ph_e, D_e, onp_sel, qlevel[er],
                                  fam1h, q60, nz)
                a, logp = actor.act(feats, mask, greedy=greedy)
                b_sel = b_lvl[np.arange(er.size), a]
                c_sel = c_lvl[np.arange(er.size), a]
                if do_collect:
                    _hold = dict(feats=feats, mask=mask, act=a, rows=er.copy())
            rw_vec = _apply(sp, er, ej, s_e, b_sel, c_sel, pred, dtrue, H, Hp,
                            started, done, ontime, Cmat, prem, t, zone, cost,
                            horizon_ok, zidx, n, W)
            if bmode not in ("rule", "slack", "grid") and do_collect:
                collect(traj, None, _hold["rows"], _hold["feats"], _hold["mask"],
                        _hold["act"], rw_vec)

        wr = np.flatnonzero(actv & (~anyact))
        if wr.size:
            notstarted = ~started[wr]
            rel = np.where(notstarted & (rel_j > (t[wr][:, None] + EPS)), rel_j, np.inf)
            nxt = np.minimum(rel.min(1), H)
            stop = (nxt <= (t[wr] + EPS)) | (nxt >= H)
            go = ~stop
            if go.any():
                t[wr[go]] = nxt[go]
            if (~go).any():
                # no valid dispatch and no future release: state can never change
                # again (the reference engine only spins to MAX_ACTIONS).  Freezing
                # is outcome-identical and is covered by the alignment gate.
                frozen[wr[~go]] = True

    Wt = float(sum(sp.w.tolist()))
    Cval = np.where(np.isnan(Cmat), H, Cmat)
    comp = np.zeros(S)
    ont = np.zeros(S)
    tard = np.zeros(S)
    for j in range(n):
        wj = sp.w[j]
        comp += wj * (done[:, j] & (~dropped[:, j]) & (Cmat[:, j] <= Hp))
        ont += wj * (done[:, j] & ontime[:, j])
        tard += wj * np.maximum(0.0, Cval[:, j] - sp.due[j])
    return dict(weighted_on_time_rate=ont / Wt,
                weighted_completion_rate=comp / Wt,
                weighted_tardiness_s=tard, cost=cost, elapsed_s=t,
                n_done=done.sum(1).astype(float), n_drop=dropped.sum(1).astype(float),
                budget_ok=(cost <= Bp), horizon_ok=horizon_ok,
                traj=traj)


def _select(sel, s, ph, valid, onp, w_j, due_j, late, gate):
    mx = np.maximum(0.5, ph)
    late_amt = np.maximum(0.0, (due_j - s) - ph)
    if sel == "risk":
        score = ((w_j * np.maximum(0.03, onp)) / mx) * np.exp(-(late_amt / late))
        onmask = valid & (onp >= gate)
        pool = np.where(onmask.any(1)[:, None], onmask, valid)
        return np.where(pool, score, -np.inf).argmax(1)
    ok2 = valid & ((s + ph) <= (due_j + 0.5))
    sc_s = np.where(ok2, (w_j / mx) * np.exp(-(late_amt / V.LATE_TOL_SLACK)), -np.inf)
    pick2 = sc_s.argmax(1)
    alt = np.where(valid, ((s + ph) - due_j) / np.maximum(1.0, w_j), np.inf)
    pick3 = alt.argmin(1)
    return np.where(ok2.any(1), pick2, pick3)


def _apply(sp, ex, ej, s_e, b_sel, c_sel, pred, dtrue, H, Hp, started, done,
           ontime, Cmat, prem, t, zone, cost, horizon_ok, zidx, n, W):
    ptrue = ALPHA * dtrue[ex, ej] + BETA
    Cv = s_e + ptrue
    Cmat[ex, ej] = Cv
    cost[ex] += c_sel
    started[ex, ej] = True
    horizon_ok[ex] &= ((s_e + b_sel) <= Hp)
    over = Cv > Hp
    if over.any():
        t[ex[over]] = H
    r = np.zeros(ex.size)
    ok = ~over
    if ok.any():
        ex2, ej2 = ex[ok], ej[ok]
        on = Cv[ok] <= (sp.due[ej2] + EPS)
        done[ex2, ej2] = True
        ontime[ex2, ej2] = on
        t[ex2] = s_e[ok] + np.maximum(ptrue[ok], b_sel[ok])
        zone[ex2] = zidx[ej2]
        for jj in np.unique(ej2):
            m = ej2 == jj
            for j2 in sp.succ[jj]:
                prem[ex2[m], j2] -= 1
        r[ok] = sp.w[ej2] * on / W
    return r


def _features(sp, par, ex, ej, t, pressure, cost, started, valid, s_e, ph_e,
              D_e, onp_sel, qlevel_e, fam1h, q60, nz):
    n, H, B = sp.n, sp.H, sp.B
    ns = ex.size
    g = np.zeros((ns, 14))
    g[:, 0] = t[ex] / H
    g[:, 1] = (H - t[ex]) / H
    g[:, 2] = pressure[ex]
    g[:, 3] = cost[ex] / B
    g[:, 4] = (B - cost[ex]) / B
    g[:, 5] = (~started[ex]).sum(1) / n
    g[:, 6] = valid[ex].sum(1) / n
    g[:, 7] = H / 125.0
    g[:, 8] = B / 40.0
    g[:, 9] = n / 16.0
    g[:, 10] = 1.0
    g[:, 11] = float(sp.case == "S1")
    g[:, 12] = float(sp.case == "S2")
    g[:, 13] = float(sp.case == "S3")

    j = np.zeros((ns, 22))
    j[:, 0] = ph_e / H
    j[:, 1] = pred_j = (ph_e - BETA) / H
    j[:, 2] = D_e / H
    j[:, 3] = s_e / H
    j[:, 4] = sp.due[ej] / H
    j[:, 5] = (sp.due[ej] - s_e) / H
    j[:, 6] = (sp.due[ej] - s_e - ph_e) / H
    j[:, 7] = sp.w[ej] / 3.0
    j[:, 8] = onp_sel
    j[:, 9] = np.log1p(sp.w[ej] / np.maximum(0.5, ph_e))
    j[:, 10] = sp.release[ej] / H
    j[:, 11] = sp.predcount[ej] / 3.0
    j[:, 12] = np.array([len(sp.succ[k]) for k in ej], float) / 4.0
    j[:, 13] = q60 / H
    j[:, 14] = qlevel_e
    j[:, 15] = par["q_hi"]
    j[:, 16] = par["gate"]
    j[:, 17] = par["late"] / 20.0
    j[:, 18:21] = fam1h[:, ej].T
    j[:, 21] = sp.zidx[ej] / nz
    return np.concatenate([g, j], axis=1)


NFEAT = 36
assert _features(V.build_spec("S1"), SLACK_CFG, np.array([0]), np.array([0]),
                 np.zeros(1), np.zeros(1), np.zeros(1), np.zeros((1, 8), bool),
                 np.ones((1, 8), bool), np.zeros(1), np.zeros(1), np.zeros(1),
                 np.zeros(1), np.zeros(1), np.zeros((3, 8)), 0.0, 4.0).shape[1] == NFEAT


# --------------------------------------------------------------------------- #
# reference evaluation through the engine
# --------------------------------------------------------------------------- #
def engine_rule(case, seeds, kind):
    sp, cfg = get_case(case, seeds)
    if kind == "slack_old":
        cand = dict(q_hi=[0.60], gate=[0.5], late_tol=[10.0],
                    rule=[V.RULE_SLACK], sel=[1], rev=[False])
    elif kind == "risk_default":
        p = RISK_DEFAULT
        cand = dict(q_hi=[p["q_hi"]], gate=[p["gate"]], late_tol=[p["late"]],
                    rule=[V.RULE_ABS], sel=[0], rev=[False])
    elif kind == "risk_case":
        p = CASE_CFG[case]
        cand = dict(q_hi=[p["q_hi"]], gate=[p["gate"]], late_tol=[p["late"]],
                    rule=[V.RULE_ABS], sel=[0], rev=[False])
    else:
        raise KeyError(kind)
    r = V.simulate_batch(sp, cfg, ALPHA, BETA, cand)
    return {k: v[0] for k, v in r.items()}


def policy_rollout(case, seeds, armmode, actor, greedy, collect=False):
    sp, cfg = get_case(case, seeds)
    arm = model_arm(case, armmode)
    return rollout(sp, cfg, arm, actor=actor, greedy=greedy, bmode="policy",
                   do_collect=collect)


# --------------------------------------------------------------------------- #
# gate
# --------------------------------------------------------------------------- #
def stage_gate(seeds=SEED_ALL):
    rows = []
    worst = 0.0
    for case in CASES:
        for kind, bmode in (("slack_old", "slack"), ("risk_default", "rule"),
                            ("risk_case", "rule")):
            eng = engine_rule(case, seeds, kind)
            arm = dict(sel="slack", params=SLACK_CFG) if bmode == "slack" \
                else dict(sel="risk", params=(RISK_DEFAULT if kind == "risk_default"
                                              else CASE_CFG[case]))
            mine = rollout(get_case(case, seeds)[0], get_case(case, seeds)[1],
                           arm, bmode=bmode)
            d = {}
            for k in ("weighted_on_time_rate", "weighted_completion_rate", "cost",
                      "weighted_tardiness_s"):
                dv = float(np.max(np.abs(np.asarray(mine[k]) - np.asarray(eng[k]))))
                d[k] = dv
                worst = max(worst, dv)
            rows.append(dict(case=case, config=kind, **d))
            print("gate %s %-13s dwotr=%.3e dcost=%.3e" %
                  (case, kind, d["weighted_on_time_rate"], d["cost"]))
    doc = base_doc("gate")
    doc["gate"] = dict(alignment_max_abs_diff=worst,
                       tolerance=1e-6,
                       passed=bool(worst < 1e-6),
                       seeds=list(seeds), cases=CASES, detail=rows)
    doc["verdict"] = dict(passes=bool(worst < 1e-6),
                          reason="alignment gate %s (max_abs_diff=%.3e)" %
                                 ("passed" if worst < 1e-6 else "FAILED", worst))
    write_json(OUT_JSON, doc)
    print("GATE max_abs_diff=%.6e passed=%s" % (worst, worst < 1e-6))
    return worst < 1e-6


# --------------------------------------------------------------------------- #
# diagnostics (train+val only)
# --------------------------------------------------------------------------- #
def stage_diag(seeds=SEED_POOL):
    out = {}
    for case in CASES:
        d = {}
        for kind in ("slack_old", "risk_default", "risk_case"):
            r = engine_rule(case, seeds, kind)
            d[kind] = dict(on_time=float(r["weighted_on_time_rate"].mean()),
                           completion=float(r["weighted_completion_rate"].mean()),
                           cost=float(r["cost"].mean()))
        # post-hoc min-reservation arms through my stepper (gate-checked)
        for tag, arm in (("slacksel_q30", dict(sel="slack", params=SLACK_CFG)),
                         ("risksel_q30", dict(sel="risk", params=CASE_CFG[case]))):
            sp, cfg = get_case(case, seeds)
            r = rollout(sp, cfg, arm, bmode="grid", fixed_q=0)
            d[tag] = dict(on_time=float(r["weighted_on_time_rate"].mean()),
                          completion=float(r["weighted_completion_rate"].mean()),
                          cost=float(r["cost"].mean()))
        out[case] = d
        print("diag %s %s" % (case, json.dumps({k: round(v["on_time"], 4)
                                                for k, v in d.items()})))
    doc = json.load(open(OUT_JSON, encoding="utf-8")) if os.path.exists(OUT_JSON) \
        else base_doc("diag")
    doc["_progress"] = dict(stage="diag", seeds=list(seeds), fixed_arms=out)
    write_json(OUT_JSON, doc)
    return out

# --------------------------------------------------------------------------- #
# training
# --------------------------------------------------------------------------- #
def make_actor(seed=PROTOCOL["seed"]):
    import torch
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = build_net(NFEAT, NA).to(device)
    return net, device


def build_net(nfeat, nact):
    import torch.nn as nn

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = nn.Sequential(nn.Linear(nfeat, 128), nn.Tanh(),
                                      nn.Linear(128, 128), nn.Tanh())
            self.pi = nn.Linear(128, nact)
            self.v = nn.Linear(128, 1)

        def forward(self, x):
            h = self.body(x)
            return self.pi(h), self.v(h).squeeze(-1)
    return Net()


class Actor(object):
    def __init__(self, net, device):
        self.net, self.device = net, device

    def act(self, feats, masks, greedy=False):
        import torch
        if feats.shape[0] == 0:
            return np.zeros(0, int), np.zeros(0)
        x = torch.as_tensor(feats, dtype=torch.float32, device=self.device)
        m = torch.as_tensor(masks, dtype=torch.bool, device=self.device)
        with torch.no_grad():
            logits, _ = self.net(x)
            logits = logits.masked_fill(~m, -1e9)
            logp_all = torch.log_softmax(logits, dim=1)
            if greedy:
                a = logp_all.argmax(1)
            else:
                a = torch.distributions.Categorical(logits=logp_all).sample()
            logp = logp_all.gather(1, a[:, None]).squeeze(1)
        return a.cpu().numpy(), logp.cpu().numpy()


VAL_BASE = {}


def val_reference(armmode):
    if armmode not in VAL_BASE:
        kind = "slack_old" if armmode == "slack" else "risk_case"
        VAL_BASE[armmode] = {c: engine_rule(c, SEED_VAL, kind) for c in CASES}
    return VAL_BASE[armmode]


def val_eval(armmode, actor):
    out = {}
    for case in CASES:
        r = policy_rollout(case, SEED_VAL, armmode, actor, greedy=True)
        b = val_reference(armmode)[case]
        out[case] = dict(rl=float(r["weighted_on_time_rate"].mean()),
                         base=float(b["weighted_on_time_rate"].mean()),
                         cost=float(r["cost"].mean()))
        out[case]["delta"] = out[case]["rl"] - out[case]["base"]
    out["score"] = float(np.mean([out[c]["delta"] for c in ("S2", "S3")]))
    return out


def stage_train(max_epochs=1200, patience=250, lr=2e-3, ent0=0.01, ent_epochs=150,
                reps=3,
                deadline=None, budget_s=25 * 60):
    import copy
    import torch

    doc = json.load(open(OUT_JSON, encoding="utf-8")) if os.path.exists(OUT_JSON) \
        else base_doc("train")
    ckpts = {}
    curves = {}
    t_start = time.time()
    for armmode in ("slack", "risk"):
        net, device = make_actor()
        actor = Actor(net, device)
        opt = torch.optim.Adam(net.parameters(), lr=lr)
        best = dict(score=-1e9, epoch=0, state=None, val=None)
        curve = []
        print("[train %s] device=%s params=%d" % (armmode, device,
              sum(p.numel() for p in net.parameters())))
        for epoch in range(1, max_epochs + 1):
            trajs = []
            for case in CASES:
                for _rep in range(reps):
                    r = policy_rollout(case, SEED_TRAIN, armmode, actor, greedy=False,
                                       collect=True)
                    trajs.append(r["traj"])
            parts = [b for b in (traj_to_batch(t) for t in trajs) if b is not None]
            if not parts:
                break
            feats = np.concatenate([p[0] for p in parts], 0)
            masks = np.concatenate([p[1] for p in parts], 0)
            acts = np.concatenate([p[2] for p in parts], 0)
            G = np.concatenate([p[3] for p in parts], 0)

            x = torch.as_tensor(feats, dtype=torch.float32, device=device)
            m = torch.as_tensor(masks, dtype=torch.bool, device=device)
            at = torch.as_tensor(acts, dtype=torch.long, device=device)
            gt = torch.as_tensor(G, dtype=torch.float32, device=device)
            logits, v = net(x)
            logits = logits.masked_fill(~m, -1e9)
            logp_all = torch.log_softmax(logits, dim=1)
            logp = logp_all.gather(1, at[:, None]).squeeze(1)
            ent = -(logp_all.exp() * logp_all).sum(1).mean()
            adv = (gt - v).detach()
            adv = (adv - adv.mean()) / (adv.std() + 1e-8)
            ent_coef = ent0 * max(0.0, 1.0 - (epoch - 1) / float(ent_epochs))
            loss = -(logp * adv).mean() + 0.5 * ((v - gt) ** 2).mean() - ent_coef * ent
            opt.zero_grad()
            loss.backward()
            opt.step()

            if epoch % 5 == 0 or epoch == 1:
                ve = val_eval(armmode, actor)
                curve.append(dict(epoch=epoch, score=ve["score"],
                                  S1=ve["S1"]["delta"], S2=ve["S2"]["delta"],
                                  S3=ve["S3"]["delta"], loss=float(loss.item())))
                if ve["score"] > best["score"]:
                    best = dict(score=ve["score"], epoch=epoch, val=ve,
                                state=copy.deepcopy(net.state_dict()))
                print("[train %s] ep%4d loss=%.4f val dS2=%+.4f dS3=%+.4f score=%+.4f best=%+.4f@%d"
                      % (armmode, epoch, loss.item(), ve["S2"]["delta"],
                         ve["S3"]["delta"], ve["score"], best["score"], best["epoch"]))
                doc["_progress"] = dict(stage="train", arm=armmode, epoch=epoch,
                                        best_epoch=best["epoch"],
                                        best_score=best["score"],
                                        elapsed_s=round(time.time() - t_start, 1),
                                        curve=curve[-40:])
                write_json(OUT_JSON, doc)
                if epoch - best["epoch"] > patience:
                    print("[train %s] early stop (patience)" % armmode)
                    break
            if deadline is not None and time.time() > deadline:
                print("[train %s] deadline hit" % armmode)
                break
        net.load_state_dict(best["state"])
        ckpts[armmode] = {k: v.cpu() for k, v in best["state"].items()}
        curves[armmode] = dict(curve=curve, best_epoch=best["epoch"],
                               best_score=best["score"], best_val=best["val"])
        print("[train %s] frozen at epoch %d (val score %+.4f)"
              % (armmode, best["epoch"], best["score"]))
        if deadline is not None and time.time() > deadline:
            break
    gpu_s = time.time() - t_start
    torch.save(ckpts, os.path.join(DATA_DIR, "up_p3_rl_ckpt.pt"))
    doc["_meta"]["gpu_train_seconds"] = round(gpu_s, 2)
    doc["_meta"].setdefault("train_runs", []).append(dict(
        max_epochs=max_epochs, patience=patience, lr=lr, ent0=ent0,
        ent_epochs=ent_epochs, reps=reps,
        gpu_seconds=round(gpu_s, 2),
        arms={a: dict(best_epoch=curves[a]["best_epoch"],
                      best_val_score=round(curves[a]["best_score"], 6),
                      val=dict(S1=curves[a]["best_val"]["S1"]["delta"],
                               S2=curves[a]["best_val"]["S2"]["delta"],
                               S3=curves[a]["best_val"]["S3"]["delta"]))
              for a in curves}))
    doc["_progress"] = dict(stage="train_done", curves=curves,
                            gpu_train_seconds=round(gpu_s, 2),
                            budget_exhausted=bool(gpu_s > budget_s))
    write_json(OUT_JSON, doc)
    print("TRAINED gpu_train_seconds=%.1f" % gpu_s)
    return doc


def load_actor(armmode, device="cpu"):
    import torch
    net, _ = make_actor()
    ck = torch.load(os.path.join(DATA_DIR, "up_p3_rl_ckpt.pt"), map_location="cpu",
                    weights_only=True)
    net.load_state_dict(ck[armmode])
    net.to(device).eval()
    return Actor(net, device)


# --------------------------------------------------------------------------- #
# final evaluation (test seeds, once)
# --------------------------------------------------------------------------- #
def eval_table(seeds, armmode, actor):
    out = {}
    for case in CASES:
        r = policy_rollout(case, seeds, armmode, actor, greedy=True)
        sp, cfg = get_case(case, seeds)
        g30 = rollout(sp, cfg, model_arm(case, armmode), bmode="grid", fixed_q=0)
        out[case] = dict(rl=r, q30=g30)
    return out


def stage_final():
    import torch
    doc = json.load(open(OUT_JSON, encoding="utf-8"))
    actors = {a: load_actor(a) for a in ("slack", "risk")}

    # --- baselines on the test slice (engine, authoritative) -----------------
    base = {}
    best_rule = {}
    for case in CASES:
        base[case] = engine_rule(case, SEED_TEST, "slack_old")
        best_rule[case] = engine_rule(case, SEED_TEST, "risk_case")

    # --- learned policies on the test slice ---------------------------------
    ev = {}
    for armmode in ("slack", "risk"):
        ev[armmode] = eval_table(SEED_TEST, armmode, actors[armmode])

    primary = "slack"        # pre-registered primary arm
    rl = {c: ev[primary][c]["rl"] for c in CASES}
    prd = {}
    for case in ("S2", "S3"):
        prd[case] = paired(rl[case]["weighted_on_time_rate"],
                           base[case]["weighted_on_time_rate"])
        prd[case]["baseline"] = float(base[case]["weighted_on_time_rate"].mean())
        prd[case]["rl_mean"] = float(rl[case]["weighted_on_time_rate"].mean())

    # secondary: best-vs-best (risk selection vs the strongest searched rule)
    alt = {}
    for case in ("S2", "S3"):
        alt[case] = paired(ev["risk"][case]["rl"]["weighted_on_time_rate"],
                           best_rule[case]["weighted_on_time_rate"])
        alt[case]["baseline"] = float(best_rule[case]["weighted_on_time_rate"].mean())
        alt[case]["rl_mean"] = float(ev["risk"][case]["rl"]["weighted_on_time_rate"].mean())

    gate_mean = float(np.mean([prd[c]["delta_mean"] for c in ("S2", "S3")]))
    ok = (gate_mean >= 0.020
          and prd["S2"]["lower"] > 0.0
          and prd["S3"]["lower"] > 0.0)
    reason = ("mean test delta vs baseline = %.4f pp on S2 %+.4f (CI95 %.4f, lower %+.4f), "
              "S3 %+.4f (CI95 %.4f, lower %+.4f); n_test=%d; rule >= 0.0200 and both "
              "lower > 0 -> %s" % (gate_mean * 100, prd["S2"]["delta_mean"],
                                   prd["S2"]["ci95"], prd["S2"]["lower"],
                                   prd["S3"]["delta_mean"], prd["S3"]["ci95"],
                                   prd["S3"]["lower"], prd["S2"]["n"],
                                   "PASS" if ok else "FAIL"))
    if doc.get("_progress", {}).get("budget_exhausted"):
        ok = False
        reason = "budget_exhausted; " + reason

    out = dict(doc)
    out["_meta"]["gpu_train_seconds"] = doc["_meta"].get("gpu_train_seconds")
    out["baseline"] = {c: float(base[c]["weighted_on_time_rate"].mean()) for c in CASES}
    out["rl"] = {c: float(rl[c]["weighted_on_time_rate"].mean()) for c in CASES}
    out["paired"] = {c: {k: prd[c][k] for k in
                         ("delta_mean", "ci95", "lower", "sd", "n", "n_pos",
                          "sign_p", "per_seed", "baseline", "rl_mean")}
                     for c in ("S2", "S3")}
    out["verdict"] = dict(passes=bool(ok), reason=reason,
                          mean_delta_S2_S3=gate_mean,
                          gate_rule=PROTOCOL["pass_rule"])
    out["_detail"] = dict(
        primary_arm="A slack selection (baseline slack_old)",
        test_seeds=SEED_TEST,
        baseline_slack_old={c: dict(on_time=float(base[c]["weighted_on_time_rate"].mean()),
                                    completion=float(base[c]["weighted_completion_rate"].mean()),
                                    cost=float(base[c]["cost"].mean()),
                                    per_seed=[float(v) for v in
                                              base[c]["weighted_on_time_rate"]])
                            for c in CASES},
        baseline_best_rule={c: dict(on_time=float(best_rule[c]["weighted_on_time_rate"].mean()),
                                    completion=float(best_rule[c]["weighted_completion_rate"].mean()),
                                    cost=float(best_rule[c]["cost"].mean()),
                                    cfg=CASE_CFG[c],
                                    per_seed=[float(v) for v in
                                              best_rule[c]["weighted_on_time_rate"]])
                            for c in CASES},
        rl_armA_slacksel={c: dict(on_time=float(rl[c]["weighted_on_time_rate"].mean()),
                                  completion=float(rl[c]["weighted_completion_rate"].mean()),
                                  cost=float(rl[c]["cost"].mean()),
                                  per_seed=[float(v) for v in
                                            rl[c]["weighted_on_time_rate"]])
                          for c in CASES},
        rl_armB_risksel={c: dict(on_time=float(ev["risk"][c]["rl"]["weighted_on_time_rate"].mean()),
                                 completion=float(ev["risk"][c]["rl"]["weighted_completion_rate"].mean()),
                                 cost=float(ev["risk"][c]["rl"]["cost"].mean()),
                                 per_seed=[float(v) for v in
                                           ev["risk"][c]["rl"]["weighted_on_time_rate"]])
                         for c in CASES},
        paired_vs_best_rule=alt,
        q30_diagnostic={c: dict(on_time=float(ev[primary][c]["q30"]["weighted_on_time_rate"].mean()),
                                completion=float(ev[primary][c]["q30"]["weighted_completion_rate"].mean()),
                                cost=float(ev[primary][c]["q30"]["cost"].mean()))
                        for c in CASES},
        note=("q30_diagnostic is post-hoc (no selection used it).  Arm A shares the "
              "baseline selector, so its delta isolates the reserve decision; arm B "
              "vs the tuned rule does the same on the strongest selector."),
    )
    out["_progress"] = dict(stage="final", curves=doc.get("_progress", {}).get("curves"))
    write_json(OUT_JSON, out)
    print("final test: baseline %s" % {c: round(out["baseline"][c], 4) for c in CASES})
    print("final test: rl(A)    %s" % {c: round(out["rl"][c], 4) for c in CASES})
    print("final test: rl(B)    %s" % {c: round(out["_detail"]["rl_armB_risksel"][c]["on_time"], 4)
                                      for c in CASES})
    print("P3RL %s S2_delta=%+.4f S3_delta=%+.4f" %
          ("PASS" if ok else "FAIL", prd["S2"]["delta_mean"],
           prd["S3"]["delta_mean"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["gate", "diag", "train", "final", "all"])
    ap.add_argument("--max-epochs", type=int, default=600)
    ap.add_argument("--budget-min", type=float, default=25.0)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--ent0", type=float, default=0.01)
    ap.add_argument("--ent-epochs", type=float, default=150.0)
    ap.add_argument("--patience", type=int, default=250)
    a = ap.parse_args()
    t0 = time.time()
    if a.stage in ("gate", "all"):
        if not stage_gate():
            print("alignment gate failed -- stopping")
            return 1
    if a.stage in ("diag", "all"):
        stage_diag()
    if a.stage in ("train", "all"):
        stage_train(max_epochs=a.max_epochs, patience=a.patience,
                    lr=a.lr, ent0=a.ent0, ent_epochs=a.ent_epochs,
                    reps=a.reps,
                    deadline=t0 + a.budget_min * 60,
                    budget_s=a.budget_min * 60)
    if a.stage in ("final", "all"):
        stage_final()
    return 0


if __name__ == "__main__":
    sys.exit(main())
