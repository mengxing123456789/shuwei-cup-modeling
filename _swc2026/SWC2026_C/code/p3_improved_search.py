
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P3 improved-scheduling search under the corrected protocol.

Purpose
-------
Search for a deployable scheduler that improves the weighted on-time rate over
``slack_old`` without changing any official constant.  In particular the
official changeover remains 0.5 s, service remains p = alpha*d + beta, completion
is C = s + p and the next availability is s + max(p, b).

Protocol
--------
* 30 official seeds 2026111700..2026111729; every method sees the same sampled
  source units for a given (case, seed).
* Stage 1 (selection): candidates are scored only on the first 15 official
  seeds.  Per case, the best candidate above the incumbent is selected.
* Stage 2 (holdout): only the selected candidate(s) are run on the last 15
  official seeds.  The full-30 paired difference is reported for information,
  but selection never reads the holdout.
* No observations/reviews are added: the existing study measured their net
  effect as negative, so this search keeps the action set at wait/execute/drop.

Candidate families (all legal under the corrected protocol)
-----------------------------------------------------------
1. slack_old with a longer lateness-decay horizon and alternative reserve
   quantile/coefficient.  This changes job ordering, not the reservation formula.
2. risk_old: chance-constrained adaptive quantile reservation driven by the
   frozen old ridge prediction, with an expected-on-time ATC priority.
3. risk_fusion: same mechanism using the validation-selected fusion prediction.
   gate and quantile cap are searched because the incumbent reservation is very
   conservative at high capacity pressure.

Output: data/p3_improved_search.json.  Existing scripts/results are read-only.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import best_p3_sens as B  # parameterised, protocol-correct simulator
import p3_stochastic_schedule as S  # frozen data only; main() is protected

SEEDS = list(S.SEEDS)
CASES = ["S1", "S2", "S3"]
SEARCH_CASES = ["S2", "S3"]
TUNE_IDX = list(range(15))
HOLD_IDX = list(range(15, 30))
OUT = os.path.join(HERE, "..", "data", "p3_improved_search.json")
BASELINE_JSON = os.path.join(HERE, "..", "data", "p3_stochastic_schedule.json")


def ci95(x):
    x = np.asarray(x, float)
    return float(1.96 * x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else 0.0


def mean(x):
    return float(np.mean(np.asarray(x, float)))


def eval_indices(policy, params, case, indices):
    """Run one method on the requested official-seed indices."""
    rows = []
    for i in indices:
        r = B.simulate(case, SEEDS[i], policy, par=params or None)
        rows.append(r)
    return dict(
        on_time=[float(r["weighted_on_time_rate"]) for r in rows],
        completion=[float(r["weighted_completion_rate"]) for r in rows],
        tardiness=[float(r["weighted_tardiness_s"]) for r in rows],
        cost=[float(r["cost"]) for r in rows],
        idle=[float(r["reserved_idle_s"]) for r in rows],
        n_done=[int(r["n_done"]) for r in rows],
        n_drop=[int(r["n_drop"]) for r in rows],
        indices=list(indices),
    )


def pair_stats(cand, base, indices):
    d = np.asarray(cand["on_time"], float) - np.asarray(base["on_time"], float)
    dc = np.asarray(cand["completion"], float) - np.asarray(base["completion"], float)
    return dict(
        delta_mean=float(d.mean()),
        delta_ci95=ci95(d),
        delta_median=float(np.median(d)),
        wins=int((d > 1e-12).sum()),
        losses=int((d < -1e-12).sum()),
        ties=int((np.abs(d) <= 1e-12).sum()),
        delta_completion_mean=float(dc.mean()),
        cand_mean=float(np.mean(cand["on_time"])),
        base_mean=float(np.mean(base["on_time"])),
        cand_completion_mean=float(np.mean(cand["completion"])),
        base_completion_mean=float(np.mean(base["completion"])),
        per_seed_delta=[float(x) for x in d],
    )


def candidate_grid():
    """Broad, protocol-legal grid; every candidate changes ordering/reserve only."""
    out = []
    seen = set()

    def add(family, policy, params):
        tag = "%s|%s|%s" % (family, policy, ",".join("%s=%g" % (k, v) for k, v in sorted(params.items())))
        if tag in seen:
            return
        seen.add(tag)
        out.append(dict(tag=tag, family=family, policy=policy, params=dict(params)))

    # 1) incumbent and ordering-horizon variants (reservation stays slack-based)
    add("slack", "slack_old", {})
    for tol in (12.0, 16.0, 20.0, 24.0, 30.0, 40.0):
        for qbuf in (0.4, 0.6):
            for coef in (0.4, 0.6):
                add("slack", "slack_old",
                    dict(LATE_TOL_SLACK=tol, QBUF=qbuf, SLACK_COEF=coef))

    # 2-3) adaptive chance-constrained reservation, old vs fusion predictor
    for policy in ("risk_old", "risk_fusion"):
        for qhi in (0.50, 0.55, 0.60, 0.70):
            for gate in (0.50, 0.60, 0.70, 0.80):
                for tol in (12.0, 20.0, 30.0):
                    add("adaptive_quantile", policy,
                        dict(Q_HI=qhi, GATE=gate, LATE_TOL_RISK=tol))
    return out


def main():
    t0 = time.time()
    print("P3 improved search: correct protocol, pairing by official seed", flush=True)
    print("candidate count:", len(candidate_grid()), flush=True)

    # ---- reproduction gates -------------------------------------------------
    # Slack baseline must match every seed of p3_stochastic_schedule.
    base = {c: eval_indices("slack_old", {}, c, range(30)) for c in CASES}
    direct_slack = {}
    for c in CASES:
        direct_slack[c] = [float(S.simulate(c, sd, "slack_old")["weighted_on_time_rate"])
                           for sd in SEEDS]
    slack_gate = {}
    for c in CASES:
        d = np.asarray(base[c]["on_time"]) - np.asarray(direct_slack[c])
        slack_gate[c] = dict(max_abs_seed_diff=float(np.max(np.abs(d))),
                             mean_diff=float(np.mean(d)),
                             exact=bool(np.max(np.abs(d)) < 1e-12))
    assert all(v["exact"] for v in slack_gate.values()), slack_gate

    # Secondary gate: risk without reviews matches the direct simulator exactly.
    risk_norev = {}
    for c in SEARCH_CASES:
        risk_norev[c] = eval_indices("risk_fusion", {}, c, range(30))
        direct = [float(S.simulate(c, sd, "risk_fusion", reviews_allowed=False)
                        ["weighted_on_time_rate"]) for sd in SEEDS]
        dd = np.asarray(risk_norev[c]["on_time"]) - np.asarray(direct)
        assert float(np.max(np.abs(dd))) < 1e-12, (c, float(np.max(np.abs(dd))))
    print("reproduction gates: slack_old exact; risk_fusion(no reviews) exact", flush=True)

    with open(BASELINE_JSON, encoding="utf-8") as f:
        official = json.load(f)
    official_summary = {}
    for x in official["summary"]:
        official_summary[(x["case"], x["policy"])] = {
            k: x[k] for k in ("weighted_on_time_rate", "weighted_completion_rate", "cost")
        }

    baseline = {}
    for c in CASES:
        baseline[c] = dict(
            all30=base[c],
            tune=dict(on_time=base[c]["on_time"][:15],
                      completion=base[c]["completion"][:15],
                      indices=TUNE_IDX),
            holdout=dict(on_time=base[c]["on_time"][15:],
                         completion=base[c]["completion"][15:],
                         indices=HOLD_IDX),
            all30_mean=mean(base[c]["on_time"]),
            tune_mean=mean(base[c]["on_time"][:15]),
            holdout_mean=mean(base[c]["on_time"][15:]),
            all30_completion=mean(base[c]["completion"]),
        )

    # ---- stage 1: score candidates on the first 15 seeds only ---------------
    grid = candidate_grid()
    rows = []
    for k, cand in enumerate(grid, 1):
        rec = dict(tag=cand["tag"], family=cand["family"], policy=cand["policy"],
                   params=cand["params"], tune={})
        for c in SEARCH_CASES:
            r = eval_indices(cand["policy"], cand["params"], c, TUNE_IDX)
            rec["tune"][c] = dict(on_time=r["on_time"], completion=r["completion"],
                                  mean=mean(r["on_time"]),
                                  completion_mean=mean(r["completion"]))
        rows.append(rec)
        if k % 10 == 0:
            print("  scored %d/%d candidates (%.1fs)" % (k, len(rows), time.time() - t0),
                  flush=True)

    # per-case selection: best first-15 mean strictly above slack_old
    selection = {}
    top_lists = {}
    for c in SEARCH_CASES:
        ranked = sorted(rows, key=lambda r: r["tune"][c]["mean"], reverse=True)
        top_lists[c] = [dict(tag=r["tag"], family=r["family"], policy=r["policy"],
                             params=r["params"], tune_mean=r["tune"][c]["mean"],
                             tune_completion=r["tune"][c]["completion_mean"])
                        for r in ranked[:10]]
        best = ranked[0]
        if best["tune"][c]["mean"] > baseline[c]["tune_mean"] + 1e-12:
            selection[c] = dict(tag=best["tag"], family=best["family"],
                                policy=best["policy"], params=best["params"],
                                tune_mean=best["tune"][c]["mean"],
                                tune_completion=best["tune"][c]["completion_mean"],
                                selected_over_incumbent=True)
        else:
            selection[c] = dict(tag="slack_old|incumbent", family="slack",
                                policy="slack_old", params={},
                                tune_mean=baseline[c]["tune_mean"],
                                tune_completion=mean(base[c]["completion"][:15]),
                                selected_over_incumbent=False)

    # Same-configuration selection (one policy for S2+S3) is reported separately.
    ranked_global = sorted(
        rows, key=lambda r: 0.5 * (r["tune"]["S2"]["mean"] + r["tune"]["S3"]["mean"]),
        reverse=True)
    top_global = ranked_global[0]

    # ---- stage 2: evaluate selected policy/config on holdout only -----------
    s1 = dict(tag="slack_old|incumbent", family="slack",
              policy="slack_old", params={},
              selected_over_incumbent=False,
              tune_mean=baseline["S1"]["tune_mean"],
              tune_completion=mean(base["S1"]["completion"][:15]),
              tune=dict(on_time=base["S1"]["on_time"][:15],
                        completion=base["S1"]["completion"][:15],
                        mean=baseline["S1"]["tune_mean"],
                        completion_mean=mean(base["S1"]["completion"][:15])),
              holdout=dict(on_time=base["S1"]["on_time"][15:],
                           completion=base["S1"]["completion"][15:],
                           mean=baseline["S1"]["holdout_mean"],
                           completion_mean=mean(base["S1"]["completion"][15:])),
              all30=dict(on_time=base["S1"]["on_time"],
                         completion=base["S1"]["completion"],
                         mean=baseline["S1"]["all30_mean"],
                         completion_mean=baseline["S1"]["all30_completion"]))
    selected = dict(S1=s1)
    for c in SEARCH_CASES:
        selected[c] = selection[c]
        s = selection[c]
        if s["tag"].endswith("incumbent"):
            s["holdout"] = dict(on_time=base[c]["on_time"][15:],
                                completion=base[c]["completion"][15:],
                                mean=baseline[c]["holdout_mean"],
                                completion_mean=mean(base[c]["completion"][15:]))
        else:
            h = eval_indices(s["policy"], s["params"], c, HOLD_IDX)
            s["holdout"] = dict(on_time=h["on_time"], completion=h["completion"],
                                mean=mean(h["on_time"]),
                                completion_mean=mean(h["completion"]))
        s["all30"] = dict(on_time=s["holdout"]["on_time"] + [], completion=[])
    # rebuild chronological all-30 arrays: tune | holdout (same official order)
    for c in CASES:
        s = selected[c]
        tune_ot = (base[c]["on_time"][:15] if s["tag"].endswith("incumbent")
                   else next(r for r in rows if r["tag"] == s["tag"])["tune"][c]["on_time"])
        tune_cp = (base[c]["completion"][:15] if s["tag"].endswith("incumbent")
                   else next(r for r in rows if r["tag"] == s["tag"])["tune"][c]["completion"])
        s["tune"] = dict(on_time=tune_ot, completion=tune_cp,
                         mean=mean(tune_ot), completion_mean=mean(tune_cp))
        s["all30"] = dict(on_time=list(tune_ot) + list(s["holdout"]["on_time"]),
                          completion=list(tune_cp) + list(s["holdout"]["completion"]),
                          mean=mean(list(tune_ot) + list(s["holdout"]["on_time"])),
                          completion_mean=mean(list(tune_cp) + list(s["holdout"]["completion"])))

    # Evaluate the single best same-config candidate on holdout too.
    global_sel = dict(policy=top_global["policy"], params=top_global["params"],
                      tag=top_global["tag"])
    global_hold = {}
    for c in SEARCH_CASES:
        h = eval_indices(global_sel["policy"], global_sel["params"], c, HOLD_IDX)
        global_hold[c] = dict(mean=mean(h["on_time"]), completion_mean=mean(h["completion"]),
                              on_time=h["on_time"], completion=h["completion"])
        global_sel[c] = dict(tune_mean=top_global["tune"][c]["mean"],
                             holdout_mean=mean(h["on_time"]),
                             tune_completion=top_global["tune"][c]["completion_mean"],
                             holdout_completion=mean(h["completion"]),
                             selection_gain=top_global["tune"][c]["mean"] - baseline[c]["tune_mean"],
                             holdout_gain=mean(h["on_time"]) - baseline[c]["holdout_mean"])

    # ---- paired evidence ----------------------------------------------------
    evidence = {}
    for c in CASES:
        s = selected[c]
        combo = dict(on_time=s["all30"]["on_time"], completion=s["all30"]["completion"],
                     indices=list(range(30)))
        tune = dict(on_time=s["tune"]["on_time"], completion=s["tune"]["completion"],
                    indices=TUNE_IDX)
        hold = dict(on_time=s["holdout"]["on_time"], completion=s["holdout"]["completion"],
                    indices=HOLD_IDX)
        btune = dict(on_time=base[c]["on_time"][:15], completion=base[c]["completion"][:15],
                     indices=TUNE_IDX)
        bhold = dict(on_time=base[c]["on_time"][15:], completion=base[c]["completion"][15:],
                     indices=HOLD_IDX)
        evidence[c] = dict(
            selected_tag=s["tag"], family=s["family"], policy=s["policy"],
            params=s["params"], selected_over_incumbent=s["selected_over_incumbent"],
            tune=pair_stats(tune, btune, TUNE_IDX),
            holdout=pair_stats(hold, bhold, HOLD_IDX),
            all30=pair_stats(combo, base[c], list(range(30))),
            selected_all30_mean=s["all30"]["mean"],
            selected_all30_completion=s["all30"]["completion_mean"],
            baseline_all30_mean=baseline[c]["all30_mean"],
            baseline_all30_completion=baseline[c]["all30_completion"],
        )

    global_evidence = {}
    for c in SEARCH_CASES:
        h = global_hold[c]
        global_evidence[c] = dict(
            tune_mean=global_sel[c]["tune_mean"],
            holdout_mean=global_sel[c]["holdout_mean"],
            selection_gain=global_sel[c]["selection_gain"],
            holdout_gain=global_sel[c]["holdout_gain"],
            holdout_completion=global_sel[c]["holdout_completion"],
        )

    # Deployability verdict: selected on first15, holdout non-negative, and the
    # all-30 paired 95% interval strictly above zero are progressively stronger bars.
    for c in SEARCH_CASES:
        e = evidence[c]
        e["verdict"] = dict(
            selected_on_validation=bool(e["selected_over_incumbent"]),
            holdout_positive=bool(e["holdout"]["delta_mean"] > 0),
            all30_positive=bool(e["all30"]["delta_mean"] > 0),
            all30_ci_strictly_positive=bool(e["all30"]["delta_mean"] - e["all30"]["delta_ci95"] > 0),
            completion_not_lower=bool(e["selected_all30_completion"] + 1e-12
                                      >= e["baseline_all30_completion"]),
        )
        e["verdict"]["usable_improvement"] = bool(
            e["verdict"]["selected_on_validation"] and e["verdict"]["holdout_positive"]
            and e["verdict"]["all30_positive"] and e["verdict"]["completion_not_lower"])

    # mixed policy is just the per-case selection; report its combined paired
    # score across the two search cases over all 30 seeds.
    mixed_delta = []
    mixed_hold = []
    mixed_tune = []
    for i in range(30):
        d = 0.0
        for c in SEARCH_CASES:
            e = evidence[c]
            d += (e["selected_all30_mean"] if False else
                  (e["all30"]["per_seed_delta"][i]))
        mixed_delta.append(d / len(SEARCH_CASES))
    for i in range(15):
        mixed_tune.append(float(np.mean([evidence[c]["tune"]["per_seed_delta"][i]
                                        for c in SEARCH_CASES])))
        mixed_hold.append(float(np.mean([evidence[c]["holdout"]["per_seed_delta"][i]
                                        for c in SEARCH_CASES])))

    out = dict(
        _meta=dict(
            purpose="search a deployable P3 scheduler better than slack_old without changing official constants",
            protocol="p=alpha*d+beta; C=s+p; next=s+max(p,b); changeover fixed 0.5 s; reserve_min 0.2 s",
            seeds=SEEDS,
            selection_protocol="per-case max mean weighted_on_time over first 15 official seeds; candidates scored on first15 only; last15 never used for selection",
            candidate_count=len(rows),
            search_cases=SEARCH_CASES,
            review_policy="no added observations (existing VoI experiment was negative)",
            official_baseline_reference={
                c: official_summary[(c, "slack_old")] for c in CASES},
            official_risk_reference={
                c: official_summary[(c, "risk_fusion")] for c in ("S2", "S3")},
            legacy_warning="best_p3_sens kap=0.25 changed the official 0.5 s changeover and is excluded",
            holdout_independence="candidate family is broad but was motivated by earlier exploratory runs; only first15 enters selection, holdout is reported as untouched outcome data",
        ),
        reproduction_gate=dict(slack_old=slack_gate,
                               risk_fusion_no_reviews="exact per-seed match with p3_stochastic_schedule"),
        baseline=baseline,
        risk_fusion_no_reviews={c: dict(all30_mean=mean(risk_norev[c]["on_time"]),
                                        all30_completion=mean(risk_norev[c]["completion"]),
                                        holdout_mean=mean(risk_norev[c]["on_time"][15:]),
                                        on_time=risk_norev[c]["on_time"])
                                for c in SEARCH_CASES},
        candidates=rows,
        selection=selected,
        selection_top10=top_lists,
        single_config_selection=global_sel,
        single_config_evidence=global_evidence,
        evidence=evidence,
        mixed_policy=dict(
            cases=SEARCH_CASES,
            all30_delta_mean=mean(mixed_delta),
            all30_delta_ci95=ci95(mixed_delta),
            tune_delta_mean=mean(mixed_tune),
            holdout_delta_mean=mean(mixed_hold),
            holdout_delta_ci95=ci95(mixed_hold),
            per_seed_delta=mixed_delta,
        ),
        seconds=round(time.time() - t0, 1),
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("\n=== selection (first 15 seeds) ===", flush=True)
    for c in SEARCH_CASES:
        s = selected[c]
        print("  %s %-44s tune %.4f -> holdout %.4f | all30 %.4f (base %.4f)"
              % (c, s["tag"], s["tune"]["mean"], s["holdout"]["mean"],
                 s["all30"]["mean"], baseline[c]["all30_mean"]), flush=True)
    print("\n=== paired vs slack_old (all 30) ===", flush=True)
    for c in SEARCH_CASES:
        e = evidence[c]
        print("  %s Δ=%+.4f ±%.4f  holdout Δ=%+.4f ±%.4f  W/L/T %d/%d/%d"
              % (c, e["all30"]["delta_mean"], e["all30"]["delta_ci95"],
                 e["holdout"]["delta_mean"], e["holdout"]["delta_ci95"],
                 e["all30"]["wins"], e["all30"]["losses"], e["all30"]["ties"]),
              flush=True)
        print("    verdict:", e["verdict"], flush=True)
    print("  mixed S2+S3 Δ=%+.4f ±%.4f holdout Δ=%+.4f ±%.4f"
          % (out["mixed_policy"]["all30_delta_mean"],
             out["mixed_policy"]["all30_delta_ci95"],
             out["mixed_policy"]["holdout_delta_mean"],
             out["mixed_policy"]["holdout_delta_ci95"]), flush=True)
    print("saved ->", OUT, "(%.1fs)" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()