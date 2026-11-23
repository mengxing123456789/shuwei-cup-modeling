# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up12_p3_full_factorial.py -- 2-level full factorial over the seven rule knobs.

The one-at-a-time sweep in up9 answers "what happens when this knob moves alone".
This script crosses every knob with every other one at two levels (2^7 = 128
corners per case), replays all 30 seeds and all five mappings on the vectorised
engine, and reports the corner distribution, the main effect of each knob and
where the frozen policy sits inside that distribution.

Output: data/up12_p3_full_factorial.json
"""
import itertools
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up2_p3_final as F

DATA = os.path.join(os.path.dirname(HERE), "data")
KEYS = ("q_hi", "gate", "late_tol", "mix", "gam", "ksk", "qsl")
LEVELS = {
    "S2": {"q_hi": (0.30, 0.60), "gate": (0.55, 0.95), "late_tol": (4.0, 20.0),
           "mix": (0.30, 0.90), "gam": (0.00, 0.25), "ksk": (0.40, 0.80),
           "qsl": (0.40, 0.80)},
    "S3": {"q_hi": (0.20, 0.45), "gate": (0.15, 0.60), "late_tol": (8.0, 28.0),
           "mix": (0.00, 0.30), "gam": (0.00, 0.50), "ksk": (0.40, 0.80),
           "qsl": (0.40, 0.80)},
}


def evaluate(case, cands):
    t0 = time.time()
    res = F.run_policy_set(cands, case, F.ALL30)
    rows = []
    for i, c in enumerate(cands):
        all30 = float(np.mean([res[m]["weighted_on_time_rate"][i].mean()
                               for m in F.MAPPINGS]))
        test = float(np.mean([res[m]["weighted_on_time_rate"][i][-5:].mean()
                              for m in F.MAPPINGS]))
        cost = float(np.mean([res[m]["cost"][i].mean() for m in F.MAPPINGS]))
        rows.append(dict(name=c["name"], levels={k: float(c[k]) for k in KEYS},
                         on_time_all30=all30, on_time_test=test, cost=cost))
    return rows, time.time() - t0


def main():
    with open(os.path.join(DATA, "up2_p3_search.json"), encoding="utf-8") as f:
        search = json.load(f)
    out = {"method": "2^7 full factorial, 30 seeds x 5 mappings, vectorised engine",
           "n_corners": 128, "cases": {}}
    for case in ("S2", "S3"):
        frozen = dict(search["frozen"][case]["params"])
        frozen["name"] = "FROZEN"
        cands = [frozen]
        meta = []
        for bits in itertools.product((0, 1), repeat=len(KEYS)):
            p = dict(frozen)
            p["name"] = "ff_" + "".join(str(b) for b in bits)
            for k, b in zip(KEYS, bits):
                p[k] = LEVELS[case][k][b]
            cands.append(p)
            meta.append(bits)
        rows, secs = evaluate(case, cands)
        base = rows[0]
        corners = rows[1:]
        for r in corners:
            r["delta_all30_pt"] = (r["on_time_all30"] - base["on_time_all30"]) * 100.0
            r["cost_ratio"] = r["cost"] / base["cost"] if base["cost"] else None
        main = {}
        for j, k in enumerate(KEYS):
            hi = [r["on_time_all30"] for r in corners if r["levels"][k] == LEVELS[case][k][1]]
            lo = [r["on_time_all30"] for r in corners if r["levels"][k] == LEVELS[case][k][0]]
            main[k] = dict(mean_high=float(np.mean(hi)), mean_low=float(np.mean(lo)),
                           main_effect_pt=float((np.mean(hi) - np.mean(lo)) * 100.0),
                           levels=list(LEVELS[case][k]))
        vals = np.array([r["on_time_all30"] for r in corners])
        order = np.argsort(vals)
        out["cases"][case] = dict(
            frozen=base, n=len(corners), wall_seconds=round(secs, 2),
            corner_mean=float(vals.mean()), corner_sd=float(vals.std(ddof=1)),
            corner_min=float(vals.min()), corner_max=float(vals.max()),
            corner_range_pt=float((vals.max() - vals.min()) * 100.0),
            frozen_percentile=float((vals < base["on_time_all30"]).mean() * 100.0),
            main_effects=main,
            best=[corners[i] for i in order[-3:][::-1]],
            worst=[corners[i] for i in order[:3]],
            corners=corners,
        )
        print(case, "frozen", round(base["on_time_all30"], 4),
              "corners min/med/max", round(vals.min(), 4),
              round(float(np.median(vals)), 4), round(vals.max(), 4),
              "range pt", round((vals.max() - vals.min()) * 100, 2),
              "frozen pct", round(out["cases"][case]["frozen_percentile"], 1),
              "secs", round(secs, 1))
        for k in KEYS:
            print("  ", k, round(main[k]["main_effect_pt"], 2))
    path = os.path.join(DATA, "up12_p3_full_factorial.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", path)


if __name__ == "__main__":
    main()