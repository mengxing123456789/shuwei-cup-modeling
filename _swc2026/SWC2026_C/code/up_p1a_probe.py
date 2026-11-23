# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Scratch probe: dataset shape, K_true distribution, label priors. Read-only."""
import os
import numpy as np
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
pr = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
sg = pd.read_csv(os.path.join(DATA, "segments.csv"))

print("panel_records cols:", list(pr.columns))
print("records per split:", pr.groupby("split").size().to_dict())
print(pr.head(4).to_string())
print()
print("segments cols:", list(sg.columns))
print("segments per split:", sg.groupby("split").size().to_dict())
print("dur stats by split (s):")
print(sg.groupby("split").dur.describe().round(3).to_string())
print()
kt = sg.groupby(["split", "rec"]).size().rename("K").reset_index()
print("K_true per record:")
print(kt.pivot_table(index="rec", columns="split", values="K", fill_value=0).astype(int).to_string())
print()
print("K stats by split:")
print(kt.groupby("split").K.describe().round(3).to_string())
print()
print("segment dur by split, percentiles (frames @30fps):")
for sp, g in sg.groupby("split"):
    d = g.dur.values * 30.0
    print(f"  {sp:10s} n={len(d):3d} p10={np.percentile(d,10):6.1f} p25={np.percentile(d,25):6.1f} "
          f"med={np.median(d):6.1f} p75={np.percentile(d,75):6.1f} max={d.max():7.1f}")
print()
fin = pd.read_csv(os.path.join(DATA, "p1a_gpu_segmentation_final_records.csv"))
print("final per-record (baseline):")
print(fin.round(3).to_string(index=False))
print()
print("dataset / env map for test:")
te = pr[pr.split == "test"]
print(te.to_string(index=False))