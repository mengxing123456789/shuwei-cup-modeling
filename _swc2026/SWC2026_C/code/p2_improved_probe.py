
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 improvement probe: feature/linear diagnostics before committing a GPU model.

No existing artifacts are overwritten.  Writes data/p2_improved_probe.json.

Protocol
--------
* target: dominant-hand wrist position in head frame, displacement from the last
  observed frame (anchor), horizons L in {6,18,30,60} frames.
* windows: every clean start (no annotated bad frame in context+target), exactly
  the `train_gpu_p2.windows` / `p2_masked.windows` window set.
* split: train 55 records / validation 7 / test 7 records.  Alpha and all model
  choices are made on validation only; test is touched once in this script.
* metrics: 3-D RMSE (cm), per-coordinate RMSE (cm), endpoint within-2cm.

The probe answers three questions cheaply:
  1. does a longer context (20/30 frames) help, or is 10 frames enough?
  2. does predicting the *residual over constant velocity* beat direct regression?
  3. which feature block (other hand, hand shape, absolute anchor/head motion)
     actually carries signal on validation?
"""
import json
import os
import time

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "p2_improved_probe.json")
LENS = [6, 18, 30, 60]
CTXS = [10, 20, 30]
ALPHAS = [0.1, 1.0, 10.0, 100.0, 1000.0]
WRIST_L = slice(0, 3)
WRIST_R = slice(32, 35)


def quat_to_R(q):
    q = np.asarray(q, dtype=np.float64)
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3), np.float64)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z)
    R[:, 0, 1] = 2 * (x * y - z * w)
    R[:, 0, 2] = 2 * (x * z + y * w)
    R[:, 1, 0] = 2 * (x * y + z * w)
    R[:, 1, 1] = 1 - 2 * (x * x + z * z)
    R[:, 1, 2] = 2 * (y * z - x * w)
    R[:, 2, 0] = 2 * (x * z - y * w)
    R[:, 2, 1] = 2 * (y * z + x * w)
    R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def load():
    st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    z = np.load(os.path.join(DATA, "panel.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    rec = st["rec"].astype(np.int64)
    dom = st["dom"].astype(np.int64)
    rich = np.concatenate([st["fl"], st["fr"], st["gl"], st["gr"]],
                          axis=1).astype(np.float32)
    badL, badR = st["badL"].astype(bool), st["badR"].astype(bool)
    slices = {}
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        slices[int(r)] = (int(ii[0]), int(ii[-1]) + 1)
    # head motion: gravity direction expressed in head frame and head velocity.
    R = quat_to_R(z["Q"])                       # head -> world
    H = z["H"].astype(np.float64)               # head position in world
    Rh = np.transpose(R, (0, 2, 1))             # world -> head
    g_world = np.array([0.0, 0.0, -1.0])
    grav = np.einsum("nij,j->ni", Rh, g_world).astype(np.float32)
    head_v = np.zeros_like(H)
    head_v[1:] = np.diff(H, axis=0) * 30.0
    head_vh = np.einsum("nij,nj->ni", Rh, head_v).astype(np.float32)
    # angular velocity from consecutive orientation matrices (world frame,
    # then rotated into the current head frame).  Small-angle log map.
    ang = np.zeros_like(H)
    rel = np.einsum("nji,njk->nik", R[:-1], R[1:])   # R_i^T R_{i+1}
    vee = np.stack([rel[:, 2, 1] - rel[:, 1, 2],
                    rel[:, 0, 2] - rel[:, 2, 0],
                    rel[:, 1, 0] - rel[:, 0, 1]], axis=1) * 0.5
    ang[1:] = vee * 30.0
    ang = np.einsum("nij,nj->ni", Rh, ang).astype(np.float32)
    return recs, rec, dom, badL, badR, rich, slices, grav, head_vh, ang


def build(recs, rec, dom, badL, badR, rich, slices, grav, head_v, ang,
          split, L, C):
    """Return feature packet and targets for all clean windows with context C."""
    xs, ys, rec_ids, anchors_abs, statics = [], [], [], [], []
    for r in recs[recs.split == split].rec.astype(int):
        lo, hi = slices[r]
        d = int(dom[r])
        bad = (badL[lo:hi] if d == 0 else badR[lo:hi]).astype(bool)
        wrist = rich[lo:hi, WRIST_L if d == 0 else WRIST_R]
        other = rich[lo:hi, WRIST_R if d == 0 else WRIST_L]
        dblock = rich[lo:hi, 0:32] if d == 0 else rich[lo:hi, 32:64]
        oblock = rich[lo:hi, 32:64] if d == 0 else rich[lo:hi, 0:32]
        n = hi - lo
        span = C + L
        if n <= span:
            continue
        clean = np.lib.stride_tricks.sliding_window_view(bad, span).sum(axis=1) == 0
        idx = np.flatnonzero(clean)
        if len(idx) == 0:
            continue
        anchor_i = idx + C - 1
        y = wrist[anchor_i[:, None] + 1 + np.arange(L)[None, :]] - wrist[anchor_i][:, None, :]
        rel_dom = np.stack([wrist[i:i + C] - wrist[i + C - 1] for i in idx])
        rel_oth = np.stack([other[i:i + C] - wrist[i + C - 1] for i in idx])
        # hand descriptors: all 32 dims at the anchor frame, first 3 made relative.
        d_anchor = np.stack([dblock[i + C - 1] for i in idx]).copy()
        d_anchor[:, 0:3] -= wrist[anchor_i]
        o_anchor = np.stack([oblock[i + C - 1] for i in idx]).copy()
        o_anchor[:, 0:3] -= wrist[anchor_i]
        xs.append((rel_dom.astype(np.float32), rel_oth.astype(np.float32),
                   d_anchor.astype(np.float32), o_anchor.astype(np.float32)))
        ys.append(y.astype(np.float32))
        rec_ids.append(np.full(len(idx), r, np.int32))
        anchors_abs.append(wrist[anchor_i].astype(np.float32))
        ai = lo + anchor_i
        statics.append(np.concatenate([
            grav[ai], head_v[ai], ang[ai],
            rich[ai, 64:80],                 # dominant geometry at anchor
        ], axis=1).astype(np.float32))
    if not xs:
        return None
    x = tuple(np.concatenate([row[k] for row in xs], axis=0) for k in range(4))
    return dict(x=x, y=np.concatenate(ys), rec=np.concatenate(rec_ids),
                anchor=np.concatenate(anchors_abs), static=np.concatenate(statics))


def features(p, kind):
    rel_dom, rel_oth, d_anchor, o_anchor = p["x"]
    C = rel_dom.shape[1]
    # dynamic summaries from the dominant hand descriptors (velocity at 21:24,
    # acceleration at 24:27, aperture 27, reach 28, palm 29, normal 30:33? -> use
    # only the stable, documented columns: velocity, accel, speed, accnorm).
    if kind == "base":       # exact spirit of the existing CPU ridge
        v = rel_dom[:, -1] - rel_dom[:, -2]
        a = rel_dom[:, -1] - 2 * rel_dom[:, -2] + rel_dom[:, -3]
        return np.concatenate([rel_dom.reshape(len(rel_dom), -1), v, a], axis=1)
    if kind == "both":
        v = rel_dom[:, -1] - rel_dom[:, -2]
        a = rel_dom[:, -1] - 2 * rel_dom[:, -2] + rel_dom[:, -3]
        vo = rel_oth[:, -1] - rel_oth[:, -2]
        ao = rel_oth[:, -1] - 2 * rel_oth[:, -2] + rel_oth[:, -3]
        return np.concatenate([rel_dom.reshape(len(rel_dom), -1),
                               rel_oth.reshape(len(rel_oth), -1),
                               v, a, vo, ao], axis=1)
    if kind == "hand":
        v = rel_dom[:, -1] - rel_dom[:, -2]
        a = rel_dom[:, -1] - 2 * rel_dom[:, -2] + rel_dom[:, -3]
        vo = rel_oth[:, -1] - rel_oth[:, -2]
        ao = rel_oth[:, -1] - 2 * rel_oth[:, -2] + rel_oth[:, -3]
        # descriptors at anchor: normal(6), aperture/reach/palm(3 from col 27..29),
        # velocity(3), accel(3), speed/accnorm(2) -- duplicated motion is fine.
        return np.concatenate([rel_dom.reshape(len(rel_dom), -1),
                               rel_oth.reshape(len(rel_oth), -1),
                               d_anchor, o_anchor, v, a, vo, ao], axis=1)
    if kind == "full":
        base = features(p, "hand")
        return np.concatenate([base, p["anchor"], p["static"]], axis=1)
    raise ValueError(kind)


def metrics(pred, y):
    e = pred - y
    d = np.sqrt((e ** 2).sum(axis=2))
    return dict(rmse_cm=float(np.sqrt((d ** 2).mean()) * 100),
                rmse_coord_cm=float(np.sqrt((e ** 2).mean()) * 100),
                end_rmse_cm=float(np.sqrt((d[:, -1] ** 2).mean()) * 100),
                within_2cm=float((d[:, -1] <= 0.02).mean()),
                median_end_cm=float(np.median(d[:, -1]) * 100))


def fit_ridge(Xtr, Ytr, Xva, Yva, Xte, resid, L):
    """Alpha selected by validation 3-D RMSE, then one test evaluation.

    All alphas share one eigendecomposition of the centred Gram matrix, so the
    alpha grid is effectively free.
    """
    Ytr = Ytr.reshape(len(Ytr), -1)
    mu = Xtr.mean(axis=0)
    Xc = Xtr - mu
    ym = Ytr.mean(axis=0)
    Yc = Ytr - ym
    G = Xc.T @ Xc
    B = Xc.T @ Yc
    evals, evec = np.linalg.eigh(G)
    evals = np.maximum(evals, 0.0)
    Xv = Xva - mu
    Xt = Xte - mu
    Cv = Xv @ evec
    Ct = Xt @ evec
    Bt = evec.T @ B
    best = (1e9, None, None, None)
    for alpha in ALPHAS:
        coef = evec @ (Bt / (evals[:, None] + alpha))
        pv = (Cv @ (Bt / (evals[:, None] + alpha)) + ym).reshape(len(Yva), L, 3)
        vm = float(np.sqrt(np.mean((pv - Yva.reshape(len(Yva), L, 3)) ** 2)) * 100)
        if vm < best[0]:
            pt = (Ct @ (Bt / (evals[:, None] + alpha)) + ym).reshape(len(Xte), L, 3)
            best = (vm, alpha, pt, coef)
    return best[1], best[0], best[2]


def main():
    t0 = time.time()
    recs, rec, dom, badL, badR, rich, slices, grav, hv, ang = load()
    # patch geometry into rich? rich is fl/fr/gl/gr; gl starts at 64.  The hand
    # descriptor blocks used above are fl/fr only; static carries gl/gr.
    out = {"_meta": {
        "script": "p2_improved_probe.py",
        "window_protocol": "all clean starts, no bad frame in context+target; same as train_gpu_p2",
        "metrics": "3-D RMSE and per-coordinate RMSE in cm; endpoint within-2cm",
        "selection": "ridge alpha and feature block by validation only; test evaluated once",
        "contexts": CTXS, "horizons": LENS, "alphas": ALPHAS,
    }, "rows": []}
    for C in CTXS:
        for L in LENS:
            tr = build(recs, rec, dom, badL, badR, rich, slices, grav, hv, ang, "train", L, C)
            va = build(recs, rec, dom, badL, badR, rich, slices, grav, hv, ang, "validation", L, C)
            te = build(recs, rec, dom, badL, badR, rich, slices, grav, hv, ang, "test", L, C)
            if tr is None or va is None or te is None:
                continue
            v_last = tr["x"][0][:, -1] - tr["x"][0][:, -2]
            vv_last = va["x"][0][:, -1] - va["x"][0][:, -2]
            vt_last = te["x"][0][:, -1] - te["x"][0][:, -2]
            # (x is a tuple: rel_dom, rel_oth, d_anchor, o_anchor)
            h = np.arange(1, L + 1)[None, :, None]
            # hold / cv baselines
            for name, pv, pt in [
                ("hold", np.zeros_like(va["y"]), np.zeros_like(te["y"])),
                ("cv", vv_last[:, None, :] * h, vt_last[:, None, :] * h),
            ]:
                out["rows"].append(dict(context=C, L=L, model=name,
                                        n_train=int(len(tr["y"])), n_val=int(len(va["y"])),
                                        n_test=int(len(te["y"])),
                                        val=metrics(pv, va["y"]), test=metrics(pt, te["y"])))
            for kind in ["base", "both", "hand", "full"]:
                Xtr, Xva, Xte = (features(tr, kind), features(va, kind), features(te, kind))
                Xtr = np.nan_to_num(Xtr); Xva = np.nan_to_num(Xva); Xte = np.nan_to_num(Xte)
                for resid in [False, True]:
                    if resid:
                        Ytr = tr["y"] - v_last[:, None, :] * h
                        Yva = va["y"] - vv_last[:, None, :] * h
                    else:
                        Ytr, Yva = tr["y"], va["y"]
                    alpha, vm, pt = fit_ridge(Xtr, Ytr, Xva, Yva, Xte, resid, L)
                    if resid:
                        pt = pt + vt_last[:, None, :] * h
                    out["rows"].append(dict(
                        context=C, L=L, model=f"ridge_{kind}" + ("_resid" if resid else ""),
                        alpha=alpha, val_rmse_coord_cm=vm,
                        n_train=int(len(tr["y"])), n_val=int(len(va["y"])),
                        n_test=int(len(te["y"])), test=metrics(pt, te["y"])))
                print(f"C={C} L={L} {kind} done ({time.time()-t0:.1f}s)", flush=True)
            # compact leaderboard for this cell
            rows = [r for r in out["rows"] if r["context"] == C and r["L"] == L and "val" in r]
            rr = [r for r in out["rows"] if r["context"] == C and r["L"] == L and "val_rmse_coord_cm" in r]
            print(f"  cell C={C} L={L}: n={len(te['y'])} "
                  f"best-val {min(rr, key=lambda z: z['val_rmse_coord_cm'])['model']}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", OUT, out["seconds"], "s", flush=True)


if __name__ == "__main__":
    main()