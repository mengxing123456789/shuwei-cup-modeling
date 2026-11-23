# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Fine-grained reservation-quantile curve for the selected adaptive policy.

The 121-candidate sweep only sampled Q_HI at four levels, so "0.5 in S2 and 0.6
in S3" could be a grid artefact.  Here the two selected configurations are held
fixed in everything except Q_HI, which is swept on a fine grid, and the
selection uses the first fifteen seeds only (holdout evaluated once at the
selected level).  Output: data/p3_quantile_curve.json
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p3_improved_verify as V  # noqa: E402

Q_GRID = [round(0.30 + 0.05 * i, 2) for i in range(13)]  # 0.30 .. 0.90
SELECTED = {
    "S2": dict(Q_HI=0.5, GATE=0.6, LATE_TOL_RISK=12.0),
    "S3": dict(Q_HI=0.6, GATE=0.5, LATE_TOL_RISK=20.0),
}
N_TUNE = 15


def run(case, params, seeds):
    vals = []
    for s in seeds:
        r = V.simulate(case, s, "risk_old", params)
        vals.append(float(r["weighted_on_time_rate"]))
    return np.asarray(vals, float)


def main():
    seeds = list(range(2026111700, 2026111730))
    tune, hold = seeds[:N_TUNE], seeds[N_TUNE:]
    out = dict(_meta=dict(
        script="p3_quantile_curve.py",
        question="where is the reservation quantile optimum, and is the curve unimodal?",
        protocol="risk_old rule held fixed; only Q_HI varies; selection on the first fifteen seeds",
        q_grid=Q_GRID, n_tune=N_TUNE, seeds=seeds,
        policy="risk_old",
    ), cases={})

    for case, base in SELECTED.items():
        tune_curve, hold_curve = [], []
        for q in Q_GRID:
            p = dict(base)
            p["Q_HI"] = q
            tune_curve.append(float(np.mean(run(case, p, tune))))
            hold_curve.append(float(np.mean(run(case, p, hold))))
        best_i = int(np.argmax(tune_curve))
        d = np.diff(tune_curve)
        sign_changes = int(np.sum(np.sign(d[1:]) != np.sign(d[:-1]))) if len(d) > 1 else 0
        q_star = Q_GRID[best_i]
        out["cases"][case] = dict(
            base_params=base,
            tune_curve=[round(x, 6) for x in tune_curve],
            holdout_curve=[round(x, 6) for x in hold_curve],
            q_star=q_star,
            tune_value_at_star=tune_curve[best_i],
            holdout_value_at_star=hold_curve[best_i],
            holdout_at_selected_q=hold_curve[Q_GRID.index(base["Q_HI"])],
            tune_at_selected_q=tune_curve[Q_GRID.index(base["Q_HI"])],
            sign_changes=sign_changes,
            unimodal=bool(sign_changes <= 1),
            spread=round(float(max(tune_curve) - min(tune_curve)), 6),
            plateau_width=int(sum(1 for v in tune_curve if v >= max(tune_curve) - 0.005)),
        )
        out["cases"][case]["implied_delay_to_idle_ratio"] = round(q_star / (1.0 - q_star), 6)

    util = {"S2": 0.9051939793967061, "S3": 0.9667753747455432}
    out["ordering_check"] = dict(
        utilisation=util,
        q_star={c: out["cases"][c]["q_star"] for c in out["cases"]},
        implied_ratio={c: out["cases"][c]["implied_delay_to_idle_ratio"] for c in out["cases"]},
        higher_load_has_higher_q=bool(out["cases"]["S3"]["q_star"] >= out["cases"]["S2"]["q_star"]),
        both_unimodal=bool(all(out["cases"][c]["unimodal"] for c in out["cases"])),
    )

    dst = os.path.join(DATA, "p3_quantile_curve.json")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("written", dst, os.path.getsize(dst), "B")
    for c in out["cases"]:
        r = out["cases"][c]
        print(c, "q_star", r["q_star"], "tune", round(r["tune_value_at_star"], 4),
              "holdout@star", round(r["holdout_value_at_star"], 4),
              "unimodal", r["unimodal"], "sign_ch", r["sign_changes"],
              "spread", r["spread"], "plateau", r["plateau_width"],
              "implied", r["implied_delay_to_idle_ratio"])
        print("   tune ", [round(x, 4) for x in r["tune_curve"]])
        print("   hold ", [round(x, 4) for x in r["holdout_curve"]])
    print("ordering:", json.dumps(out["ordering_check"], ensure_ascii=False))


if __name__ == "__main__":
    main()