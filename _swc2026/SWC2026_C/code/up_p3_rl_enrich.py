# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
r"""Post-hoc enrichment of ``data/up_p3_rl.json`` (P3 deep-RL reserve experiment).

Everything appended here is either

* validation-slice only (level curves, greedy action histograms, val CI), or
* derived from arrays that ``up_p3_rl.py --stage final`` already stored
  (the arm-B vs slack_old pairing on the test slice).

The test slice is **not** re-simulated: no new rollout touches SEED_TEST here,
so the "test evaluated exactly once" discipline of the pre-registered protocol
still holds.  Run after ``python code/up_p3_rl.py --stage final``::

    python code/up_p3_rl_enrich.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import up_p3_rl as R                                    # noqa: E402

JSON = R.OUT_JSON


def _pairs(a, b):
    """paired summary of two per-seed arrays (a = method, b = baseline)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return R.paired(a, b)


def val_level_curves():
    """13-level reserve grid on the validation slice, both selectors."""
    out = {}
    for arm in ("slack", "risk"):
        out[arm] = {}
        base_kind = "slack_old" if arm == "slack" else "risk_case"
        for case in R.CASES:
            sp, cfg = R.get_case(case, R.SEED_VAL)
            base = float(R.engine_rule(case, R.SEED_VAL, base_kind)
                         ["weighted_on_time_rate"].mean())
            curve = []
            for j in range(R.NA):
                r = R.rollout(sp, cfg, R.model_arm(case, arm), bmode="grid", fixed_q=j)
                curve.append(float(r["weighted_on_time_rate"].mean()))
            jb = int(np.argmax(curve))
            out[arm][case] = dict(baseline=base, curve=curve,
                                  best_level=jb, best_q=float(R.Q_GRID[jb]),
                                  best_gain=curve[jb] - base)
    return out


def greedy_histograms():
    """What the frozen policy actually does on val (constant vs state-dependent)."""
    out = {}
    for arm in ("slack", "risk"):
        act = R.load_actor(arm)
        out[arm] = {}
        for case in R.CASES:
            r = R.policy_rollout(case, R.SEED_VAL, arm, act, greedy=True, collect=True)
            a = np.concatenate([np.asarray(x).reshape(-1) for x in r["traj"]["act"]])
            hist = np.bincount(a, minlength=R.NA).astype(int).tolist()
            base_kind = "slack_old" if arm == "slack" else "risk_case"
            base = np.asarray(R.engine_rule(case, R.SEED_VAL, base_kind)
                              ["weighted_on_time_rate"])
            out[arm][case] = dict(
                hist=hist, n=int(a.size),
                dominant_level=int(np.argmax(hist)),
                dominant_share=float(hist[int(np.argmax(hist))] / max(a.size, 1)),
                val_on_time=float(np.mean(r["weighted_on_time_rate"])),
                val_delta=float(np.mean(r["weighted_on_time_rate"]) - base.mean()))
    return out


def val_pairing_primary():
    """Arm A vs slack_old on the validation slice (same pairing as the test gate)."""
    act = R.load_actor("slack")
    out = {}
    for case in ("S2", "S3"):
        r = R.policy_rollout(case, R.SEED_VAL, "slack", act, greedy=True)
        b = R.engine_rule(case, R.SEED_VAL, "slack_old")
        out[case] = _pairs(r["weighted_on_time_rate"], b["weighted_on_time_rate"])
    return out


def armB_vs_slack_old_on_test(doc):
    """Offline pairing: arm B (risk selector) vs slack_old, using stored arrays."""
    det = doc["_detail"]
    out = {}
    for case in ("S2", "S3"):
        out[case] = _pairs(det["rl_armB_risksel"][case]["per_seed"],
                           det["baseline_slack_old"][case]["per_seed"])
        out[case]["note"] = ("post-hoc, derived offline from per-seed arrays already "
                             "stored by the single final pass; no new test rollout")
    return out


def main():
    doc = json.load(open(JSON, encoding="utf-8"))
    runs = doc["_meta"]["train_runs"]
    gpu_total = float(sum(r["gpu_seconds"] for r in runs))
    sel = runs[-1]                                   # run C = checkpoint on disk
    doc["_meta"]["gpu_train_seconds"] = round(gpu_total, 2)
    doc["_meta"]["gpu_seconds_by_run"] = {r["run"]: r["gpu_seconds"] for r in runs}
    doc["_meta"]["params"] = dict(
        net="MLP 36-128-128 (tanh) -> 13 action logits + 1 state value = 23,054 params",
        optimizer="Adam, lr=%.4g" % sel["lr"],
        entropy="%.4g annealed linearly to 0 over %d epochs" % (sel["ent0"],
                                                               sel["ent_epochs"]),
        advantage="reward-to-go minus learned value, normalised per batch",
        episodes_per_epoch="%d sampled rollouts x %d cases x %d train seeds = %d "
                           "trajectories/epoch" % (sel["reps"], len(R.CASES),
                                                   len(R.SEED_TRAIN),
                                                   sel["reps"] * len(R.CASES)
                                                   * len(R.SEED_TRAIN)),
        epochs_per_arm={a: sel["arms"][a]["best_epoch"] for a in sel["arms"]},
        early_stop="validation score must improve within %d epochs" % sel["patience"],
        action_grid=doc["_meta"]["action_grid"],
        selection="best validation score across runs A-C; run C checkpoint evaluated "
                  "on test once",
    )
    doc["_meta"]["hyperparameters"] = [{k: v for k, v in r.items()
                                       if k not in ("arms", "note")} for r in runs]

    doc["_detail"]["val_level_curve"] = val_level_curves()
    doc["_detail"]["greedy_action_hist"] = greedy_histograms()
    doc["_detail"]["val_paired_armA"] = val_pairing_primary()
    doc["_detail"]["posthoc_armB_vs_slack_old"] = armB_vs_slack_old_on_test(doc)

    curves = {a: [(p["epoch"], p["score"]) for p in c["curve"][::5]]
              for a, c in doc["_progress"]["curves"].items()}
    doc["_detail"]["learning_curve_val"] = {a: dict(best_epoch=doc["_progress"]
                                                  ["curves"][a]["best_epoch"],
                                                  best_score=doc["_progress"]
                                                  ["curves"][a]["best_score"],
                                                  points=curves[a])
                                           for a in curves}

    R.write_json(JSON, doc)

    v = doc["verdict"]
    print("enriched %s (%.1f KB)" % (JSON, os.path.getsize(JSON) / 1024.0))
    print("gpu_train_seconds=%.1f over runs %s" % (gpu_total, list(doc["_meta"]
                                                                  ["gpu_seconds_by_run"])))
    for arm in ("slack", "risk"):
        print("greedy hist %-5s %s" % (arm, {c: doc["_detail"]["greedy_action_hist"][arm][c]
                                            ["hist"] for c in R.CASES}))
    for case in ("S2", "S3"):
        p = doc["paired"][case]
        print("primary %s delta %+.4f CI95 %.4f lower %+.4f n_pos %d/%d"
              % (case, p["delta_mean"], p["ci95"], p["lower"], p["n_pos"], p["n"]))
        q = doc["_detail"]["val_paired_armA"][case]
        print("   val  %s delta %+.4f CI95 %.4f lower %+.4f" % (case, q["delta_mean"],
                                                               q["ci95"], q["lower"]))
        r2 = doc["_detail"]["posthoc_armB_vs_slack_old"][case]
        print("   armB(test) %s delta %+.4f CI95 %.4f lower %+.4f" % (case,
                                                                     r2["delta_mean"],
                                                                     r2["ci95"],
                                                                     r2["lower"]))
    print("P3RL %s S2_delta=%+.4f S3_delta=%+.4f"
          % ("PASS" if v["passes"] else "FAIL",
             doc["paired"]["S2"]["delta_mean"], doc["paired"]["S3"]["delta_mean"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())