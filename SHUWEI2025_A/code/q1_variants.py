# -*- coding: utf-8 -*-
"""Question 1 under every reasonable reading of the same angle table.

The statement says the eccentric mass "forms an angle theta with the x-axis",
which leaves two things open: which axis the transverse force is measured on
(cos vs sin of theta) and which of the four columns belongs to which group.
This script measures all of them so the paper can report a conclusion that is
robust to the reading, instead of one that depends on a silent convention.

    python code/q1_variants.py     ->  data/q1_variants.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import model as M

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(r"C:\Users\29900\Downloads\AsterLink\Problem A：Data.xlsx")
OUT = ROOT / "data" / "q1_variants.json"

READINGS = ("cos+", "cos-", "sin+", "sin-", "cos0", "sin0", "swap", "alpha+")


def force(t: np.ndarray, th: np.ndarray, om: np.ndarray, al: np.ndarray,
          reading: str) -> np.ndarray:
    """Total y-force for one reading of the angle table.

    With theta measured from the *lateral* (y) axis the mass sits at
    y = r cos(theta), so the reaction on the body is  m r (omega^2 cos + alpha sin).
    With theta measured from the *forward* (x) axis, as the statement's wording
    allows, y = r sin(theta) and the reaction is  m r (omega^2 sin - alpha cos).
    Getting the alpha term's trig wrong here is worth a factor of several on the
    index, so both are written out instead of sharing one expression.
    """
    kk = M.M_ECC * M.RADIUS
    cols = th[:, [1, 0, 3, 2]] if reading == "swap" else th
    if reading.startswith("sin"):
        g = 2.0 * kk * (om ** 2 * np.sin(cols) - al * np.cos(cols))
    elif reading == "alpha+":
        g = 2.0 * kk * (om ** 2 * np.cos(cols) - al * np.sin(cols))
    else:                                   # cos+, cos-
        g = 2.0 * kk * (om ** 2 * np.cos(cols) + al * np.sin(cols))
    if reading.endswith("0"):               # published form: alpha term dropped
        g = 2.0 * kk * om ** 2 * (np.sin(cols) if reading.startswith("sin") else np.cos(cols))
    sign = -1.0 if reading.endswith("-") else 1.0
    return sign * g.sum(axis=1)


def main() -> int:
    sc = M.load_scenarios(str(DATA))
    t, f1, th = sc["t"], sc["F1"], sc["theta1"]
    om, al, _ = M.angles_to_rates(th, M.DT, M.ALPHA_MAX, M.OMEGA_MAX)
    res = {"I_off": M.vibration_index(t, M.simulate(t, f1)["a"]),
           "omega_max": float(np.abs(om).max()),
           "alpha_max": float(np.abs(al).max()),
           "readings": {}}
    for r in READINGS:
        fa = force(t, th, om, al, r)
        a = M.simulate(t, f1, fa)["a"]
        res["readings"][r] = {"I": M.vibration_index(t, a),
                              "f_max_kN": float(np.abs(fa).max() / 1e3),
                              "pct": 100 * (M.vibration_index(t, a) / res["I_off"] - 1)}
    print(f"actuator off: I={res['I_off']:.3f}  |omega|={res['omega_max']:.2f}  "
          f"|alpha|={res['alpha_max']:.1f}")
    for r, v in res["readings"].items():
        print(f"  {r:7s} I={v['I']:9.3f}  ({v['pct']:+7.2f}%)  |F|max={v['f_max_kN']:7.2f} kN")
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
