# -*- coding: utf-8 -*-
"""Two independent verifications of the plant model, stored for the figure.

    python code/verify_model.py

1. Free decay: start the body at y0 = 0.01 m, v0 = 0, no force, and compare the
   envelope of the simulated peaks with exp(-zeta*wn*t).  This checks stiffness,
   mass and damping at once.
2. Transfer function: drive the model with a 1 kN sinusoid at 8 Hz for 20 s and
   read amplitude and phase over the last 10 s (the first 10 s are contaminated by
   the free response), then compare with the analytic
   H = -w^2 / (k - M w^2 + j c w) evaluated at the same frequency.

Both numbers are quoted in Section 2.5 of the paper; this script is what makes
them reproducible rather than asserted.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import model as M

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"


def _envelope(t: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ay = np.abs(y)
    pk = np.array([i for i in range(1, len(y) - 1)
                   if ay[i] >= ay[i - 1] and ay[i] > ay[i + 1]])
    return t[pk], ay[pk]


def free_decay(t_end: float = 3.0) -> dict:
    """Envelope of the free response, sampled at the reporting step and finely.

    The 0.01 s reporting step leaves only ~12 samples per 8.08 Hz period, so the
    detected peaks sit off the true extremum by a varying phase and the envelope
    ratio comes out 20 % low.  The fine grid (h = 1e-4, own RK4, no model.simulate)
    is what actually tests the damping; both are stored so the discrepancy is on
    the record instead of hidden.
    """
    wn, zeta, wd = M.natural()

    dt = M.DT
    n = int(round(t_end / dt)) + 1
    t = np.arange(n) * dt
    s = M.simulate(t, np.zeros(n), np.zeros(n), y0=0.01, v0=0.0)
    y = s["y"]
    t_pk, env = _envelope(t, y)

    h = 1e-4
    m = int(round(t_end / h))
    yf, vf = 0.01, 0.0
    keep = 100                      # store every 0.01 s of the fine run
    ts, ys = [], []
    k_eq, c_eq, m_tot = M.K_EQ, M.C_EQ, M.M_TOTAL

    def f(yy, vv):
        return vv, (-c_eq * vv - k_eq * yy) / m_tot

    for i in range(m):
        k1 = f(yf, vf)
        k2 = f(yf + h / 2 * k1[0], vf + h / 2 * k1[1])
        k3 = f(yf + h / 2 * k2[0], vf + h / 2 * k2[1])
        k4 = f(yf + h * k3[0], vf + h * k3[1])
        yf += h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        vf += h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        if i % keep == 0:
            ts.append(i * h)
            ys.append(yf)
    ts, ys = np.array(ts), np.array(ys)
    tf_pk, env_f = _envelope(ts, ys)

    def rate(tp, ev):
        span = tp[-1] - tp[0]
        return float(-np.log(ev[-1] / ev[0]) / span)

    return {
        "t": t.tolist(), "y": y.tolist(),
        "t_peak": t_pk.tolist(), "env": env.tolist(),
        "env_analytic": (0.01 * np.exp(-zeta * wn * t_pk)).tolist(),
        "t_fine": ts.tolist(), "y_fine": ys.tolist(),
        "t_peak_fine": tf_pk.tolist(), "env_fine": env_f.tolist(),
        "env_fine_analytic": (0.01 * np.exp(-zeta * wn * tf_pk)).tolist(),
        "wn": wn, "zeta": zeta, "wd": wd,
        "rate_coarse": rate(t_pk, env), "rate_fine": rate(tf_pk, env_f),
        "rate_analytic": float(zeta * wn),
        "decay_ratio": float(env[-1] / env[0]),
        "decay_analytic": float(np.exp(-zeta * wn * (t_pk[-1] - t_pk[0]))),
        "decay_ratio_fine": float(env_f[-1] / env_f[0]),
        "decay_analytic_fine": float(np.exp(-zeta * wn * (tf_pk[-1] - tf_pk[0]))),
    }


def transfer(f_hz: float = 8.0, amp_kN: float = 1.0, t_end: float = 20.0,
             t_meas: float = 10.0) -> dict:
    """Amplitude and phase of a_y for a 1 kN sinusoid at f_hz.

    The window is the last t_meas seconds.  At 8 Hz the reporting step of 0.01 s
    gives 12.5 samples per period, so a window is never an integer number of
    samples *and* cycles: assuming the textbook N/2 normalisation biases the
    amplitude by 8 % right at the resonance, which would be read as model error.
    The projection therefore solves the exact 2x2 normal equations for the pair
    (sin, cos) over the actual sample set -- closed form, no LAPACK.
    """
    dt = M.DT
    n = int(round(t_end / dt)) + 1
    t = np.arange(n) * dt
    w = 2.0 * np.pi * f_hz
    f = amp_kN * 1e3 * np.sin(w * t)
    s = M.simulate(t, f, np.zeros(n))
    a = s["a"]
    mm = t >= (t_end - t_meas)
    tt = t[mm] - t[mm][0]
    aa = a[mm]
    sn, cs = np.sin(w * tt), np.cos(w * tt)
    # least squares for aa ~ A*sin + B*cos, solved by Cramer on the 2x2 Gram
    ss, cc, sc = float(np.dot(sn, sn)), float(np.dot(cs, cs)), float(np.dot(sn, cs))
    as_, ac = float(np.dot(aa, sn)), float(np.dot(aa, cs))
    det = ss * cc - sc * sc
    A = (as_ * cc - ac * sc) / det
    B = (ac * ss - as_ * sc) / det
    amp_meas = float(np.hypot(A, B))
    ph_meas = float(np.degrees(np.arctan2(B, A)))
    par = {"M_TOTAL": M.M_TOTAL, "K_EQ": M.K_EQ, "C_EQ": M.C_EQ}
    H = -w * w / (par["K_EQ"] - par["M_TOTAL"] * w * w + 1j * par["C_EQ"] * w)
    amp_th = float(abs(H)) * amp_kN * 1e3
    ph_th = float(np.degrees(np.angle(H)))
    dph = float((ph_meas - ph_th + 180.0) % 360.0 - 180.0)
    return {"f_hz": f_hz, "t": t.tolist(), "a": a.tolist(), "f": f.tolist(),
            "amp_meas": amp_meas, "amp_th": amp_th, "phase_meas": ph_meas,
            "phase_th": ph_th, "phase_err_deg": dph, "samples_per_period": 1.0 / (f_hz * dt),
            "amp_err_pct": 100 * (amp_meas / amp_th - 1)}


def sweep(freqs=(1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0),
          amp_kN: float = 1.0, t_end: float = 20.0) -> dict:
    """Bode sweep: the same 1 kN sinusoid at several frequencies.

    Cheap (each run is 20 s of a one-DOF oscillator) and it is the only place
    where the model is compared with the analytic transfer function off the
    design point, i.e. where a wrong mass or stiffness would show up as a
    shifted resonance rather than as a constant offset.
    """
    out = {"f_hz": [], "amp_meas": [], "amp_th": [], "phase_meas": [], "phase_th": []}
    for f_hz in freqs:
        tr = transfer(f_hz=f_hz, amp_kN=amp_kN, t_end=t_end)
        out["f_hz"].append(f_hz)
        out["amp_meas"].append(tr["amp_meas"])
        out["amp_th"].append(tr["amp_th"])
        out["phase_meas"].append(tr["phase_meas"])
        out["phase_th"].append(tr["phase_th"])
    return out


def main() -> int:
    d = free_decay()
    tr = transfer()
    sw = sweep()
    print(f"free decay: zeta*wn = {d['rate_analytic']:.4f} /s; "
          f"envelope rate {d['rate_coarse']:.4f} /s at the 0.01 s reporting step, "
          f"{d['rate_fine']:.4f} /s on the 1e-4 grid "
          f"({100*(d['rate_fine']/d['rate_analytic']-1):+.2f}% vs analytic)")
    print(f"transfer @ {tr['f_hz']:.1f} Hz: {tr['amp_meas']:.2f} m/s^2/kN measured, "
          f"{tr['amp_th']:.2f} analytic ({tr['amp_err_pct']:+.1f}%); phase "
          f"{tr['phase_meas']:.2f} vs {tr['phase_th']:.2f} deg")
    for i, f_hz in enumerate(sw["f_hz"]):
        print(f"  {f_hz:5.1f} Hz  amp {sw['amp_meas'][i]:7.2f} / {sw['amp_th'][i]:7.2f}"
              f"  phase {sw['phase_meas'][i]:8.2f} / {sw['phase_th'][i]:8.2f}")
    (OUT / "verify.json").write_text(
        json.dumps({"decay": d, "transfer": tr, "sweep": sw}, indent=1), encoding="utf-8")
    print(f"saved {OUT / 'verify.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
