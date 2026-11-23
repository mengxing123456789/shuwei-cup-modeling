# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p3_review.py -- paid re-observation arm on the vectorised P3 engine.

Question
--------
Does paying for a second observation (prefix 0.6) / third (1.0) ever raise the
weighted on-time rate by >= 1 point with a 95% CI lower bound above zero?

Engine
------
``code/up_p3_vectorized.py`` already implements the review branch inside
``simulate_batch`` (candidate key ``rev`` / ``REVIEW``); no new simulator is
needed.  The branch is re-gated here against the untouched reference
``code/p3_stochastic_schedule.simulate(case, seed, "risk_old",
reviews_allowed=True)`` at Q_HI = 0.70 -- the only point where the stochastic
engine's hardcoded ``q = clip(.70 - .55*max(pressure-.75), .35, .70)`` coincides
with the vectorised candidate -- and must reach max_abs_diff < 1e-9.

Grid
----
15 combos x q in {0.30, 0.40, 0.50, 0.60, 0.70, 0.80} x 30 seeds, both arms run
in the same lock-step batch so the paired difference uses identical draws.
Review arm parameters are fixed at GATE=0.50, LATE_TOL_RISK=12.0, rule=abs.
The JSON is rewritten after every combo, so an interruption leaves a readable
partial artifact.

CLI:
    python up_p3_review.py
"""
import json
import math
import os
import random
import sys
import time

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V  # noqa: E402
from common import DATA, write_json  # noqa: E402

OUT = "up_p3_review.json"
SEEDS = list(V.SEEDS)
N_TUNE = 15
CASES = ("S1", "S2", "S3")
MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]
Q_GRID = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
GATE = 0.5
LATE = 12.0
RULE = V.RULE_ABS
THRESHOLD_PT = 1.0
TOL = 1e-9
METRICS = ("weighted_on_time_rate", "weighted_completion_rate",
           "weighted_tardiness_s", "cost", "elapsed_s", "n_done", "n_drop")


def paired(a, b):
    """Paired t statistics of a - b (per-seed vectors)."""
    d = np.asarray(a, float) - np.asarray(b, float)
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
                n_positive=int((d > 0).sum()), n_negative=int((d < 0).sum()),
                n_zero=int((d == 0).sum()))


def cand_row(q, review, name=None):
    return dict(SEL=0, RULE=RULE, q_hi=q, gate=GATE, late_tol=LATE, REVIEW=review,
                name=name or ("q%.2f_%s" % (q, "rev" if review else "no")))


def _gate_one(seeds, alpha, beta):
    """Reference vs vectorised review arm on one (mapping, seed block)."""
    per_case = {}
    worst = 0.0
    rev_counts = {}
    for case in CASES:
        sp = V.build_spec(case)
        cfg = V.build_configs(sp, seeds)
        scen = V._scen(sp, cfg, alpha, beta)
        vec = V.simulate_batch(sp, cfg, alpha, beta,
                               V._cand_arrays([cand_row(0.70, True)]),
                               n_seeds=len(seeds), scen=scen)
        ref = [V.STO.simulate(case, sd, "risk_old", alpha=alpha, beta=beta,
                              reviews_allowed=True) for sd in seeds]
        d = {}
        for m in METRICS:
            a = np.array([float(r[m]) for r in ref], float)
            b = np.asarray(vec[m], float)[0]
            diff = np.abs(a - b)
            d[m] = dict(max_abs=float(diff.max()), mean_abs=float(diff.mean()),
                        n_exact=int((diff == 0).sum()), n=int(diff.size))
            worst = max(worst, float(diff.max()))
        revs = [int(r["reviews"]) for r in ref]
        rev_counts[case] = dict(mean=float(np.mean(revs)), min=int(min(revs)),
                                max=int(max(revs)), total=int(sum(revs)),
                                n_seeds_with_review=int(sum(1 for x in revs if x > 0)),
                                n_seeds=len(revs))
        per_case[case] = d
    return dict(worst=worst, per_case=per_case, rev_counts=rev_counts,
                n_trials=len(seeds) * len(CASES),
                n_trials_with_review=int(sum(rev_counts[c]["n_seeds_with_review"]
                                             for c in CASES)),
                n_reviews=int(sum(rev_counts[c]["total"] for c in CASES)))


def gate_test(store):
    """Bit-exactness of the review branch against the stochastic reference.

    The stochastic engine hardcodes ``qlevel = clip(.70 - .55*max(0, pressure-.75),
    .35, .70)``, so a fixed candidate ``q_hi = 0.70`` coincides with the reference
    only while its pressure ceiling stays at the .70 clip.  That is true for all
    five alpha/beta mappings used by the grid (verified here), so the gate is swept
    over all 5 mappings x 3 cases x 30 official seeds = 450 trials rather than the
    90 of the baseline mapping alone.  Coverage matters: on the baseline mapping
    only 2/90 trials ever take a paid review, while alpha = 1.5 fires 19/90, which
    is what actually exercises the accept path.
    """
    t0 = time.time()
    sweep = {}
    worst = 0.0
    n_trials = 0
    n_firing = 0
    n_reviews = 0
    for alpha, beta in MAPPINGS:
        tag = "a%.2f_b%.2f" % (alpha, beta)
        r = _gate_one(SEEDS, alpha, beta)
        sweep[tag] = dict(
            alpha=alpha, beta=beta, max_abs_diff=float(r["worst"]),
            passed=bool(r["worst"] <= TOL), per_case=r["per_case"],
            reference_review_usage_at_q070=r["rev_counts"],
            n_trials=r["n_trials"], n_trials_with_review=r["n_trials_with_review"],
            n_reviews=r["n_reviews"])
        worst = max(worst, float(r["worst"]))
        n_trials += r["n_trials"]
        n_firing += r["n_trials_with_review"]
        n_reviews += r["n_reviews"]
        print("[gate] %s max|diff|=%.2e firing=%d/%d reviews/seed(sum)=%d"
              % (tag, r["worst"], r["n_trials_with_review"], r["n_trials"],
                 r["n_reviews"]), flush=True)
    base = sweep["a1.00_b0.50"]
    store["gate"] = dict(
        reference="code/p3_stochastic_schedule.simulate(case, seed, 'risk_old', "
                  "alpha, beta, reviews_allowed=True)",
        engine="code/up_p3_vectorized.py simulate_batch(REVIEW=True)",
        params=dict(Q_HI=0.70, GATE=GATE, LATE_TOL_RISK=LATE, rule="abs", SEL=0),
        tolerance=TOL,
        max_abs_diff=float(worst),
        passed=bool(worst <= TOL),
        primary_mapping=dict(alpha=1.0, beta=0.5, max_abs_diff=base["max_abs_diff"],
                             passed=base["passed"], per_case=base["per_case"],
                             reference_review_usage_at_q070=base["reference_review_usage_at_q070"]),
        mapping_sweep=sweep,
        coverage=dict(n_trials=int(n_trials), n_trials_with_review=int(n_firing),
                      frac_trials_with_review=float(n_firing) / n_trials,
                      n_reviews=int(n_reviews),
                      note="the accept path needs a fired review to be exercised; the "
                           "alpha=1.5 mapping provides 19/90 fired trials, the baseline "
                           "mapping only 2/90"),
        note="the stochastic reference fixes the qlevel ceiling at 0.70 and GATE/LATE_TOL "
             "at 0.50/12.0, so q=0.70 is the only candidate that can be compared "
             "pointwise; q != 0.70 sweeps the same branch under a different pressure "
             "ceiling and is reported as an extension, not as a re-gated arm",
        seconds=float(time.time() - t0))
    return store


def two_regime_argmax_q():
    """argmax q per combo from the finished two-regime artifact (reference only)."""
    p = os.path.join(DATA, "up_p3_two_regime.json")
    out = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in d["argmax"].items():
            out[k] = float(v["argmax_q"])
    return out


def combo_block(case, alpha, beta, ref_q, store):
    sp = V.build_spec(case)
    cfg = V.build_configs(sp, SEEDS)
    scen = V._scen(sp, cfg, alpha, beta)
    rows = [cand_row(q, True) for q in Q_GRID] + [cand_row(q, False) for q in Q_GRID]
    t0 = time.time()
    r = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays(rows),
                         n_seeds=len(SEEDS), scen=scen)
    wall = time.time() - t0
    nQ = len(Q_GRID)
    entries = []
    for i, q in enumerate(Q_GRID):
        j_no = nQ + i
        with_ = {m: np.asarray(r[m], float)[i] for m in METRICS}
        no_ = {m: np.asarray(r[m], float)[j_no] for m in METRICS}
        # review usage proxy: taking a review adds 1.0 s and 1.0 cost, so an arm
        # that is bit-identical on every metric cannot have taken a review.
        identical = bool(all(np.array_equal(with_[m], no_[m]) for m in METRICS))
        st = paired(with_["weighted_on_time_rate"], no_["weighted_on_time_rate"])
        st_t = paired(with_["weighted_on_time_rate"][:N_TUNE],
                      no_["weighted_on_time_rate"][:N_TUNE])
        st_h = paired(with_["weighted_on_time_rate"][N_TUNE:],
                      no_["weighted_on_time_rate"][N_TUNE:])
        e = dict(
            q=float(q),
            on_time_with_review=float(with_["weighted_on_time_rate"].mean()),
            on_time_no_review=float(no_["weighted_on_time_rate"].mean()),
            tune_with=float(with_["weighted_on_time_rate"][:N_TUNE].mean()),
            tune_no=float(no_["weighted_on_time_rate"][:N_TUNE].mean()),
            holdout_with=float(with_["weighted_on_time_rate"][N_TUNE:].mean()),
            holdout_no=float(no_["weighted_on_time_rate"][N_TUNE:].mean()),
            delta=st["mean_delta"], delta_pt=float(st["mean_delta"] * 100.0),
            ci95=[float(x) for x in st["ci95"]],
            ci95_pt=[float(st["ci95"][0] * 100.0), float(st["ci95"][1] * 100.0)],
            se_pt=float(st["se"] * 100.0), t=st["t"], p_value=st["p_value"],
            n_positive=st["n_positive"], n_negative=st["n_negative"],
            n_zero=st["n_zero"], n=st["n"],
            delta_tune_pt=float(st_t["mean_delta"] * 100.0),
            delta_holdout_pt=float(st_h["mean_delta"] * 100.0),
            ci95_holdout_pt=[float(st_h["ci95"][0] * 100.0),
                             float(st_h["ci95"][1] * 100.0)],
            cost_with=float(with_["cost"].mean()), cost_no=float(no_["cost"].mean()),
            elapsed_with=float(with_["elapsed_s"].mean()),
            elapsed_no=float(no_["elapsed_s"].mean()),
            completion_with=float(with_["weighted_completion_rate"].mean()),
            completion_no=float(no_["weighted_completion_rate"].mean()),
            tardiness_with=float(with_["weighted_tardiness_s"].mean()),
            tardiness_no=float(no_["weighted_tardiness_s"].mean()),
            n_drop_with=float(with_["n_drop"].mean()),
            n_drop_no=float(no_["n_drop"].mean()),
            cost_diff=float((with_["cost"] - no_["cost"]).mean()),
            elapsed_diff=float((with_["elapsed_s"] - no_["elapsed_s"]).mean()),
            arms_identical=identical,
            review_fired=bool(not identical),
            improves_ge_1pt_and_sig=bool(st["mean_delta"] * 100.0 >= THRESHOLD_PT
                                         and st["ci95"][0] > 0.0),
        )
        entries.append(e)
    key = "%s|a%.2f_b%.2f" % (case, alpha, beta)
    block = dict(case=case, alpha=alpha, beta=beta, combo=key,
                 two_regime_argmax_q=ref_q.get(key),
                 gate=GATE, late_tol=LATE, rule="abs",
                 q=entries, wall_clock_s=float(wall),
                 n_cells_review_fired=int(sum(1 for e in entries if e["review_fired"])),
                 n_cells_arms_identical=int(sum(1 for e in entries if e["arms_identical"])),
                 max_mean_cost_diff=float(max(e["cost_diff"] for e in entries)),
                 max_mean_elapsed_diff=float(max(e["elapsed_diff"] for e in entries)))
    store.setdefault("combos", {})[key] = block
    print("[review] %-22s %.2fs  best d=%+.2fpt at q=%.2f (threshold %.1fpt)"
          % (key, wall, max(e["delta_pt"] for e in entries),
             entries[int(np.argmax([e["delta_pt"] for e in entries]))]["q"],
             THRESHOLD_PT), flush=True)
    return block, wall


def information_gain(store):
    """Why the review lever is (or is not) taken: how much the prefix 0.6 prediction moves.

    The paid review only pays when the sharper prefix changes the probability that a
    job finishes by its due date, and that probability can only move if the point
    prediction moves.  This block measures the move directly on the frozen ridge
    predictions of the eligible validation units.
    """
    out = {}
    for case in CASES:
        rows = V.STO.TASKS[V.STO.TASKS.case_id == case].sort_values("job_id")
        d01, d06, d16 = [], [], []
        for si, seed in enumerate(SEEDS):
            rng = random.Random(seed)
            for _, row in rows.iterrows():
                u = V.STO.sample_unit(row.family_id, rng)
                p0 = float(V.OLD.DHAT[(u.unit_id, 0.2)])
                p6 = float(V.OLD.DHAT[(u.unit_id, 0.6)])
                p1 = float(V.OLD.DHAT[(u.unit_id, 1.0)])
                d01.append(p6 - p0)
                d06.append(p1 - p6)
                d16.append(p1 - p0)
        d01 = np.array(d01)
        out[case] = dict(
            n_draws=int(d01.size),
            mean_abs_pred_change_02_to_06=float(np.abs(d01).mean()),
            p95_abs_pred_change_02_to_06=float(np.percentile(np.abs(d01), 95)),
            mean_abs_pred_change_06_to_10=float(np.abs(d06).mean()),
            mean_abs_pred_change_02_to_10=float(np.abs(d16).mean()),
            mean_signed_pred_change_02_to_06=float(d01.mean()),
            frac_jobs_change_gt_0_1=float((np.abs(d01) > 0.1).mean()),
            frac_jobs_change_gt_0_5=float((np.abs(d01) > 0.5).mean()),
        )
    store["information_gain"] = dict(
        source="code/p3_schedule.DHAT (frozen ridge predictions), eligible validation unit",
        note="a paid review can only change a decision if pred(0.6) - pred(0.2) moves a "
             "scenario across the due date; a near-zero move means the second "
             "observation carries little information and the VoI hurdle is never met",
        per_case=out)


def cross_check_no_review(store):
    """The no-review arm must equal the two-regime curve wherever GATE/LATE match."""
    p = os.path.join(DATA, "up_p3_two_regime.json")
    if not os.path.exists(p):
        store["no_review_cross_check"] = dict(available=False)
        return
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    qgrid = [round(float(q), 4) for q in d["_meta"]["q_grid"]]
    worst = 0.0
    n_cmp = 0
    skipped = []
    per = {}
    for key, blk in store["combos"].items():
        cur = d["curve"].get(key)
        if cur is None:
            continue
        if abs(float(cur["gate"]) - GATE) > 1e-12 or abs(float(cur["late_tol"]) - LATE) > 1e-12:
            skipped.append(key)
            continue
        mine_t = [e["tune_no"] for e in blk["q"]]
        mine_h = [e["holdout_no"] for e in blk["q"]]
        ref_t = [cur["tune"][qgrid.index(round(e["q"], 4))] for e in blk["q"]]
        ref_h = [cur["holdout"][qgrid.index(round(e["q"], 4))] for e in blk["q"]]
        dt = float(np.max(np.abs(np.array(mine_t) - np.array(ref_t))))
        dh = float(np.max(np.abs(np.array(mine_h) - np.array(ref_h))))
        worst = max(worst, dt, dh)
        n_cmp += 1
        per[key] = dict(max_abs_tune=dt, max_abs_holdout=dh)
    store["no_review_cross_check"] = dict(
        source="data/up_p3_two_regime.json curve block",
        n_compared=n_cmp, skipped_legacy_gate=skipped,
        max_abs_diff=float(worst), tolerance=1e-9,
        passed=bool(n_cmp > 0 and worst <= 1e-9), per_combo=per,
        note="the no-review arm is run at the review-arm GATE/LATE (0.50/12.0); the two "
             "legacy combos (S2|a1.00_b0.50 gate .60, S3|a1.00_b0.50 late 20) are skipped "
             "by design")


def verdict(store):
    rows = []
    for key, blk in store["combos"].items():
        for e in blk["q"]:
            rows.append(dict(combo=key, q=e["q"], delta_pt=e["delta_pt"],
                             ci95_pt=e["ci95_pt"], p_value=e["p_value"],
                             improves_ge_1pt_and_sig=e["improves_ge_1pt_and_sig"],
                             case=blk["case"], alpha=blk["alpha"], beta=blk["beta"]))
    ok = [r for r in rows if r["improves_ge_1pt_and_sig"]]
    harmful = [r for r in rows if r["ci95_pt"][1] < 0]
    best = max(rows, key=lambda r: r["delta_pt"]) if rows else None
    v = dict(
        rule=("delta = mean(weighted_on_time_rate | review) - mean(... | no review), "
              "paired over %d seeds; passes if delta >= %.1f point and the paired-t "
              "95%% CI lower bound > 0 on ANY (case, q)" % (len(SEEDS), THRESHOLD_PT)),
        threshold_pt=THRESHOLD_PT,
        n_tested=len(rows),
        n_ge_1pt=int(sum(1 for r in rows if r["delta_pt"] >= THRESHOLD_PT)),
        n_ge_1pt_and_sig=len(ok),
        passes=bool(len(ok) > 0),
        best_delta_pt=float(best["delta_pt"]) if best else None,
        min_delta_pt=float(min(r["delta_pt"] for r in rows)) if rows else None,
        best_combo=dict(combo=best["combo"], q=best["q"],
                        delta_pt=best["delta_pt"], ci95_pt=best["ci95_pt"],
                        p_value=best["p_value"]) if best else None,
        passing=[dict(combo=r["combo"], q=r["q"], delta_pt=r["delta_pt"],
                      ci95_pt=r["ci95_pt"], p_value=r["p_value"]) for r in ok],
        n_cells_review_fired=int(sum(1 for blk in store["combos"].values()
                                     for e in blk["q"] if e["review_fired"])),
        n_cells_significantly_harmful=len(harmful),
        significantly_harmful=[dict(combo=r["combo"], q=r["q"], delta_pt=r["delta_pt"],
                                    ci95_pt=r["ci95_pt"], p_value=r["p_value"])
                               for r in harmful],
        max_delta_pt_by_q={("%.2f" % q): float(max(
            [r["delta_pt"] for r in rows if abs(r["q"] - q) < 1e-9] or [float("nan")]))
            for q in Q_GRID},
        mean_delta_pt_by_q={("%.2f" % q): float(np.mean(
            [r["delta_pt"] for r in rows if abs(r["q"] - q) < 1e-9]))
            for q in Q_GRID},
    )
    store["verdict"] = v
    return v


def write(store, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)


def main():
    t_all = time.time()
    out_path = os.path.join(DATA, OUT)
    ref_q = two_regime_argmax_q()
    store = dict(
        _meta=dict(
            purpose="paid re-observation (review) arm of the P3 restocking scheduler",
            script="code/up_p3_review.py",
            engine="code/up_p3_vectorized.py simulate_batch(REVIEW=True/False)",
            reference="code/p3_stochastic_schedule.simulate(..., reviews_allowed=True)",
            q_grid=Q_GRID, seeds=SEEDS, n_tune=N_TUNE,
            n_holdout=len(SEEDS) - N_TUNE,
            split="seeds 0-14 = tune, 15-29 = holdout (both reported)",
            review_params=dict(Q_HI="the swept q", GATE=GATE,
                               LATE_TOL_RISK=LATE, rule="abs", SEL=0),
            review_mechanism="prefix 0.2 -> 0.6 -> 1.0, cost 1.0 per observation, "
                             "at most K per trial and 2 per job, decision = expected "
                             "lateness-probability gain net of 0.02 hurdle",
            mappings=[dict(alpha=a, beta=b) for a, b in MAPPINGS],
            n_combos=15, n_cells=15 * len(Q_GRID),
            trials=int(15 * len(Q_GRID) * 2 * len(SEEDS)),
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            writes="rewritten after every (case, mapping) combo"),
        wall_clock_s=dict(per_combo={}),
    )
    write(store, out_path)

    gate_test(store)
    write(store, out_path)
    print("[gate] passed=%s max_abs_diff=%.2e"
          % (store["gate"]["passed"], store["gate"]["max_abs_diff"]), flush=True)

    walls = []
    for case in CASES:
        for alpha, beta in MAPPINGS:
            blk, w = combo_block(case, alpha, beta, ref_q, store)
            walls.append(w)
            store["wall_clock_s"]["per_combo"][blk["combo"]] = float(w)
            write(store, out_path)          # incremental: never lose a finished combo

    cross_check_no_review(store)
    information_gain(store)
    v = verdict(store)
    store["wall_clock_s"]["total"] = float(time.time() - t_all)
    store["wall_clock_s"]["sum_per_combo"] = float(sum(walls))
    store["_meta"]["generated_at_final"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    write(store, out_path)

    print("P3FINAL review_passes=%s best_delta=%.2fpt table_rows=%d"
          % ("True" if v["passes"] else "False",
             v["best_delta_pt"] if v["best_delta_pt"] is not None else float("nan"),
             len(json.load(open(os.path.join(DATA, "up_p3_table.json"), encoding="utf-8"))["rows"])
             if os.path.exists(os.path.join(DATA, "up_p3_table.json")) else 0))
    print("[verdict] passes=%s n_ge_1pt=%d n_ge_1pt_sig=%d best=%s"
          % (v["passes"], v["n_ge_1pt"], v["n_ge_1pt_and_sig"],
             json.dumps(v["best_combo"], ensure_ascii=False)))
    print("[cross] no_review_matches_two_regime=%s max_abs=%.2e"
          % (store["no_review_cross_check"]["passed"],
             store["no_review_cross_check"]["max_abs_diff"]))
    print("saved ->", out_path, " %.1fs" % (time.time() - t_all))


if __name__ == "__main__":
    main()