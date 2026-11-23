
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Visual prefix descriptor extraction from the official videos.

The videos were shipped inside the zips but are not in the CSV export, so every
previous model was blind to the image. This extracts a compact visual descriptor
of each segment's released prefix (0.2/0.6/1.0 s), using one cheap sequential
pass per camera: grab() skips frames without decoding, retrieve() decodes only
the wanted ones.

Descriptor groups (no pretrained network needed, fully reproducible):
  structure : edge density, Sobel energy per axis, orientation histogram
  texture   : Laplacian variance, local contrast, gradient coherence
  content   : HSV mean/std, low-saturation-high-value share (bare shelf proxy),
              dark share, colour histogram
  layout    : vertical/horizontal edge profile statistics (shelf rows, gaps)
  motion    : Farneback flow magnitude between first and last prefix frame
"""
import glob
import json
import os
import sys
import time
import numpy as np
import pandas as pd
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, ATT, load_index, write_json

VID = r"Restocking_Problem_and_Data_EN"
PREFIX = [0.2, 0.6, 1.0]
W, H = 320, 180
IDX = load_index()


def find_head_left(dataset, sample):
    pats = [
        os.path.join(VID, dataset, "**", str(sample), "**", "videos", "head_left.mp4"),
        os.path.join(VID, dataset, "**", str(sample), "**", "observation.images.head_left", "**", "*.mp4"),
    ]
    for p in pats:
        hits = glob.glob(p, recursive=True)
        if hits:
            return sorted(hits)[0]
    return None


def frame_features(bgr):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    edges = cv2.Canny(g, 60, 160)
    lap = cv2.Laplacian(g, cv2.CV_32F)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hh, ss, vv = hsv[..., 0].astype(np.float32), hsv[..., 1].astype(np.float32), hsv[..., 2].astype(np.float32)
    ang = np.arctan2(gy, gx)
    hist, _ = np.histogram(ang, bins=8, range=(-np.pi, np.pi), weights=mag)
    hist = hist / max(hist.sum(), 1e-6)
    # vertical edge profile: shelf risers produce strong periodic contrast
    colmag = mag.mean(axis=0); rowmag = mag.mean(axis=1)
    bare = ((ss < 45) & (vv > 130)).mean()          # white/bare shelf surface
    dark = (vv < 60).mean()
    colourful = ((ss > 90) & (vv > 70)).mean()
    colorhist = cv2.calcHist([hsv], [0], None, [8], [0, 180]).ravel()
    colorhist = colorhist / max(colorhist.sum(), 1e-6)
    coh = float(np.abs(np.mean(np.exp(2j * ang))) )
    f = [
        float(edges.mean() / 255.0), float(mag.mean()), float(mag.std()),
        float(np.mean(g)), float(np.std(g)),
        float(lap.var()), float(np.mean(np.abs(lap))),
        float(colmag.mean()), float(colmag.std()), float(rowmag.mean()), float(rowmag.std()),
        float(np.abs(np.diff(colmag)).mean()), float(np.abs(np.diff(rowmag)).mean()),
        float(hh.mean() / 180.0), float(hh.std() / 180.0),
        float(ss.mean() / 255.0), float(ss.std() / 255.0),
        float(vv.mean() / 255.0), float(vv.std() / 255.0),
        float(bare), float(dark), float(colourful), coh,
    ]
    f.extend(hist.tolist())
    f.extend(colorhist.tolist())
    return np.asarray(f, dtype=np.float32), g


def extract_one(video, jobs):
    """jobs: list of (unit_id, prefix, target_frame_idx). Returns dict unit->feat vectors."""
    cap = cv2.VideoCapture(video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    want = {}
    for uid, pre, fidx in jobs:
        want.setdefault(fidx, []).append((uid, pre))
    got = {}
    first_gray = {}
    last_gray = {}
    for i in range(n):
        ok = cap.grab()
        if not ok:
            break
        if i in want:
            ok, img = cap.retrieve()
            if not ok or img is None:
                continue
            img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
            feat, gray = frame_features(img)
            for uid, pre in want[i]:
                got[(uid, pre)] = feat
                if pre == 0.2:
                    first_gray[uid] = gray
                if pre == 1.0:
                    last_gray[uid] = gray
    cap.release()
    # prefix motion: flow between the 0.2 s and 1.0 s frames of the same segment
    for uid in list(first_gray):
        if uid in last_gray:
            a, b = first_gray[uid], last_gray[uid]
            fl = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            m = np.hypot(fl[..., 0], fl[..., 1])
            got[("__flow__", uid)] = np.array([float(m.mean()), float(m.std()),
                                               float(np.percentile(m, 90))], dtype=np.float32)
    return got, n, fps


def main():
    t0 = time.time()
    os.makedirs(DATA, exist_ok=True)
    rows = []
    missing = []
    stats = []
    for (dataset, sample), g in IDX.groupby(["dataset", "sample"]):
        video = find_head_left(dataset, str(sample))
        if video is None:
            missing.append(f"{dataset}/{sample}")
            continue
        cap = cv2.VideoCapture(video)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()
        jobs = []
        for r in g.itertuples():
            for pre in PREFIX:
                t = min(float(r.start_s) + pre, float(r.end_s))
                fidx = int(round(t * fps))
                if 0 <= fidx < n:
                    jobs.append((r.unit_id, pre, fidx))
        got, n2, fps2 = extract_one(video, jobs)
        stats.append(dict(dataset=dataset, sample=str(sample), video=os.path.basename(video),
                          n_frames=n, fps=round(fps2, 3), n_requested=len(jobs),
                          n_got=len([k for k in got if k[0] != "__flow__"])))
        for r in g.itertuples():
            for pre in PREFIX:
                f = got.get((r.unit_id, pre))
                if f is None:
                    continue
                flow = got.get(("__flow__", r.unit_id), np.zeros(3, dtype=np.float32))
                rows.append(dict(unit_id=r.unit_id, split=r.split, family=r.family_id,
                                 task=r.task, duration=float(r.duration_s), prefix=pre,
                                 v= f.tolist(), flow=flow.tolist()))
        print(f"{dataset}/{sample}: frames={n} req={len(jobs)} got={len([k for k in got if k[0]!='__flow__'])}", flush=True)

    # Flatten to a table: visual descriptor (mean over the prefix) + flow.
    dim = max(len(r["v"]) for r in rows) if rows else 0
    recs = []
    for r in rows:
        d = dict(unit_id=r["unit_id"], split=r["split"], family=r["family"],
                 task=r["task"], duration=r["duration"], prefix=r["prefix"])
        for i, x in enumerate(r["v"]):
            d[f"v{i}"] = float(x)
        for i, x in enumerate(r["flow"]):
            d[f"flow{i}"] = float(x)
        recs.append(d)
    T = pd.DataFrame(recs)
    fp = os.path.join(DATA, "prefix_visual_features.csv")
    T.to_csv(fp, index=False, encoding="utf-8")
    meta = dict(_meta=dict(source="official Raw_Data videos, head-left camera",
                           resize=[W, H], prefix_seconds=PREFIX,
                           descriptor="edge/texture/colour/layout/motion, "+str(dim)+" dims + 3 flow",
                           method="sequential grab()/retrieve(); no frame skipping beyond needed"),
                n_rows=len(T), n_units=int(T.unit_id.nunique()) if len(T) else 0,
                n_visual_dim=dim, missing=missing, per_sample=stats,
                seconds=round(time.time() - t0, 1))
    write_json("prefix_visual_meta.json", meta)
    print("saved", fp, T.shape, "seconds", round(time.time() - t0, 1))
    print("missing videos:", missing)


if __name__ == "__main__":
    main()