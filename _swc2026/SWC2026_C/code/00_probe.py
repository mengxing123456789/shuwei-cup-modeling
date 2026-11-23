
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""30-line probe: schema, counts, alignment, environment coverage."""
import os
import json, os, glob
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CD = os.path.join(ROOT, "cdata")
ATT = r"Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"
idx = pd.read_csv(os.path.join(ATT, "source_segment_index.csv"), encoding="utf-8-sig")
print("index", idx.shape, "eligible", int(idx.eligible.sum()))
print(idx.groupby(["dataset", "split"]).size().to_string())

d = pd.read_parquet(os.path.join(CD, "EgoDemo", "E001", "data", "chunk-000", "file-000.parquet"))
print("demo parquet", d.shape)
print(list(d.columns))
print("ts", d.timestamp.iloc[[0, -1]].tolist(), "frame", d.frame_index.iloc[[0, -1]].tolist())
print("state shape", np.asarray(d["observation.state.hand_left_world"].iloc[0]).shape)
print("hand range", np.asarray(d["observation.state.hand_left_world"].iloc[0])[:, 0].min(),
      np.asarray(d["observation.state.hand_left_world"].iloc[0])[:, 0].max())

p = os.path.join(CD, "EgoPro", os.listdir(os.path.join(CD, "EgoPro"))[0], "tables")
for f in ["pose_left_hand.csv", "pose_head.csv", "pose_headcam.csv", "annotation_bad_frame_pose_hand.csv"]:
    x = pd.read_csv(os.path.join(p, f), encoding="utf-8-sig")
    print(f, x.shape, "t0..t1", float(x["_offset_from_first_log_s"].iloc[0]), float(x["_offset_from_first_log_s"].iloc[-1]))

st = pd.read_csv(os.path.join(CD, "EgoStandard", os.listdir(os.path.join(CD, "EgoStandard"))[0], "tables", "pose_right_hand.csv"), encoding="utf-8-sig")
print("std right hand", st.shape, "t", st["_offset_from_first_log_s"].iloc[[0, -1]].tolist())

for e in ["EgoDemo", "EgoPro", "EgoStandard"]:
    print(e, len(os.listdir(os.path.join(CD, e))), "records")
print("envs in split", idx.environment_id.nunique(), "splits", idx.groupby("split").environment_id.nunique().to_dict())
print("bad demo", json.load(open(os.path.join(CD, "EgoDemo", "E001", "bad_frame_ratio.json"))).keys())