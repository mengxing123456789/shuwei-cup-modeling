# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""v3 video re-extraction: stream every mp4, keep 10 Hz motion/brightness
statistics. No frames are ever written to disk (E: has ~8.5 GB free).

Rows: one per (record_id, camera, second_sample).
Columns:
  record_id, camera, dataset, t_s (sample time in seconds),
  diff_mean, diff_p90, static_frac,            whole-frame temporal change
  roi_diff_mean, roi_diff_p90, roi_static_frac, hand-region change
  bright_mean, bright_std, roi_bright_mean, roi_bright_std,
  flow_mean, flow_p90, roi_flow_mean, roi_flow_p90,
  decoded_frames, decode_ok

The hand region is the lower-centre box (x 0.25-0.75, y 0.45-1.00 of the frame),
a proxy for where hands act in these ego views.

Usage:
  python code/v2_video_extract.py            # full run over all 184 files
  python code/v2_video_extract.py --limit 3   # smoke test on 3 files
"""
from __future__ import annotations

import os

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

C = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = C / "data"
LOGS = C / "logs"
OUT_CSV = DATA / "v3_video_features.csv"
OUT_MANIFEST = DATA / "v3_video_manifest.json"

SAMPLE_HZ = 10.0         # rows per second of video (5x the pilot rate)
SMALL = (320, 240)       # working resolution for diffs / brightness
FLOW_RES = (160, 120)    # working resolution for optical flow
STATIC_ABS = 2.0         # |diff| below this (0-255 grey) counts as static
ROI = (0.25, 0.75, 0.45, 1.00)   # x0, x1, y0, y1 as fractions

FIELDS = [
    "record_id", "camera", "dataset", "t_s",
    "diff_mean", "diff_p90", "static_frac",
    "roi_diff_mean", "roi_diff_p90", "roi_static_frac",
    "bright_mean", "bright_std", "roi_bright_mean", "roi_bright_std",
    "flow_mean", "flow_p90", "roi_flow_mean", "roi_flow_p90",
    "decoded_frames", "decode_ok",
]


def roi_box(h: int, w: int):
    x0, x1, y0, y1 = ROI
    return slice(int(y0 * h), h), slice(int(x0 * w), int(x1 * w))


def stats(a: np.ndarray) -> tuple[float, float, float]:
    return float(a.mean()), float(np.percentile(a, 90)), float((a < STATIC_ABS).mean())


def process_video(row: pd.Series) -> tuple[list[list], dict]:
    path = Path(row["video_path"])
    cam = str(row["camera"]).replace(".mp4", "")
    rec = str(row["record_id"])
    ds = str(row["dataset"])
    fps = float(row["fps"]) if row["fps"] else 30.0
    step = max(1, int(round(fps / SAMPLE_HZ)))

    info = {
        "record_id": rec, "camera": cam, "dataset": ds,
        "path": str(path), "fps": fps, "step": step,
        "exists": path.exists(), "decode_ok": False,
        "decoded_frames": 0, "samples": 0, "seconds": 0.0,
        "est_frames": int(row["est_frames"]) if row["est_frames"] else None,
        "duration_s": float(row["duration_s"]) if row["duration_s"] else None,
        "error": None,
    }
    rows: list[list] = []
    if not path.exists():
        info["error"] = "missing"
        return rows, info

    t0 = time.time()
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        info["error"] = "cannot_open"
        try:
            cap.release()
        except Exception:
            pass
        return rows, info

    prev_small = None
    prev_flow = None
    i = 0
    last_t = -1.0
    try:
        while True:
            ok = cap.grab()
            if not ok:
                break
            if i % step == 0:
                ok2, frame = cap.retrieve()
                if not ok2 or frame is None:
                    i += 1
                    continue
                small = cv2.cvtColor(
                    cv2.resize(frame, SMALL, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
                flow_small = cv2.resize(small, FLOW_RES, interpolation=cv2.INTER_AREA)
                h, w = small.shape
                rs, cs = roi_box(h, w)
                bright_mean, bright_std = float(small.mean()), float(small.std())
                rb_mean, rb_std = float(small[rs, cs].mean()), float(small[rs, cs].std())

                if prev_small is None or prev_small.shape != small.shape:
                    d_mean = d_p90 = s_frac = 0.0
                    rd_mean = rd_p90 = rs_frac = 0.0
                    f_mean = f_p90 = rf_mean = rf_p90 = 0.0
                else:
                    diff = cv2.absdiff(small, prev_small).astype(np.float32)
                    d_mean, d_p90, s_frac = stats(diff)
                    rdiff = diff[rs, cs]
                    rd_mean, rd_p90, rs_frac = stats(rdiff)

                    if prev_flow is not None and prev_flow.shape == flow_small.shape:
                        fl = cv2.calcOpticalFlowFarneback(
                            prev_flow, flow_small, None, 0.5, 3, 15, 3, 5, 1.1, 0)
                        mag = np.hypot(fl[..., 0], fl[..., 1]).astype(np.float32)
                        fh, fw = mag.shape
                        frs, fcs = roi_box(fh, fw)
                        f_mean, f_p90 = float(mag.mean()), float(np.percentile(mag, 90))
                        rmag = mag[frs, fcs]
                        rf_mean = float(rmag.mean())
                        rf_p90 = float(np.percentile(rmag, 90))
                    else:
                        f_mean = f_p90 = rf_mean = rf_p90 = 0.0
                    prev_flow = flow_small
                if i == 0:
                    prev_flow = flow_small

                t_s = i / fps
                rows.append([
                    rec, cam, ds, round(t_s, 3),
                    round(d_mean, 4), round(d_p90, 4), round(s_frac, 4),
                    round(rd_mean, 4), round(rd_p90, 4), round(rs_frac, 4),
                    round(bright_mean, 4), round(bright_std, 4),
                    round(rb_mean, 4), round(rb_std, 4),
                    round(f_mean, 4), round(f_p90, 4), round(rf_mean, 4), round(rf_p90, 4),
                    -1, 1,
                ])
                prev_small = small
                last_t = t_s
            i += 1
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        cap.release()

    info["decoded_frames"] = i
    info["samples"] = len(rows)
    info["seconds"] = round(time.time() - t0, 2)
    info["decode_ok"] = len(rows) > 0
    info["last_t_s"] = last_t
    for r in rows:
        r[-2] = i
    return rows, info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    inv = pd.read_csv(DATA / "video_inventory.csv")
    if args.limit:
        inv = inv.head(args.limit)
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / "v3_video_extract.log"

    write_header = not OUT_CSV.exists() or args.limit == 0
    mode = "w"
    infos: list[dict] = []
    t_all = time.time()

    with open(OUT_CSV, mode, newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        if write_header:
            wr.writerow(FIELDS)
        for n, (_, row) in enumerate(inv.iterrows(), 1):
            rows, info = process_video(row)
            wr.writerows(rows)
            fh.flush()
            infos.append(info)
            line = (f"[{n}/{len(inv)}] {info['record_id']} {info['camera']} "
                    f"frames={info['decoded_frames']} samples={info['samples']} "
                    f"{info['seconds']}s ok={info['decode_ok']} err={info['error']}")
            print(line, flush=True)
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(line + "\n")
            # keep a rolling manifest so a crash never loses the audit trail
            OUT_MANIFEST.write_text(json.dumps({
                "_meta": {"script": "v3_video_extract_10hz.py", "sample_hz": SAMPLE_HZ,
                          "small": SMALL, "flow_res": FLOW_RES, "static_abs": STATIC_ABS,
                          "roi": ROI, "n_planned": len(inv), "n_done": len(infos),
                          "elapsed_s": round(time.time() - t_all, 1)},
                "videos": infos,
            }, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = sum(1 for i in infos if i["decode_ok"])
    frames = sum(i["decoded_frames"] for i in infos)
    print(f"\nDONE {ok}/{len(infos)} decoded, {frames} frames read, "
          f"{round(time.time() - t_all, 1)} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())