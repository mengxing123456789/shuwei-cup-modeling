# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p3_prereg.py -- write the P3 dispatch v2 pre-registration BEFORE any test run.

The file this writes (data/up2_p3_prereg.json) is frozen: the final evaluation
reads it, recomputes the gate exactly as written here, and records its sha256.
Nothing in the v2 search may read seeds 2026111725..2026111729.
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import DATA  # noqa: E402

PREREG = dict(
    version="p3-v2",
    written_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    purpose=("upgrade the P3 stochastic restocking dispatcher relative to the frozen "
             "slack policy (code/up_p3_vectorized.py SEL=slack, RULE=slack, q=0.60, "
             "gate=0.50, late_tol=12, no review)"),
    split=dict(
        train=[2026111700 + i for i in range(15)],
        val=[2026111715 + i for i in range(10)],
        test=[2026111725 + i for i in range(5)],
        note="seeds 2026111725..2026111729 are evaluated exactly once, after the "
             "policies are frozen on train/val; no test seed enters any search, "
             "early stopping, or hyper-parameter choice"),
    baseline=dict(name="slack_old", SEL=1, RULE="slack", q_hi=0.60, gate=0.50,
                  late_tol=12.0, REVIEW=False,
                  note="bit-identical to code/p3_improved_verify.simulate(case, seed, "
                       "'slack_old') on all 30 official seeds"),
    cases=["S2", "S3"],
    mappings=[dict(alpha=1.0, beta=0.5), dict(alpha=0.75, beta=0.5),
              dict(alpha=1.5, beta=0.5), dict(alpha=1.0, beta=0.0),
              dict(alpha=1.0, beta=1.0)],
    metric=dict(
        primary="weighted_on_time_rate",
        secondary=["weighted_completion_rate", "weighted_tardiness_s", "cost",
                   "n_reviews"],
    ),
    strategy_classes=[
        "A: parametric rule search (slack coefficient, reserve quantile, EDF/ATC mix, "
        "review hurdle, blocking weight) -- joint random grid, selection on train mean, "
        "shortlist re-ranked on val",
        "B: learned linear policy over online context features (queue pressure, remaining "
        "budget fraction, mean predictive slack, fraction of feasible set already late) "
        "-> reserve multiplier and selector mix; trained with the cross-entropy method on "
        "train seeds, early stopping on val seeds (no gradients on test)",
        "C: distributionally robust reservation over the five official (alpha,beta) "
        "mappings: min-max (worst mapping) and CVaR(0.2) objectives on train, val check",
    ],
    selection=dict(
        rule=("for each case independently: candidates ranked by mean train weighted "
              "on-time rate over the 5 mappings; the top 5 per class are re-ranked by "
              "mean val rate over the 5 mappings; the single best val candidate per case "
              "is frozen. If no class reaches +1.5pp on val, the best val candidate "
              "overall is frozen anyway and the report states the shortfall."),
        no_test_tuning=True,
    ),
    gate=dict(
        statistic=("blocked paired difference vs slack_old. Blocks = 2 cases x 5 official "
                   "mappings (10 blocks, fixed conditions); each block has the 5 test seeds "
                   "as replicates. Delta_bar = mean of the 10 block means; SE from the "
                   "pooled within-block variance (each block's s^2/5), 95% t interval with "
                   "Welch-Satterthwaite df."),
        g1_delta_ge_0p015=True,
        g2_ci_lower_gt_0=True,
        g3_both_cases_positive=True,
        g4_no_mapping_regression_beyond_0p005=True,
        g5_completion_no_regression=0.01,
        g6_cost_inflation_max=0.05,
        passes="G1 and G2 and G3 and G4 and G5 and G6",
        secondary_reported=[
            "strict cluster-by-seed interval (5 seed-level means, df=4) -- conservative",
            "naive 50-pair interval -- optimistic, reported only as a bound",
            "sign test over the 50 (case,mapping,seed) pairs",
        ],
        note=("the blocked analysis is a randomised-block design: mapping and case are "
              "fixed conditions, seeds are replicates. The strict seed-clustered interval "
              "is reported alongside and is not used for the pass decision."),
    ),
    reference_arms=dict(
        v1_improved=dict(S2=dict(SEL=0, RULE="abs", q_hi=0.50, gate=0.60, late_tol=12.0),
                         S3=dict(SEL=0, RULE="abs", q_hi=0.60, gate=0.50, late_tol=20.0),
                         note="data/p3_improved_verify.json selected policy, 30-seed mean "
                              "+5.85pp; reported as the incumbent v1 arm"),
        edf=dict(SEL=0, RULE="abs", q_hi=0.30, gate=1.01, late_tol=1e6,
                 note="EDF-dominated reference, not a target"),
    ),
    budgets=dict(cpu_minutes=40, gpu_minutes=0,
                 note="vectorised replay only; no neural training on GPU"),
    cost_definition=("cost = sum over dispatches of (2 + 0.1*b + 0.2*D) plus 1.0 per paid "
                     "re-observation; budget B per case per trial"),
    review_definition=("paid prefix re-observation 0.2 -> 0.6 -> 1.0 s, 1.0 s and 1.0 cost "
                       "unit each, at most K per trial and 2 per job, taken when the "
                       "expected weighted lateness-probability gain exceeds the hurdle"),
)


def main():
    path = os.path.join(DATA, "up2_p3_prereg.json")
    blob = json.dumps(PREREG, ensure_ascii=False, indent=1)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(blob)
    sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    print("wrote", path)
    print("sha256", sha)
    print("split", [(len(PREREG["split"][k]), PREREG["split"][k][0], PREREG["split"][k][-1])
                    for k in ("train", "val", "test")])
    return sha


if __name__ == "__main__":
    main()