
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Probe 2: correct recursive layout, map segment time to frames, decode a prefix."""
import glob
import os
import sys
import numpy as np
import pandas as pd
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ATT, load_index

VID = r"Restocking_Problem_and_Data_EN"
IDX = load_index()


def head_left_video(dataset, sample):
    hits = glob.glob(os.path.join(VID, dataset, "**", str(sample), "**", "head_left*.mp4"), recursive=True)
    return hits[0] if hits else None


def frames_table(dataset, sample):
    hits = glob.glob(os.path.join(VID, dataset, "**", str(sample), "**", "head_left_frames.csv"), recursive=True)
    if not hits:
        # EgoDemo keeps frame timing in parquet/meta
        hits = glob.glob(os.path.join(VID, dataset, "**", str(sample), "**", "head_left*.csv"), recursive=True)
    return hits[0] if hits else None


for dataset in ("EgoPro", "EgoStandard", "EgoDemo"):
    g = IDX[IDX.dataset == dataset]
    print(f"\n=== {dataset} segments={len(g)} samples={g['sample'].nunique()}")
    for s in sorted(g["sample"].astype(str).unique())[:2]:
        v = head_left_video(dataset, s)
        ft = frames_table(dataset, s)
        print(" sample", s)
        print("   video", v)
        print("   frames", ft)
        if not v:
            continue
        cap = cv2.VideoCapture(v)
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT); fps = cap.get(cv2.CAP_PROP_FPS)
        print("   mp4 frames", int(n), "fps", round(fps, 4), "dur_s", round(n / max(fps, 1e-9), 3))
        if ft:
            f = pd.read_csv(ft, encoding="utf-8-sig")
            col = "_offset_from_first_log_s" if "_offset_from_first_log_s" in f else None
            print("   frames rows", len(f), "cols", list(f.columns)[:6])
            if col:
                off = f[col].values.astype(float)
                print("   offset range", round(off.min(), 4), round(off.max(), 4))
        sub = g[g["sample"].astype(str) == s]
        print("   segs", [(round(float(a), 3), round(float(b), 3)) for a, b in zip(sub.start_s, sub.end_s)][:4])
        t0 = float(sub.start_s.iloc[0])
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000.0 * t0)
        ok, img = cap.read()
        print("   seek", round(t0, 3), "->", ok, None if img is None else img.shape)
        cap.release()