# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up9_p3_sensitivity.py -- one-at-a-time sensitivity of the frozen P3 rule.

The frozen policies were selected by a joint search over rule sub-parameters.
This script freezes every parameter at its selected value and moves ONE parameter
at a time, then re-runs the same vectorised replay on all 30 seeds and the five
mappings. It does not re-select anything: it answers "how much of the gain depends
on this knob, holding the others fixed".

Output: data/up9_p3_sensitivity.json
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up2_p3_final as F
import up2_p3_engine as E

DATA = os.path.join(os.path.dirname(HERE), "data")
KEYS = ("q_hi", "gate", "late_tol", "mix", "gam", "ksk", "qsl", "tau")


def variants(case, base):
    """Two one-at-a-time values per knob, clipped to the legal box.

    Duplicates of the frozen value are dropped, so every row is a real move.
    """
    out = []
    def add(key, label, v):
        cur = float(base.get(key, 0.0))
        if abs(float(v) - cur) > 1e-12:
            out.append((case, key, label.format(v), v))

    q = float(base["q_hi"])
    add("q_hi", "q_hi={:.2f}", max(0.20, q - 0.15))
    add("q_hi", "q_hi={:.2f}", min(0.90, q + 0.15))
    g = float(base["gate"])
    add("gate", "gate={:.2f}", max(0.10, g - 0.20))
    add("gate", "gate={:.2f}", min(0.95, g + 0.20))
    l = float(base["late_tol"])
    add("late_tol", "late_tol={:.1f}", max(1.0, l - 8.0))
    add("late_tol", "late_tol={:.1f}", l + 8.0)
    m = float(base.get("mix", 0.0))
    add("mix", "mix={:.2f}", max(0.0, m - 0.30))
    add("mix", "mix={:.2f}", min(1.0, m + 0.30))
    gm = float(base.get("gam", 0.0))
    if gm > 0:
        add("gam", "gam={:.2f}", 0.0)
        add("gam", "gam={:.2f}", gm + 0.25)
    else:
        add("gam", "gam={:.2f}", 0.25)
        add("gam", "gam={:.2f}", 0.50)
    k = float(base.get("ksk", 0.60))
    add("ksk", "ksk={:.2f}", max(0.0, k - 0.20))
    add("ksk", "ksk={:.2f}", min(1.0, k + 0.20))
    qs = float(base.get("qsl", 0.60))
    add("qsl", "qsl={:.2f}", max(0.20, qs - 0.20))
    add("qsl", "qsl={:.2f}", min(0.90, qs + 0.20))
    if base.get("REVIEW", False):
        for v in (0.01, 0.05):
            add("tau", "tau={:.2f}", v)
    return out


def main():
    with open(os.path.join(DATA, "up2_p3_search.json"), encoding="utf-8") as f:
        search = json.load(f)
    frozen = search["frozen"]

    result = {"cases": {}, "method": "one-at-a-time around frozen params; all 30 seeds; 5 mappings",
              "n_seeds": len(F.ALL30), "n_mappings": len(F.MAPPINGS)}
    for case in ("S2", "S3"):
        base = dict(frozen[case]["params"])
        base["name"] = "FROZEN"
        cands = [base]
        meta = [("FROZEN", None, None)]
        for (c, key, label, val) in variants(case, base):
            p = dict(base)
            p[key] = val
            p["name"] = label
            cands.append(p)
            meta.append((label, key, val))

        res = F.run_policy_set(cands, case, F.ALL30)
        ref = res[F.MAPPINGS[0]]["weighted_on_time_rate"][0]
        rows = []
        for i, (name, key, val) in enumerate(meta):
            all30 = float(np.mean([res[m]["weighted_on_time_rate"][i].mean()
                                   for m in F.MAPPINGS]))
            test = float(np.mean([res[m]["weighted_on_time_rate"][i][-5:].mean()
                                  for m in F.MAPPINGS]))
            cost = float(np.mean([res[m]["cost"][i].mean() for m in F.MAPPINGS]))
            rows.append(dict(name=name, key=key, value=val,
                             on_time_all30=all30, on_time_test=test, cost=cost))
        base_row = rows[0]
        for r in rows:
            r["delta_all30_pt"] = (r["on_time_all30"] - base_row["on_time_all30"]) * 100.0
            r["delta_test_pt"] = (r["on_time_test"] - base_row["on_time_test"]) * 100.0
            r["cost_ratio"] = r["cost"] / base_row["cost"] if base_row["cost"] else None
        result["cases"][case] = {
            "frozen": base_row,
            "rows": rows,
            "max_abs_delta_all30_pt": max(abs(r["delta_all30_pt"]) for r in rows),
        }
        print(case, "frozen", round(base_row["on_time_all30"], 6),
              "max |delta|", round(result["cases"][case]["max_abs_delta_all30_pt"], 3))

    out = os.path.join(DATA, "up9_p3_sensitivity.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    print("wrote", out)


if __name__ == "__main__":
    main()