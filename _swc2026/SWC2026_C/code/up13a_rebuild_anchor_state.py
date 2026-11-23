# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up13a_rebuild_anchor_state.py -- rebuild state features around three representative points.

The paper's Part I picks a representative point for the hand and then argues
that the palm centroid is the right choice.  The leave-one-keypoint sweep in
``up10`` shows the palm centroid is insensitive to any single MCP joint, but it
does *not* retrain the downstream models under a different representative
point.  This script produces the three state tensors needed for that test.

Representative points
---------------------
``wrist``  keypoint 0, the anatomical wrist (what ``p1_state.py`` currently uses)
``palm``   centroid of keypoints 0, 5, 9, 13, 17 (wrist + four MCP joints)
``tips``   centroid of keypoints 4, 8, 12, 16, 20 (the five fingertips)

Only the features that are *anchored* to the representative point change:
reach, the palm normal, the forward axis, and the first/second derivatives.
The five landmark coordinates, the aperture, the palm width and the eight
geometric observability features are unchanged, because they are defined from
landmark pairs and not from the anchor.  Keeping them fixed is deliberate: it
isolates the effect of the representative point instead of confounding it with
a wholesale feature redefinition.

Outputs ``data/state_anchor_wrist.npz``, ``..._palm.npz``, ``..._tips.npz`` and
``data/up13_anchor_features.json``.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common import DATA, quat_to_R, write_json

ANCHORS = {
    "wrist": [0],
    "palm": [0, 5, 9, 13, 17],
    "tips": [4, 8, 12, 16, 20],
}

Z = np.load(os.path.join(DATA, "panel.npz"))
L, R, H, Q, T, REC = Z["L"], Z["R"], Z["H"], Z["Q"], Z["t"], Z["rec"]
badL, badR = Z["badL"], Z["badR"]

Rh = quat_to_R(Q)
Rht = np.transpose(Rh, (0, 2, 1))


def to_head(P):
    return np.einsum("nij,nkj->nki", Rht, P - H[:, None, :])


def hand_feats_anchor(P, side, idx):
    """Same 32 columns as ``p1_state.hand_feats`` but anchored on ``idx``."""
    anchor = P[:, idx, :].mean(axis=1)
    thumb_tip, index_tip = P[:, 4], P[:, 8]
    index_mcp, little_mcp, mid_mcp = P[:, 5], P[:, 17], P[:, 9]
    palm_w = np.linalg.norm(index_mcp - little_mcp, axis=1) + 1e-6
    aperture = np.linalg.norm(thumb_tip - index_tip, axis=1) / palm_w
    reach = np.linalg.norm(index_tip - anchor, axis=1) / palm_w
    n = np.cross(index_mcp - anchor, little_mcp - anchor)
    n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    fwd = mid_mcp - anchor
    fwd = fwd / (np.linalg.norm(fwd, axis=1, keepdims=True) + 1e-9)
    v = np.zeros_like(anchor)
    a = np.zeros_like(anchor)
    for _, g in pd.DataFrame({"rec": REC}).groupby("rec").groups.items():
        ii = np.asarray(g)
        tt = T[ii]
        if len(ii) < 4:
            continue
        for k in range(3):
            v[ii, k] = np.gradient(anchor[ii, k], tt)
            a[ii, k] = np.gradient(v[ii, k], tt)
    feats = np.concatenate([
        P[:, 0], P[:, 4], P[:, 8], P[:, 5], P[:, 17],
        aperture[:, None], reach[:, None], palm_w[:, None],
        n, fwd, v, a,
        np.linalg.norm(v, axis=1)[:, None], np.linalg.norm(a, axis=1)[:, None],
    ], axis=1)
    return feats.astype(np.float32)


def geom_feats(P, side):
    """Identical to ``p1_state.geom_feats`` (no anchor dependence)."""
    n = len(P)
    d = np.linalg.norm(np.diff(P, axis=1), axis=2)
    med = np.median(d, axis=1)[:, None]
    bone_cv = np.std(d / (med + 1e-6), axis=1)
    fingers = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]
    coll = np.zeros(n)
    for fi in fingers:
        Qf = P[:, fi, :] - P[:, fi, :].mean(axis=1, keepdims=True)
        s = np.linalg.svd(Qf, compute_uv=False)
        coll += np.sqrt(s[:, 1] ** 2 + s[:, 2] ** 2) / (s[:, 0] + 1e-9)
    coll /= 5
    pair = np.linalg.norm(P[:, :, None, :] - P[:, None, :, :], axis=-1)
    pair[:, np.arange(21), np.arange(21)] = np.inf
    min_gap = pair.reshape(n, -1).min(axis=1) / (med[:, 0] + 1e-6)
    bbox = P.max(axis=1) - P.min(axis=1)
    vol = bbox[:, 0] * bbox[:, 1] * bbox[:, 2]
    z_std = P[:, :, 2].std(axis=1)
    palm_w = np.linalg.norm(P[:, 5] - P[:, 17], axis=1)
    step = np.linalg.norm(np.diff(P, axis=0), axis=2)
    jump = np.concatenate([[0.0], np.median(step, axis=1)]) / (med[:, 0] + 1e-6)
    jmax = np.concatenate([[0.0], step.max(axis=1)]) / (med[:, 0] + 1e-6)
    return np.stack([coll, bone_cv, min_gap, vol, z_std, palm_w, jump, jmax], axis=1).astype(np.float32)


def main():
    Pl, Pr = to_head(L), to_head(R)
    gl, gr = geom_feats(Pl, "L"), geom_feats(Pr, "R")
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    meta = {}

    # dominant hand stays as in the original pipeline (wrist path length)
    dom = np.zeros(len(recs), np.int8)
    for r in range(len(recs)):
        ii = np.where(REC == r)[0]
        dl = np.linalg.norm(np.diff(Pl[ii, 0], axis=0), axis=1).sum()
        dr = np.linalg.norm(np.diff(Pr[ii, 0], axis=0), axis=1).sum()
        dom[r] = 0 if dl >= dr else 1

    for name, idx in ANCHORS.items():
        fl = hand_feats_anchor(Pl, "L", idx)
        fr = hand_feats_anchor(Pr, "R", idx)
        out = os.path.join(DATA, "state_anchor_%s.npz" % name)
        np.savez_compressed(out,
                            fl=fl, fr=fr, gl=gl, gr=gr, dom=dom,
                            badL=badL, badR=badR, rec=REC, t=T,
                            validL=np.isfinite(fl).all(1),
                            validR=np.isfinite(fr).all(1))
        # a sanity metric: how far the anchored motion features move
        meta[name] = dict(
            anchor_keypoints=idx,
            speed_mean=float(np.nanmean(fl[:, -2])),
            speed_p95=float(np.nanpercentile(fl[:, -2], 95)),
            acc_mean=float(np.nanmean(fl[:, -1])),
            reach_mean=float(np.nanmean(fl[:, 16])),
            path_length_m=float(np.nansum(np.linalg.norm(np.diff(fl[:, 0:3], axis=0), axis=1))),
            bytes=int(os.path.getsize(out)),
        )
        print(name, "speed_mean %.4f reach_mean %.4f bytes %d"
              % (meta[name]["speed_mean"], meta[name]["reach_mean"], meta[name]["bytes"]),
              flush=True)

    write_json("up13_anchor_features.json", dict(
        _meta=dict(note="state tensors rebuilt around three representative points; only "
                        "anchor-dependent columns (reach, normal, forward, velocity, "
                        "acceleration, speed, accnorm) change",
                   anchors={k: v for k, v in ANCHORS.items()}),
        by_anchor=meta))


if __name__ == "__main__":
    main()
