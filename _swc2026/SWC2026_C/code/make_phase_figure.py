# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""make_phase_figure.py -- phase diagram of the P3 reservation.

Sweeps the service multiplier alpha and the residual quantile q of the
adaptive-quantile reservation (absorption rule, slack selection), on the two
loaded cases, with the official 30 seeds.  Two quantities are mapped: the
weighted on-time rate and the mean cost.  The picture is the empirical form of
Propositions 2 and 3: the reservation is a pure liability once it exceeds the
realised service time -- the rate falls in q while the cost does not fall with
it -- whereas the service law moves the rate monotonically.

Outputs
-------
figures/fig9_phase.png          four heat maps (S2/S3 x rate/cost)
data/phase_diagram.json         full grid + axis summaries
"""
import json
import os
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V
from common import DATA, PROJ, write_json

SEEDS = V.SEEDS
CASES = ("S2", "S3")
ALPHAS = [0.75, 1.00, 1.25, 1.50]
QS = [round(0.30 + 0.05 * i, 2) for i in range(13)]


def run_cell(case, alpha, beta=0.5):
    sp = V.build_spec(case)
    cfg = V.build_configs(sp, SEEDS)
    scen = V._scen(sp, cfg, alpha, beta)
    cands = [dict(SEL=1, RULE=V.RULE_ABS, q_hi=q, gate=0.50,
                  late_tol=12.0, REVIEW=False, name="q%.2f" % q) for q in QS]
    r = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays(cands),
                         n_seeds=len(SEEDS), scen=scen)
    return (np.asarray(r["weighted_on_time_rate"], float),
            np.asarray(r["cost"], float))


def main():
    t0 = time.time()
    grid_rate = {}
    grid_cost = {}
    for case in CASES:
        mr = np.zeros((len(ALPHAS), len(QS)))
        mc = np.zeros((len(ALPHAS), len(QS)))
        for ia, a in enumerate(ALPHAS):
            rate, cost = run_cell(case, a)
            mr[ia, :] = rate.mean(axis=1)
            mc[ia, :] = cost.mean(axis=1)
            print("[phase] %s alpha=%.2f done %.1fs" % (case, a, time.time() - t0),
                  flush=True)
        grid_rate[case] = mr
        grid_cost[case] = mc

    # -------- figure -------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(6.6, 4.6), constrained_layout=True)
    panels = [("S2", "rate"), ("S3", "rate"), ("S2", "cost"), ("S3", "cost")]
    for ax, (case, metric) in zip(axes.ravel(), panels):
        m = grid_rate[case] if metric == "rate" else grid_cost[case]
        cmap = "viridis" if metric == "rate" else "magma"
        im = ax.imshow(m, aspect="auto", origin="lower", cmap=cmap)
        _xt = list(range(0, len(QS), 2))
        ax.set_xticks(_xt)
        ax.set_xticklabels(["%.2f" % QS[i] for i in _xt], fontsize=7.4, rotation=0)
        ax.set_yticks(range(len(ALPHAS)))
        ax.set_yticklabels(["%.2f" % a for a in ALPHAS], fontsize=7.6)
        ax.set_xlabel("reservation quantile $q$", fontsize=8.4)
        ax.set_ylabel(r"service multiplier $\alpha$", fontsize=8.0)
        ax.set_title("Case %s: %s" % (case, "on-time rate" if metric == "rate" else "mean cost"),
                     fontsize=9.2)
        cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
        cb.ax.tick_params(labelsize=7.2)
        cb.set_label("on-time rate" if metric == "rate" else "mean cost", fontsize=7.6)

    out = os.path.join(PROJ, "figures", "fig9_phase.png")
    fig.savefig(out, dpi=400, bbox_inches="tight")
    print("saved", out)

    payload = dict(
        alphas=ALPHAS, qs=QS,
        grid_rate={c: [[float(x) for x in row] for row in grid_rate[c]] for c in CASES},
        grid_cost={c: [[float(x) for x in row] for row in grid_cost[c]] for c in CASES},
        spread_alpha={c: float(grid_rate[c].mean(axis=1).max() - grid_rate[c].mean(axis=1).min())
                      for c in CASES},
        spread_q={c: float(grid_rate[c].mean(axis=0).max() - grid_rate[c].mean(axis=0).min())
                  for c in CASES},
        rate_drop_q30_q90={c: float(grid_rate[c][:, 0].mean() - grid_rate[c][:, -1].mean())
                           for c in CASES},
        mean_by_alpha={c: {("%.2f" % a): float(grid_rate[c][i].mean())
                           for i, a in enumerate(ALPHAS)} for c in CASES},
        mean_by_q={c: {("%.2f" % q): float(grid_rate[c][:, i].mean())
                       for i, q in enumerate(QS)} for c in CASES},
        seconds=time.time() - t0,
        source="code/make_phase_figure.py",
        note="slack selection with absorption reserve, beta=0.5, official seeds 2026111700..2026111729",
    )
    write_json(os.path.join(DATA, "phase_diagram.json"), payload)
    print(json.dumps({c: dict(spread_alpha=payload["spread_alpha"][c],
                              spread_q=payload["spread_q"][c],
                              drop_q=payload["rate_drop_q30_q90"][c]) for c in CASES}, indent=1))


if __name__ == "__main__":
    main()
