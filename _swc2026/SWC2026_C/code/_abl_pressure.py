
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Single-factor ablation: workload pressure from the raw point estimate vs from
the calibrated predictive median (+1.5 s bias correction). Reservation always
uses the calibrated distribution."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import p3_adaptive as A

SEEDS = A.SEEDS[:10]
eta = lambda r: r["weighted_on_time_rate"]

for case in ("S2", "S3"):
    for al in (1.5, 1.0, .75):
        cur = np.mean([eta(A.simulate(case, s, A.CAL_INFO, al, .5, alpha_mode="fixed")) for s in SEEDS])
        alt = np.mean([eta(A.simulate(case, s, A.CAL_INFO, al, .5, alpha_mode="fixed",
                                      pressure_pred=True)) for s in SEEDS])
        base = np.mean([eta(A.simulate(case, s, "model_quant", al, .5, alpha_mode="fixed",
                                       pressure_pred=True)) for s in SEEDS])
        print(f"{case} a={al:>4}  pressure=median {cur:.4f}   pressure=pred {alt:.4f}   "
              f"model_quant+predpressure {base:.4f}")