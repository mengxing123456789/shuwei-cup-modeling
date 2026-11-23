#!/usr/bin/env python
"""The award papers' reading: force ~ sin(theta), not cos(theta).

If the eccentric block's angle is measured from the x axis (the papers say "angle
with the x-axis"), the lateral component is sin(theta). That is a 90 degree
reference shift, and it changes whether the supplied table helps or hurts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import model as M  # noqa: E402

XLSX = Path(r"C:\Users\29900\Downloads\AsterLink\Problem A：Data.xlsx")


def main() -> int:
    sc = M.load_scenarios(XLSX)
    t, f1, th = sc["t"], sc["F1"], sc["theta1"]
    om, al, _ = M.angles_to_rates(th, 0.01, M.ALPHA_MAX, M.OMEGA_MAX)
    out = {}
    for mass in (2800.0, 2000.0):
        par = {"M_TOTAL": mass}
        base = M.vibration_index(t, M.simulate(t, f1, np.zeros_like(f1), par)["a"])
        rows = {"baseline": round(base, 3)}
        for name, fn in (
            ("sin+", lambda: 2 * M.M_ECC * M.RADIUS * ((om ** 2) * np.sin(th)).sum(axis=1)),
            ("sin-", lambda: -2 * M.M_ECC * M.RADIUS * ((om ** 2) * np.sin(th)).sum(axis=1)),
            ("papers 4mr", lambda: 4 * M.M_ECC * M.RADIUS * ((om ** 2) * np.sin(th)).sum(axis=1)),
            ("papers 4mr-", lambda: -4 * M.M_ECC * M.RADIUS * ((om ** 2) * np.sin(th)).sum(axis=1)),
            ("cos+-group", lambda: 2 * M.M_ECC * M.RADIUS
             * (((om ** 2) * np.cos(th))[:, :2].sum(axis=1)
                - ((om ** 2) * np.cos(th))[:, 2:].sum(axis=1))),
        ):
            fa = fn()
            rows[name] = round(M.vibration_index(
                t, M.simulate(t, f1, fa, par)["a"]), 3)
        out[f"M{mass:.0f}"] = rows
        print(f"M={mass:.0f}  " + "  ".join(f"{k}={v:11.3f}" for k, v in rows.items()))
    p = ROOT / "data" / "q1_sin.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())