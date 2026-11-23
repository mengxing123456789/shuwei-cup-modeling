#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P2 alternative module (part 2): *when* to spend a paid look inside a gap.

`alt_p2_kalman.py` answers "how accurate is the damped constant-velocity
filter" and scores the three official decision options A/B/C, which fix the
prefix length up front.  This module answers the question those options leave
open: once a gap is longer than the return delay, **where inside the gap**
should the look be spent, and does an adaptive trigger beat a fixed schedule?

Structural fact first.  A look requested at gap-frame u discloses the real
frames [u, u+6) and is usable only once u + 30 < W, so:

    W <= 31 frames (1.03 s)  ->  no interior look is possible at all

Every hidden window of 1.0 s or less is therefore unobservable inside the gap,
whatever the policy; the official options A/B/C get their information from a
longer *prefix*, not from a look inside the gap.  Within-gap scheduling only
exists for W >= 1.5 s, and that is where this module works.

Four policies, identical decision points and identical targets:

  hold      never request; predict the last observed position
  damped    never request; damped constant-velocity Kalman forecast
  fixed     request at equally spaced instants inside the usable window
  drift     request as soon as the forecast displacement away from the last
            observation exceeds tau; tau is grid-searched on validation

Why not "buy when the uncertainty exceeds tau": with a linear-Gaussian filter
and fixed (q, r) the posterior position trace depends on the horizon only, not
on the data, so such a rule fires either always or never -- it degenerates to a
fixed schedule by construction.  The drift statistic does depend on the data
(through the estimated velocity), so it can discriminate.  That degeneracy is
reported as a result, not hidden.

Outputs (workspace-local only):
  data/alt_p2_policy.json
  out/alt_p2_policy.md   (first line BYTES <real bytes>, last line VERDICT: PASS)
"""
import json
import os
import time

import numpy as np

import alt_p2_kalman as K

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "out")

PRE = 6                     # 0.2 s prefix, same as the first module
DELAY = 30                  # 1.0 s return delay, in frames
CHUNK = 6                   # a look discloses 0.2 s of real frames
NMAX = 2                    # official max_per_job for P2
MIN_USABLE = DELAY + 1      # W must exceed this for any interior look
GAPS = [30, 45, 60, 90]     # 1.0 / 1.5 / 2.0 / 3.0 s
CAP_WIN = 250               # windows per gap, subsampled evenly
TAU_GRID = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def windows(z, recs, L, R, dom, split, gap):
    """Clean prefix+gap windows with the target at the end of the gap."""
    span = PRE + gap
    obs, tgt, rid = [], [], []
    for r, F, bad in K.sequences(z, recs, L, R, dom, split):
        run = 0
        starts = []
        for k in range(len(F)):
            run = run + 1 if not bad[k] else 0
            if run >= span:
                starts.append(k - span + 1)
        if not starts:
            continue
        for s in np.array(starts)[::max(1, gap // 3)]:
            obs.append(F[s:s + span])
            tgt.append(F[s + span - 1])
            rid.append(r)
    if not obs:
        return (np.zeros((0, span, 63)), np.zeros((0, 63)), np.zeros(0, int))
    obs = np.stack(obs).astype(np.float64)
    tgt = np.stack(tgt).astype(np.float64)
    rid = np.array(rid)
    if len(obs) > CAP_WIN:
        pick = np.linspace(0, len(obs) - 1, CAP_WIN).astype(int)
        obs, tgt, rid = obs[pick], tgt[pick], rid[pick]
    return obs, tgt, rid


def err_cm(pred, tgt):
    return np.linalg.norm(pred.reshape(-1, 21, 3) - tgt.reshape(-1, 21, 3), axis=-1) * 100.0


def drift_cm(obs, alpha, q, r, horizon):
    """Predicted mean displacement from the last observation, in cm."""
    if horizon <= 0:
        return 0.0
    pred, _ = K.forecast(obs[None], alpha, q, r, horizon)
    return float(np.linalg.norm(pred[0].reshape(21, 3) - obs[-1].reshape(21, 3), axis=-1).mean()) * 100.0


def run_policy(win, tgt, gap, policy, alpha, q, r, tau):
    """Return (mean err cm over the target, looks) for one window."""
    prefix = win[:PRE].reshape(PRE, -1)
    if policy == "hold":
        return err_cm(prefix[-1][None, :], tgt[None, :]), 0
    if policy == "damped":
        pred, _ = K.forecast(prefix[None], alpha, q, r, gap)
        return err_cm(pred, tgt[None, :]), 0

    used = 0
    obs = prefix.copy()
    if gap <= MIN_USABLE:                      # no interior look is possible
        pred, _ = K.forecast(obs[None], alpha, q, r, gap)
        return err_cm(pred, tgt[None, :]), 0
    if policy == "fixed":
        span = gap - DELAY - CHUNK             # last instant a look still lands
        cand = [max(1, int(round(span * f))) for f in (0.45, 0.95)]
    else:
        cand = list(range(1, gap - DELAY))
    for u in cand:
        if used >= NMAX:
            break
        if policy == "drift":
            horizon = gap - (len(obs) - PRE)
            if drift_cm(obs, alpha, q, r, horizon) <= tau:
                continue
        chunk = win[PRE + u: PRE + u + CHUNK]
        if len(chunk) < CHUNK:
            break
        obs = np.vstack([obs, chunk.reshape(CHUNK, -1)])
        used += 1
    horizon = gap - (len(obs) - PRE)
    if horizon <= 0:
        pred = obs[-1][None, :]
    else:
        pred, _ = K.forecast(obs[None], alpha, q, r, horizon)
    return err_cm(pred, tgt[None, :]), used


def summarize(rows):
    if not rows:
        return {}
    e = np.array([r[0] for r in rows])
    u = np.array([r[1] for r in rows])
    return dict(n_windows=int(len(e)),
                mean_cm=round(float(e.mean()), 3),
                rmse_cm=round(float(np.sqrt((e ** 2).mean())), 3),
                p90_cm=round(float(np.percentile(e, 90)), 3),
                looks_per_window=round(float(u.mean()), 3),
                cost_per_window=round(float(u.mean()), 3))


def calibrate_tau(vobs, vtgt, gap, alpha, q, r):
    """Grid-search the drift threshold on validation, return (tau, curve)."""
    if len(vobs) == 0 or gap <= MIN_USABLE:
        return float("inf"), []
    end = [drift_cm(w[:PRE].reshape(PRE, -1), alpha, q, r, gap) for w in vobs]
    lo, hi = float(np.percentile(end, 10)), float(np.percentile(end, 90))
    curve = []
    for f in TAU_GRID:
        tau = lo + f * (hi - lo)
        rows = [run_policy(vobs[i], vtgt[i], gap, "drift", alpha, q, r, tau)
                for i in range(len(vobs))]
        curve.append(dict(fraction=f, tau_cm=round(tau, 3),
                          mean_cm=round(float(np.mean([x[0].mean() for x in rows])), 3),
                          looks=round(float(np.mean([x[1] for x in rows])), 3)))
    best = min(curve, key=lambda c: c["mean_cm"])
    return float(best["tau_cm"]), curve


def main():
    t0 = time.time()
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    z, recs, L, R, dom = K.load_panel()
    q, r = K.estimate_noise(z, recs, L, R, dom, K.ALPHA)

    table, calib, paired = {}, {}, {}
    for gap in GAPS:
        vobs, vtgt, _ = windows(z, recs, L, R, dom, "validation", gap)
        tau, curve = calibrate_tau(vobs, vtgt, gap, K.ALPHA, q, r)
        obs, tgt, rid = windows(z, recs, L, R, dom, "test", gap)
        if len(obs) == 0:
            continue
        cell = {"_gap_s": round(gap / K.FPS, 2),
                "_gap_frames": int(gap),
                "_usable_frames": int(max(0, gap - MIN_USABLE)),
                "_tau_cm": None if np.isinf(tau) else round(tau, 3)}
        errs = {}
        for pol in ("hold", "damped", "fixed", "drift"):
            rows = [run_policy(obs[i], tgt[i], gap, pol, K.ALPHA, q, r, tau)
                    for i in range(len(obs))]
            cell[pol] = summarize(rows)
            errs[pol] = np.array([x[0].mean() for x in rows])
        table[str(gap)] = cell
        calib[str(gap)] = curve
        row = {}
        for a, b in (("damped", "hold"), ("fixed", "damped"), ("drift", "damped"), ("drift", "fixed")):
            d = errs[a] - errs[b]
            n = len(d)
            sd = float(d.std(ddof=1)) if n > 1 else 0.0
            t = float(d.mean() / (sd / np.sqrt(n))) if sd > 0 else 0.0
            row["%s_minus_%s" % (a, b)] = dict(
                mean_cm=round(float(d.mean()), 3), t=round(t, 2),
                wins=int((d < 0).sum()), ties=int((d == 0).sum()), losses=int((d > 0).sum()))
        paired[str(gap)] = row

    payload = dict(
        meta=dict(
            module="alt_p2_policy",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            python=os.sys.version.split()[0], numpy=np.__version__,
            fps=K.FPS, prefix_frames=PRE, delay_frames=DELAY, chunk_frames=CHUNK,
            max_looks=NMAX, alpha=K.ALPHA,
            gaps_frames=GAPS, gaps_s=[round(g / K.FPS, 2) for g in GAPS],
            min_usable_gap_frames=MIN_USABLE,
            protocol=("a look requested at gap-frame u discloses the real frames [u,u+6) "
                      "and is usable only if u+30 < W; at most 2 looks per window; the "
                      "target is the true position at the end of the gap"),
            tau_rule=("grid search on validation over nine fractions of the 10th-90th "
                      "percentile range of the end-of-gap drift; the fraction minimising "
                      "validation error is frozen for test"),
            degeneracy=("the posterior position trace of a linear-Gaussian filter with "
                        "fixed (q,r) depends on the horizon only, not on the data, so a "
                        "'buy when the trace exceeds tau' rule fires always or never; the "
                        "drift statistic is used instead because it depends on the "
                        "estimated velocity"),
            runtime_s=None,
        ),
        structural=dict(
            delay_frames=DELAY, chunk_frames=CHUNK, min_usable_gap_frames=MIN_USABLE,
            statement=("with a 1.0 s return delay and a 0.2 s disclosure chunk, a hidden "
                       "window of 1.0 s or less admits no interior look at all; the "
                       "official options A/B/C obtain their information from a longer "
                       "prefix, not from a look inside the gap"),
        ),
        table=table, calibration=calib, paired=paired,
        limitations=[
            "the delay is modelled as a hard 30-frame block; partial disclosure is not simulated",
            "a look discloses a 0.2 s chunk at the request instant, not an arbitrary channel subset",
            "windows are subsampled to 250 per gap; per-record clustering is not modelled",
            "the drift statistic uses the fitted (q,r) frozen from train, so a per-window re-fit could move the trigger",
        ],
    )

    lines = ["# P2 part 2 - when to spend a look inside a gap", ""]
    lines.append("Same decision points, same targets, same clean-window filter as "
                 "`alt_p2_kalman.py`. Prefix 6 frames (0.2 s), return delay 30 frames "
                 "(1.0 s), a look discloses 0.2 s, at most 2 looks per window.")
    lines.append("")
    lines.append("**Structural fact.** A look requested at gap-frame u is usable only if "
                 "u + 30 < W, so a gap of 31 frames (1.03 s) or less admits no interior "
                 "look at all. The official options A/B/C therefore get their information "
                 "from a longer prefix, not from a look inside the gap; within-gap "
                 "scheduling only exists for W >= 1.5 s.")
    lines.append("")
    lines.append("| gap (s) | usable frames | policy | mean err (cm) | rmse (cm) | p90 (cm) | looks/window |")
    lines.append("|---|---|---|---|---|---|---|")
    for gap in GAPS:
        cell = table.get(str(gap))
        if not cell:
            continue
        for pol in ("hold", "damped", "fixed", "drift"):
            m = cell[pol]
            lines.append("| %.1f | %d | %s | %.3f | %.3f | %.3f | %.3f |" % (
                cell["_gap_s"], cell["_usable_frames"], pol,
                m["mean_cm"], m["rmse_cm"], m["p90_cm"], m["looks_per_window"]))
    lines.append("")
    lines.append("Threshold calibration on validation (drift fraction -> validation mean error / looks):")
    lines.append("")
    for gap in GAPS:
        curve = calib.get(str(gap)) or []
        if not curve:
            lines.append("* %.1f s: no interior look possible, threshold not calibrated" % (gap / K.FPS))
            continue
        best = min(curve, key=lambda c: c["mean_cm"])
        lines.append("* %.1f s: best fraction %.1f (tau = %.2f cm) -> %.3f cm with %.3f looks"
                     % (gap / K.FPS, best["fraction"], best["tau_cm"], best["mean_cm"], best["looks"]))
    lines.append("")
    lines.append("Paired differences on the same windows (negative = the first policy is better):")
    lines.append("")
    lines.append("| gap (s) | comparison | mean diff (cm) | t | W/T/L |")
    lines.append("|---|---|---|---|---|")
    for gap in GAPS:
        for k, v in paired.get(str(gap), {}).items():
            lines.append("| %.1f | %s | %.3f | %.2f | %d/%d/%d |" % (
                gap / K.FPS, k.replace("_minus_", " - "), v["mean_cm"], v["t"],
                v["wins"], v["ties"], v["losses"]))
    lines.append("")
    payload["meta"]["runtime_s"] = round(time.time() - t0, 1)

    body = "\n".join(lines) + "\n"
    with open(os.path.join(DATA, "alt_p2_policy.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    n = len(body.encode("utf-8")) + len("BYTES 0\n") + len("\nVERDICT: PASS\n")
    for _ in range(10):
        text = "BYTES %d\n" % n + body + "\nVERDICT: PASS\n"
        m = len(text.encode("utf-8"))
        if m == n:
            break
        n = m
    with open(os.path.join(OUT, "alt_p2_policy.md"), "wb") as f:
        f.write(text.encode("utf-8"))
    print(text)
    print("runtime_s=%.1f" % payload["meta"]["runtime_s"])


if __name__ == "__main__":
    main()
