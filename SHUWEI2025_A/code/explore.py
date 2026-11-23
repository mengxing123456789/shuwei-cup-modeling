# -*- coding: utf-8 -*-
"""Quick look: what the given angle signal actually is, and what Q1 scores.

Run:  python code/explore.py
Writes nothing; prints only. (Kept out of the deliverable chain on purpose.)
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

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402

DATA = Path(_corpus_root() + r"\Problem A：Data.xlsx")
d = M.load_scenarios(str(DATA))
t, F1, th, F2 = d["t"], d["F1"], d["theta1"], d["F2"]

print("params:", {k: v for k, v in list(d["params"].items())[:6]})
wn, zeta, wd = M.natural()
print(f"wn={wn:.2f} rad/s ({wn/2/np.pi:.2f} Hz)  zeta={zeta:.4f}  wd={wd:.2f}")

base = M.simulate(t, F1)
print(f"Q1(1) no actuator : y_pp={np.ptp(base['y']):.4f} m  a_pp={np.ptp(base['a']):.1f} m/s2  "
      f"I={M.vibration_index(t, base['a']):.3f}")

# spectrum of the disturbance and of the given angle rates
for nm, sig in (("F1", F1), ("F2", F2)):
    S = np.abs(np.fft.rfft(sig - sig.mean()))
    f = np.fft.rfftfreq(len(sig), M.DT)
    top = np.argsort(S)[-4:][::-1]
    print(nm, "peaks:", [(round(float(f[i]), 2), round(float(S[i] / S.max()), 3)) for i in top])

om, al, raw = M.angles_to_rates(th)
print("omega: max|.|=%.3f (raw %.3f)  rms=%.2f  |alpha| max=%.1f (raw %.1f)"
      % (np.abs(om).max(), np.abs(raw).max(), np.sqrt((om ** 2).mean()), np.abs(al).max(),
         np.abs(np.gradient(raw, M.DT)).max()))
print("rate projection moved omega by rms %.3f, max %.3f"
      % (np.sqrt(((om - raw) ** 2).mean()), np.abs(om - raw).max()))
S = np.abs(np.fft.rfft(om[:, 0] - om[:, 0].mean()))
f = np.fft.rfftfreq(len(om), M.DT)
top = np.argsort(S)[-3:][::-1]
print("omega spectrum peaks (group 1):", [(round(float(f[i]), 2), round(float(S[i] / S.max()), 3)) for i in top])

for sg in (+1.0, -1.0):
    fa = M.actuator_force(th, om, al, sign=sg)
    r = M.simulate(t, F1, fa)
    print(f"Q1(2) sign={sg:+.0f}: |F_act|max={np.abs(fa).max()/1e3:.1f} kN  "
          f"y_pp={np.ptp(r['y']):.4f} m  a_pp={np.ptp(r['a']):.1f}  "
          f"I={M.vibration_index(t, r['a']):.3f}")

fa = M.actuator_force(th, om, al)
print("F_act rms %.1f kN   F_dist rms %.1f kN" % (np.sqrt((fa ** 2).mean()) / 1e3,
                                                   np.sqrt((F1 ** 2).mean()) / 1e3))