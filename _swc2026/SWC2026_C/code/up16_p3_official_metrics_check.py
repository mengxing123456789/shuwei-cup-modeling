# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Verify the three newly added official measures (reserved idle, overrun,
censoring) against the untouched stochastic engine, on the arm that engine can
actually replay: risk_old with reviews allowed at Q_HI=0.70, GATE=0.5,
LATE_TOL_RISK=12 (the arm the bit-exactness gate already pins)."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import p3_stochastic_schedule as STO  # noqa: E402
import up_p3_vectorized as V  # noqa: E402

SEEDS = list(range(2026111700, 2026111730))
ARM = dict(SEL=0, RULE=V.RULE_ABS, q_hi=0.70, gate=0.5, late_tol=12.0, REVIEW=True)
FIELDS = ("reviews", "reserved_idle_s", "observed_overrun_s", "censored_units",
          "elapsed_s", "cost", "weighted_on_time_rate")

out = {}
for case in ("S2", "S3"):
    sp = V.build_spec(case)
    cfg = V.build_configs(sp, SEEDS)
    vec = V.simulate_batch(sp, cfg, 1.0, 0.5, V._cand_arrays([ARM]),
                           n_seeds=len(SEEDS), scen=V._scen(sp, cfg, 1.0, 0.5))
    ref = [STO.simulate(case, sd, "risk_old", reviews_allowed=True) for sd in SEEDS]
    row = {}
    for f in FIELDS:
        a = np.array([float(r[f]) for r in ref], float)
        b = np.array(vec[f], float)
        row[f] = dict(max_abs=float(np.abs(a - b).max()),
                      n_exact=int((np.abs(a - b) == 0).sum()), n=int(a.size))
    out[case] = row

worst = max(v["max_abs"] for c in out.values() for v in c.values())
print(json.dumps(out, indent=1))
print("\nWORST max_abs over all fields/cases:", worst)
print("GATE (<=1e-9):", "PASS" if worst <= 1e-9 else "FAIL")

path = os.path.join(os.path.dirname(HERE), "data", "up16_p3_official_metrics_check.json")
with open(path, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(dict(_meta=dict(purpose="bit-exact check of the three official measures "
                                      "added to the vectorised engine",
                              arm=ARM, seeds=SEEDS,
                              reference="code/p3_stochastic_schedule.simulate"),
                   cases=out, worst_max_abs=worst,
                   passed=bool(worst <= 1e-9)), fh, indent=1)
print("wrote", path)
