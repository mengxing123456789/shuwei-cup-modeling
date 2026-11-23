# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
"""Sensitivity of the Part II economic optimum to the cost coefficients.

The body claims the economic conclusion is re-run over a grid of cost
coefficients.  This script makes that claim true: it re-solves

    J(T) = R(T) + lambda * (C0 / T + C1)

on the measured ridge error curve for a grid of (C0, C1, lambda) and reports
how far the argmin moves and how often it leaves the interior of the measured
domain.  Nothing here re-fits a predictor; only the priced decision moves.

Output: data/up21_p2_cost_sweep.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

C0_GRID = [0.10, 0.25, 0.50, 1.00, 2.00]
C1_GRID = [0.05, 0.10, 0.20, 0.40]
LAM_GRID = [0.25, 0.50, 1.00, 2.00, 4.00]
# Same search grid as code/p2_predict.py: 0.10..2.50 step 0.05, then restricted to
# the measured domain.  Keeping the grid identical is what makes the baseline cell
# reproduce the published optimum instead of drifting by one grid step.
STEP = 0.05
DOMAIN = (0.2, 1.0)


def main() -> int:
    p2 = json.loads((DATA / "p2_prediction.json").read_text(encoding="utf-8"))
    rows = sorted(
        [r for r in p2["by_length"] if r["method"] == "ridge"], key=lambda r: r["L_s"]
    )
    Ts = np.array([r["L_s"] for r in rows], dtype=float)
    # by_length stores RMSE in metres; the priced rule works in centimetres.
    Rs = np.array([r["rmse"] * 100.0 for r in rows], dtype=float)

    lo, hi = DOMAIN
    grid = np.arange(lo, hi + 1e-9, STEP)
    R = np.interp(grid, Ts, Rs)

    cells = []
    for c0 in C0_GRID:
        for c1 in C1_GRID:
            for lam in LAM_GRID:
                J = R + lam * (c0 / grid + c1)
                i = int(np.argmin(J))
                cells.append(
                    dict(
                        C0=c0,
                        C1=c1,
                        lambda_per_cm=lam,
                        T_star_s=float(grid[i]),
                        rmse_cm=float(R[i]),
                        objective=float(J[i]),
                    )
                )

    tstar = np.array([c["T_star_s"] for c in cells])
    baseline = [c for c in cells if c["C0"] == 0.5 and c["C1"] == 0.2 and c["lambda_per_cm"] == 1.0][0]
    at_left = int(np.sum(np.isclose(tstar, lo)))
    at_right = int(np.sum(np.isclose(tstar, hi)))
    interior = int(len(cells) - at_left - at_right)

    # one-at-a-time moves, holding the other two coefficients at their baseline
    oat = []
    for name, values, setter in (
        ("C0", C0_GRID, lambda v: dict(C0=v, C1=0.2, lambda_per_cm=1.0)),
        ("C1", C1_GRID, lambda v: dict(C0=0.5, C1=v, lambda_per_cm=1.0)),
        ("lambda", LAM_GRID, lambda v: dict(C0=0.5, C1=0.2, lambda_per_cm=v)),
    ):
        picked = []
        for v in values:
            kw = setter(v)
            J = R + kw["lambda_per_cm"] * (kw["C0"] / grid + kw["C1"])
            picked.append(float(grid[int(np.argmin(J))]))
        oat.append(
            dict(
                knob=name,
                values=values,
                T_star_s=picked,
                span_s=float(max(picked) - min(picked)),
            )
        )

    out = {
        "_meta": {
            "script": "code/up21_p2_cost_sweep.py",
            "source": "data/p2_prediction.json by_length[method=ridge]",
            "formula": "J(T)=R(T)[cm] + lambda*(C0/T + C1)",
            "domain_s": [lo, hi],
            "grid_step_s": STEP,
            "n_cells": len(cells),
            "note": (
                "Only the priced decision is re-solved; the predictor and its measured "
                "error curve are untouched, and T* is restricted to the measured domain."
            ),
        },
        "baseline": dict(
            C0=0.5, C1=0.2, lambda_per_cm=1.0,
            T_star_s=baseline["T_star_s"], rmse_cm=baseline["rmse_cm"],
            objective=baseline["objective"],
        ),
        "cells": cells,
        "summary": {
            "n_cells": len(cells),
            "T_star_min_s": float(tstar.min()),
            "T_star_max_s": float(tstar.max()),
            "T_star_span_s": float(tstar.max() - tstar.min()),
            "T_star_median_s": float(np.median(tstar)),
            "n_at_left_edge": at_left,
            "n_at_right_edge": at_right,
            "n_interior": interior,
            "frac_interior": interior / len(cells),
            "frac_within_005_of_baseline": float(
                np.mean(np.abs(tstar - baseline["T_star_s"]) <= 0.05)
            ),
            "one_at_a_time": oat,
        },
    }
    (DATA / "up21_p2_cost_sweep.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8", newline="\n"
    )
    s = out["summary"]
    print(f"cells {s['n_cells']}  T* {s['T_star_min_s']:.2f}..{s['T_star_max_s']:.2f} s  "
          f"span {s['T_star_span_s']:.2f}  interior {s['n_interior']}  "
          f"within 0.05 s of baseline {s['frac_within_005_of_baseline']*100:.1f}%")
    for row in oat:
        print(f"  {row['knob']:6s} span {row['span_s']:.2f} s  {row['T_star_s']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
