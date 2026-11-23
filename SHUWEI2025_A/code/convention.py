"""Convention audit: how much of the gap to the award papers is the mass/damping convention?

The award papers mostly take the vehicle mass as 2000 kg (the body alone) and report a
Scenario-2 uncontrolled index around 210-226 m^2/s^4.  This script recomputes the same
two indices under four conventions, and then solves for the damping coefficient that
would be needed to land on 211.253 with a body-only mass.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M                                          # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"
XLSX = Path(_corpus_root() + r"\Problem A：Data.xlsx")


def indices(mass: float, c: float) -> dict:
    par = {"M_TOTAL": float(mass), "C_EQ": float(c)}
    sc = M.load_scenarios(str(XLSX))
    t = sc["t"]
    wn, zeta, _ = M.natural(par)
    r1 = M.simulate(t, sc["F1"], np.zeros_like(t), par)
    r2 = M.simulate(t, sc["F2"], np.zeros_like(t), par)
    return {"m_total": par["M_TOTAL"], "c": c, "wn_hz": wn / 2 / np.pi, "zeta": zeta,
            "I_scen1": float(M.vibration_index(t, r1["a"])),
            "a_rms_scen2": float(np.sqrt((r2["a"] ** 2).mean())),
            "I_scen2": float(M.vibration_index(t, r2["a"])),
            "y_pp_scen2_mm": float(np.ptp(r2["y"]) * 1e3)}


def main() -> int:
    rows = [indices(m, c) for m in (2800.0, 2000.0) for c in (3600.0, 7200.0, 14400.0)]
    for r in rows:
        print(f"M={r['m_total']:6.0f} c={r['c']:7.0f}  wn={r['wn_hz']:5.2f} Hz "
              f"zeta={r['zeta']:.4f}  I1={r['I_scen1']:9.3f}  "
              f"a_rms2={r['a_rms_scen2']:7.2f}  I2={r['I_scen2']:10.2f}")

    # what damping makes the body-only model report the award-paper number?
    target = 211.253

    def err(c: float) -> float:
        return indices(2000.0, c)["I_scen2"] - target

    lo, hi = 3600.0, 4.0e5
    if err(lo) * err(hi) > 0:
        print(f"no bracket: err(lo)={err(lo):.1f} err(hi)={err(hi):.1f}")
        best = None
    else:
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if err(lo) * err(mid) <= 0:
                hi = mid
            else:
                lo = mid
        best = indices(2000.0, 0.5 * (lo + hi))
        print(f"to report I2=211.253 with M=2000 kg you need c={best['c']:.0f} N.s/m "
              f"(= {best['c'] / M.C_EQ:.1f} x the given damping), zeta={best['zeta']:.3f}")
    # the two designs are body-mass independent (their force follows from the disturbance),
    # so the same actuator forces replay under the award-paper convention.
    q2 = json.loads((DATA / "q2.json").read_text(encoding="utf-8"))

    def replay(key: str, mass: float) -> float:
        par = {"M_TOTAL": float(mass)}
        sc = M.load_scenarios(str(XLSX))
        fa = np.array(q2[key]["fa"])
        r = M.simulate(sc["t"], sc["F2"], fa, par)
        return float(M.vibration_index(sc["t"], r["a"]))

    replay_out = {}
    for key in ("A", "D", "F"):
        m2000 = replay(key, 2000.0)
        replay_out[key] = {"M2800": q2[key]["I"], "M2000": m2000}
        red = 100 * (1 - m2000 / 217.53)
        print("design " + key + ": I(M=2800)=" + f"{q2[key]['I']:.3f}"
              + "  I(M=2000)=" + f"{m2000:.3f}" + f"  ({red:.2f}% below 217.53)")
    out = {"rows": rows, "match_211": best, "target": target, "replay": replay_out}
    (DATA / "convention.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {DATA / 'convention.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())