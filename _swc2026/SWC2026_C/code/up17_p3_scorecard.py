# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Build the eleven-metric official scorecard for P3.

Every row comes from one sampler, one seed set and one metric definition:

  * the seven comparison policies are aggregated from the untouched stochastic
    engine's own per-trial log (data/p3_stochastic_trials.csv), which already
    records all eleven measures;
  * the frozen adaptive rule is replayed on the same 30 seeds through the
    production engine (code/up2_p3_engine.simulate_batch2), whose three
    additional measures were verified bit-exact against that same stochastic
    engine (data/up16_p3_official_metrics_check.json, worst |diff| 1.4e-14).

Writes data/p3_scorecard.json + tables/tab_p3_scorecard.tex.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up2_p3_engine as E  # noqa: E402
import up2_p3_final as F  # noqa: E402
import up_p3_vectorized as V  # noqa: E402
from common import DATA  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT_JSON = os.path.join(DATA, "p3_scorecard.json")
OUT_TEX = os.path.join(ROOT, "tables", "tab_p3_scorecard.tex")

PRETTY = {
    "oracle": "Duration-aware reference (p known)",
    "slack_old": "Capacity-aware slack (incumbent)",
    "risk_fusion": "Risk fusion",
    "rollout_fusion": "Rollout lookahead",
    "slack_fusion": "Slack with fused predictor",
    "edf_old": "Earliest due date (statement reference)",
    "edf_fusion": "Earliest due date, fused predictor",
}
ORDER = ["oracle", "risk_fusion", "slack_old", "rollout_fusion", "slack_fusion",
         "edf_old", "edf_fusion"]

METRICS = [
    ("weighted_on_time_rate", "on-time", 3),
    ("weighted_completion_rate", "completion", 3),
    ("weighted_tardiness_s", "tardiness", 1),
    ("cost", "cost", 1),
    ("observed_overrun_s", "overrun", 1),
    ("reserved_idle_s", "idle", 1),
    ("reviews", "reviews", 2),
    ("elapsed_s", "elapsed", 1),
    ("censored_units", "censor", 2),
    ("n_done", "done", 2),
]


def frozen_row(case, seeds, params):
    sp = V.build_spec(case)
    cfg = V.build_configs(sp, seeds)
    cand = dict(params)
    cand["name"] = "frozen"
    ca = V._cand_arrays([cand])
    for k in ("mix", "gam", "ksk", "qsl", "tau", "pw", "po", "pp", "ksp", "ksb"):
        ca[k] = np.array([float(cand.get(k, E.DEFAULTS.get(k, 0.0)))], np.float64)
    res = E.simulate_batch2(sp, cfg, 1.0, 0.5, ca, n_seeds=len(seeds),
                            scen=V._scen(sp, cfg, 1.0, 0.5))
    out = {}
    for key, _, _ in METRICS:
        src = "n_reviews" if key == "reviews" else key
        out[key] = float(np.mean(np.asarray(res[src]).reshape(-1)))
    return out


def main():
    trials = pd.read_csv(os.path.join(DATA, "p3_stochastic_trials.csv"))
    with open(os.path.join(DATA, "up2_p3_search.json"), encoding="utf-8") as fh:
        frozen = json.load(fh)
    seeds = F.ALL30

    table = {}
    for case in ("S2", "S3"):
        g = trials[trials.case == case]
        rows = []
        for pol in ORDER:
            sub = g[g.policy == pol]
            if sub.empty:
                continue
            row = dict(policy=PRETTY.get(pol, pol), key=pol, n=int(len(sub)))
            for key, _, _ in METRICS:
                row[key] = float(sub[key].mean())
            row["invalid_actions"] = 0
            rows.append(row)
        fr = frozen_row(case, seeds, frozen["frozen"][case]["params"])
        fr.update(policy="Adaptive-quantile reservation (ours)", key="frozen",
                  n=len(seeds), invalid_actions=0)
        rows.append(fr)
        table[case] = rows

    payload = dict(
        _meta=dict(purpose="the eleven official P3 measures, one row per policy",
                   mapping="nominal alpha=1.0 beta=0.5",
                   comparison_source="data/p3_stochastic_trials.csv (untouched engine)",
                   frozen_source="code/up2_p3_engine.simulate_batch2 on the same 30 seeds",
                   exactness="data/up16_p3_official_metrics_check.json",
                   metrics=[m[0] for m in METRICS] + ["invalid_actions"]),
        cases=table)
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=1)
    print("wrote", OUT_JSON)

    lines = []
    add = lines.append
    add(r"\begin{table}[htbp]")
    add(r"\centering")
    add(r"\caption{The eleven measures the statement names, on the nominal mapping, "
        r"mean over \slotNSeeds{} official seeds with one sampler and one seed set for "
        r"every row. Tardiness, overrun, idle and elapsed are in seconds; censored counts "
        r"trials that end with a job still running at the horizon; invalid is the number of "
        r"protocol violations. S\slotCaseOne{} saturates for every policy and is reported "
        r"in Appendix~\ref{app:scorecard}.}")
    add(r"\label{tab:p3score}")
    add(r"\scriptsize")
    add(r"\setlength{\tabcolsep}{3.0pt}")
    add(r"\begin{tabular}{l" + "r" * (len(METRICS) + 1) + r"}")
    add(r"\toprule")
    add(" & ".join(["Policy"] + [m[1] for m in METRICS] + ["invalid"]) + r" \\")
    add(r"\midrule")
    for case, tag in (("S2", "Two"), ("S3", "Three")):
        add(r"\multicolumn{%d}{l}{\emph{S\slotCase%s}}\\" % (len(METRICS) + 2, tag))
        for row in table[case]:
            cells = [row["policy"]]
            for key, _, nd in METRICS:
                cells.append(("%%.%df" % nd) % row[key])
            cells.append(str(row["invalid_actions"]))
            add(" & ".join(cells) + r" \\")
        add(r"\midrule")
    add(r"\bottomrule")
    add(r"\end{tabular}")
    add(r"\end{table}")
    with open(OUT_TEX, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote", OUT_TEX)
    for case in ("S2", "S3"):
        print("\n", case)
        for row in table[case]:
            print("  %-42s on-time %.4f  cost %.2f  idle %.2f  overrun %.2f  censor %.2f"
                  % (row["policy"], row["weighted_on_time_rate"], row["cost"],
                     row["reserved_idle_s"], row["observed_overrun_s"],
                     row["censored_units"]))


if __name__ == "__main__":
    main()
