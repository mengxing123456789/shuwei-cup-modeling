# -*- coding: utf-8 -*-
"""Q1: build the lateral model and evaluate the two prescribed cases of scenario 1.

(1) actuator off, disturbance of scenario 1 -> curves and index.
(2) actuator on, angles exactly as scenario 1 gives them -> curves and index.

The second case is where a careless answer loses points: the provided angle
sequence is *not* a suppression design.  Driven with the sign that follows from
the force law, it raises the index from 49.3 to 205.9 -- 4.2x worse than doing
nothing -- because the angles are in phase with the disturbance rather than
opposed to it.  We report that, then audit the two places it could hide:

  * the sign convention (F_act = +sum or -sum of the reaction);
  * the rotation sense (two groups counter-rotating, as the statement says,
    versus co-rotating).

Both are printed with their index so the paper can state which convention it
adopted and what the alternative would have given, instead of silently picking
the flattering one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402

DATA = Path(r"C:\Users\29900\Downloads\AsterLink\Problem A：Data.xlsx")
OUT = Path(__file__).resolve().parents[1] / "data"


def main() -> int:
    d = M.load_scenarios(str(DATA))
    t, f1, th1 = d["t"], d["F1"], d["theta1"]
    wn, zeta, wd = M.natural(d["params"])
    print(f"model: M={M.M_TOTAL:.0f} kg (2000 body + 8x100 added), k={M.K_EQ:.0f} N/m, "
          f"c={M.C_EQ:.0f} N s/m")
    print(f"  wn={wn:.4f} rad/s = {wn/2/np.pi:.4f} Hz, zeta={zeta:.5f}, "
          f"decay tau=1/(zeta*wn)={1/(zeta*wn):.2f} s")

    # ---------------- (1) actuator off
    r1 = M.simulate(t, f1)
    I1 = M.vibration_index(t, r1["a"])
    print(f"\n(1) actuator off:  y_pp={np.ptp(r1['y'])*1e3:.2f} mm  "
          f"a_pp={np.ptp(r1['a']):.2f} m/s^2  y_rms={np.sqrt((r1['y']**2).mean())*1e3:.2f} mm  "
          f"I={I1:.3f}")

    # ---------------- (2) actuator on, angles as given
    om, al, raw = M.angles_to_rates(th1, M.DT)
    print(f"\n(2) angles as given: |omega|max={np.abs(om).max():.2f} rad/s "
          f"({100*np.abs(om).max()/M.OMEGA_MAX:.1f}% of 100), "
          f"|alpha|max={np.abs(al).max():.1f} rad/s^2 ({100*np.abs(al).max()/M.ALPHA_MAX:.1f}% of 5000)")
    print(f"    raw differences without projection: |omega|max={np.abs(raw).max():.2f}, "
          f"|alpha_raw|max={np.abs(np.gradient(raw, M.DT, axis=0)).max():.1f} "
          f"(projection active: {not np.allclose(om, raw)})")

    fa = M.actuator_force(th1, om, al, sign=1.0)
    r2 = M.simulate(t, f1, fa)
    I2 = M.vibration_index(t, r2["a"])
    r2m = M.simulate(t, f1, -fa)
    I2m = M.vibration_index(t, r2m["a"])
    print(f"    sign +1 (adopted): I={I2:.3f}   |F_act|max={np.abs(fa).max()/1e3:.2f} kN  "
          f"F_act_rms={np.sqrt((fa**2).mean())/1e3:.2f} kN")
    print(f"    sign -1          : I={I2m:.3f}")
    print(f"    -> the prescribed angles make it {I2/I1:.2f}x worse than no actuator "
          f"({I2m/I1:.2f}x under the opposite sign)")

    # convention audit: co-rotating groups would emit a different line
    ths = np.column_stack([th1[:, 0], th1[:, 0], th1[:, 2], th1[:, 2]])
    oms, als, _ = M.angles_to_rates(ths, M.DT)
    fas = M.actuator_force(ths, oms, als, sign=1.0)
    I3 = M.vibration_index(t, M.simulate(t, f1, fas)["a"])
    print(f"    co-rotating reading of the same angles: I={I3:.3f} -> the statement's "
          f"counter-rotating reading is the one used")

    # index of the disturbance lines for the record
    T = t[-1] - t[0]
    spec = {}
    for hz in (5.0, 9.0):
        w = 2 * np.pi * hz
        a_ = 2 * np.trapezoid(f1 * np.sin(w * t), t) / T
        b_ = 2 * np.trapezoid(f1 * np.cos(w * t), t) / T
        spec[hz] = {"amp": float(np.hypot(a_, b_)), "phase": float(np.arctan2(-a_, b_))}
    print(f"\nscenario 1 disturbance lines: 5 Hz {spec[5.0]['amp']/1e3:.2f} kN "
          f"@{np.degrees(spec[5.0]['phase']):.1f} deg, 9 Hz {spec[9.0]['amp']/1e3:.2f} kN "
          f"@{np.degrees(spec[9.0]['phase']):.1f} deg; rms={np.sqrt((f1**2).mean())/1e3:.2f} kN")

    res = {
        "natural_hz": wn / 2 / np.pi, "zeta": zeta, "decay_tau_s": 1 / (zeta * wn),
        "I_off": I1, "y_off": r1["y"].tolist(), "a_off": r1["a"].tolist(),
        "y_pp_off_mm": float(np.ptp(r1["y"]) * 1e3), "a_pp_off": float(np.ptp(r1["a"])),
        "I_on": I2, "y_on": r2["y"].tolist(), "a_on": r2["a"].tolist(), "fa_on": fa.tolist(),
        "I_on_negative_sign": I2m, "I_on_corotating": I3,
        "y_pp_on_mm": float(np.ptp(r2["y"]) * 1e3), "a_pp_on": float(np.ptp(r2["a"])),
        "omega_max": float(np.abs(om).max()), "alpha_max": float(np.abs(al).max()),
        "omega_raw_max": float(np.abs(raw).max()),
        "f_act_max_kN": float(np.abs(fa).max() / 1e3),
        "f_act_rms_kN": float(np.sqrt((fa ** 2).mean()) / 1e3),
        "f_dist_rms_kN": float(np.sqrt((f1 ** 2).mean()) / 1e3),
        "worse_by": float(I2 / I1),
        "scenario1_lines": {str(k): v for k, v in spec.items()},
        "t": t.tolist(), "f1": f1.tolist(), "theta1": th1.tolist(),
        "omega1": om.tolist(), "alpha1": al.tolist(),
    }
    p = OUT / "q1.json"
    p.write_text(json.dumps(res), encoding="utf-8")
    print(f"\nwrote {p} ({p.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())