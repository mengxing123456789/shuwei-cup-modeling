# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p3_engine.py -- P3 dispatch engine v2 (superset of code/up_p3_vectorized).

Adds four policy dimensions to the frozen vectorised replay
(``up_p3_vectorized.simulate_batch``), keeping the legacy code path byte-for-byte
when the new parameters sit at their defaults:

    ksk   slack reservation coefficient           (legacy 0.60, hard-coded)
    qsl   residual quantile of the slack rule     (legacy 0.60, hard-coded)
    mix   EDF <-> ATC selector mix in [0,1]       (legacy 0 = pure ATC/risk score)
    gam   blocking weight: penalise a job whose predicted service keeps another
          job past its own slack (a pairwise "delay externality" term)
    tau   value-of-information hurdle of the paid review arm (legacy 0.02)
    pw/po/pp  exponents on priority w, on-time probability and predicted service

Correctness gate (``--check``): with all new parameters at their legacy values the
replay must reproduce ``up_p3_vectorized.simulate_batch`` exactly (max |diff| = 0)
on slack_old, risk_old, the two selected v1 policies and the review arm.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V            # frozen engine (bit-exact vs reference)
from common import DATA                 # noqa: F401

EPS = V.EPS
CHANGEOVER = V.CHANGEOVER
B_FLOOR = V.B_FLOOR
SCEN_Q = V.SCEN_Q
Q_SLOPE = V.Q_SLOPE
Q_KNEE = V.Q_KNEE
Q_LO = V.Q_LO
MAX_ACTIONS = V.MAX_ACTIONS
quant_lerp = V.quant_lerp

RULE_ABS, RULE_ADD, RULE_SLACK, RULE_FIX = (V.RULE_ABS, V.RULE_ADD, V.RULE_SLACK,
                                           V.RULE_FIX)

DEFAULTS = dict(ksk=0.60, qsl=0.60, mix=0.0, gam=0.0, tau=0.02,
                pw=1.0, po=1.0, pp=1.0)


def _params(cand, key, default, dtype=np.float64):
    v = cand.get(key)
    if v is None:
        return np.full(len(cand["q_hi"]), default, dtype)
    a = np.asarray(v, dtype)
    if a.ndim == 0:
        return np.full(len(cand["q_hi"]), float(a), dtype)
    return a


def simulate_batch2(spec, cfg, alpha, beta, cand, n_seeds=None, scen=None):
    """Same contract as ``up_p3_vectorized.simulate_batch`` + new knobs."""
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

    ksk = np.repeat(_params(cand, "ksk", DEFAULTS["ksk"]), S)
    ksp = np.repeat(_params(cand, "ksp", 0.0), S)
    ksb = np.repeat(_params(cand, "ksb", 0.0), S)
    qsl = np.repeat(_params(cand, "qsl", DEFAULTS["qsl"]), S)
    mix = np.repeat(_params(cand, "mix", DEFAULTS["mix"]), S)
    gam = np.repeat(_params(cand, "gam", DEFAULTS["gam"]), S)
    tau = np.repeat(_params(cand, "tau", DEFAULTS["tau"]), S)
    pw = np.repeat(_params(cand, "pw", DEFAULTS["pw"]), S)
    po = np.repeat(_params(cand, "po", DEFAULTS["po"]), S)
    pp = np.repeat(_params(cand, "pp", DEFAULTS["pp"]), S)

    any_rev_cand = bool(rev.any())
    legacy_score = bool(np.all(pw == 1.0) and np.all(po == 1.0) and np.all(pp == 1.0))
    legacy_slack = bool(np.all(ksk == 0.60) and np.all(qsl == 0.60)
                        and np.all(ksp == 0.0) and np.all(ksb == 0.0))
    pure_atc = bool(np.all(mix == 0.0))
    no_block = bool(np.all(gam == 0.0))

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
    Wsum = float(spec.w.sum())

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
        if legacy_slack:
            b_slack = ph + 0.6 * (alpha * spec.q60[pidx])
        else:
            qs0 = quant_lerp(spec.res0, qsl)
            if pidx.any():
                qs1 = quant_lerp(spec.res1, qsl)
                qs2 = quant_lerp(spec.res2, qsl)
                qsv = np.where(pidx == 0, qs0[:, None],
                               np.where(pidx == 1, qs1[:, None], qs2[:, None]))
            else:
                qsv = qs0[:, None]
            # context-conditioned slack coefficient: pressure raises the need for
            # reserve, a nearly spent budget lowers it (b is charged into cost)
            kk = (ksk + ksp * np.maximum(0.0, pressure - 0.75)
                  + ksb * (1.0 - cost / Bmax))
            b_slack = ph + kk[:, None] * (alpha * qsv)
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

        # ---------------- paid re-observation (VoI) ---------------------------
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
                    gain = w_j * (p1 - p0) - tau[rr][:, None]
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

        # ---------------- selection -------------------------------------------
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
            if legacy_score:
                base = ((w_j * mw) / mx) * expo
            else:
                base = ((w_j ** pw[sr][:, None]) * (mw ** po[sr][:, None])
                        / (mx ** pp[sr][:, None])) * expo

            onmask = valid_s & (onp >= gate[sr][:, None])
            has_on = onmask.any(1)
            pool = np.where(has_on[:, None], onmask, valid_s)

            if pure_atc:
                score = np.where(pool, base, -np.inf)
            else:
                # per-row min-max normalisation of the ATC score and of the due date
                big = 1e18
                aa = np.where(pool, base, np.nan)
                amin = np.nanmin(np.where(pool, base, np.inf), axis=1)[:, None]
                amax = np.nanmax(np.where(pool, base, -np.inf), axis=1)[:, None]
                an = (np.where(pool, base, amin) - amin) / np.maximum(
                    amax - amin, 1e-12)
                en = (due_j.max() + 1.0 - due_j) / (due_j.max() + 1.0)
                score = (1.0 - mix[sr][:, None]) * an + mix[sr][:, None] * en
                score = np.where(pool, score, -np.inf)
                del big

            if not no_block:
                # delay externality: starting j blocks the machine for ph_j seconds;
                # jobs whose own slack is smaller than that become late with their
                # current on-time probability.
                slack_k = (due_j - s_s) - ph_s
                w_on = w_j * onp
                combo = np.where(slack_k[:, None, :] < ph_s[:, :, None],
                                 w_on[:, None, :], 0.0)
                blk = combo.sum(2) / Wsum
                score = score - gam[sr][:, None] * blk

            pick_risk = score.argmax(1)

            if (sel[sr] == 1).any():
                ok2 = valid_s & ((s_s + ph_s) <= (due_j + 0.5))
                has2 = ok2.any(1)
                sc_s = (w_j / mx) * np.exp(-(late_amt / V.LATE_TOL_SLACK))
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
            dropc = (pressure[sr] > V.DROP_P) & (onp_a < V.DROP_ON)

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
        n_reviews=nrev.reshape(nC, S).astype(float),
        reserved_idle_s=idle.reshape(nC, S),
        observed_overrun_s=overrun.reshape(nC, S),
        censored_units=censored.reshape(nC, S).astype(float),
        budget_ok=budget_ok.reshape(nC, S),
        horizon_ok=horizon_ok.reshape(nC, S),
    )


# --------------------------------------------------------------------------- #
# correctness: legacy parameters must reproduce the frozen engine exactly
# --------------------------------------------------------------------------- #
CHECK_ARMS = [
    ("slack_old", dict(SEL=1, RULE=RULE_SLACK, q_hi=0.60, gate=0.50, late_tol=12.0,
                       REVIEW=False)),
    ("risk_default", dict(SEL=0, RULE=RULE_ABS, q_hi=0.60, gate=0.50, late_tol=12.0,
                          REVIEW=False)),
    ("risk_S2_sel", dict(SEL=0, RULE=RULE_ABS, q_hi=0.50, gate=0.60, late_tol=12.0,
                         REVIEW=False)),
    ("risk_S3_sel", dict(SEL=0, RULE=RULE_ABS, q_hi=0.60, gate=0.50, late_tol=20.0,
                         REVIEW=False)),
    ("slack_rev", dict(SEL=0, RULE=RULE_ABS, q_hi=0.70, gate=0.50, late_tol=12.0,
                       REVIEW=True)),
]


def run_check(out_path=None):
    store = []
    worst = 0.0
    keys = ("weighted_on_time_rate", "weighted_completion_rate", "weighted_tardiness_s",
            "cost", "elapsed_s", "n_done", "n_drop")
    for case in V.CASES:
        sp = V.build_spec(case)
        cfg = V.build_configs(sp, V.SEEDS)
        scen = V._scen(sp, cfg, 1.0, 0.5)
        for name, row in CHECK_ARMS:
            ca = V._cand_arrays([row])
            a = V.simulate_batch(sp, cfg, 1.0, 0.5, ca, n_seeds=len(V.SEEDS), scen=scen)
            b = simulate_batch2(sp, cfg, 1.0, 0.5, ca, n_seeds=len(V.SEEDS), scen=scen)
            d = {k: float(np.max(np.abs(a[k] - b[k]))) for k in keys}
            worst = max(worst, max(d.values()))
            store.append(dict(case=case, arm=name, max_abs=float(max(d.values())),
                              detail=d,
                              on_time_mean=float(b["weighted_on_time_rate"][0].mean())))
    # speed: 64 candidates x 30 seeds on S3, legacy vs extended with blocking on
    sp = V.build_spec("S3")
    cfg = V.build_configs(sp, V.SEEDS)
    scen = V._scen(sp, cfg, 1.0, 0.5)
    rows = [dict(SEL=0, RULE=RULE_ABS, q_hi=0.45 + 0.01 * (i % 20), gate=0.5, late_tol=12.0,
                 REVIEW=(i % 2 == 0), ksk=0.6, qsl=0.55, mix=0.3, gam=0.15,
                 tau=0.02, pw=1.0, po=1.0, pp=1.0) for i in range(64)]
    t0 = time.time()
    simulate_batch2(sp, cfg, 1.0, 0.5, V._cand_arrays(rows), n_seeds=30, scen=scen)
    dt_full = time.time() - t0
    out = dict(_meta=dict(purpose="v2 engine correctness + speed",
                          reference="code/up_p3_vectorized.py simulate_batch",
                          legacy_defaults=DEFAULTS),
               gate=dict(max_abs_diff=worst, passed=bool(worst == 0.0),
                         tolerance=0.0, per_arm=store),
               timing=dict(extended_64x30_s3_seconds=float(dt_full),
                           per_candidate_seed_ms=float(dt_full / (64 * 30) * 1000)))
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=os.path.join(DATA, "up2_p3_engine_check.json"))
    args = ap.parse_args()
    if args.check:
        t0 = time.time()
        o = run_check(args.out)
        print(json.dumps(dict(gate={k: o["gate"][k] for k in
                                 ("max_abs_diff", "passed")},
                             timing=o["timing"]), indent=1))
        print("arms:", [(r["case"], r["arm"], r["max_abs"]) for r in o["gate"]["per_arm"]])
        print("saved ->", args.out, "%.1fs" % (time.time() - t0))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()