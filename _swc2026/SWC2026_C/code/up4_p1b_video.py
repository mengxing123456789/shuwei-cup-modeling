# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up4_p1b_video.py -- add the 184-video camera branch to the P1-b detector.

Purpose: the earlier video experiment targeted job duration (a record-level target)
and found nothing. This one targets the bad-frame / occlusion task, which is a
frame-level visual event. The video statistics (2 Hz, four cameras, 14 quantities
per camera) are aligned to the 66,070 released frames with a nearest sample within
0.75 s, robust-standardised within each record, and appended to the 164 pose
features of V8. V8 is the current production detector (test AP 0.1494).

Protocol: same train/validation/test record split as V8, same 18-epoch budget,
same seeds, same selection by validation AUC, test evaluated once.
Pre-registered bar: mean test AP gain >= +5% relative to V8 and mean worst per-env
AUC not below V8's.
"""
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import up2_p1b_v2 as base  # noqa: E402

DATA = base.DATA
LOG_PATH = os.path.join(base.LOGS, "up4_p1b_video.log")
OUT = os.path.join(DATA, "up4_p1b_video.json")
CAMERAS = ["head_left", "head_right", "left_wrist", "right_wrist"]
STATS = ["diff_mean", "diff_p90", "static_frac", "roi_diff_mean", "roi_diff_p90",
         "roi_static_frac", "bright_mean", "bright_std", "roi_bright_mean",
         "roi_bright_std", "flow_mean", "flow_p90", "roi_flow_mean", "roi_flow_p90"]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def build_video_matrix(rec, t):
    """Return (N, 60) raw video features and (N, 60) record-robust-normalised."""
    v = pd.read_csv(os.path.join(DATA, "v2_video_features.csv"))
    out = np.zeros((len(rec), len(CAMERAS) * len(STATS) + len(CAMERAS)), np.float32)
    for r in np.unique(rec):
        m = rec == r
        tr = t[m]
        for j, cam in enumerate(CAMERAS):
            g = v[(v["record_id"] == r) & (v["camera"] == cam)].sort_values("t_s")
            col0 = j * len(STATS)
            if len(g) == 0:
                continue
            out[m, col0 + len(STATS)] = 1.0
            tv = g["t_s"].to_numpy(float)
            for k, st in enumerate(STATS):
                yv = g[st].to_numpy(float)
                # nearest neighbour, only if inside the covered span +-0.75 s
                idx = np.searchsorted(tv, tr)
                idx = np.clip(idx, 1, len(tv) - 1)
                left = tv[idx - 1]
                right = tv[idx]
                choose = np.where(np.abs(tr - left) <= np.abs(right - tr), idx - 1, idx)
                dist = np.abs(tr - tv[choose])
                vals = np.where(dist <= 0.75, yv[choose], np.nan)
                out[m, col0 + k] = np.nan_to_num(vals, nan=0.0)
    # record-level robust standardisation of the 56 continuous columns
    norm = out.copy()
    cont = np.ones(out.shape[1], bool)
    for j in range(len(CAMERAS)):
        cont[j * len(STATS) + len(STATS)] = False
    for r in np.unique(rec):
        m = rec == r
        for c in np.flatnonzero(cont):
            x = out[m, c]
            med = np.median(x)
            mad = np.median(np.abs(x - med)) * 1.4826
            norm[m, c] = np.clip((x - med) / max(mad, 1e-6), -6.0, 6.0)
    return out, norm


def main():
    t0 = time.time()
    D = base.build_data()
    AX = base.build_aux(D)
    raw, norm = build_video_matrix(D["rec"], np.load(os.path.join(DATA, "panel.npz"))["t"])
    D["X"] = np.concatenate([D["X"], raw, norm], axis=1).astype(np.float32)
    log(f"video matrix: {raw.shape[1]} raw + {norm.shape[1]} normalized; X={D['X'].shape}")
    cfg = dict(base.CONFIGS["V8"])
    cfg["views"] = "both"
    cfg["desc"] = "V8 pose detector + camera video statistics (60 raw + 60 record-normalised)"
    rows, payload = [], dict(
        _meta=dict(script="up4_p1b_video.py",
                   gate=dict(ap_gain_rel_min=0.05, note="mean test AP >= 5% over V8, worst per-env AUC not below V8"),
                   protocol=dict(windows=[list(x) for x in base.SPECS], epochs=base.EPOCHS,
                                 seeds=base.SEEDS, batch=base.BATCH)),
        configs={"V9": cfg}, results={})
    for seed in base.SEEDS:
        log(f"running V9 seed={seed}")
        res = base.run_one("V9", cfg, seed, D, AX, base.EPOCHS)
        probs = res.pop("probs")
        np.savez_compressed(os.path.join(DATA, f"up4_p1b_video_probs_{seed}.npz"), **probs)
        rows.append(res)
        payload["results"].setdefault("V9", dict(desc=cfg["desc"], per_seed={}))
        payload["results"]["V9"]["per_seed"][str(seed)] = res
        payload["results"]["V9"]["aggregate"] = base.agg(rows)
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    a = payload["results"]["V9"]["aggregate"]
    # compare with V8 stored in up2_p1b.json
    v8 = json.load(open(os.path.join(DATA, "up2_p1b.json"), encoding="utf-8"))["results"]["V8"]["aggregate"]
    ap_gain = a["test_ap"] / v8["test_ap"] - 1.0
    worst_ok = a["worst_env"] >= v8["worst_env"] - 1e-12
    payload["comparison"] = dict(v8_ap=v8["test_ap"], v9_ap=a["test_ap"], ap_gain_rel=float(ap_gain),
                                 v8_worst=v8["worst_env"], v9_worst=a["worst_env"],
                                 worst_not_lower=bool(worst_ok),
                                 passes=bool(ap_gain >= 0.05 and worst_ok))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    log(f"V9 AP={a['test_ap']:.5f} gain={ap_gain*100:.2f}% worst={a['worst_env']:.5f} "
        f"v8AP={v8['test_ap']:.5f} passes={payload['comparison']['passes']} total={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
