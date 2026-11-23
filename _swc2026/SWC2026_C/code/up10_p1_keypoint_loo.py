# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up10_p1_keypoint_loo.py -- leave-one-keypoint-out for the P1 representative point.

The paper justifies the representative point with three candidates (wrist, palm
centre, fingertip centroid). This script removes one keypoint at a time from the
palm set and from the fingertip set, and recomputes the same rigidity/jitter/
finger-sensitivity metrics on all 66,070 frames. It answers whether the choice
depends on any single keypoint.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import state_layer as S


def metrics_for(P, recs, pts):
    L, R, H, Q, rec = P["L"].astype(np.float64), P["R"].astype(np.float64), \
        P["H"].astype(np.float64), P["Q"].astype(np.float64), P["rec"]
    ds_of = recs.set_index("rec")["dataset"]
    resid, jitter, finger_std, dist = [], [], [], []
    for X in (L, R):
        e1 = X[:, 5] - X[:, 9]
        e1 /= np.linalg.norm(e1, axis=1, keepdims=True) + 1e-12
        e3 = np.cross(e1, X[:, 13] - X[:, 9])
        e3 /= np.linalg.norm(e3, axis=1, keepdims=True) + 1e-12
        e2 = np.cross(e3, e1)
        p = X[:, list(pts), :].mean(axis=1)
        rel = p - X[:, 9]
        loc = np.stack([np.sum(rel * e1, 1), np.sum(rel * e2, 1),
                        np.sum(rel * e3, 1)], 1)
        dist.append(np.linalg.norm(S.head_frame(p, H, Q), axis=1))
        pc = X[:, list(S.PALM), :].mean(axis=1)
        for r in np.unique(rec):
            mm = rec == r
            resid.append(float(np.linalg.norm(loc[mm] - loc[mm].mean(0), axis=1).mean()))
            finger_std.append(float(np.std(np.linalg.norm(p[mm] - pc[mm], axis=1))))
        step = np.linalg.norm(np.diff(p, axis=0), axis=1)
        jit = np.linalg.norm(p[1:-1] - 0.5 * (p[:-2] + p[2:]), axis=1)
        jitter.append(float(np.median(jit) / (np.median(step[step > 1e-9]) + 1e-12)))
    rec2 = np.concatenate([rec, rec])
    d = np.concatenate(dist)
    by_ds = {}
    for ds in ("EgoDemo", "EgoPro", "EgoStandard"):
        m = np.isin(rec2, ds_of[ds_of == ds].index.values)
        by_ds[ds] = float(d[m].mean())
    return dict(n_points=len(pts), rigidity_cm=float(np.mean(resid) * 100),
                jitter_ratio=float(np.mean(jitter)),
                finger_pose_sensitivity_cm=float(np.mean(finger_std) * 100),
                dhead_by_dataset_m={k: round(v, 4) for k, v in by_ds.items()},
                cross_dataset_spread_m=float(max(by_ds.values()) - min(by_ds.values())))


def main():
    P, recs = S.panel()
    palm = list(S.PALM)
    tips = list(S.TIPS)
    cands = {"wrist_kp0": [0], "palm_full": palm, "tips_full": tips}
    for k in palm[1:]:          # wrist is the anchor; drop the four MCP joints
        cands[f"palm_minus_kp{k}"] = [x for x in palm if x != k]
    for k in tips:
        cands[f"tips_minus_kp{k}"] = [x for x in tips if x != k]
    rows = []
    for name, pts in cands.items():
        m = metrics_for(P, recs, pts)
        m["name"] = name
        rows.append(m)
        print(name, round(m["rigidity_cm"], 4), round(m["jitter_ratio"], 4))
    base = next(r for r in rows if r["name"] == "palm_full")
    for r in rows:
        r["d_rigidity_vs_palm_cm"] = r["rigidity_cm"] - base["rigidity_cm"]
        r["d_jitter_vs_palm"] = r["jitter_ratio"] - base["jitter_ratio"]
    out = dict(
        note=("palm_full is the paper's representative point. Each row removes one "
              "keypoint; a small |d_rigidity| means the choice does not rest on it."),
        n_frames=66070, rows=rows,
        max_abs_d_rigidity_cm=float(max(abs(r["d_rigidity_vs_palm_cm"]) for r in rows)),
    )
    path = os.path.join(ROOT, "data", "up10_p1_keypoint_loo.json")
    open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, indent=1, ensure_ascii=False))
    print("wrote", path, "max |d rigidity| cm", out["max_abs_d_rigidity_cm"])


if __name__ == "__main__":
    main()