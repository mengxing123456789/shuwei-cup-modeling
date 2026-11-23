# -*- coding: utf-8 -*-
"""Q2: minimal-index design of the eccentric-mass angle curves.

Mechanism (all of it comes from the problem's own force law F = 2mr(omega^2 cos th
+ alpha sin th) applied to two counter-rotating groups per actuator):

    F_pair = 2mr w^2 [cos(wt + phi1) + cos(wt - phi2)]
           = 4mr w^2 cos(kappa) cos(wt + psi),   kappa=(phi1+phi2)/2, psi=(phi1-phi2)/2

so a pair emits ONE spectral line whose amplitude is set by kappa (0..202 kN per
actuator, 404 kN for the pair of actuators) and whose phase is set by psi.
Cancelling the 8 Hz line is therefore a closed-form problem, not an optimisation.

Three designs are produced and compared, because the comparison is the answer:

  A  static line cancellation: kappa, psi constant over the window.
     I = 85.98.  The line is cancelled to 0.1% but the projection residual (6.9%
     rms) still rings a suspension whose zeta is 0.0127.

  D  tracked cancellation (adopted): kappa(t), psi(t) from a CAUSAL 0.25 s moving
     window, so the pair follows the drift of the line.  The phase is unwrapped
     and enters theta directly, so |omega| and |alpha| stay inside the limits by
     construction (measured 58 rad/s, 937 rad/s^2).  I = 13.28, i.e. 99.92% of the
     uncontrolled index gone (x1225).  The window length is a genuine optimum:
     0.20 s overruns the pair (I = 20.4, |omega| = 69), 0.40 s lags the drift
     (I = 64.3), so the sweep in this script is U-shaped rather than monotone.

  N  "neutral angle" alpha channel (rejected): park at theta = pi/2 so
     cos th = 0 and the group becomes a linear force source alpha*2mr*sin(th),
     then alpha = -F/(8mr).  Exact in principle and broad-band, but the double
     integration of the request makes theta travel; the low-frequency content of
     the disturbance demands an angle swing of F/(8mr w^2), which is 0.04 rad at
     8 Hz but 0.6 rad at 0.5 Hz, and there sin(th) starts to vanish.  Measured
     I = 311 (band-limited, sigma = 0.06 s) -- worse than A.  Kept in the code
     because "we tried the elegant thing and measured why it fails" is the
     honest version.

Two bugs found on the way, kept as comments because they are easy to repeat:
 (1) the phase of a projected sinusoid is atan2(-a, b), not atan2(-b, a);
 (2) same-direction groups give a pair force proportional to -sin(theta1 - d/2)
     and cannot be amplitude-tuned without a pi jump, which is not the mechanism.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402

DATA = Path(r"C:\Users\29900\Downloads\AsterLink\Problem A：Data.xlsx")
LINES = (3.0, 5.0, 8.0)
F_LINE = 8.0
WIN = 25                      # causal window, 0.25 s = 2.0 cycles at 8 Hz (swept: U-shaped)
OUT = Path(__file__).resolve().parents[1] / "data"
GAIN = 4 * 2 * M.M_ECC * M.RADIUS          # 8mr = 160 N s^2 (alpha-channel gain)
CAP_PAIR = 4 * M.M_ECC * M.RADIUS * (2 * np.pi * F_LINE) ** 2   # 202 kN per actuator pair
CAP_LINE = 2 * CAP_PAIR                    # 404 kN: both actuators emit the same line


# ------------------------------------------------------------------ spectral fit
def project(t: np.ndarray, f: np.ndarray, freqs=LINES) -> dict:
    """Project a signal onto DC + a few sinusoids; f ~ sum A_k cos(w_k t + psi_k).

    The window is 10 s, an integer number of cycles for every line used, so the
    basis is orthogonal and the coefficients are plain integrals -- no least
    squares, no linear algebra (this environment's BLAS aborts the interpreter on
    LAPACK calls such as np.linalg.lstsq: exit code 0xC06D007F, empty output).
    """
    T = t[-1] - t[0]
    out = {"dc": float(np.trapezoid(f, t) / T), "lines": {}}
    for hz in freqs:
        w = 2 * np.pi * hz
        a = 2 * np.trapezoid(f * np.sin(w * t), t) / T
        b = 2 * np.trapezoid(f * np.cos(w * t), t) / T
        out["lines"][hz] = {"a": float(a), "b": float(b),
                            "amp": float(np.hypot(a, b)),
                            "phase": float(np.arctan2(-a, b))}
    return out


def line_signal(t: np.ndarray, spec: dict, hz: float) -> np.ndarray:
    p = spec["lines"][hz]
    return p["amp"] * np.cos(2 * np.pi * hz * t + p["phase"])


# ------------------------------------------------------------------ helpers
def movavg_past(x: np.ndarray, n: int) -> np.ndarray:
    """Mean of the last n samples; the first samples average over what exists."""
    k = np.ones(n) / n
    y = np.convolve(x, k, mode="full")[:len(x)]
    out = np.empty_like(y)
    out[:n - 1] = y[:n - 1] / np.arange(1, n)[:min(len(y), n - 1)]
    out[n - 1:] = y[n - 1:]
    return out


def lp_gauss(x: np.ndarray, dt: float, sigma: float) -> np.ndarray:
    """Zero-phase Gaussian low-pass (edges reflected), for the rejected design N."""
    n = max(3, int(round(6 * sigma / dt)) | 1)
    k = np.arange(n) - (n - 1) / 2
    g = np.exp(-0.5 * (k * dt / sigma) ** 2)
    g /= g.sum()
    pad = n // 2
    xp = np.concatenate([x[pad:0:-1], x, x[-2:-pad - 2:-1]])
    return np.convolve(xp, g, mode="same")[pad:pad + len(x)]


def pair_from_kappa_psi(t: np.ndarray, kappa, psi, hz: float = F_LINE) -> np.ndarray:
    """Four angle columns (two counter-rotating pairs) from amplitude/phase knobs."""
    w = 2 * np.pi * hz
    th1 = w * t + (kappa + psi)
    th2 = -w * t + (kappa - psi)
    return np.column_stack([th1, th2, th1, th2])


# ------------------------------------------------------------------ design A
def design_static(t: np.ndarray, spec: dict) -> tuple[np.ndarray, dict]:
    amp = spec["lines"][F_LINE]["amp"]
    psi = spec["lines"][F_LINE]["phase"] + np.pi
    kappa = float(np.arccos(np.clip(amp / CAP_LINE, 0.0, 1.0)))
    return pair_from_kappa_psi(t, kappa, psi), {"kappa_deg": float(np.degrees(kappa)),
                                                "psi_deg": float(np.degrees(psi) % 360),
                                                "load_pct": float(100 * amp / CAP_LINE)}


# ------------------------------------------------------------------ design D
def design_tracked(t: np.ndarray, f: np.ndarray, win: int = WIN,
                   gain_scale: float = 1.0, phase_offset: float = 0.0) -> tuple[np.ndarray, dict]:
    """Amplitude/phase of the 8 Hz line from a causal moving window."""
    w = 2 * np.pi * F_LINE
    a = 2 * movavg_past(f * np.sin(w * t), win) * gain_scale
    b = 2 * movavg_past(f * np.cos(w * t), win) * gain_scale
    amp, psi = np.hypot(a, b), np.unwrap(np.arctan2(-a, b))
    kappa = np.arccos(np.clip(amp / CAP_LINE, 0.0, 1.0))
    theta = pair_from_kappa_psi(t, kappa, psi + np.pi + phase_offset)
    return theta, {"amp_max_kN": float(amp.max() / 1e3),
                   "amp_min_kN": float(amp.min() / 1e3)}


# ------------------------------------------------------------------ design N (rejected)
def design_neutral(t: np.ndarray, f: np.ndarray, sigma: float = 0.06) -> tuple[np.ndarray, dict]:
    """Park at pi/2 and drive the alpha channel.  Kept to reproduce the rejection."""
    req = -(f - lp_gauss(f, M.DT, sigma))
    al = (req / GAIN)[:, None] * np.ones((1, 4))
    om = np.zeros_like(al)
    om[1:] = np.cumsum(0.5 * (al[1:] + al[:-1]) * M.DT, axis=0)
    th = (np.pi / 2) + np.zeros_like(al)
    th[1:] += np.cumsum(0.5 * (om[1:] + om[:-1]) * M.DT, axis=0)
    return th, {"alpha_max": float(np.abs(al).max()), "omega_max": float(np.abs(om).max()),
                "theta_dev_max": float(np.abs(th - np.pi / 2).max())}


# ------------------------------------------- designs F/G (rejected: see the paper)
def _demod(t: np.ndarray, f: np.ndarray, hz: float, win: int) -> tuple[np.ndarray, np.ndarray]:
    w = 2 * np.pi * hz
    a = 2 * movavg_past(f * np.sin(w * t), win)
    b = 2 * movavg_past(f * np.cos(w * t), win)
    return np.hypot(a, b), np.unwrap(np.arctan2(-a, b))


def _cap(hz: float) -> float:
    return 4 * M.M_ECC * M.RADIUS * (2 * np.pi * hz) ** 2


def design_split(t: np.ndarray, f: np.ndarray, hz_a: float = F_LINE, hz_b: float = 5.0,
                 win_a: int = WIN, win_b: int = 40, track_b: bool = False) -> tuple[np.ndarray, dict]:
    """One pair per line: actuator 1 does hz_a, actuator 2 does hz_b."""
    amp_a, psi_a = _demod(t, f, hz_a, win_a)
    ka = np.arccos(np.clip(amp_a / _cap(hz_a), 0.0, 1.0))
    pa = pair_from_kappa_psi(t, ka, psi_a + np.pi, hz=hz_a)
    if track_b:
        amp_b, psi_b = _demod(t, f, hz_b, win_b)
    else:
        d = project(t, f, [hz_b])["lines"][hz_b]
        amp_b, psi_b = np.full_like(t, d["amp"]), np.full_like(t, d["phase"])
    kb = np.arccos(np.clip(amp_b / _cap(hz_b), 0.0, 1.0))
    pb = pair_from_kappa_psi(t, kb, psi_b + np.pi, hz=hz_b)
    theta = np.column_stack([pa[:, 0], pa[:, 1], pb[:, 2], pb[:, 3]])
    return theta, {"kappa_a_deg": float(np.degrees(ka[win_a:].mean())),
                   "kappa_b_deg": float(np.degrees(kb[win_b:].mean())),
                   "cap_a_kN": float(_cap(hz_a) / 1e3), "cap_b_kN": float(_cap(hz_b) / 1e3)}


def run(t: np.ndarray, f2: np.ndarray, theta: np.ndarray) -> dict:
    om, al, _ = M.angles_to_rates(theta, M.DT)
    fa = M.actuator_force(theta, om, al)
    s = M.simulate(t, f2, fa)
    return {"theta": theta, "om": om, "al": al, "fa": fa, "y": s["y"], "a": s["a"],
            "I": M.vibration_index(t, s["a"])}


def main() -> int:
    d = M.load_scenarios(str(DATA))
    t, f2 = d["t"], d["F2"]
    wn, zeta, wd = M.natural(d["params"])
    base = M.simulate(t, f2)
    I0 = M.vibration_index(t, base["a"])
    spec = project(t, f2)

    print(f"natural: wn={wn:.4f} rad/s = {wn/2/np.pi:.4f} Hz, zeta={zeta:.5f}, "
          f"wd/2pi={wd/2/np.pi:.4f} Hz")
    print(f"uncontrolled: y_pp={np.ptp(base['y'])*1e3:.2f} mm, a_pp={np.ptp(base['a']):.2f} m/s^2, "
          f"I={I0:.3f}")
    for hz in LINES:
        p = spec["lines"][hz]
        print(f"  line {hz:>4.1f} Hz: amp={p['amp']/1e3:7.3f} kN  phase={np.degrees(p['phase']):8.2f} deg")
    rec = sum((line_signal(t, spec, hz) for hz in LINES), np.zeros_like(f2)) + spec["dc"]
    print(f"projection residual = {100*np.sqrt(((rec-f2)**2).mean())/np.sqrt((f2**2).mean()):.2f}% of rms")

    res = {"natural_hz": wn / 2 / np.pi, "zeta": zeta, "wd_hz": wd / 2 / np.pi,
           "lines": {str(k): dict(v) for k, v in spec["lines"].items()},
           "I_uncontrolled": I0,
           "y_pp_uncontrolled_mm": float(np.ptp(base["y"]) * 1e3),
           "a_pp_uncontrolled": float(np.ptp(base["a"])),
           "y_uncontrolled": base["y"].tolist(), "a_uncontrolled": base["a"].tolist()}

    # References, not "floors": what the index would be if a design cancelled the
    # 8 Hz line perfectly and instantaneously (unattainable: it needs the future),
    # or if it removed all three lines and left only the projection residual.
    ref8 = M.vibration_index(t, M.simulate(t, f2 - line_signal(t, spec, F_LINE))["a"])
    refall = M.vibration_index(t, M.simulate(t, rec)["a"])
    res["I_ref_line8"] = ref8
    res["I_ref_residual"] = refall
    print(f"reference (8 Hz line removed outright, unattainable): I={ref8:.3f};  "
          f"all three lines removed: I={refall:.3f}")

    for name, theta, info in (("A", *design_static(t, spec)),):
        r = run(t, f2, theta)
        print(f"\n[A] static line cancellation (kappa={info['kappa_deg']:.2f} deg):")
        print(f"    |omega|max={np.abs(r['om']).max():.2f}/100  |alpha|max={np.abs(r['al']).max():.1f}/5000"
              f"  |F|max={np.abs(r['fa']).max()/1e3:.2f} kN")
        print(f"    I = {r['I']:.3f}  ({100*(1-r['I']/I0):.2f}% below uncontrolled)")
        res["A"] = {"I": r["I"], "reduction_pct": 100 * (1 - r["I"] / I0), **info,
                    "omega_max": float(np.abs(r["om"]).max()),
                    "alpha_max": float(np.abs(r["al"]).max()),
                    "f_max_kN": float(np.abs(r["fa"]).max() / 1e3),
                    "theta": r["theta"].tolist(), "y": r["y"].tolist(), "a": r["a"].tolist(),
                    "fa": r["fa"].tolist()}

    theta_d, info_d = design_tracked(t, f2)
    rd = run(t, f2, theta_d)
    print(f"\n[D] tracked cancellation, causal {WIN/100:.2f} s window "
          f"(line amplitude {info_d['amp_min_kN']:.2f}..{info_d['amp_max_kN']:.2f} kN):")
    print(f"    |omega|max={np.abs(rd['om']).max():.2f}/100  |alpha|max={np.abs(rd['al']).max():.1f}/5000"
          f"  |F|max={np.abs(rd['fa']).max()/1e3:.2f} kN")
    print(f"    y_pp={np.ptp(rd['y'])*1e3:.2f} mm (was {np.ptp(base['y'])*1e3:.2f}), "
          f"a_pp={np.ptp(rd['a']):.2f} m/s^2 (was {np.ptp(base['a']):.2f})")
    print(f"    I = {rd['I']:.3f}  ({100*(1-rd['I']/I0):.2f}% below uncontrolled, "
          f"x{I0/rd['I']:.0f})   [ideal 8 Hz removal would give {ref8:.3f}]")
    res["D"] = {"I": rd["I"], "reduction_pct": 100 * (1 - rd["I"] / I0),
                "ratio": I0 / rd["I"], **info_d,
                "omega_max": float(np.abs(rd["om"]).max()),
                "alpha_max": float(np.abs(rd["al"]).max()),
                "f_max_kN": float(np.abs(rd["fa"]).max() / 1e3),
                "f_rms_kN": float(np.sqrt((rd["fa"] ** 2).mean()) / 1e3),
                "y_pp_mm": float(np.ptp(rd["y"]) * 1e3),
                "a_pp": float(np.ptp(rd["a"])),
                "theta": rd["theta"].tolist(), "y": rd["y"].tolist(), "a": rd["a"].tolist(),
                "fa": rd["fa"].tolist()}

    # specificity: the same design force, applied to the disturbance with the 8 Hz
    # line removed, must NOT suppress anything — it then acts as a fresh excitation.
    f_no_line = f2 - line_signal(t, spec, F_LINE)
    d_spec = float(M.vibration_index(t, M.simulate(t, f_no_line, rd["fa"])["a"]))
    res["I_D_on_removed_line"] = d_spec
    print(f"    specificity: same force on the line-free disturbance -> I={d_spec:.2f}")

    theta_n, info_n = design_neutral(t, f2)
    rn = run(t, f2, theta_n)
    print(f"\n[N] parked alpha channel, band-limited (sigma=0.06 s): I = {rn['I']:.2f} "
          f"({100*(1-rn['I']/I0):.2f}%)  |theta-pi/2|max={info_n['theta_dev_max']:.3f} rad -> rejected")
    res["N"] = {"I": rn["I"], "reduction_pct": 100 * (1 - rn["I"] / I0), **info_n,
                "theta": rn["theta"].tolist(), "y": rn["y"].tolist(), "a": rn["a"].tolist()}

    # F/G: one pair per line.  Measured here because the modulation index of a
    # half-capacity pair is far higher (kappa ~ 85 deg vs 72 deg), so the same
    # 0.2% amplitude error leaks several kN into the neighbouring lines.
    theta_f, info_f = design_split(t, f2)
    rf = run(t, f2, theta_f)
    print(f"\n[F] one pair per line (8 Hz tracked kappa={info_f['kappa_a_deg']:.2f} deg, "
          f"5 Hz static kappa={info_f['kappa_b_deg']:.2f} deg): I={rf['I']:.3f} "
          f"({100 * (1 - rf['I'] / I0):.2f}%)  |F|max={np.abs(rf['fa']).max()/1e3:.2f} kN")
    res["F"] = {"I": rf["I"], "reduction_pct": 100 * (1 - rf["I"] / I0), **info_f,
                "omega_max": float(np.abs(rf["om"]).max()),
                "alpha_max": float(np.abs(rf["al"]).max()),
                "f_max_kN": float(np.abs(rf["fa"]).max() / 1e3),
                "theta": rf["theta"].tolist(), "y": rf["y"].tolist(), "a": rf["a"].tolist(),
                "fa": rf["fa"].tolist()}

    theta_g, info_g = design_split(t, f2, track_b=True)
    rg = run(t, f2, theta_g)
    print(f"[G] both lines tracked (kappa_5={info_g['kappa_b_deg']:.2f} deg): I={rg['I']:.3f} "
          f"({100 * (1 - rg['I'] / I0):.2f}%)  |F|max={np.abs(rg['fa']).max()/1e3:.2f} kN")
    res["G"] = {"I": rg["I"], "reduction_pct": 100 * (1 - rg["I"] / I0), **info_g,
                "omega_max": float(np.abs(rg["om"]).max()),
                "alpha_max": float(np.abs(rg["al"]).max()),
                "f_max_kN": float(np.abs(rg["fa"]).max() / 1e3)}

    # window sweep: the design's only tuning knob
    sweep = []
    for win in (15, 20, 25, 30, 40, 50, 60, 80, 100):
        th, _ = design_tracked(t, f2, win)
        r = run(t, f2, th)
        sweep.append({"win_s": win / 100, "I": r["I"],
                      "omega_max": float(np.abs(r["om"]).max()),
                      "alpha_max": float(np.abs(r["al"]).max()),
                      "f_max_kN": float(np.abs(r["fa"]).max() / 1e3)})
        print(f"  win={win/100:.2f}s  I={r['I']:8.2f}  |omega|={sweep[-1]['omega_max']:6.2f} "
              f"|alpha|={sweep[-1]['alpha_max']:7.1f}  |F|={sweep[-1]['f_max_kN']:6.2f} kN")
    res["window_sweep"] = sweep

    # robustness: amplitude scale and phase offset of the realised line
    sens = []
    for gs in (0.8, 0.9, 1.0, 1.1, 1.2):
        for dphi in (-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20):
            th, _ = design_tracked(t, f2, WIN, gain_scale=gs, phase_offset=dphi)
            r = run(t, f2, th)
            sens.append({"scale": gs, "dphi_rad": dphi, "dphi_deg": float(np.degrees(dphi)),
                         "I": r["I"]})
    res["sensitivity"] = sens
    lo = min(sens, key=lambda s: s["I"])
    hi = max(sens, key=lambda s: s["I"])
    print(f"\nsensitivity: best I={lo['I']:.2f} (scale={lo['scale']}, dphi={lo['dphi_deg']:.0f} deg); "
          f"worst I={hi['I']:.2f} (scale={hi['scale']}, dphi={hi['dphi_deg']:.0f} deg)")
    for s in sens:
        if s["scale"] == 1.0:
            print(f"  nominal amplitude: dphi={s['dphi_deg']:5.0f} deg -> I={s['I']:8.2f}")

    p = OUT / "q2.json"
    p.write_text(json.dumps(res), encoding="utf-8")
    print(f"\nwrote {p} ({p.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())