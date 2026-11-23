# -*- coding: utf-8 -*-
"""A trained model, not a fitted curve: learn the drift of the 8 Hz line.

Why a learner is needed at all
------------------------------
The analytic design D demodulates the disturbance with a causal window of WIN
samples.  A moving average of length WIN has group delay (WIN-1)/2 samples, so
the phasor it reports is the phasor of the *past*: at WIN=25 that is 0.12 s,
which is 0.96 cycles at 8 Hz.  Design D pays for this with a phase error that
grows with the drift rate of the line, and the measured penalty is brutal --
6 deg of residual phase error costs one order of magnitude in I (paper Fig. 7).

The line is not stationary (measured: amplitude 13.4..20.3 kN, phase peak-to-
peak 33 deg over 10 s), so the delay cannot be removed by a longer window: a
longer window averages the drift away, a shorter one lets the pair overrun the
actuator limits (both measured in the window sweep, U-shaped with its minimum at
0.25 s).  The remaining option is to *predict* the phasor rather than average it.

What is learned
---------------
  x_t  = [a(t), b(t)] demodulated causally at four lags (0, 0.05, 0.10, 0.20 s)
         -> 8 numbers, all of them measurable at time t
  y_t  = [a(t+H), b(t+H)] - [a(t), b(t)]   the phasor increment over the lead H
  f    = MLP 8-32-32-2, tanh, Adam, early stopping on a held-out split

The label is computed from a *centred* two-cycle window (non-causal).  That is
legitimate: labels are what training needs, and the deployed model only ever
sees causal features.  This is stated in the paper, because a non-causal label
is exactly the kind of thing that silently turns a forecast into a cheat.

Data
----
The official workbook contains one 10 s realisation of each scenario -- 1000
samples, far too few to train anything and, worse, a single draw of the drift.
Training therefore uses a *synthetic corpus* of disturbances built from the
measured spectral content of scenario 2 (three lines at 3/5/8 Hz with the
measured amplitudes, a random-walk phase whose peak-to-peak matches the measured
33 deg, plus the measured projection residual as colour noise).  160 sequences
for training, 24 for validation, 24 held out for test -- split by sequence, so
no window of a test sequence was ever seen.  The real scenario 2 is *never* used
for training: it is the deployment test, and the honest headline number.

Two tasks share the same machinery:
  L2  phasor of the disturbance -> actuator angles  (Question 2)
  L3  phasor of the disturbance from a_y only        (Question 3, sensor-limited)

Outputs data/lead.json.  Torch is only used for the network; the plant stays in
numpy, and nothing here calls LAPACK (this environment aborts on it).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M            # noqa: E402
import solve_q2 as Q2        # noqa: E402

DATA = Path(r"C:\Users\29900\Downloads\AsterLink\Problem A：Data.xlsx")
OUT = Path(__file__).resolve().parents[1] / "data"
HZ = Q2.F_LINE               # 8 Hz
W = 2 * np.pi * HZ
LAGS = (0, 5, 10, 20)        # samples: 0, 0.05, 0.10, 0.20 s
WIN_F = 25                   # the demodulator of design D (0.25 s)
WIN_C = 20                   # centred label window: 2 cycles, exact for 8 Hz
LEAD = 12                    # samples, 0.12 s: the group delay of WIN_F
SEED = 20251119


# --------------------------------------------------------------------- windows
def _box_sym(x: np.ndarray, n: int) -> np.ndarray:
    """Centred box average with reflected edges (label window, non-causal)."""
    if n <= 1:
        return x.copy()
    pad = n // 2
    xp = np.concatenate([x[pad:0:-1], x, x[-2:-pad - 2:-1]][: len(x) + 2 * pad])
    k = np.ones(n) / n
    return np.convolve(xp, k, mode="same")[pad:pad + len(x)]


def causal_phasor(t: np.ndarray, f: np.ndarray, win: int = WIN_F) -> tuple[np.ndarray, np.ndarray]:
    a = 2 * Q2.movavg_past(f * np.sin(W * t), win)
    b = 2 * Q2.movavg_past(f * np.cos(W * t), win)
    return a, b


def centred_phasor(t: np.ndarray, f: np.ndarray, win: int = WIN_C) -> tuple[np.ndarray, np.ndarray]:
    a = 2 * _box_sym(f * np.sin(W * t), win)
    b = 2 * _box_sym(f * np.cos(W * t), win)
    return a, b


def _shift(x: np.ndarray, k: int) -> np.ndarray:
    """x(t - k*dt), edge-padded.  Negative k looks *forward* (labels only)."""
    if k == 0:
        return x.copy()
    out = np.empty_like(x)
    if k > 0:
        out[k:] = x[:-k]
        out[:k] = x[0]
    else:
        j = -k
        out[:-j] = x[j:]
        out[-j:] = x[-1]
    return out


def features(t: np.ndarray, f: np.ndarray, win: int = WIN_F) -> np.ndarray:
    a, b = causal_phasor(t, f, win)
    cols = []
    for lag in LAGS:
        cols += [_shift(a, lag), _shift(b, lag)]
    return np.column_stack(cols)


def target_increment(t: np.ndarray, f: np.ndarray, lead: int = LEAD) -> np.ndarray:
    a, b = centred_phasor(t, f)
    a0, b0 = causal_phasor(t, f)
    return np.column_stack([_shift(a, -lead) - a0, _shift(b, -lead) - b0])


# ------------------------------------------------------------- synthetic corpus
def synth_sequence(rng: np.random.Generator, amps=(3.111e3, 7.760e3, 16.788e3),
                   drift_deg_pp=33.0, resid=0.0686, n: int = 1000, dt: float = M.DT) -> np.ndarray:
    """A disturbance with scenario 2's measured spectrum, but its own drift draw."""
    t = np.arange(n) * dt
    f = np.zeros(n)
    for hz, amp in zip((3.0, 5.0, 8.0), amps):
        a_scale = amp * rng.uniform(0.80, 1.20)
        # random-walk phase, smoothed so that its p2p matches the measurement
        step = np.radians(drift_deg_pp) / np.sqrt(n) * rng.uniform(0.6, 1.4)
        ph = np.cumsum(rng.normal(0.0, step, n))
        ph -= np.linspace(ph[0], ph[-1], n)          # remove the net ramp
        ph = _box_sym(ph, 41)
        f += a_scale * np.cos(2 * np.pi * hz * t + rng.uniform(0, 2 * np.pi) + ph)
    # colour noise with the measured residual share, band-limited by a short average
    wn = _box_sym(rng.normal(0.0, 1.0, n), 11)
    wn *= np.sqrt((resid * np.sqrt((f ** 2).mean())) ** 2 / max(wn.var(), 1e-18))
    return f + wn


# ---------------------------------------------------------------------- network
class MLP(nn.Module):
    def __init__(self, d_in: int = 8, hidden: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, 2),
        )

    def forward(self, x):
        return self.net(x)


def _scale(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = X.mean(0)
    sd = X.std(0) + 1e-9
    return (X - mu) / sd, mu, sd


def train_mlp(Xtr, Ytr, Xva, Yva, hidden=32, epochs=60, lr=2e-3, batch=2048,
              verbose=False) -> tuple[MLP, dict, tuple]:
    """Mini-batch Adam on standardised inputs and targets.

    Both standardisations matter: the phasor increments live at 1e4 N while the
    features live at 1e1, and with raw targets the first-epoch MSE is 4e7 and the
    network never leaves that plateau (measured: 400 full-batch steps, val MSE
    stuck at 4.5e7, held-out phase error 19.8 deg).  Standardising both sides and
    using mini-batches (about 4.7e3 steps) is what makes it learn.
    """
    torch.manual_seed(SEED)
    Xtr_s, mx, sx = _scale(Xtr)
    Xva_s = (Xva - mx) / sx
    my = Ytr.mean(0)
    sy = Ytr.std(0) + 1e-9
    Ytr_s = (Ytr - my) / sy
    xt = torch.tensor(Xtr_s, dtype=torch.float32)
    yt = torch.tensor(Ytr_s, dtype=torch.float32)
    xv = torch.tensor(Xva_s, dtype=torch.float32)
    yv = torch.tensor((Yva - my) / sy, dtype=torch.float32)
    net = MLP(Xtr.shape[1], hidden)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    loss = nn.MSELoss()
    hist = {"train": [], "val": []}
    n = len(xt)
    best, best_state, best_ep = float("inf"), None, -1
    for ep in range(epochs):
        net.train()
        perm = torch.randperm(n)
        tot = 0.0
        for i in range(0, n, batch):
            idxb = perm[i:i + batch]
            opt.zero_grad()
            l = loss(net(xt[idxb]), yt[idxb])
            l.backward()
            opt.step()
            tot += float(l.detach()) * len(idxb)
        sched.step()
        net.eval()
        with torch.no_grad():
            lv = float(loss(net(xv), yv))
        hist["train"].append(tot / n)
        hist["val"].append(lv)
        if lv < best - 1e-12:
            best, best_ep = lv, ep
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
        if verbose and (ep % 10 == 0 or ep == epochs - 1):
            print(f"  ep {ep:3d}  train {hist['train'][-1]:.4f}  val {lv:.4f}")
    if best_state is not None:
        net.load_state_dict(best_state)
    net.eval()
    hist["best_epoch"] = best_ep
    hist["best_val"] = best
    return net, hist, (mx, sx, my, sy)


def predict(net: MLP, X: np.ndarray, sc: tuple) -> np.ndarray:
    mx, sx, my, sy = sc
    with torch.no_grad():
        out = net(torch.tensor((X - mx) / sx, dtype=torch.float32)).numpy().astype(float)
    return out * sy + my


# ---------------------------------------------------------------- phasor -> angle
def angles_from_amp_phase(t: np.ndarray, amp: np.ndarray, psi: np.ndarray,
                          cap: float = Q2.CAP_LINE) -> np.ndarray:
    kappa = np.arccos(np.clip(amp / cap, 0.0, 1.0))
    return Q2.pair_from_kappa_psi(t, kappa, psi + np.pi)


def phase_error_deg(pred_ab: np.ndarray, true_ab: np.ndarray) -> np.ndarray:
    pa = np.arctan2(-pred_ab[:, 0], pred_ab[:, 1])
    ta = np.arctan2(-true_ab[:, 0], true_ab[:, 1])
    return np.degrees(np.angle(np.exp(1j * (pa - ta))))


def _q3_reference() -> float | None:
    """The analytic Q3 answer (Newton loop), read back so the table is in one file."""
    try:
        d = json.loads((OUT / "q3.json").read_text(encoding="utf-8"))
        return float(d["Q3"]["I_steady"])
    except Exception:
        return None


# ------------------------------------------------------------------------- main
def main() -> int:
    rng = np.random.default_rng(SEED)
    d = M.load_scenarios(str(DATA))
    t, f2 = d["t"], d["F2"]
    base = M.simulate(t, f2)
    I0 = M.vibration_index(t, base["a"])
    spec = Q2.project(t, f2)

    print("=" * 78)
    print("corpus: 208 synthetic disturbances (160/24/24), real scenario 2 held out")
    seqs = [synth_sequence(rng) for _ in range(208)]
    idx = {"train": range(0, 160), "val": range(160, 184), "test": range(184, 208)}

    def stack(part, lead=LEAD):
        Xs, Ys = [], []
        for i in idx[part]:
            f = seqs[i]
            Xs.append(features(t, f))
            Ys.append(target_increment(t, f, lead))
        return np.vstack(Xs), np.vstack(Ys)

    Xtr, Ytr = stack("train")
    Xva, Yva = stack("val")
    Xte, Yte = stack("test")
    print(f"  train {Xtr.shape}, val {Xva.shape}, test {Xte.shape}")

    # ---------------------------------------------------------------- L2 model
    print("-" * 78)
    print("[L2] forecasting the 8 Hz phasor 0.12 s ahead")
    net, hist, sc = train_mlp(Xtr, Ytr, Xva, Yva, verbose=True)
    pred_te = predict(net, Xte, sc) + Xte[:, 0:2]
    true_te = Yte + Xte[:, 0:2]
    e_mlp = phase_error_deg(pred_te, true_te)
    print(f"  best epoch {hist['best_epoch']}, val MSE {hist['best_val']:.3e}")
    print(f"  held-out phase error |median| {np.median(np.abs(e_mlp)):.2f} deg, "
          f"p95 {np.percentile(np.abs(e_mlp), 95):.2f} deg")

    # physics baseline: linear extrapolation of the unwrapped phase
    e_lin = []
    for i in idx["test"]:
        f = seqs[i]
        a, b = causal_phasor(t, f)
        psi = np.unwrap(np.arctan2(-a, b))
        slope = np.gradient(Q2.movavg_past(psi, 41), M.DT)
        amp = np.hypot(a, b)
        pred = np.column_stack([-np.sin(psi + slope * LEAD * M.DT), np.cos(psi + slope * LEAD * M.DT)]) * amp[:, None]
        ta, tb = centred_phasor(t, f)
        true = np.column_stack([_shift(ta, -LEAD), _shift(tb, -LEAD)])
        e_lin.append(phase_error_deg(pred, true))
    e_lin = np.concatenate(e_lin)
    print(f"  linear-extrapolation baseline |median| {np.median(np.abs(e_lin)):.2f} deg")

    # -------------------------------------------------- deployment on scenario 2
    print("-" * 78)
    print("[L2] deployment on the real scenario 2 (never trained on)")

    def close_loop_with(pred_ab: np.ndarray) -> dict:
        amp = np.hypot(pred_ab[:, 0], pred_ab[:, 1])
        psi = np.unwrap(np.arctan2(-pred_ab[:, 0], pred_ab[:, 1]))
        th = angles_from_amp_phase(t, amp, psi)
        return Q2.run(t, f2, th)

    X2 = features(t, f2)
    inc = predict(net, X2, sc)
    a0, b0 = causal_phasor(t, f2)
    pred_ab = np.column_stack([a0 + inc[:, 0], b0 + inc[:, 1]])
    r = close_loop_with(pred_ab)
    print(f"  learned lead: I={r['I']:.3f}  ({100*(1-r['I']/I0):.2f}%)  "
          f"|omega|max={np.abs(r['om']).max():.2f}/100  |alpha|max={np.abs(r['al']).max():.1f}/5000  "
          f"|F|max={np.abs(r['fa']).max()/1e3:.2f} kN")

    # ablation: how much of the gain is the lead, how much is the network?
    lab = {}
    tr_seq = [seqs[i] for i in idx["train"]]
    va_seq = [seqs[i] for i in idx["val"]]
    for lead in (0, 6, 9, 12, 15, 18):
        if lead == LEAD:
            rl = r
        else:
            Xs = np.vstack([features(t, f) for f in tr_seq])
            Ys = np.vstack([target_increment(t, f, lead) for f in tr_seq])
            Xv = np.vstack([features(t, f) for f in va_seq])
            Yv = np.vstack([target_increment(t, f, lead) for f in va_seq])
            n2, h2, s2 = train_mlp(Xs, Ys, Xv, Yv)
            inc2 = predict(n2, X2, s2)
            ab2 = np.column_stack([a0 + inc2[:, 0], b0 + inc2[:, 1]])
            rl = close_loop_with(ab2)
        lab[str(lead)] = {"I": rl["I"], "reduction_pct": 100 * (1 - rl["I"] / I0),
                          "fs_ms": lead * 10}
        print(f"    lead {lead*10:2d} ms -> I={rl['I']:.3f}")

    # ---------------------------------------------------------------- L3 model
    print("-" * 78)
    print("[L3] the same forecast from a_y alone (Question 3)")
    n3tr, n3va = 48, 12
    X3s, Y3s = [], []
    for f in tr_seq[:n3tr]:
        s = M.simulate(t, f)
        a, b = causal_phasor(t, s["a"])
        cols = []
        for lag in LAGS:
            cols += [_shift(a, lag), _shift(b, lag)]
        X3s.append(np.column_stack(cols))
        ta, tb = centred_phasor(t, f)
        Y3s.append(np.column_stack([_shift(ta, -LEAD), _shift(tb, -LEAD)]))
    X3va, Y3va = [], []
    for f in va_seq[:n3va]:
        s = M.simulate(t, f)
        a, b = causal_phasor(t, s["a"])
        cols = []
        for lag in LAGS:
            cols += [_shift(a, lag), _shift(b, lag)]
        X3va.append(np.column_stack(cols))
        ta, tb = centred_phasor(t, f)
        Y3va.append(np.column_stack([_shift(ta, -LEAD), _shift(tb, -LEAD)]))
    print(f"  corpus {n3tr}/{n3va} simulated sequences")
    net3, hist3, sc3 = train_mlp(np.vstack(X3s), np.vstack(Y3s),
                                 np.vstack(X3va), np.vstack(Y3va))
    print(f"  best epoch {hist3['best_epoch']}, val MSE {hist3['best_val']:.3e}")

    # deployment: the loop changes a_y, so the estimate must survive its own
    # feedback.  A naive fixed-point iteration (re-estimate from the *controlled*
    # a_y, re-apply, repeat) diverges: the model was trained on uncontrolled
    # a_y, so the ring it now sees is out of distribution and each pass adds
    # more force.  Measured, kept in the log because "we tried the obvious thing"
    # is worth a line in the paper.
    I3 = {}
    for iters in range(1, 4):
        s = M.simulate(t, f2)
        for _ in range(iters):
            aa, bb = causal_phasor(t, s["a"])
            cols = []
            for lag in LAGS:
                cols += [_shift(aa, lag), _shift(bb, lag)]
            ab = predict(net3, np.column_stack(cols), sc3)
            amp = np.hypot(ab[:, 0], ab[:, 1])
            psi = np.unwrap(np.arctan2(-ab[:, 0], ab[:, 1]))
            th = angles_from_amp_phase(t, amp, psi)
            s = M.simulate(t, f2, M.actuator_force(th, *M.angles_to_rates(th, M.DT)[:2]))
        I3[str(iters)] = M.vibration_index(t, s["a"])
        print(f"  fixed-point iteration {iters}: I={I3[str(iters)]:.2f} "
              f"({100*(1-I3[str(iters)]/I0):.2f}%)  <- diverges, see DAgger")

    # DAgger: let the policy visit its own states, label them with the truth,
    # and retrain.  This is the standard fix for exactly the failure above.
    def l3_feats(sig: np.ndarray) -> np.ndarray:
        a, b = causal_phasor(t, sig)
        cols = []
        for lag in LAGS:
            cols += [_shift(a, lag), _shift(b, lag)]
        return np.column_stack(cols)

    _ta, _tb = centred_phasor(t, f2)
    tgt2 = np.column_stack([_shift(_ta, -LEAD), _shift(_tb, -LEAD)])
    Xagg, Yagg = [np.vstack(X3s)], [np.vstack(Y3s)]
    dagger = {"0": {"I": I3["1"], "reduction_pct": 100 * (1 - I3["1"] / I0)}}
    best = {"I": float("inf"), "net": net3, "sc": sc3, "round": 0}
    for rnd in range(1, 5):
        s = M.simulate(t, f2)
        ab = predict(net3, l3_feats(s["a"]), sc3)
        th = angles_from_amp_phase(t, np.hypot(ab[:, 0], ab[:, 1]),
                                   np.unwrap(np.arctan2(-ab[:, 0], ab[:, 1])))
        om, al, _ = M.angles_to_rates(th, M.DT)
        s2 = M.simulate(t, f2, M.actuator_force(th, om, al))
        Xagg.append(l3_feats(s2["a"]))
        Yagg.append(tgt2)
        net3, hist3, sc3 = train_mlp(np.vstack(Xagg), np.vstack(Yagg),
                                     np.vstack(X3va), np.vstack(Y3va))
        # re-deploy the retrained policy (one pass, no iteration)
        s = M.simulate(t, f2)
        ab = predict(net3, l3_feats(s["a"]), sc3)
        th = angles_from_amp_phase(t, np.hypot(ab[:, 0], ab[:, 1]),
                                   np.unwrap(np.arctan2(-ab[:, 0], ab[:, 1])))
        om, al, _ = M.angles_to_rates(th, M.DT)
        s3 = M.simulate(t, f2, M.actuator_force(th, om, al))
        Ir = M.vibration_index(t, s3["a"])
        dagger[str(rnd)] = {"I": Ir, "reduction_pct": 100 * (1 - Ir / I0),
                            "f_max_kN": float(np.abs(M.actuator_force(th, om, al)).max() / 1e3),
                            "omega_max": float(np.abs(om).max()),
                            "alpha_max": float(np.abs(al).max())}
        print(f"  DAgger round {rnd}: I={Ir:.2f} ({100*(1-Ir/I0):.2f}%)  "
              f"|F|max={dagger[str(rnd)]['f_max_kN']:.2f} kN  best_ep={hist3['best_epoch']}")
        if Ir < best["I"]:
            best = {"I": Ir, "net": net3, "sc": sc3, "round": rnd,
                    "theta": th, "om": om, "al": al, "fa": M.actuator_force(th, om, al)}

    # ------------------------------------------------- robustness of the deployed model
    print("-" * 78)
    net3, sc3 = best["net"], best["sc"]
    print(f"[L3] deploying DAgger round {best['round']} (I={best['I']:.2f}); robustness:")

    def deploy(par: dict | None = None, noise: float = 0.0, rng_n=None) -> dict:
        s = M.simulate(t, f2, par=par)
        sig = s["a"]
        if noise > 0:
            sig = sig + (rng_n or np.random.default_rng(0)).normal(0.0, noise, len(sig))
        ab = predict(net3, l3_feats(sig), sc3)
        th = angles_from_amp_phase(t, np.hypot(ab[:, 0], ab[:, 1]),
                                   np.unwrap(np.arctan2(-ab[:, 0], ab[:, 1])))
        om, al, _ = M.angles_to_rates(th, M.DT)
        s2 = M.simulate(t, f2, M.actuator_force(th, om, al), par=par)
        return {"I": M.vibration_index(t, s2["a"]), "y": s2["y"], "a": s2["a"],
                "f_max_kN": float(np.abs(M.actuator_force(th, om, al)).max() / 1e3),
                "omega_max": float(np.abs(om).max()), "alpha_max": float(np.abs(al).max())}

    rob = {}
    for name, par in (("nominal", None),
                      ("k+10%", {"K_EQ": M.K_EQ * 1.1}), ("k-10%", {"K_EQ": M.K_EQ * 0.9}),
                      ("c+50%", {"C_EQ": M.C_EQ * 1.5}), ("c-50%", {"C_EQ": M.C_EQ * 0.5}),
                      ("M+10%", {"M_TOTAL": M.M_TOTAL * 1.1}), ("M-10%", {"M_TOTAL": M.M_TOTAL * 0.9})):
        rr = deploy(par)
        rob[name] = {"I": rr["I"], "reduction_pct": 100 * (1 - rr["I"] / I0)}
        print(f"  {name:6s} I={rr['I']:9.2f}  ({rob[name]['reduction_pct']:6.2f}%)")
    for sg in (0.5, 2.0, 5.0):
        rr = deploy(None, noise=sg)
        rob[f"noise{sg}"] = {"I": rr["I"], "reduction_pct": 100 * (1 - rr["I"] / I0)}
        print(f"  noise {sg:4.1f} m/s^2  I={rr['I']:9.2f}  ({rob[f'noise{sg}']['reduction_pct']:6.2f}%)")
    # the deployed trajectory, for the figure
    dep = deploy(None)

    # ------------------------------------------------------- learned FF + Newton trim
    print("-" * 78)
    print("[L3] hybrid: the learned feedforward, with the Newton loop trimming on top")
    import solve_q3 as S3  # noqa: E402  (imported late: it pulls solve_q2 back in)

    s = M.simulate(t, f2)
    ab = predict(net3, l3_feats(s["a"]), sc3)
    A_, P_ = np.hypot(ab[:, 0], ab[:, 1]), np.arctan2(-ab[:, 0], ab[:, 1])
    fc_init = A_ * np.exp(1j * (P_ + np.pi))
    hyb = {}
    for name, par in (("nominal", None),
                      ("k+10%", {"K_EQ": M.K_EQ * 1.1}), ("k-10%", {"K_EQ": M.K_EQ * 0.9}),
                      ("c+50%", {"C_EQ": M.C_EQ * 1.5}), ("c-50%", {"C_EQ": M.C_EQ * 0.5}),
                      ("M+10%", {"M_TOTAL": M.M_TOTAL * 1.1}), ("M-10%", {"M_TOTAL": M.M_TOTAL * 0.9})):
        rh = S3.run_fb(t, f2, fc_init=fc_init, par_nom=par, par_true=par)
        hyb[name] = {"I": rh["I_ss"], "I_full": rh["I"],
                     "reduction_pct": 100 * (1 - rh["I_ss"] / I0)}
        print(f"  {name:6s} I(0.25-10 s)={rh['I_ss']:9.2f}  ({hyb[name]['reduction_pct']:6.2f}%)")

    # --------------------------------------------------- phasor series for the figure
    # The whole idea of the paper is a vector in the (a,b) plane, so the figure needs
    # the true phasor, what the causal window reports, and what the network adds.
    _ta2, _tb2 = centred_phasor(t, f2)
    true_ab = np.column_stack([_shift(_ta2, -LEAD), _shift(_tb2, -LEAD)])
    causal_ab = np.column_stack([a0, b0])
    l3_ab = predict(net3, l3_feats(M.simulate(t, f2)["a"]), sc3)

    # phase error against the true phasor on the official record (post-transient)
    def _perr(xa, xb) -> float:
        pt_ = np.unwrap(np.arctan2(-true_ab[:, 0], true_ab[:, 1]))
        e_ = np.degrees(np.angle(np.exp(1j * (np.arctan2(-xa, xb) - pt_))))
        return float(np.median(np.abs(e_[t > 0.5])))

    pe_real = {"causal_median_deg": _perr(causal_ab[:, 0], causal_ab[:, 1]),
               "learned_median_deg": _perr(pred_ab[:, 0], pred_ab[:, 1]),
               "l3_median_deg": _perr(l3_ab[:, 0], l3_ab[:, 1])}
    print(f"official-record phase error: causal {pe_real['causal_median_deg']:.2f} deg, "
          f"learned {pe_real['learned_median_deg']:.2f} deg, "
          f"from a_y {pe_real['l3_median_deg']:.2f} deg")

    # --------------------------------------------------------------------- save
    res = {
        "seed": SEED, "hz": HZ, "lags_samples": list(LAGS), "lead_samples": LEAD,
        "phasor": {"true_a": true_ab[:, 0].tolist(), "true_b": true_ab[:, 1].tolist(),
                   "causal_a": causal_ab[:, 0].tolist(), "causal_b": causal_ab[:, 1].tolist(),
                   "learned_a": pred_ab[:, 0].tolist(), "learned_b": pred_ab[:, 1].tolist(),
                   "l3_a": l3_ab[:, 0].tolist(), "l3_b": l3_ab[:, 1].tolist()},
        "corpus": {"n": 208, "train": 160, "val": 24, "test": 24},
        "history": {"train": hist["train"], "val": hist["val"], "best_epoch": hist["best_epoch"]},
        "history_q3": {"train": hist3["train"], "val": hist3["val"], "best_epoch": hist3["best_epoch"]},
        "phase_error": {"mlp_median_deg": float(np.median(np.abs(e_mlp))),
                        "mlp_p95_deg": float(np.percentile(np.abs(e_mlp), 95)),
                        "linear_median_deg": float(np.median(np.abs(e_lin))),
                        "official_causal_median_deg": pe_real["causal_median_deg"],
                        "official_learned_median_deg": pe_real["learned_median_deg"],
                        "official_l3_median_deg": pe_real["l3_median_deg"]},
        "I_uncontrolled": I0,
        "L2": {"I": r["I"], "reduction_pct": 100 * (1 - r["I"] / I0),
               "omega_max": float(np.abs(r["om"]).max()),
               "alpha_max": float(np.abs(r["al"]).max()),
               "f_max_kN": float(np.abs(r["fa"]).max() / 1e3),
               "kappa_deg_mean": float(np.degrees(np.arccos(
                   np.clip(np.hypot(pred_ab[:, 0], pred_ab[:, 1]) / Q2.CAP_LINE, 0, 1))).mean())},
        "lead_sweep": lab,
        "L3": {"I_by_iteration": I3, "dagger": dagger, "robustness": rob,
               "best_round": best["round"], "best_I": best["I"],
               "hybrid": hyb,
               "I_newton_loop_q3": _q3_reference(),
               "y_final": dep["y"].tolist(), "a_final": dep["a"].tolist()},
        "lines": {str(k): {kk: float(vv) for kk, vv in v.items()} for k, v in spec["lines"].items()},
        "I_ref_line8": float(M.vibration_index(
            t, M.simulate(t, f2 - Q2.line_signal(t, spec, HZ))["a"])),
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "lead.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("-" * 78)
    print(f"saved {OUT / 'lead.json'}")
    print(f"reference (oracle, 8 Hz line removed): I={res['I_ref_line8']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
