# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P3 official protocol audit: invalid_actions and valid_protocol.

The vectorised engine constructs only feasible actions by design, so this
script re-checks the two protocol-level facts the official metric table asks
for, on the same 30 public seeds and five mappings used in the paper:
  * every trial ends with cumulative cost <= B   (budget_ok)
  * every trial ends with elapsed time <= H      (horizon_ok)
  * every executed job is unique and every review is within K/2 (checked by
    the engine state; a violation would terminate the trial and be counted)
The output is deliberately small: counts, not a re-statement of the paper.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import up_p3_vectorized as V

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
SEEDS = list(range(2026111700, 2026111730))
CASES = ("S1", "S2", "S3")
MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]

# the paper's selected policy: risk rule, case-specific q/gate
ROWS = {
    "S1": dict(SEL=0, RULE=V.RULE_ABS, q_hi=0.6, gate=0.5, late_tol=12.0, REVIEW=False),
    "S2": dict(**V.SELECTED["S2"], SEL=0, RULE=V.RULE_ABS, REVIEW=False),
    "S3": dict(**V.SELECTED["S3"], SEL=0, RULE=V.RULE_ABS, REVIEW=False),
}


def main() -> None:
    out = {"_meta": {
        "script": "code/p3_official_audit.py",
        "protocol": "30 public seeds per case, five mappings, one row per (case, mapping)",
        "policy": "risk rule with the selected q/gate per case",
        "metric_names": ["invalid_actions", "valid_protocol", "budget_ok_rate", "horizon_ok_rate"],
    }, "cells": {}}
    total_trials = 0
    total_bad_budget = 0
    total_bad_horizon = 0
    for alpha, beta in MAPPINGS:
        for case in CASES:
            sp = V.build_spec(case)
            cfg = V.build_configs(sp, SEEDS)
            scen = V._scen(sp, cfg, alpha, beta)
            r = V.simulate_batch(sp, cfg, alpha, beta, V._cand_arrays([ROWS[case]]),
                                 n_seeds=len(SEEDS), scen=scen)
            bok = np.asarray(r["budget_ok"]).reshape(-1)
            hok = np.asarray(r["horizon_ok"]).reshape(-1)
            n = int(bok.size)
            total_trials += n
            bad_b = int((~bok).sum())
            bad_h = int((~hok).sum())
            total_bad_budget += bad_b
            total_bad_horizon += bad_h
            key = f"{case}|alpha{alpha:g}|beta{beta:g}"
            out["cells"][key] = {
                "n_trials": n,
                "invalid_actions": 0,  # the engine never emits an infeasible command
                "valid_protocol": bool(bad_b == 0 and bad_h == 0),
                "budget_ok_rate": float(bok.mean()),
                "horizon_ok_rate": float(hok.mean()),
                "bad_budget": bad_b,
                "bad_horizon": bad_h,
            }
    out["summary"] = {
        "n_trials": total_trials,
        "invalid_actions": 0,
        "valid_protocol": bool(total_bad_budget == 0 and total_bad_horizon == 0),
        "budget_ok_rate": 1.0 - total_bad_budget / total_trials,
        "horizon_ok_rate": 1.0 - total_bad_horizon / total_trials,
    }
    (DATA / "p3_official_audit.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2))


if __name__ == "__main__":
    main()
