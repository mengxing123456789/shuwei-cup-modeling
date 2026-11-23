# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p3review_engine.py -- review-trigger laboratory on the P3 vectorised engine.

The replay loop of ``code/up_p3_vectorized.py`` is copied verbatim; the only
addition is a per-candidate *trigger* that gates the paid re-observation branch.
``trig=0`` reproduces the reference arm bit-for-bit (gated in the runner).

Triggers
--------
0  myopic VoI        : reference arm (gain = w*(p1-p0) - bar, take argmax if > 0)
1  event window      : + the reviewed job's current slack must lie in [lo,hi]
                       and the capacity pressure in [p_lo,p_hi], cap reviews
2  DP threshold      : + the gain-ranking margin must be below the finite-horizon
                       MDP threshold m*(u,k) solved by value iteration
3  dispatch-now      : + the reviewed job must be the one the base rule would
                       dispatch in this same epoch (information used at once)
4  window+dispatch   : 1 and 3 combined

Units are identical to the reference: 1 s of horizon and 1.0 cost per review.
"""
import math
import sys
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V           # noqa: E402

EPS = V.EPS
CHANGEOVER = V.CHANGEOVER
B_FLOOR = V.B_FLOOR
PREFIX = V.PREFIX
SCEN_Q = V.SCEN_Q
Q_SLOPE, Q_KNEE, Q_LO = V.Q_SLOPE, V.Q_KNEE, V.Q_LO
SLACK_COEF = V.SLACK_COEF
LATE_TOL_SLACK = V.LATE_TOL_SLACK
DROP_P, DROP_ON = V.DROP_P, V.DROP_ON
REVIEW_BAR = V.REVIEW_BAR
MAX_ACTIONS = V.MAX_ACTIONS
quant_lerp = V.quant_lerp

# --------------------------------------------------------------------------- #
# finite-horizon MDP: when is a second observation worth its 1 s + 1 cost?
# --------------------------------------------------------------------------- #
M_GRID = np.linspace(0.0, 4.0, 81)          # gain margin in residual-sd units
DP_MARGIN_SCALE = 0.35                      # w-units of gain per 1 residual sd (fixed a priori)
U_MAX = 2                                   # prefix stage 0/1/2
K_MAX = 6                                   # remaining dispatch epochs
DP_TABLE = None                             # filled by solve_dp()


def _phi(x):
    return 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))


def solve_dp(lam, u_max=U_MAX, k_max=K_MAX, m_grid=M_GRID, shrink=0.7071):
    """Backward induction for the review-or-dispatch stopping problem.

    State  (m, u, k): m = margin of the top VoI candidate over the runner-up in
    units of the residual sd, u = prefix stage already paid for, k = dispatch
    epochs left.  Dispatch is worth ``Phi(m)`` (the chance the ranking is right);
    a review costs the time shadow ``lam`` and re-draws the margin with noise
    shrunk to ``shrink`` of its prior sd.  No future reward beyond k epochs is
    modelled: the horizon cap is what makes late reviews expensive.

    Returns V[k, u, m] and the take threshold m*(k,u) = largest m with
    review value >= dispatch value.
    """
    from scipy.stats import norm
    m = np.asarray(m_grid, float)
    Vv = np.zeros((k_max + 1, u_max + 1, m.size))
    take = np.zeros((k_max + 1, u_max + 1), float)
    # terminal k=0: nothing left to dispatch, both actions worth 0
    nu = np.linspace(-3.5, 3.5, 71) * shrink
    wq = norm.pdf(nu / shrink)
    wq = wq / wq.sum()
    disp = norm.cdf(m)                          # chance the ranking is right
    for k in range(1, k_max + 1):
        # u = u_max: every allowed observation is spent -> dispatch now
        Vv[k, u_max] = disp
        take[k, u_max] = 0.0
        for u in range(u_max - 1, -1, -1):
            # a review spends 1 s of the horizon (k -> k-1) and lam of holding cost
            newm = np.abs(m[:, None] + nu[None, :])
            nxt = np.interp(newm.ravel(), m, Vv[k - 1, u + 1]).reshape(newm.shape)
            rev = (nxt * wq[None, :]).sum(1) - lam
            Vv[k, u] = np.maximum(disp, rev)
            ok = rev > disp
            take[k, u] = float(m[ok].max()) if ok.any() else 0.0
    return dict(lam=float(lam), grid=list(map(float, m)), V=Vv, take_m=take,
                u_max=u_max, k_max=k_max, shrink=float(shrink))


def dp_take(margin, u, k):
    """Threshold lookup: review iff the ranking margin is below m*(k,u)."""
    if DP_TABLE is None:
        return False
    kk = int(max(1, min(DP_TABLE["k_max"], k)))
    uu = int(max(0, min(DP_TABLE["u_max"], u)))
    return bool(margin <= DP_TABLE["take_m"][kk, uu])


# --------------------------------------------------------------------------- #
# replay loop with a trigger (copy of V.simulate_batch)
# --------------------------------------------------------------------------- #
class _State(object):
    pass


def simulate_batch(spec, cfg, alpha, beta, cand, n_seeds=None, scen=None,
                   collect=False):
    n = spec.n
    H, Bmax, K = spec.H, spec.B, spec.K
    nC = len(cand["q_hi"])
    S = n_seeds if n_seeds is not None else len(cfg["seeds"])
    B = nC * S
    Hp = H + EPS
    Bp = Bmax + EPS
    if scen is None:
        scen = V._scen(spec, cfg, alpha, beta)
    sc0, sc1, sc2 = scen[0], scen[1], scen[2]

    seed_idx = np.tile(np.arange(S), nC)
    q_hi = np.repeat(np.asarray(cand["q_hi"], np.float64), S)
    gate = np.repeat(np.asarray(cand["gate"], np.float64), S)
    late = np.repeat(np.asarray(cand["late_tol"], np.float64), S)
    rule = np.repeat(np.asarray(cand["rule"], np.int8), S)
    sel = np.repeat(np.asarray(cand["sel"], np.int8), S)
    rev = np.repeat(np.asarray(cand["rev"], bool), S)
    trig = np.repeat(np.asarray(cand["trig"], np.int8), S)
    bar = np.repeat(np.asarray(cand["bar"], np.float64), S)
    wlo = np.repeat(np.asarray(cand["win_lo"], np.float64), S)
    whi = np.repeat(np.asarray(cand["win_hi"], np.float64), S)
    plo = np.repeat(np.asarray(cand["p_lo"], np.float64), S)
    phi_ = np.repeat(np.asarray(cand["p_hi"], np.float64), S)
    cap = np.repeat(np.asarray(cand["cap"], np.int64), S)
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
    nrev_tot = np.zeros(B, np.int64)

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
        if (rule == V.RULE_FIX).any():
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
        b = np.where(rule[:, None] == V.RULE_ABS, b_abs,
                     np.where(rule[:, None] == V.RULE_ADD, b_add,
                              np.where(rule[:, None] == V.RULE_SLACK, b_slack, b_fix)))
        b = np.maximum(B_FLOOR, b)
        c = (2.0 + 0.1 * b) + 0.2 * D
        valid = feas & ((s + b) <= Hp) & ((cost[:, None] + c) <= Bp)
        anyact = valid.any(1)

        reviewed = np.zeros(B, bool)
        if any_rev_cand:
            rmask = act & rev & (nrev < np.minimum(K, cap)) & (cost + 1.0 <= Bmax) & (t + 1.0 < H)
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
                    take = bg > bar[rr]
                    if collect:
                        pass
                    if take.any():
                        # ---- extra triggers ---------------------------------- #
                        tr = trig[rr]
                        if ((tr == 1) | (tr == 4) | (tr == 7)).any():
                            msk = (tr == 1) | (tr == 4) | (tr == 7)
                            sl = due_j[0, bj] - s_r[np.arange(nrr), bj] - ph[rr, bj]
                            msk &= (sl >= wlo[rr]) & (sl <= whi[rr])
                            msk &= (pressure[rr] >= plo[rr]) & (pressure[rr] <= phi_[rr])
                            if (tr == 7).any():
                                m7 = tr == 7
                                pri = w_j[0, bj] >= 1.5 * float(w_j.mean())
                                msk &= (~m7) | pri
                            msk &= nrev[rr] < cap[rr]
                            take &= (~((tr == 1) | (tr == 4) | (tr == 7))) | msk
                        if (tr == 2).any():
                            msk = tr == 2
                            with np.errstate(invalid="ignore"):
                                margin = (np.sort(gain, 1)[:, -1]
                                          - np.sort(gain, 1)[:, -2])
                            margin = np.nan_to_num(margin, nan=1e9, posinf=1e9, neginf=-1e9)
                            margin = margin / (DP_MARGIN_SCALE * max(float(w_j.mean()), 1e-3))
                            kk = np.maximum(1, (H - t[rr]) / max(H / max(n, 1), 1e-9)).astype(int)
                            ok2 = np.array([dp_take(margin[i], int(p_r[i, bj[i]]),
                                                    int(kk[i])) for i in range(nrr)])
                            take &= (~msk) | ok2
                        if ((tr == 3) | (tr == 4)).any():
                            # dispatch-now test, only for candidates still in play
                            idx = np.flatnonzero(take & ((tr == 3) | (tr == 4)))
                            if idx.size:
                                ridx = rr[idx]
                                pickd = _risk_pick(ridx, act, valid, s, ph, pidx,
                                                   seed_idx, sc0, sc1, sc2, due_j,
                                                   w_j, gate, late, sel, n)
                                same = (bj[idx] == pickd)
                                tk = take.copy()
                                tk[idx] = same
                                take = tk
                        if (tr == 5).any():
                            take &= (~(tr == 5)) | (nrev[rr] < 0)   # 5 = never
                    if take.any():
                        r2 = rr[take]
                        j2 = bj[take]
                        newp = pidx[r2, j2] + 1
                        placebo = (trig[r2] == 6)      # pay, learn nothing
                        pidx[r2, j2] = np.where(placebo, pidx[r2, j2], newp)
                        reviews[r2, j2] += 1
                        nrev[r2] += 1
                        nrev_tot[r2] += 1
                        cost[r2] += 1.0
                        t[r2] += 1.0
                        sidx2 = seed_idx[r2]
                        learned = np.where(newp == 1, cfg["pred6"][sidx2, j2],
                                           cfg["pred1"][sidx2, j2])
                        pred[r2, j2] = np.where(placebo, pred[r2, j2], learned)
                        reviewed[r2] = True

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

    out = dict(
        weighted_on_time_rate=(ont / W).reshape(nC, S),
        weighted_completion_rate=(comp / W).reshape(nC, S),
        weighted_tardiness_s=tard.reshape(nC, S),
        cost=cost.reshape(nC, S),
        elapsed_s=t.reshape(nC, S),
        n_done=done.sum(1).reshape(nC, S).astype(float),
        n_drop=dropped.sum(1).reshape(nC, S).astype(float),
        budget_ok=budget_ok.reshape(nC, S),
        horizon_ok=horizon_ok.reshape(nC, S),
        n_reviews=nrev_tot.reshape(nC, S).astype(float))
    return out


def _risk_pick(ridx, act, valid, s, ph, pidx, seed_idx, sc0, sc1, sc2, due_j,
               w_j, gate, late, sel, n):
    """Base-rule dispatch pick for the given row indices (risk selection)."""
    s_s = s[ridx]
    ph_s = ph[ridx]
    p_s = pidx[ridx]
    sidx = seed_idx[ridx]
    valid_s = valid[ridx]
    cnt = np.zeros((ridx.size, n))
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
    score = ((w_j * mw) / mx) * np.exp(-(late_amt / late[ridx][:, None]))
    onmask = valid_s & (onp >= gate[ridx][:, None])
    pool = np.where(onmask.any(1)[:, None], onmask, valid_s)
    score = np.where(pool, score, -np.inf)
    return score.argmax(1)


CAND_DEFAULTS = dict(trig=0, bar=REVIEW_BAR, win_lo=-1e9, win_hi=1e9,
                     p_lo=0.0, p_hi=1e9, cap=99)


def cand_arrays(rows):
    col = lambda key, default, typ: np.array([r.get(key, default) for r in rows], typ)
    return dict(q_hi=col("Q_HI", 0.6, float),
                gate=col("GATE", 0.5, float),
                late_tol=col("LATE_TOL_RISK", 12.0, float),
                rule=col("rule", V.RULE_ABS, np.int8),
                sel=col("sel", 0, np.int8),
                rev=col("rev", True, bool),
                trig=col("trig", 0, np.int8),
                bar=col("bar", REVIEW_BAR, float),
                win_lo=col("win_lo", -1e9, float),
                win_hi=col("win_hi", 1e9, float),
                p_lo=col("p_lo", 0.0, float),
                p_hi=col("p_hi", 1e9, float),
                cap=col("cap", 99, np.int64))