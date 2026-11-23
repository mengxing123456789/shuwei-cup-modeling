# -*- coding: utf-8 -*-
"""Transport-delay sweep for design D, kept as its own script so the numbers in
the paper have a reproducible source.

A transport delay in the command path is modelled the only way the data allow:
the realised crank sequence is shifted later by k samples, and the body is
re-integrated with the shifted sequence.  That is exactly what a controller that
computes the angles k samples late would emit, because design D's angles are a
pure function of the disturbance history.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DELAYS_MS = (5, 10, 20, 30, 40)


def main() -> int:
    sc = M.load_scenarios(str(DATA / "Problem A：Data.xlsx"))
    t, f2 = sc["t"], sc["F2"]
    dt = float(t[1] - t[0])
    q2 = json.loads((DATA / "q2.json").read_text(encoding="utf-8"))
    th = np.array(q2["D"]["theta"], dtype=float)
    n = th.shape[0]

    rows = []
    for ms in DELAYS_MS:
        k = int(round(ms / 1e3 / dt))
        shifted = np.empty_like(th)
        if k == 0:
            shifted[:] = th
        else:
            shifted[:k] = th[0]
            shifted[k:] = th[:-k]
        om, al, _ = M.angles_to_rates(shifted, dt)
        fa = M.actuator_force(shifted, om, al)
        r = M.simulate(t, f2, fa)
        I = M.vibration_index(t, r["a"])
        rows.append({"delay_ms": ms, "samples": k, "I": I,
                     "reduction_pct": 100 * (1 - I / q2["I_uncontrolled"])})
        print(f"  delay {ms:3d} ms ({k:2d} samples): I_h={I:10.3f}  "
              f"({100*(1-I/q2['I_uncontrolled']):7.2f}%)")

    out = {"note": "design D command shifted later by k samples",
           "I_nominal": q2["D"]["I"], "rows": rows,
           "I_uncontrolled": q2["I_uncontrolled"]}
    p = DATA / "q3_delay.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {p} ({p.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
