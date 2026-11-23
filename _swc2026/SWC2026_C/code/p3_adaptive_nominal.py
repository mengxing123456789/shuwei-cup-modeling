
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Paired comparison of the deployed policy against the stored baselines at the
nominal mapping (alpha=1.0, beta=0.5), seed by seed."""
import os
import json, os, sys
import numpy as np
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TRI = pd.read_csv(os.path.join(DATA, "p3_stochastic_trials.csv"))
MINE = pd.read_csv(os.path.join(DATA, "p3_adaptive_b.csv"))
MINE = MINE[(MINE.alpha == 1.0) & (MINE.beta == 0.5)]


def ci95(x):
    x = np.asarray(x, float)
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


out = []
for case in ("S1", "S2", "S3"):
    m = MINE[MINE.case == case].set_index("seed").weighted_on_time_rate
    row = dict(case=case, mine=float(m.mean()))
    for pol in ("slack_old", "risk_fusion", "slack_fusion"):
        b = TRI[(TRI.case == case) & (TRI.policy == pol)].set_index("seed").weighted_on_time_rate
        d = m - b.reindex(m.index)
        row[pol] = float(b.mean()); row["vs_" + pol] = float(d.mean()); row["ci_" + pol] = float(ci95(d))
    out.append(row)
j = json.load(open(os.path.join(DATA, "p3_adaptive_stats.json"), encoding="utf-8"))
j["nominal_vs_baselines_paired"] = out
open(os.path.join(DATA, "p3_adaptive_stats.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(j, ensure_ascii=False, indent=1))
for r in out:
    print(r["case"], "mine", round(r["mine"], 4), "slack", round(r["slack_old"], 4),
          "d", round(r["vs_slack_old"], 4), "±", round(r["ci_slack_old"], 4),
          "| risk", round(r["risk_fusion"], 4), "d", round(r["vs_risk_fusion"], 4),
          "±", round(r["ci_risk_fusion"], 4))