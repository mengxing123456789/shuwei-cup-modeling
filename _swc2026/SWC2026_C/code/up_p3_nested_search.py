# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p3_nested_search.py -- nested (select-inside / evaluate-outside) search for P3.

Grid (5 requested dimensions)
-----------------------------
    Q_HI           0.40 .. 0.90 step 0.05        (11)
    GATE           0.30 .. 0.80 step 0.10        (6)
    LATE_TOL_RISK  6 / 12 / 20 / 40              (4)
    reservation rule  abs / add / slack / fix    (4)
    paid re-observation (second request) on/off  (2)
    => 2112 candidates, + 2 slack-selection probes (one of which is the baseline)
    => 2114 candidate rows, 2113 in the selection pool

Protocol (pre-registered, see the task brief)
---------------------------------------------
* 15 combos = 3 cases x 5 service-law mappings (alpha,beta).
* official seeds 2026111700..2026111729: first 15 = tune, last 15 = holdout only.
* baseline = slack_old (SEL=1, RULE=slack, no review) -- bit-identical to
  code/p3_improved_verify.simulate(case, seed, "slack_old").
* P1 per-combo winner: argmax tune mean inside that combo.
* P2 case-robust winner (PRIMARY): argmax of the mean tune score over the 5
  mappings of the case -> one policy per case, evaluated in its 5 combos.
* P3 global winner: argmax of the mean tune score over all 15 combos.
* statistics: per-seed paired difference vs the baseline inside each combo;
  Delta = mean, CI = paired t (df=14); combo-level Mean Delta CI = t over the
  15 combo Deltas (df=14); BH over the 15 combo tests; Bonferroni over the
  2114-candidate family reported as the conservative bound.

CLI
---
    python up_p3_nested_search.py --stage search
    python up_p3_nested_search.py --stage regime
    python up_p3_nested_search.py --stage all
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V
from common import DATA, ATT, write_json

SEEDS = V.SEEDS
N_TUNE = 15
CASES = ("S1", "S2", "S3")
MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]
QHI_GRID = [round(0.40 + 0.05 * i, 2) for i in range(11)]
GATE_GRID = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
LATE_GRID = [6.0, 12.0, 20.0, 40.0]
RULE_NAMES = {V.RULE_ABS: "abs", V.RULE_ADD: "add", V.RULE_SLACK: "slack", V.RULE_FIX: "fix"}
BASELINE = dict(SEL=1, RULE=V.RULE_SLACK, q_hi=0.60, gate=0.50, late_tol=12.0,
                REVIEW=False)
CHUNK = 320


# --------------------------------------------------------------------------- #
def build_grid():
    """Full factorial + the two slack-selection probes; row 0 is the baseline."""
    cands = [dict(BASELINE, name="slack_old")]
    for q in QHI_GRID:
        for g in GATE_GRID:
            for lt in LATE_GRID:
                for ru in (V.RULE_ABS, V.RULE_ADD, V.RULE_SLACK, V.RULE_FIX):
                    for rv in (False, True):
                        cands.append(dict(SEL=0, RULE=ru, q_hi=q, gate=g, late_tol=lt,
                                          REVIEW=rv,
                                          name="risk_q%.2f_g%.2f_l%g_%s%s"
                                               % (q, g, lt, RULE_NAMES[ru],
                                                  "_rev" if rv else "")))
    for rv in (False, True):
        if rv:      # row 0 already covers the no-review slack probe
            cands.append(dict(SEL=1, RULE=V.RULE_SLACK, q_hi=0.60, gate=0.50,
                              late_tol=12.0, REVIEW=rv, name="slack_old_rev"))
    return cands


def utilisation(case, alpha=1.0, beta=0.5):
    """rho = sum_j E[alpha*d_j+beta] / H, E over the eligible segment pool of j's family."""
    import common
    idx = common.load_index()
    elig = idx[idx.eligible == 1]
    fam = {f: elig[elig.family_id == f].duration_s.astype(float).values
           for f in sorted(elig.family_id.unique())}
    rows = V.STO.TASKS[V.STO.TASKS.case_id == case].sort_values("job_id")
    ep = [float(np.mean(alpha * fam[r.family_id] + beta)) for _, r in rows.iterrows()]
    H = float([c for c in V.STO.COND["cases"] if c["case_id"] == case][0]["horizon_s"])
    return float(sum(ep) / H), float(sum(ep)), float(H)


def run_combo(case, alpha, beta, cands, seeds, chunk=CHUNK, keep=("weighted_on_time_rate",)):
    """One (case, mapping) x all candidates x all seeds -> arrays (nC, nSeeds)."""
    sp = V.build_spec(case)
    cfg = V.build_configs(sp, seeds)
    scen = V._scen(sp, cfg, alpha, beta)
    n = len(cands)
    out = {k: np.zeros((n, len(seeds))) for k in keep}
    for i0 in range(0, n, chunk):
        sub = cands[i0:i0 + chunk]
        r = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays(sub),
                             n_seeds=len(seeds), scen=scen)
        for k in keep:
            out[k][i0:i0 + chunk] = r[k]
    return out


def paired_stats(cand_vec, base_vec):
    d = np.asarray(cand_vec, float) - np.asarray(base_vec, float)
    n = d.size
    m = float(d.mean())
    sd = float(d.std(ddof=1)) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    tc = float(stats.t.ppf(0.975, n - 1)) if n > 1 else 0.0
    if se > 0:
        tval = m / se
        p = float(2.0 * stats.t.sf(abs(tval), n - 1))
    else:
        tval = float("inf") if m > 0 else (float("-inf") if m < 0 else 0.0)
        p = 0.0 if m != 0 else 1.0
    return dict(n=int(n), mean_delta=m, sd=sd, se=se, t=tval,
                ci95=[m - tc * se, m + tc * se], p_value=p,
                n_positive=int((d > 0).sum()), n_negative=int((d < 0).sum()))


def bh(pvals, alpha=0.05):
    """Benjamini-Hochberg adjusted p-values (monotone)."""
    p = np.asarray(pvals, float)
    m = p.size
    order = np.argsort(p)
    adj = np.empty(m)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        val = min(prev, p[i] * m / (rank + 1.0))
        adj[i] = val
        prev = val
    return adj


# --------------------------------------------------------------------------- #
def stage_search(out_path=None):
    t_start = time.time()
    cands = build_grid()
    n_cand = len(cands)
    combos = [(c, m) for c in CASES for m in MAPPINGS]
    store = {}
    walls = []
    for case, (alpha, beta) in combos:
        t0 = time.time()
        r = run_combo(case, alpha, beta, cands, SEEDS)
        walls.append(time.time() - t0)
        store[(case, alpha, beta)] = r["weighted_on_time_rate"]
        print("[search] %s a=%.2f b=%.2f  %.1fs" % (case, alpha, beta, walls[-1]), flush=True)

    # ---- per-candidate scores -------------------------------------------- #
    tune = {}
    hold = {}
    for c, m in combos:
        M = store[(c, m)]
        tune[(c, m)] = M[:, :N_TUNE].mean(1)
        hold[(c, m)] = M[:, N_TUNE:].mean(1)
    base_t = {k: float(v[0]) for k, v in tune.items()}
    base_h = {k: float(v[0]) for k, v in hold.items()}

    # ---- protocols -------------------------------------------------------- #
    # P3: one winner for all 15 combos
    glob_score = np.mean([tune[k] for k in combos], axis=0)
    glob_score[0] = -1.0                       # exclude baseline from selection
    p3_idx = int(np.argmax(glob_score))
    # P2: one winner per case (mean over the 5 mappings)
    p2_idx = {}
    for c in CASES:
        ks = [k for k in combos if k[0] == c]
        sc = np.mean([tune[k] for k in ks], axis=0)
        sc[0] = -1.0
        p2_idx[c] = int(np.argmax(sc))
    # P1: winner inside each combo
    p1_idx = {}
    for k in combos:
        sc = tune[k].copy()
        sc[0] = -1.0
        p1_idx[k] = int(np.argmax(sc))

    def evaluate(pick, tag):
        rows = []
        for k in combos:
            M = store[k]
            j = pick[k] if isinstance(pick, dict) else pick
            st = paired_stats(M[j, N_TUNE:], M[0, N_TUNE:])
            st.update(case=k[0], alpha=k[1], beta=k[2],
                      cand=cands[j]["name"], cand_index=int(j),
                      tune_mean=float(tune[k][j]), holdout_mean=float(hold[k][j]),
                      baseline_tune=base_t[k], baseline_holdout=base_h[k])
            rows.append(st)
        ps = [r["p_value"] for r in rows]
        q = bh(ps)
        for r, qv in zip(rows, q):
            r["bh_q"] = float(qv)
        dm = np.array([r["mean_delta"] for r in rows])
        sd = float(dm.std(ddof=1))
        se = sd / math.sqrt(dm.size)
        tc = float(stats.t.ppf(0.975, dm.size - 1))
        summ = dict(tag=tag, n_combos=int(dm.size),
                    delta_mean=float(dm.mean()),
                    delta_ci95=[float(dm.mean() - tc * se), float(dm.mean() + tc * se)],
                    delta_min=float(dm.min()), delta_max=float(dm.max()),
                    delta_sd=float(sd),
                    combo_t=float(dm.mean() / se) if se > 0 else None,
                    combo_p=float(2 * stats.t.sf(abs(dm.mean() / se), dm.size - 1)) if se > 0 else None,
                    n_same_direction=int((dm > 0).sum()),
                    n_bh_significant=int((q < 0.05).sum()),
                    # pre-registered gate
                    gate_delta_ge_002=bool(dm.mean() >= 0.02),
                    gate_ci_lower_gt_0=bool((dm.mean() - tc * se) > 0.0),
                    gate_same_direction_12of15=bool((dm > 0).sum() >= 12),
                    gate_pass=bool(dm.mean() >= 0.02 and (dm.mean() - tc * se) > 0.0
                                   and (dm > 0).sum() >= 12))
        return dict(summary=summ, combos=rows)

    p2_pick = {k: p2_idx[k[0]] for k in combos}
    res = dict(P2_case_robust=evaluate(p2_pick, "P2 primary: one policy per case, "
                                                "selected on tune seeds averaged over the 5 mappings"),
               P1_per_combo=evaluate(p1_idx, "P1: winner inside each combo"),
               P3_global=evaluate(p3_idx, "P3: single policy for all 15 combos"))

    # ---- leaderboards ----------------------------------------------------- #
    boards = {}
    for k in combos:
        order = np.argsort(-tune[k])[:10]
        boards["%s|a%.2f_b%.2f" % (k[0], k[1], k[2])] = [
            dict(index=int(i), name=cands[i]["name"], tune=float(tune[k][i]),
                 holdout=float(hold[k][i]), baseline_tune=base_t[k],
                 baseline_holdout=base_h[k]) for i in order]
    # top candidates by case-robust score
    case_board = {}
    for c in CASES:
        ks = [k for k in combos if k[0] == c]
        sc = np.mean([tune[k] for k in ks], axis=0)
        order = np.argsort(-sc)[:15]
        case_board[c] = [dict(index=int(i), name=cands[i]["name"],
                              score=float(sc[i]),
                              per_mapping=[float(tune[k][i]) for k in ks],
                              holdout_per_mapping=[float(hold[k][i]) for k in ks])
                         for i in order]

    # ---- winner detail: full 30-seed vectors + secondary metrics ---------- #
    winner_detail = {}
    for c in CASES:
        j = p2_idx[c]
        row = cands[j]
        d = {}
        for (case, alpha, beta) in [k for k in combos if k[0] == c]:
            sp = V.build_spec(case)
            cfg = V.build_configs(sp, SEEDS)
            r = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays([row]),
                                 n_seeds=len(SEEDS), scen=V._scen(sp, cfg, alpha, beta))
            rb = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays([BASELINE]),
                                  n_seeds=len(SEEDS), scen=V._scen(sp, cfg, alpha, beta))
            d["a%.2f_b%.2f" % (alpha, beta)] = dict(
                winner_on_time=[float(x) for x in r["weighted_on_time_rate"][0]],
                baseline_on_time=[float(x) for x in rb["weighted_on_time_rate"][0]],
                winner_completion=float(r["weighted_completion_rate"][0, N_TUNE:].mean()),
                baseline_completion=float(rb["weighted_completion_rate"][0, N_TUNE:].mean()),
                winner_tardiness=float(r["weighted_tardiness_s"][0, N_TUNE:].mean()),
                baseline_tardiness=float(rb["weighted_tardiness_s"][0, N_TUNE:].mean()),
                winner_cost=float(r["cost"][0, N_TUNE:].mean()),
                baseline_cost=float(rb["cost"][0, N_TUNE:].mean()))
        winner_detail[c] = dict(cand=row["name"], index=int(j), combos=d)

    # ---- sensitivity: how much does each dimension matter? --------------- #
    dims = {}
    for dim, key, vals in (("Q_HI", "q_hi", QHI_GRID), ("GATE", "gate", GATE_GRID),
                           ("LATE_TOL_RISK", "late_tol", LATE_GRID),
                           ("rule", "RULE", [V.RULE_ABS, V.RULE_ADD, V.RULE_SLACK,
                                             V.RULE_FIX]),
                           ("review", "REVIEW", [False, True])):
        per_case = {}
        for c in CASES:
            ks = [k for k in combos if k[0] == c]
            sc = np.mean([tune[k] for k in ks], axis=0)
            m = {}
            for v in vals:
                idx = [i for i, cd in enumerate(cands)
                       if cd.get(key) == v and i != 0 and cd.get("SEL") == 0]
                m[str(v)] = float(sc[idx].mean()) if idx else None
            per_case[c] = m
        dims[dim] = per_case

    rho = {}
    for c in CASES:
        for (alpha, beta) in MAPPINGS:
            v, ep, H = utilisation(c, alpha, beta)
            rho["%s|a%.2f_b%.2f" % (c, alpha, beta)] = dict(
                rho=v, expected_service_sum=ep, horizon_s=H)

    out = dict(
        _meta=dict(
            purpose="nested search over the P3 stochastic scheduler",
            engine="code/up_p3_vectorized.py (bit-exact vs code/p3_improved_verify.py)",
            seeds=SEEDS, n_tune=N_TUNE, n_holdout=len(SEEDS) - N_TUNE,
            split="first 15 seeds = selection, last 15 seeds = evaluation only",
            mappings=[dict(alpha=a, beta=b) for a, b in MAPPINGS],
            grid=dict(Q_HI=QHI_GRID, GATE=GATE_GRID, LATE_TOL_RISK=LATE_GRID,
                      rule=[RULE_NAMES[k] for k in (V.RULE_ABS, V.RULE_ADD,
                                                   V.RULE_SLACK, V.RULE_FIX)],
                      review=[False, True]),
            n_candidates=n_cand, n_in_pool=n_cand - 1,
            n_combos=len(combos), n_trials=n_cand * len(SEEDS) * len(combos),
            previous_search=dict(file="data/p3_improved_search.json", candidates=121),
            search_space_multiplier=float(n_cand / 121.0),
            correction=dict(primary="Benjamini-Hochberg over the 15 combo tests",
                            conservative="Bonferroni alpha/m = %.3e for m=%d candidates"
                                         % (0.05 / n_cand, n_cand)),
        ),
        wall_clock_s=dict(total=time.time() - t_start, per_combo=walls),
        utilisation_rho=rho,
        protocols=res,
        leaders=dict(per_combo=boards, per_case=case_board),
        winners=dict(P2={c: cands[p2_idx[c]]["name"] for c in CASES},
                     P2_index={c: p2_idx[c] for c in CASES},
                     P1={"%s|a%.2f_b%.2f" % k: cands[p1_idx[k]]["name"] for k in combos},
                     P3=cands[p3_idx]["name"]),
        winner_detail=winner_detail,
        dimension_marginals=dims,
    )
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    return out


# --------------------------------------------------------------------------- #
LEGACY_GATE = {"S2|a1.00_b0.50": (0.60, 12.0),   # data/p3_quantile_curve.json base_params
               "S3|a1.00_b0.50": (0.50, 20.0)}


def stage_regime(out_path=None, q_lo=0.30, q_hi=0.90, step=0.01):
    """Two-regime law: q-reservation curve on all 15 combos + argmax q vs rho.

    The two (case, 1.0/0.5) combos reuse the GATE / LATE_TOL_RISK that
    data/p3_quantile_curve.json held fixed, so the q = 0.30 .. 0.90 lattice
    reproduces that artifact point for point (independent cross-check of the
    whole vectorised path).
    """
    t_start = time.time()
    qgrid = [round(q_lo + step * i, 4) for i in range(int(round((q_hi - q_lo) / step)) + 1)]
    combos = [(c, m) for c in CASES for m in MAPPINGS]
    curve = {}
    argmax = {}
    walls = []
    base_rows = {}
    for case, (alpha, beta) in combos:
        k = "%s|a%.2f_b%.2f" % (case, alpha, beta)
        gate, late = LEGACY_GATE.get(k, (0.50, 12.0))
        cands = [dict(SEL=0, RULE=V.RULE_ABS, q_hi=q, gate=gate, late_tol=late,
                      REVIEW=False, name="q%.2f" % q) for q in qgrid]
        sp = V.build_spec(case)
        cfg = V.build_configs(sp, SEEDS)
        scen = V._scen(sp, cfg, alpha, beta)
        t0 = time.time()
        r = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays(cands),
                             n_seeds=len(SEEDS), scen=scen)
        rb = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays([BASELINE]),
                              n_seeds=len(SEEDS), scen=scen)
        walls.append(time.time() - t0)
        M = r["weighted_on_time_rate"]
        base = rb["weighted_on_time_rate"][0]
        tune = M[:, :N_TUNE].mean(1)
        hold = M[:, N_TUNE:].mean(1)
        i = int(np.argmax(tune))
        base_rows[k] = dict(tune=[float(x) for x in base],
                            holdout_mean=float(base[N_TUNE:].mean()),
                            tune_mean=float(base[:N_TUNE].mean()))
        # paired deltas of every q against the slack_old baseline
        pair = []
        for j in range(len(qgrid)):
            st = paired_stats(M[j, N_TUNE:], base[N_TUNE:])
            st["q"] = float(qgrid[j])
            pair.append(st)
        curve[k] = dict(q=[float(x) for x in qgrid],
                        tune=[float(x) for x in tune],
                        holdout=[float(x) for x in hold],
                        gate=gate, late_tol=late,
                        baseline_tune=float(base[:N_TUNE].mean()),
                        baseline_holdout=float(base[N_TUNE:].mean()),
                        paired=pair)
        # left plateau: how wide is the region within 0.002 of the argmax, and
        # does it reach the left edge?
        thr = tune.max() - 0.002
        near = np.where(tune >= thr)[0]
        # is the interior peak really better than the left edge q=0.30?  The
        # comparison is made on the held-out seeds, so it is not selection-biased.
        peak_vs_left = paired_stats(M[i, N_TUNE:], M[0, N_TUNE:])
        # collapse in the high-quantile block (q >= 0.80) relative to the peak
        left = tune[qgrid.index(0.30):qgrid.index(0.40) + 1].mean()
        hi_blk = tune[qgrid.index(0.80):].mean()
        argmax[k] = dict(argmax_q=float(qgrid[i]), tune_max=float(tune.max()),
                         holdout_at_argmax=float(hold[i]),
                         holdout_best_q=float(qgrid[int(np.argmax(hold))]),
                         holdout_best=float(hold.max()),
                         plateau_q=[float(qgrid[j]) for j in near],
                         plateau_reaches_left=bool(near.min() == 0),
                         argmax_at_left=bool(qgrid[i] <= 0.35),
                         left_block_mean=float(left), high_block_mean=float(hi_blk),
                         drop_vs_peak=float(tune.max() - hi_blk),
                         collapse_after_080=bool(tune.max() - hi_blk > 0.02),
                         monotone_decreasing_after_argmax=bool(
                             np.all(np.diff(tune[i:]) <= 1e-12)),
                         peak_minus_left_holdout=peak_vs_left,
                         )
        print("[regime] %s  %.1fs  argmax q=%.2f" % (k, walls[-1], qgrid[i]), flush=True)

    # rho per combo
    rho = {}
    for case, (alpha, beta) in combos:
        v, ep, H = utilisation(case, alpha, beta)
        rho["%s|a%.2f_b%.2f" % (case, alpha, beta)] = dict(rho=v,
                                                          expected_service_sum=ep,
                                                          horizon_s=H)
    keys = [k for k in argmax]
    x = np.array([rho[k]["rho"] for k in keys])
    y = np.array([argmax[k]["argmax_q"] for k in keys])
    slope, intercept, rvalue, pvalue, stderr = stats.linregress(x, y)
    spear = stats.spearmanr(x, y)

    # ---- independent cross-check against data/p3_quantile_curve.json ------ #
    old_path = os.path.join(DATA, "p3_quantile_curve.json")
    cross = dict(source="data/p3_quantile_curve.json", cases={}, max_abs_tune_diff=0.0,
                 max_abs_hold_diff=0.0)
    if os.path.exists(old_path):
        with open(old_path, encoding="utf-8") as f:
            old = json.load(f)
        oldq = old["_meta"]["q_grid"]
        for c, blk in old["cases"].items():
            cur = curve["%s|a1.00_b0.50" % c]
            idx = [cur["q"].index(round(q, 4)) for q in oldq]
            t_mine = [cur["tune"][i] for i in idx]
            h_mine = [cur["holdout"][i] for i in idx]
            dt = float(np.max(np.abs(np.array(t_mine) - np.array(blk["tune_curve"]))))
            dh = float(np.max(np.abs(np.array(h_mine) - np.array(blk["holdout_curve"]))))
            cross["cases"][c] = dict(
                q_grid=[round(q, 4) for q in oldq],
                tune_mine=[round(v, 6) for v in t_mine],
                tune_old=blk["tune_curve"],
                holdout_mine=[round(v, 6) for v in h_mine],
                holdout_old=blk["holdout_curve"],
                max_abs_tune_diff=dt, max_abs_hold_diff=dh,
                old_q_star=blk["q_star"],
                my_argmax_q=argmax["%s|a1.00_b0.50" % c]["argmax_q"])
            cross["max_abs_tune_diff"] = max(cross["max_abs_tune_diff"], dt)
            cross["max_abs_hold_diff"] = max(cross["max_abs_hold_diff"], dh)
        cross["note"] = ("the old artifact stores its curves rounded to 6 decimals, so "
                         "agreement is asserted at 1e-6")
        cross["reproduced"] = bool(cross["max_abs_tune_diff"] <= 1e-6
                                   and cross["max_abs_hold_diff"] <= 1e-6)

    both_left = all(argmax[k]["plateau_reaches_left"] for k in keys)
    n_collapse = int(sum(1 for k in keys if argmax[k]["collapse_after_080"]))
    at_left = int(sum(1 for k in keys if argmax[k]["argmax_at_left"]))
    # a peak is "really" right of the left edge only if the held-out paired
    # difference against q=0.30 excludes zero
    n_peak_sig = int(sum(1 for k in keys
                         if argmax[k]["peak_minus_left_holdout"]["ci95"][0] > 0.0))
    max_peak_gain = max(argmax[k]["tune_max"] - cur0
                        for k, cur0 in ((k, curve[k]["tune"][0]) for k in keys))
    out = dict(
        _meta=dict(purpose="two-regime law for the residual-quantile reservation",
                   engine="code/up_p3_vectorized.py",
                   q_grid=qgrid, seeds=SEEDS, n_tune=N_TUNE,
                   fixed=dict(GATE="0.50 (0.60 for S2 and 0.50/20 for S3 on the 1.0/0.5 "
                                   "mapping, so the old 13-point curve is reproduced exactly)",
                              LATE_TOL_RISK="12.0 (see the two legacy combos)",
                              rule="abs", review=False, selection="risk"),
                   legacy_combos={k: dict(GATE=v[0], LATE_TOL_RISK=v[1])
                                  for k, v in LEGACY_GATE.items()},
                   rho_definition="sum_j E[alpha*d_j+beta]/H over the eligible "
                                  "segment-index pool of each job's family"),
        wall_clock_s=dict(total=time.time() - t_start, per_combo=walls),
        curve=curve, argmax=argmax, utilisation_rho=rho,
        regression=dict(n=len(keys), slope=float(slope), intercept=float(intercept),
                        r=float(rvalue), r2=float(rvalue ** 2), p_value=float(pvalue),
                        stderr=float(stderr),
                        spearman=float(spear.statistic), spearman_p=float(spear.pvalue),
                        x_rho=[float(v) for v in x], y_argmax_q=[float(v) for v in y],
                        keys=keys),
        verdict=dict(all_combos_left_plateau_at_argmax=bool(both_left),
                     n_argmax_at_left=at_left,
                     n_peak_significantly_right_of_left=n_peak_sig,
                     max_peak_gain_over_left=float(max_peak_gain),
                     n_combos_collapse_after_080=n_collapse,
                     n_combos=len(keys),
                     higher_load_higher_q=bool(slope > 0),
                     cross_check=cross),
    )
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["search", "regime", "all"])
    ap.add_argument("--search-out", default=os.path.join(DATA, "up_p3_nested.json"))
    ap.add_argument("--regime-out", default=os.path.join(DATA, "up_p3_two_regime.json"))
    args = ap.parse_args()
    if args.stage in ("search", "all"):
        o = stage_search(args.search_out)
        for tag in ("P2_case_robust", "P1_per_combo", "P3_global"):
            s = o["protocols"][tag]["summary"]
            print("%-16s dMean=%+.4f CI=[%+.4f,%+.4f] same=%d/%d BH=%d gate=%s"
                  % (tag, s["delta_mean"], s["delta_ci95"][0], s["delta_ci95"][1],
                     s["n_same_direction"], s["n_combos"], s["n_bh_significant"],
                     s["gate_pass"]), flush=True)
        print("winners:", json.dumps(o["winners"]["P2"], ensure_ascii=False))
        print("saved ->", args.search_out)
    if args.stage in ("regime", "all"):
        o = stage_regime(args.regime_out)
        print("regression:", json.dumps(o["regression"]["slope"]), "r2",
              round(o["regression"]["r2"], 4), "p", o["regression"]["p_value"])
        print("verdict:", json.dumps(o["verdict"], ensure_ascii=False))
        print("saved ->", args.regime_out)


if __name__ == "__main__":
    main()