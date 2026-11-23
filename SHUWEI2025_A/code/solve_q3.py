# -*- coding: utf-8 -*-
"""Q3: cancellation when the only sensor is the lateral accelerometer.

The reconstruction route (F_d = M a - F_act + c v + k y, with y, v integrated from
a) was tried first and is in the log as a rejected design: the integrals drift, the
bias closes a positive loop through the command, and the index diverges
(I = 1493 after the sign fix, estimator error growing without bound).  It is exact
only when the parameters are exact and the integration never drifts -- not a
scheme one can defend for a vehicle.

What is used instead is acceleration feedback: the measured a is demodulated at the
line frequency into a phasor, and the commanded line phasor is corrected by the
force imbalance that this acceleration implies,

    F_cmd <- F_cmd - mu * (E / H(j w0)),        H = 1 / (k - M w0^2 + j c w0)

i.e. a filtered-x Newton step.  H comes from the *given* parameters, so the loop
knows the phase its own force produces; the demodulation window is exactly two
periods, which is why the phasor estimate carries no bias.  The loop is a
contraction: parameter error changes the gain and the convergence rate, not the
stability, and none of the runs below diverge.

The cost the question cares about is the settling time: nothing can be concluded
before two periods are in the window, so the first 0.25 s runs uncontrolled.  Both
the full-window index and the index over the controlled span are reported.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402
import solve_q2 as Q  # noqa: E402

DATA = Path(r"C:\Users\29900\Downloads\AsterLink\Problem A：Data.xlsx")
OUT = Path(__file__).resolve().parents[1] / "data"
W0 = 2 * np.pi * Q.F_LINE
WIN = Q.WIN            # 0.25 s = exactly two periods at 8 Hz -> unbiased demodulation
MU = 0.20


class Ring:
    """Mean of the last n samples in O(1) per sample."""

    def __init__(self, n: int) -> None:
        self.buf = np.zeros(n)
        self.i = 0
        self.filled = 0

    def push(self, x: float) -> float:
        self.buf[self.i] = x
        self.i = (self.i + 1) % len(self.buf)
        self.filled = min(self.filled + 1, len(self.buf))
        return float(self.buf[:self.filled].mean()) if self.filled else 0.0


def plant(par: dict | None = None) -> complex:
    """Force -> acceleration transfer at the line frequency.

    M y'' + c y' + k y = f gives Y/F = 1/(k - M w^2 + j c w); the measured signal
    is the acceleration, so the transfer carries the -w^2 of the second
    derivative.  Dropping it (as the first version did) leaves a factor of 2527
    and a sign, which turns the contraction below into a diverging loop.
    """
    p = {**M.__dict__, **(par or {})}
    return -W0 ** 2 / (p["K_EQ"] - p["M_TOTAL"] * W0 ** 2 + 1j * p["C_EQ"] * W0)


def run_fb(t: np.ndarray, fd: np.ndarray, win: int = WIN, mu: float = MU,
           par_nom: dict | None = None, par_true: dict | None = None,
           noise: float = 0.0, seed: int = 0,
           fc_init: np.ndarray | None = None) -> dict:
    """Integrate the body while the controller sees only a_y.

    fc_init (optional) is a per-sample *feedforward* command phasor: the loop
    starts from it and the Newton step trims on top, so a learned open-loop
    command can be combined with the model-based corrector.  With fc_init=None
    the behaviour is unchanged (pure feedback).
    """
    nom = {**M.__dict__, **(par_nom or {})}
    tru = {**M.__dict__, **(par_true or {})}
    Mt, ct, kt = tru["M_TOTAL"], tru["C_EQ"], tru["K_EQ"]
    H = plant(nom)
    n = len(t)
    dt = t[1] - t[0]
    sub = max(1, int(round(dt / M.DT_SIM)))
    h = dt / sub
    rng = np.random.default_rng(seed)

    y = np.empty(n); v = np.empty(n); a = np.empty(n); fa = np.empty(n)
    kap = np.zeros(n) + 0.5 * np.pi
    psi = np.zeros(n)
    y[0], v[0] = M.Y0, M.V0
    a[0] = (fd[0] - ct * v[0] - kt * y[0]) / Mt

    rb_c, rb_s = Ring(win), Ring(win)
    fc = 0j          # commanded line phasor, (b, s) as b + j s
    fc_corr = 0j     # feedback part, added on top of any feedforward command
    locked = False
    kk = M.M_ECC * M.RADIUS
    w1 = w2 = W0
    al1 = al2 = 0.0
    prev_kap = 0.5 * np.pi
    prev_psi = 0.0

    for i in range(n - 1):
        bc = rb_c.push(a[i] * np.cos(W0 * t[i]))
        bs = rb_s.push(a[i] * np.sin(W0 * t[i]))
        E = 2.0 * (bc - 1j * bs)          # a(t) ~ Re{E e^{j w0 t}}
        if rb_c.filled >= win and i % win == 0:
            # one Newton step per window, and the command is HELD in between:
            # updating every sample multiplies the gain by the window length
            # (0.35 x 25 = 8.75 per window -> divergence for every mu), and a
            # command that moves continuously also emits at w0 + psi-dot instead
            # of w0, which the phasor model does not allow.
            locked = True
            fc_corr -= mu * (E / H)
            fc = (complex(fc_init[i]) if fc_init is not None else 0j) + fc_corr

        amp = min(abs(fc), Q.CAP_LINE)
        # the phase must be UNWRAPPED: feeding np.angle straight in makes the
        # second difference explode at every +-pi crossing (alpha spikes of
        # 6e4 rad/s^2, megawatts of force for one sample, and the loop never
        # settles -- that was the "same result for every gain" signature)
        raw = float(np.angle(fc)) if amp > 1e-9 else prev_psi
        d = (raw - prev_psi + np.pi) % (2 * np.pi) - np.pi if i else raw
        psi[i] = prev_psi + d
        prev_psi = psi[i]
        kap[i] = float(np.arccos(np.clip(amp / Q.CAP_LINE, 0.0, 1.0)))
        # kappa and psi are held between updates, so within a window the pair is
        # a pure +-w0 ramp: omega = +-w0 exactly and alpha = 0, which is what the
        # phasor bookkeeping above assumes
        w1, w2 = W0, -W0
        al1 = al2 = 0.0
        ki, ph = kap[i], psi[i]
        kk = M.M_ECC * M.RADIUS

        def force(tt: float) -> float:
            # identical to Q2's pair law: the pair emits +CAP cos(kappa) cos(w0 t + psi),
            # so psi is the phase of the commanded phasor and no extra pi belongs here
            th1 = W0 * tt + ki + ph
            th2 = -W0 * tt + ki - ph
            g1 = 2 * kk * (w1 ** 2 * np.cos(th1) + al1 * np.sin(th1))
            g2 = 2 * kk * (w2 ** 2 * np.cos(th2) + al2 * np.sin(th2))
            return 2.0 * (g1 + g2)          # two identical actuators

        # ---- RK4 on the true body -------------------------------------------
        fd0, fd1 = fd[i], fd[i + 1]

        def acc(yy: float, vv: float, tt: float) -> float:
            u = (tt - t[i]) / dt
            return ((fd0 + (fd1 - fd0) * u) + force(tt) - ct * vv - kt * yy) / Mt

        yy, vv = y[i], v[i]
        for j in range(sub):
            t1 = t[i] + j * h
            t2 = t1 + 0.5 * h
            t3 = t1 + h
            k1y, k1v = vv, acc(yy, vv, t1)
            k2y, k2v = vv + 0.5 * h * k1v, acc(yy + 0.5 * h * k1y, vv + 0.5 * h * k1v, t2)
            k3y, k3v = vv + 0.5 * h * k2v, acc(yy + 0.5 * h * k2y, vv + 0.5 * h * k2v, t2)
            k4y, k4v = vv + h * k3v, acc(yy + h * k3y, vv + h * k3v, t3)
            yy += h * (k1y + 2 * k2y + 2 * k3y + k4y) / 6
            vv += h * (k1v + 2 * k2v + 2 * k3v + k4v) / 6
        y[i + 1], v[i + 1] = yy, vv
        fa[i + 1] = force(t[i + 1])
        a[i + 1] = (fd[i + 1] + fa[i + 1] - ct * vv - kt * yy) / Mt
        if noise:
            a[i + 1] += noise * rng.standard_normal()

    i0 = int(round((win * dt) / dt))          # first sample with a full window
    ss = M.vibration_index(t[i0:], a[i0:])
    return {"I": M.vibration_index(t, a), "I_ss": ss, "i_ss": i0,
            "y": y, "v": v, "a": a, "fa": fa, "kappa": kap, "psi": psi,
            "omega_max": float(max(abs(w1), abs(w2))),
            "alpha_max": float(max(abs(al1), abs(al2)))}


def main() -> int:
    d = M.load_scenarios(str(DATA))
    t, f2 = d["t"], d["F2"]
    I0 = M.vibration_index(t, M.simulate(t, f2)["a"])
    q2 = json.loads((OUT / "q2.json").read_text(encoding="utf-8"))
    print(f"uncontrolled I={I0:.3f}   Q2 open-loop I={q2['D']['I']:.3f}")

    r = run_fb(t, f2)
    print(f"\nQ3 acceleration feedback, mu={MU}, window {WIN/100:.2f} s "
          f"(= 2 periods, unbiased):")
    print(f"   I(full 0-10 s) = {r['I']:.3f}   I(0.25-10 s) = {r['I_ss']:.3f}  "
          f"({100*(1-r['I_ss']/I0):.2f}% of the uncontrolled steady level)")
    print(f"   y_pp={np.ptp(r['y'])*1e3:.2f} mm  a_pp={np.ptp(r['a']):.2f} m/s^2  "
          f"|F|max={np.abs(r['fa']).max()/1e3:.2f} kN  |omega|={r['omega_max']:.2f}  "
          f"|alpha|={r['alpha_max']:.1f}")
    # settle time: last moment the instantaneous index over one period exceeds 2x floor
    res = {"I_uncontrolled": I0, "I_q2_reference": q2["D"]["I"], "mu": MU,
           "Q3": {"I_full": r["I"], "I_steady": r["I_ss"], "i_steady": r["i_ss"],
                  "reduction_pct_steady": 100 * (1 - r["I_ss"] / I0),
                  "y_pp_mm": float(np.ptp(r["y"]) * 1e3), "a_pp": float(np.ptp(r["a"])),
                  "f_max_kN": float(np.abs(r["fa"]).max() / 1e3),
                  "omega_max": r["omega_max"], "alpha_max": r["alpha_max"],
                  "kappa_deg": np.degrees(r["kappa"]).tolist(),
                  "psi_deg": np.degrees(r["psi"]).tolist(),
                  "y": r["y"].tolist(), "a": r["a"].tolist(), "fa": r["fa"].tolist()}}

    print("\ngain scheduling (mu):")
    mus = []
    for mu in (0.1, 0.2, 0.35, 0.5, 0.8):
        rr = run_fb(t, f2, mu=mu)
        mus.append({"mu": mu, "I_steady": rr["I_ss"], "I_full": rr["I"]})
        print(f"   mu={mu:4.2f}  I(0.25-10 s)={rr['I_ss']:8.2f}  I(full)={rr['I']:8.2f}")
    res["mu"] = mus

    print("\nparameter error (controller nominal, plant perturbed):")
    sens = []
    for label, fac in (("k+10%", {"K_EQ": 1.1 * M.K_EQ}), ("k-10%", {"K_EQ": 0.9 * M.K_EQ}),
                       ("c+50%", {"C_EQ": 1.5 * M.C_EQ}), ("c-50%", {"C_EQ": 0.5 * M.C_EQ}),
                       ("M+10%", {"M_TOTAL": 1.1 * M.M_TOTAL}),
                       ("M-10%", {"M_TOTAL": 0.9 * M.M_TOTAL})):
        rr = run_fb(t, f2, par_true=fac)
        sens.append({"case": label, "I_steady": rr["I_ss"], "I_full": rr["I"]})
        print(f"   {label:<7} I(0.25-10 s)={rr['I_ss']:8.2f}  I(full)={rr['I']:8.2f}")
    res["param_error"] = sens

    print("\naccelerometer noise:")
    noise, a_rms = [], float(np.sqrt((M.simulate(t, f2)["a"] ** 2).mean()))
    for sig in (0.5, 2.0, 5.0, 10.0):
        rr = run_fb(t, f2, noise=sig)
        noise.append({"sigma": sig, "relative_pct": 100 * sig / a_rms,
                      "I_steady": rr["I_ss"], "I_full": rr["I"]})
        print(f"   sigma={sig:5.1f} ({100*sig/a_rms:5.2f}% of a_rms)  "
              f"I(0.25-10 s)={rr['I_ss']:8.2f}")
    res["noise"] = noise

    print("\ntuning grid, I over the controlled span (rows: window, columns: mu):")
    wins, mus = (13, 25, 38, 50, 75), (0.1, 0.15, 0.2, 0.3, 0.4)
    grid = []
    for win in wins:
        row = []
        for mu in mus:
            rr = run_fb(t, f2, win=win, mu=mu)
            row.append(rr["I_ss"])
        grid.append({"win_s": win / 100, "periods": win * 0.01 / 0.125, "I": row})
        print(f"   win={win/100:.2f} s ({win*0.01/0.125:.1f}T): " +
              "  ".join(f"mu={m:.2f}:{v:8.1f}" for m, v in zip(mus, row)))
    res["grid"] = {"mu": list(mus), "rows": grid}

    th = np.column_stack([W0 * t + r["kappa"] + r["psi"] + np.pi,
                          -W0 * t + r["kappa"] - r["psi"] - np.pi] * 2)
    res["theta"] = th.tolist()

    p = OUT / "q3.json"
    p.write_text(json.dumps(res), encoding="utf-8")
    print(f"\nwrote {p} ({p.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())