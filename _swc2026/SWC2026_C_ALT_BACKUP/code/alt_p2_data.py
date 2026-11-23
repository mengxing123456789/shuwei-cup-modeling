#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the frame panel used by alt_p2_kalman.py, directly from the official raw data.

Outputs (inside the ALT backup workspace only):
    data/panel_alt.npz          L,R (N,21,3) world coords; H (N,3); Q (N,4 wxyz);
                                t (N,), badL,badR (N,), rec (N,)
    data/panel_alt_records.csv  one row per record with split / environment

The reader mirrors the official P2 convention: 30 fps, MediaPipe 21-keypoint
topology (0 wrist, 1-4 thumb, 5-8 index, 9-12 middle, 13-16 ring, 17-20 pinky).
Nothing is written outside this workspace.
"""
from __future__ import annotations
# Data root is environment-driven so the package carries no machine identity:
#   set RESTOCK_DATA_ROOT to the folder where you unpacked Restocking_Problem_and_Data_EN.
import os as _os
_RESTOCK_DATA_ROOT = _os.environ.get(
    "RESTOCK_DATA_ROOT",
    _os.path.join(_os.path.expanduser("~"), "Desktop", "Restocking_Problem_and_Data_EN"),
)


import glob
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
RAW_CANDIDATES = [
    os.environ.get("MM_C_RAW_ROOT", ""),
    _RESTOCK_DATA_ROOT,
    os.environ.get("MM_C_RAW_FALLBACK", ""),
]
ATT_CANDIDATES = [
    os.environ.get("MM_C_PROBLEM_ROOT", ""),
    _os.path.join(_RESTOCK_DATA_ROOT, "Restocking_Tasks_and_Constraints"),
]


def _first_existing(cands, needle):
    for c in cands:
        if c and os.path.exists(os.path.join(c, needle)):
            return c
    raise FileNotFoundError(f"none of {cands} contains {needle}")


RAW = _first_existing(RAW_CANDIDATES, "Raw_Data")
ATT = _first_existing(ATT_CANDIDATES, "record_split.csv")
# RAW may be either the folder that directly contains Raw_Data, or Raw_Data itself.
RAW_DATA = os.path.join(RAW, "Raw_Data") if os.path.isdir(os.path.join(RAW, "Raw_Data")) else RAW


def _stack_cells(col):
    return np.stack([np.stack([np.asarray(v, dtype=np.float32) for v in row]) for row in col.values])


def _demo_bad_array(path, n, total):
    bl = np.zeros(n, bool)
    br = np.zeros(n, bool)
    if not os.path.exists(path):
        return bl, br
    d = json.load(open(path, encoding="utf-8"))
    for it in d.get("hand_bad_frame_details", []):
        f = int(it["frame"])
        if f >= total:
            f -= 1
        if 0 <= f < n:
            if it.get("left_bad_reason"):
                bl[f] = True
            if it.get("right_bad_reason"):
                br[f] = True
    return bl, br


def read_demo(p):
    d = pd.read_parquet(os.path.join(p, "data", "chunk-000", "file-000.parquet"))
    t = d["timestamp"].to_numpy(np.float32)
    l = _stack_cells(d["observation.state.hand_left_world"]).astype(np.float32)
    r = _stack_cells(d["observation.state.hand_right_world"]).astype(np.float32)
    h = _stack_cells(d["observation.state.head_world"])[:, 0].astype(np.float32)
    q = _stack_cells(d["observation.state.head_world_rotation"])[:, 0].astype(np.float32)
    total = int(json.load(open(os.path.join(p, "meta", "info.json"), encoding="utf-8"))["total_frames"])
    bl, br = _demo_bad_array(os.path.join(p, "bad_frame_ratio.json"), len(t), total)
    return t, l, r, h, q, bl, br


def read_pose(p):
    def rd(name):
        return pd.read_csv(os.path.join(p, "tables", name), encoding="utf-8-sig")

    def joints(df):
        cols = [f"transforms[{i}].pos.{a}" for i in range(21) for a in "xyz"]
        return df[cols].to_numpy(np.float32).reshape(len(df), 21, 3)

    ldf, rdf = rd("pose_left_hand.csv"), rd("pose_right_hand.csv")
    hdf, bdf = rd("pose_head.csv"), rd("annotation_bad_frame_pose_hand.csv")
    n = min(len(ldf), len(rdf), len(hdf), len(bdf))
    t = hdf["_offset_from_first_log_s"].to_numpy(np.float32)[:n]
    l, r = joints(ldf)[:n], joints(rdf)[:n]
    h = hdf[[f"transforms[0].pos.{a}" for a in "xyz"]].to_numpy(np.float32)[:n]
    q = hdf[[f"transforms[0].quat.{a}" for a in "wxyz"]].to_numpy(np.float32)[:n]
    bad = bdf["is_bad"].astype(bool).to_numpy()[:n]
    return t, l, r, h, q, bad, bad.copy()


def main():
    os.makedirs(DATA, exist_ok=True)
    idx = pd.read_csv(os.path.join(ATT, "source_segment_index.csv"), encoding="utf-8-sig")
    meta = {}
    for ds in ("EgoDemo", "EgoPro", "EgoStandard"):
        sub = idx[idx.dataset == ds]
        for sample, g in sub.groupby("sample"):
            row = g.iloc[0]
            meta[(ds, str(sample))] = dict(uuid=row.episode_uuid, split=row.split,
                                           env=row.environment_id)

    L, R, H, Q, T, BL, BR, REC = [], [], [], [], [], [], [], []
    records = []
    for ds in ("EgoDemo", "EgoPro", "EgoStandard"):
        base = os.path.join(RAW_DATA, ds)
        if not os.path.isdir(base):
            continue
        for sample in sorted(os.listdir(base)):
            p = os.path.join(base, sample)
            if not os.path.isdir(p):
                continue
            if ds == "EgoDemo":
                t, l, r, h, q, bl, br = read_demo(p)
            else:
                t, l, r, h, q, bl, br = read_pose(p)
            key = (ds, sample)
            if key not in meta:
                raise KeyError(f"{key} missing from source_segment_index.csv")
            rid = len(records)
            n = len(t)
            records.append(dict(rec=rid, dataset=ds, sample=sample, uuid=meta[key]["uuid"],
                                env=meta[key]["env"], split=meta[key]["split"], n=n,
                                dur=float(t[-1] - t[0]),
                                fps=float((n - 1) / max(t[-1] - t[0], 1e-6)),
                                badL=float(bl.mean()), badR=float(br.mean())))
            L.append(l); R.append(r); H.append(h); Q.append(q); T.append(t)
            BL.append(bl); BR.append(br); REC.append(np.full(n, rid, np.int16))
            print(f"[{ds}] {sample} n={n} dur={t[-1]-t[0]:.1f}s split={meta[key]['split']}", flush=True)

    out = dict(L=np.concatenate(L), R=np.concatenate(R), H=np.concatenate(H),
               Q=np.concatenate(Q), t=np.concatenate(T), badL=np.concatenate(BL),
               badR=np.concatenate(BR), rec=np.concatenate(REC))
    np.savez_compressed(os.path.join(DATA, "panel_alt.npz"), **out)
    rec_df = pd.DataFrame(records)
    rec_df.to_csv(os.path.join(DATA, "panel_alt_records.csv"), index=False, encoding="utf-8")
    print("records", len(rec_df), "frames", len(out["t"]))
    print(rec_df.groupby(["dataset", "split"]).size().to_string())


if __name__ == "__main__":
    main()
