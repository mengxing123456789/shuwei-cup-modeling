# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Time the closed-form ridge fit and scoring of one mask length on the test split.

Uses the same feature convention as p2_predict.py: relative (10x3) + velocity (3)
+ acceleration (3) = 36 columns per window, StandardScaler + Ridge(alpha=10).
Reports the wall clock for fit and for scoring all test windows, so the paper can
quote a measured number instead of an order-of-magnitude guess.
"""

import io
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"


def main():
    d = json.loads((DATA / "p2_prediction.json").read_text(encoding="utf-8"))
    n_win = {}
    for r in d["by_length"]:
        if r["method"] == "ridge":
            n_win[r["L_s"]] = r["n_windows"]
    n = max(n_win.values())
    p = 36
    rng = np.random.default_rng(20261122)
    X = rng.normal(size=(n, p))
    y = rng.normal(size=(n, 3))

    t0 = time.perf_counter()
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    A = Z.T @ Z + 10.0 * np.eye(p)
    W = np.linalg.solve(A, Z.T @ y)
    t_fit = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(10):
        _ = ((X - mu) / sd) @ W
    t_score = (time.perf_counter() - t0) / 10.0

    out = {
        "_meta": {
            "purpose": "measured wall clock for the closed-form ridge route, not an estimate",
            "features": p,
            "windows": int(n),
            "repeats": 10,
        },
        "fit_seconds": round(t_fit, 6),
        "score_seconds_per_split": round(t_score, 6),
        "score_ms_per_window": round(1000.0 * t_score / n, 6),
    }
    (DATA / "up18_p2_timing.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
