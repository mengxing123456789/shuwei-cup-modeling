
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Build a harmonised frame panel (all 69 records) + segment table.

Outputs:
  data/panel.npz         L,R (N,21,3) head-frame later; here world coords
                         H (N,3), Q (N,4 wxyz), t, badL, badR, rec
  data/panel_records.csv one row per record with split / environment
  data/segments.csv      one row per annotated segment
"""
import os, json, glob
import numpy as np
import pandas as pd
from common import (CD, DATA, ensure_dirs, load_index, load_split, quat_to_R)

ensure_dirs()
idx = load_index()
sp = load_split()

# sample -> meta (uuid/env/split); EgoDemo uses E001, others use uuid dir names
meta = {}
for ds in ["EgoDemo", "EgoPro", "EgoStandard"]:
    sub = idx[idx.dataset == ds]
    for sample, g in sub.groupby("sample"):
        r = g.iloc[0]
        meta[(ds, str(sample))] = dict(uuid=r.episode_uuid, env=r.environment_id,
                                       split=r.split, scene=getattr(r, "scene_id", ""))

records, segs = [], []
L, R, H, Q, T, BL, BR, REC = [], [], [], [], [], [], [], []


def demo_bad_array(path, n, total):
    d = json.load(open(path, encoding="utf-8"))
    bl = np.zeros(n, bool); br = np.zeros(n, bool)
    reasons_l, reasons_r = {}, {}
    for it in d.get("hand_bad_frame_details", []):
        f = int(it["frame"])
        if f >= total:  # 1-based fallback
            f -= 1
        if 0 <= f < n:
            if it.get("left_bad_reason"):
                bl[f] = True; reasons_l[it["left_bad_reason"]] = reasons_l.get(it["left_bad_reason"], 0) + 1
            if it.get("right_bad_reason"):
                br[f] = True; reasons_r[it["right_bad_reason"]] = reasons_r.get(it["right_bad_reason"], 0) + 1
    return bl, br, reasons_l, reasons_r


def stack_cells(col, shape):
    return np.stack([np.stack([np.asarray(v) for v in row]) for row in col.values]).astype(np.float32)


def read_demo(p):
    d = pd.read_parquet(os.path.join(p, "data", "chunk-000", "file-000.parquet"))
    t = d["timestamp"].to_numpy(np.float32)
    l = stack_cells(d["observation.state.hand_left_world"], (21, 3))
    r = stack_cells(d["observation.state.hand_right_world"], (21, 3))
    h = stack_cells(d["observation.state.head_world"], (1, 3))[:, 0]
    q = stack_cells(d["observation.state.head_world_rotation"], (1, 4))[:, 0]
    total = int(json.load(open(os.path.join(p, "meta", "info.json"), encoding="utf-8"))["total_frames"])
    bl, br, rl, rr = demo_bad_array(os.path.join(p, "bad_frame_ratio.json"), len(t), total)
    ann = json.load(open(os.path.join(p, "annotation.json"), encoding="utf-8"))
    sg = [(s["start_time"], s["end_time"], s.get("description", ""), s.get("subtask_id", ""))
          for s in ann.get("subtask_annotations", [])]
    desc = ann.get("episode_description", "")
    return t, l, r, h, q, bl, br, sg, desc, int(total), {"left": rl, "right": rr}


def read_pose_ds(p):
    def rd(name):
        return pd.read_csv(os.path.join(p, "tables", name), encoding="utf-8-sig")

    def joints(df):
        cols = [f"transforms[{i}].pos.{a}" for i in range(21) for a in "xyz"]
        return df[cols].to_numpy(np.float32).reshape(len(df), 21, 3)

    ldf = rd("pose_left_hand.csv"); rdf = rd("pose_right_hand.csv")
    hdf = rd("pose_head.csv"); bdf = rd("annotation_bad_frame_pose_hand.csv")
    n = min(len(ldf), len(rdf), len(hdf), len(bdf))
    t = hdf["_offset_from_first_log_s"].to_numpy(np.float32)[:n]
    l = joints(ldf)[:n]; r = joints(rdf)[:n]
    h = hdf[[f"transforms[0].pos.{a}" for a in "xyz"]].to_numpy(np.float32)[:n]
    q = hdf[[f"transforms[0].quat.{a}" for a in "wxyz"]].to_numpy(np.float32)[:n]
    bad = bdf["is_bad"].astype(bool).to_numpy()[:n]
    types = {}
    for c in [c for c in bdf.columns if c.startswith("problem_type[")]:
        for v in bdf[c].dropna().astype(str):
            types[v] = types.get(v, 0) + 1
    sg = []
    try:
        sdf = rd("annotation_semantic_segments.csv")
        for _, s in sdf.iterrows():
            sg.append((float(s["segment.start_time"]), float(s["segment.end_time"]),
                       str(s.get("segment.subtask_description", "")), ""))
        desc = str(sdf["task_description"].iloc[0]) if len(sdf) else ""
    except Exception:
        desc = ""
    return t, l, r, h, q, bad, bad.copy(), sg, desc, n, types


for ds, sample, p in [x for ds in ["EgoDemo", "EgoPro", "EgoStandard"]
                      for x in [(ds, s, os.path.join(CD, ds, s))
                                for s in sorted(os.listdir(os.path.join(CD, ds)))
                                if os.path.isdir(os.path.join(CD, ds, s))]]:
    if ds == "EgoDemo":
        t, l, r, h, q, bl, br, sg, desc, total, types = read_demo(p)
    else:
        t, l, r, h, q, bl, br, sg, desc, total, types = read_pose_ds(p)
    m = meta[(ds, sample)]
    rid = len(records)
    n = len(t)
    records.append(dict(rec=rid, dataset=ds, sample=sample, uuid=m["uuid"], env=m["env"],
                        split=m["split"], scene=m["scene"], n=n, total=total,
                        t0=float(t[0]), t1=float(t[-1]), dur=float(t[-1] - t[0]),
                        fps=float((n - 1) / max(t[-1] - t[0], 1e-6)),
                        badL=float(bl.mean()), badR=float(br.mean()),
                        bad_types=json.dumps(types, ensure_ascii=False),
                        description=desc[:200]))
    for k, (a, b, txt, sid) in enumerate(sg):
        segs.append(dict(rec=rid, dataset=ds, sample=sample, env=m["env"], split=m["split"],
                         seg=k, start=float(a), end=float(b), dur=float(b - a),
                         label=txt, sid=sid))
    L.append(l); R.append(r); H.append(h); Q.append(q)
    T.append(t); BL.append(bl); BR.append(br); REC.append(np.full(n, rid, np.int16))

L = np.concatenate(L); R = np.concatenate(R); H = np.concatenate(H); Q = np.concatenate(Q)
T = np.concatenate(T); BL = np.concatenate(BL); BR = np.concatenate(BR); REC = np.concatenate(REC)
np.savez_compressed(os.path.join(DATA, "panel.npz"),
                    L=L, R=R, H=H, Q=Q, t=T, badL=BL, badR=BR, rec=REC)
pd.DataFrame(records).to_csv(os.path.join(DATA, "panel_records.csv"), index=False, encoding="utf-8")
pd.DataFrame(segs).to_csv(os.path.join(DATA, "segments.csv"), index=False, encoding="utf-8")

print("records", len(records), "frames", len(T), "segments", len(segs))
print(pd.DataFrame(records).groupby(["dataset", "split"]).agg(n=("rec", "size"), frames=("n", "sum")))
print("bad ratios by dataset")
print(pd.DataFrame(records).groupby("dataset")[["badL", "badR"]].mean().round(4))
print("envs", pd.DataFrame(records).env.nunique(), "split envs",
      pd.DataFrame(records).groupby("split").env.nunique().to_dict())
print("seg dur", pd.DataFrame(segs).dur.describe().round(2).to_dict())