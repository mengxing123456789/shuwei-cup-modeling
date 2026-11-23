
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Ablation: cap × tail_guard on the stress cells (alpha=1.5 / 0.75, S2, S3)."""
import sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import p3_adaptive as A

SEEDS10 = A.SEEDS[:10]
rows = []
for case in ("S2", "S3"):
    for (al, be) in ((1.5, .5), (.75, .5), (1.0, .5)):
        for cap in (True, False):
            for tg in (True, False):
                vals = [A.simulate(case, sd, A.CAL_INFO, alpha=al, beta=be, reviews=False,
                                   alpha_mode="fixed", cap=cap, tail_guard=tg)
                        for sd in SEEDS10]
                eta = float(np.mean([v["weighted_on_time_rate"] for v in vals]))
                comp = float(np.mean([v["weighted_completion_rate"] for v in vals]))
                cost = float(np.mean([v["cost"] for v in vals]))
                res = float(np.mean([v["reserved_s"] for v in vals]))
                rows.append(dict(case=case, alpha=al, beta=be, cap=cap, tg=tg,
                                 eta=round(eta, 4), comp=round(comp, 4),
                                 cost=round(cost, 2), res=round(res, 1)))
for r in rows:
    print(r["case"], r["alpha"], "cap" if r["cap"] else "---", "tg" if r["tg"] else "--",
          "eta", r["eta"], "comp", r["comp"], "cost", r["cost"], "res", r["res"])
import os
with open(r"data\p3_adaptive_cap_ablation.json", "w",
          encoding="utf-8", newline="\n") as f:
    json.dump(dict(_meta=dict(seeds=10, info="unit_resid", alpha_mode="fixed",
                              design="cap x tail_guard on the stress cells"),
                   rows=rows), f, ensure_ascii=False, indent=1)
print(json.dumps(rows))