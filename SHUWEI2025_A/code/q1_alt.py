#!/usr/bin/env python
"""The published solutions' convention, reproduced.

Three knobs separate their numbers from ours: the eccentric mass is not added to
the body, the angle is referenced to the x axis (lateral component = sin theta,
and the alpha term dropped), and the damping is very slightly below the table
value.  With those three the award papers' Question 1 pair and their scenario-2
baseline are reproduced to about a quarter of a percent:

    published 95.3699 -> 57.9738 (-39.21%) and 211.253
    ours      95.480  -> 57.910  (-39.35%) and 210.756

The damping knob is c = 3500 N s/m, i.e. 0.97 c0.  Before the integrator was
fixed the same target needed c = 1.13 c0; the difference is entirely the old
integrator's 8% amplitude error at resonance, which is why the third knob is
reported as "a few percent" rather than as a fitted constant.
"""
from __future__ import annotations

def _corpus_root():
    """语料根：MM_CORPUS_ROOT > 向上找含 corpus/problems 的一级 > 旧 AsterLink 兜底。"""
    import os as _os
    from pathlib import Path as _P
    env = _os.environ.get("MM_CORPUS_ROOT")
    if env:
        return env
    for _probe in _P(__file__).resolve().parents:
        if (_probe / "corpus" / "problems").is_dir():
            return str(_probe / "corpus")
    return r"C:\Users\29900\Downloads\AsterLink"

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import model as M  # noqa: E402

XLSX = Path(_corpus_root() + r"\Problem A：Data.xlsx")


def main() -> int:
    sc = M.load_scenarios(XLSX)
    t, f1, th, f2 = sc["t"], sc["F1"], sc["theta1"], sc["F2"]
    om, al, _ = M.angles_to_rates(th, 0.01, M.ALPHA_MAX, M.OMEGA_MAX)
    # x-axis reference: lateral component is sin(theta); 8 blocks, 4 groups.
    # The published form keeps only the omega^2 term (the alpha term is dropped),
    # which is the fourth knob and the one that makes the given sequence look good.
    fa = 2 * M.M_ECC * M.RADIUS * ((om ** 2) * np.sin(th)).sum(axis=1)
    out = {}
    for name, mass, damp in (("ours_2800_3600", 2800.0, 3600.0),
                             ("theirs_2000_3600", 2000.0, 3600.0),
                             ("theirs_2000_3500", 2000.0, 3500.0)):
        par = {"M_TOTAL": mass, "C_EQ": damp}
        wn, zeta, _ = M.natural(par)
        i1_off = M.vibration_index(t, M.simulate(t, f1, np.zeros_like(f1), par)["a"])
        i1_on = M.vibration_index(t, M.simulate(t, f1, fa, par)["a"])
        i2 = M.vibration_index(t, M.simulate(t, f2, np.zeros_like(f2), par)["a"])
        out[name] = {
            "wn_Hz": round(wn / 2 / np.pi, 4), "zeta": round(zeta, 5),
            "Q1_off": round(i1_off, 3), "Q1_on_sin": round(i1_on, 3),
            "Q1_pct_sin": round(100 * (1 - i1_on / i1_off), 2),
            "Q2_off": round(i2, 3),
        }
        print(f"{name:18s} " + "  ".join(f"{k}={v}" for k, v in out[name].items()))
    p = ROOT / "data" / "q1_alt.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())