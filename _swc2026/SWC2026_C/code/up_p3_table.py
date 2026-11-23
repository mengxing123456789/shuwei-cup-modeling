# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p3_table.py -- compact paper table from data/up_p3_two_regime.json.

Reads the finished two-regime artifact (15 combos x 61 q values x 30 seeds) and
emits one row per (case, alpha/beta mapping):

    combo | rho | argmax_q | tune_max | holdout_at_argmax | holdout_best_q
          | argmax_at_left | drop_after_080_pt | ...

Nothing is re-simulated here: every number is derived from the stored ``curve``
(tune/holdout means) and ``argmax`` blocks, and each derived value is checked
against the stored one before it is written out.

CLI:
    python up_p3_table.py            # -> data/up_p3_table.json
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common import DATA, write_json  # noqa: E402

SRC = os.path.join(DATA, "up_p3_two_regime.json")
OUT = "up_p3_table.json"
MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]
CASES = ("S1", "S2", "S3")
LEFT_THRESHOLD = 0.35      # same rule as up_p3_nested_search.stage_regime


def _key(case, alpha, beta):
    return "%s|a%.2f_b%.2f" % (case, alpha, beta)


def build_table():
    with open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    qgrid = [round(float(q), 4) for q in d["_meta"]["q_grid"]]
    i080 = qgrid.index(0.80)
    i090 = qgrid.index(0.90)

    rows = []
    checks = dict(
        n_combos_source=len(d["argmax"]),
        argmax_q_matches_curve_argmax=0,
        tune_max_matches_curve=0,
        holdout_at_argmax_matches_curve=0,
        drop_after_080_matches_stored=0,
        holdout_best_q_matches_curve=0,
        max_abs_diff_tune_max=0.0,
        max_abs_diff_holdout_at_argmax=0.0,
        max_abs_diff_drop_080_pt=0.0,
        max_abs_diff_holdout_best=0.0,
    )

    for case in CASES:
        for alpha, beta in MAPPINGS:
            k = _key(case, alpha, beta)
            am = d["argmax"][k]
            cu = d["curve"][k]
            rho = float(d["utilisation_rho"][k]["rho"])
            tune = np.asarray(cu["tune"], float)
            hold = np.asarray(cu["holdout"], float)
            assert tune.size == len(qgrid) == hold.size, (k, tune.size, len(qgrid))

            # --- re-derive every reported quantity from the curve -------- #
            j_star = int(np.argmax(tune))
            tune_max = float(tune[j_star])
            argmax_q = float(qgrid[j_star])
            hold_at_argmax = float(hold[j_star])
            j_h = int(np.argmax(hold))
            hold_best_q = float(qgrid[j_h])
            hold_best = float(hold[j_h])
            after080 = tune[i080:]
            drop_pt = float((tune_max - after080.mean()) * 100.0)
            tune_at_080 = float(tune[i080])
            tune_at_090 = float(tune[i090])
            drop_080_090_pt = float((tune_at_080 - tune_at_090) * 100.0)
            gain_080_to_peak_pt = float((tune_max - tune_at_080) * 100.0)

            # --- cross-check against the stored argmax block ------------- #
            checks["max_abs_diff_tune_max"] = max(
                checks["max_abs_diff_tune_max"], abs(tune_max - am["tune_max"]))
            checks["max_abs_diff_holdout_at_argmax"] = max(
                checks["max_abs_diff_holdout_at_argmax"],
                abs(hold_at_argmax - am["holdout_at_argmax"]))
            checks["max_abs_diff_drop_080_pt"] = max(
                checks["max_abs_diff_drop_080_pt"],
                abs(drop_pt - am["drop_vs_peak"] * 100.0))
            checks["max_abs_diff_holdout_best"] = max(
                checks["max_abs_diff_holdout_best"], abs(hold_best - am["holdout_best"]))
            checks["argmax_q_matches_curve_argmax"] += int(
                abs(argmax_q - am["argmax_q"]) < 1e-12)
            checks["tune_max_matches_curve"] += int(
                abs(tune_max - am["tune_max"]) < 1e-12)
            checks["holdout_at_argmax_matches_curve"] += int(
                abs(hold_at_argmax - am["holdout_at_argmax"]) < 1e-12)
            checks["drop_after_080_matches_stored"] += int(
                abs(drop_pt - am["drop_vs_peak"] * 100.0) < 1e-9)
            checks["holdout_best_q_matches_curve"] += int(
                abs(hold_best_q - am["holdout_best_q"]) < 1e-12)

            plateau = [float(q) for q in am["plateau_q"]]
            rows.append(dict(
                combo=k, case=case, alpha=alpha, beta=beta, rho=float(rho),
                argmax_q=argmax_q,
                tune_max=tune_max,
                holdout_at_argmax=hold_at_argmax,
                holdout_best_q=hold_best_q,
                holdout_best=hold_best,
                argmax_at_left=bool(argmax_q <= LEFT_THRESHOLD),
                drop_after_080_pt=round(drop_pt, 4),
                tune_at_080=tune_at_080,
                tune_at_090=tune_at_090,
                drop_080_to_090_pt=round(drop_080_090_pt, 4),
                gain_080_to_peak_pt=round(gain_080_to_peak_pt, 4),
                collapse_after_080=bool(am["collapse_after_080"]),
                plateau_width_steps=int(len(plateau)),
                plateau_q_min=float(min(plateau)),
                plateau_q_max=float(max(plateau)),
                tune_gap_to_baseline_pt=round(
                    (tune_max - float(cu["baseline_tune"])) * 100.0, 4),
                baseline_tune=float(cu["baseline_tune"]),
                baseline_holdout=float(cu["baseline_holdout"]),
                gate=float(cu["gate"]),
                late_tol=float(cu["late_tol"]),
            ))

    n = len(rows)
    checks["n_rows"] = n
    checks["all_rows_complete"] = bool(n == 15)
    checks["consistent"] = bool(
        checks["argmax_q_matches_curve_argmax"] == n
        and checks["tune_max_matches_curve"] == n
        and checks["holdout_at_argmax_matches_curve"] == n
        and checks["drop_after_080_matches_stored"] == n
        and checks["holdout_best_q_matches_curve"] == n
        and checks["max_abs_diff_tune_max"] <= 1e-12
        and checks["max_abs_diff_holdout_at_argmax"] <= 1e-12
        and checks["max_abs_diff_drop_080_pt"] <= 1e-9)

    n_left = int(sum(1 for r in rows if r["argmax_at_left"]))
    n_collapse = int(sum(1 for r in rows if r["collapse_after_080"]))
    out = dict(
        _meta=dict(
            purpose="compact paper table for the P3 two-regime quantile study",
            script="code/up_p3_table.py",
            engine="code/up_p3_vectorized.py (re-derived from data/up_p3_two_regime.json)",
            source="data/up_p3_two_regime.json",
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            seeds=list(d["_meta"]["seeds"]),
            n_tune=int(d["_meta"]["n_tune"]),
            n_holdout=len(d["_meta"]["seeds"]) - int(d["_meta"]["n_tune"]),
            q_grid=qgrid,
            n_rows=n,
            mapping_order=["a%.2f_b%.2f" % m for m in MAPPINGS],
            columns=dict(
                combo="case|alpha_beta mapping key",
                rho="utilisation sum_j E[alpha*d_j+beta]/H",
                argmax_q="q maximising the tune-seed mean weighted on-time rate",
                tune_max="tune mean at argmax_q (first %d seeds)" % int(d["_meta"]["n_tune"]),
                holdout_at_argmax="holdout mean at argmax_q (last seeds, never used for selection)",
                holdout_best_q="q maximising the holdout mean",
                argmax_at_left="argmax_q <= %.2f" % LEFT_THRESHOLD,
                drop_after_080_pt="(tune_max - mean(tune for q >= 0.80)) x 100, in points",
                tune_at_080="tune mean at q = 0.80",
                tune_at_090="tune mean at q = 0.90",
                drop_080_to_090_pt="(tune@0.80 - tune@0.90) x 100, in points",
                gain_080_to_peak_pt="(tune_max - tune@0.80) x 100, in points",
                collapse_after_080="stored flag: drop_after_080 > 2 points",
                plateau_width_steps="number of q steps within 0.002 of tune_max",
                tune_gap_to_baseline_pt="(tune_max - slack_old baseline tune) x 100, in points",
            ),
            fixed=dict(rule="abs", review=False, selection="risk",
                       GATE="0.50 except S2|a1.00_b0.50=0.60 and S3|a1.00_b0.50=0.50/20 (legacy)"),
            summary=dict(n_left=n_left, n_collapse_after_080=n_collapse,
                         n_rows=n,
                         rho_min=float(min(r["rho"] for r in rows)),
                         rho_max=float(max(r["rho"] for r in rows)),
                         argmax_q_min=float(min(r["argmax_q"] for r in rows)),
                         argmax_q_max=float(max(r["argmax_q"] for r in rows))),
            checks=checks,
        ),
        rows=rows,
    )
    return out


def main():
    t0 = time.time()
    out = build_table()
    p = write_json(OUT, out)
    c = out["_meta"]["checks"]
    print("[table] rows=%d consistent=%s max|dtune|=%.2e max|ddrop|=%.2e"
          % (c["n_rows"], c["consistent"], c["max_abs_diff_tune_max"],
             c["max_abs_diff_drop_080_pt"]))
    print(json.dumps(out["_meta"]["summary"], ensure_ascii=False))
    for r in out["rows"]:
        print("%-22s rho=%.3f q*=%4.2f tune=%.4f hold@*=%.4f hold*q=%4.2f left=%-5s "
              "drop>080=%6.2fpt"
              % (r["combo"], r["rho"], r["argmax_q"], r["tune_max"],
                 r["holdout_at_argmax"], r["holdout_best_q"],
                 str(r["argmax_at_left"]), r["drop_after_080_pt"]))
    print("saved ->", p, " %.2fs" % (time.time() - t0))


if __name__ == "__main__":
    main()