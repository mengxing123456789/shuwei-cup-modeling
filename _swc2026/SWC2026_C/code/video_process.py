
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""video_process.py — 184 个 mp4 → 统一视频特征表。

用法:
  python video_process.py inventory            # 盘点 184 个视频 → data/video_inventory.csv
  python video_process.py features 0 60        # 处理第 0..59 个视频(按 inventory 顺序), 追加到 data/video_features_full.csv
  python video_process.py features 60 120
  python video_process.py features 120 184
  python video_process.py summary              # 汇总 → data/video_features_summary.json

CPU-only 解码。特征: 皮肤色(手部代理)比例与运动、Farneback 光流统计、帧差、
直方图突变(场景切点)、亮度/对比/清晰度。
"""
import json
import os
import shutil
import subprocess
import sys

import cv2
import numpy as np
import pandas as pd

cv2.setNumThreads(1)  # 多进程分批时避免线程超订

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = r"Restocking_Problem_and_Data_EN\Raw_Data"
INV = os.path.join(DATA, "video_inventory.csv")
FEAT = os.path.join(DATA, "video_features_full.csv")
SUMM = os.path.join(DATA, "video_features_summary.json")

FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"

FFMPEG = FFPROBE.replace("ffprobe.exe", "ffmpeg.exe")

SAMPLE_FPS = 2.0      # 采样帧率
MAX_FRAMES = 400      # 单视频最多采样帧
DOWNSCALE_W = 256


def find_videos():
    out = []
    for dirpath, _dirs, files in os.walk(RAW):
        for f in files:
            if f.lower().endswith(".mp4"):
                out.append(os.path.join(dirpath, f))
    out.sort()
    return out


def record_id(path):
    """EgoDemo/E001/videos/.../file-000.mp4 → E001|camera"""
    rel = os.path.relpath(path, RAW).replace("\\", "/")
    parts = rel.split("/")
    ds = parts[0]
    if ds == "EgoDemo":
        rid = parts[1]
        cam = parts[3].replace("observation.images.", "")
    else:
        rid = f"{ds[:7]}_{parts[1][:8]}"
        cam = parts[3].replace("observation.images.", "")
    return rid, cam, ds, rel


def probe(path):
    try:
        r = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate,codec_name:format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60)
        d = json.loads(r.stdout)
        st = d["streams"][0]
        num, den = st["r_frame_rate"].split("/")
        fps = float(num) / float(den)
        dur = float(d["format"]["duration"])
        return int(st["width"]), int(st["height"]), fps, dur, st["codec_name"]
    except Exception:
        cap = cv2.VideoCapture(path)
        w, h = int(cap.get(3)), int(cap.get(4))
        fps = cap.get(5) or 25.0
        n = cap.get(7)
        cap.release()
        return w, h, fps, n / fps if fps else 0.0, "unknown"


def skin_mask(img):
    """YCrCb 皮肤色掩码 → 手部区域代理（自我中心视角下的主要动肤区）。"""
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    m = cv2.inRange(ycrcb, (40, 135, 85), (255, 180, 135))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return m


def decode_ffmpeg(path, out_fps, width=DOWNSCALE_W, pix="rgb24"):
    """返回 (frames_list_of_rgb_uint8, w, h)"""
    probe = subprocess.run(
        [FFMPEG, "-v", "error", "-threads", "2", "-i", path,
         "-vf", f"fps={out_fps:.4f},scale={width}:-2", "-f", "rawvideo",
         "-pix_fmt", pix, "-"], capture_output=True)
    buf = probe.stdout
    if not buf:
        return [], width, 0
    # 高度由码流长度和帧数推不出，先读一次尺寸
    return buf, width, 0


def frame_bytes(path, out_fps, width=DOWNSCALE_W):
    w0, h0, fps0, dur, _ = probe(path)
    h = int(round(h0 * width / w0))
    h += h % 2
    r = subprocess.run(
        [FFMPEG, "-v", "error", "-threads", "2", "-i", path,
         "-vf", f"fps={out_fps:.4f},scale={width}:{h}", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"], capture_output=True)
    fsz = width * h * 3
    n = len(r.stdout) // fsz
    arr = np.frombuffer(r.stdout[:n * fsz], np.uint8).reshape(n, h, width, 3)
    return arr, fps0, dur


def video_features(path, max_frames=MAX_FRAMES):
    w0, h0, fps_src, dur, _ = probe(path)
    total = int(dur * fps_src)
    step = max(1, int(np.ceil(total / max_frames))) if total else 1
    out_fps = fps_src / step
    arr, fps_src, dur = frame_bytes(path, out_fps)
    frames = [cv2.cvtColor(a, cv2.COLOR_RGB2BGR) for a in arr]
    if not frames:
        return None
    n = len(frames)
    eff_fps = out_fps
    small = []
    for im in frames:
        h, w = im.shape[:2]
        s = DOWNSCALE_W / w
        small.append(cv2.resize(im, (DOWNSCALE_W, max(1, int(h * s)))))
    gray = [cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) for im in small]

    bright = [float(g.mean()) for g in gray]
    contrast = [float(g.std()) for g in gray]
    sharp = [float(cv2.Laplacian(g, cv2.CV_64F).var()) for g in gray]

    # 光流: 相邻采样帧 Farneback
    flows = []
    for i in range(1, n):
        f = cv2.calcOpticalFlowFarneback(gray[i - 1], gray[i], None,
                                         0.5, 3, 15, 3, 5, 1.2, 0)
        mag = np.linalg.norm(f, axis=2)
        flows.append((float(mag.mean()), float(np.percentile(mag, 95))))
    diffs = [float(cv2.absdiff(gray[i], gray[i - 1]).mean()) for i in range(1, n)]

    cuts = []
    prev_hist = None
    for i, g in enumerate(gray):
        hist = cv2.calcHist([g], [0], None, [32], [0, 256])
        hist /= hist.sum() + 1e-9
        if prev_hist is not None:
            corr = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL))
            if corr < 0.5:
                cuts.append(round(i * step / fps_src, 2))
        prev_hist = hist

    skin_frac = [float(skin_mask(im).mean() / 255.0) for im in small]

    def stats(x):
        x = np.asarray(x, np.float64)
        if len(x) == 0:
            return [0.0] * 5
        return [float(x.mean()), float(x.std()), float(np.percentile(x, 50)),
                float(np.percentile(x, 95)), float(x.max())]

    fmean = [f[0] for f in flows]
    fpeak = [f[1] for f in flows]
    return {
        "n_sampled": n, "sample_step": step, "eff_fps": round(eff_fps, 3),
        "total_frames_dec": total,
        "flow_mean": stats(fmean)[0], "flow_std": stats(fmean)[1],
        "flow_p95": stats(fmean)[3], "flow_max": stats(fmean)[4],
        "flowpeak_mean": stats(fpeak)[0],
        "diff_mean": stats(diffs)[0], "diff_std": stats(diffs)[1], "diff_max": stats(diffs)[4],
        "n_scene_cuts": len(cuts),
        "cut_times": ";".join(f"{c:.1f}" for c in cuts[:20]),
        "bright_mean": stats(bright)[0], "bright_std": stats(bright)[1],
        "contrast_mean": stats(contrast)[0],
        "sharp_mean": stats(sharp)[0],
        "skin_frac_mean": stats(skin_frac)[0], "skin_frac_std": stats(skin_frac)[1],
        "skin_frac_max": stats(skin_frac)[4],
        "motion_energy": float(np.sum(fmean)) * eff_fps,
    }


def mode_inventory():
    vids = find_videos()
    rows = []
    for v in vids:
        rid, cam, ds, rel = record_id(v)
        w, h, fps, dur, codec = probe(v)
        size_mb = os.path.getsize(v) / 1e6
        rows.append(dict(record_id=rid, camera=cam, dataset=ds, rel_path=rel,
                         video_path=v, width=w, height=h, fps=round(fps, 3),
                         duration_s=round(dur, 3), codec=codec,
                         est_frames=int(dur * fps), size_mb=round(size_mb, 2)))
    df = pd.DataFrame(rows)
    df.to_csv(INV, index=False, encoding="utf-8-sig")
    print(f"inventory: {len(df)} videos -> {INV}")
    print(df.groupby("dataset").agg(n=("record_id", "count"),
                                    dur=("duration_s", "sum"),
                                    fps=("fps", "mean")).round(2))


def load_inventory():
    if os.path.exists(INV):
        return pd.read_csv(INV, encoding="utf-8-sig")
    mode_inventory()
    return pd.read_csv(INV, encoding="utf-8-sig")


def mode_features(lo, hi):
    inv = load_inventory()
    lo, hi = int(lo), int(hi)
    batch = inv.iloc[lo:hi]
    shard = os.path.join(DATA, f"video_features_part{lo:03d}_{hi:03d}.csv")
    old = pd.read_csv(shard, encoding="utf-8-sig") if os.path.exists(shard) else None
    done = set(old["video_path"]) if old is not None and len(old) else set()
    rows = []
    for _, r in batch.iterrows():
        if r["video_path"] in done:
            continue
        try:
            f = video_features(r["video_path"])
            if f is None:
                print("EMPTY", r["rel_path"]); continue
        except Exception as e:
            print("ERR", r["rel_path"], repr(e)); continue
        rows.append({**r.to_dict(), **f})
        print(f"[{rows[-1]['record_id']}] flow={f['flow_mean']:.2f} cuts={f['n_scene_cuts']}", flush=True)
        # 每条立刻落盘，进程中断不丢进度
        hdr = not os.path.exists(shard)
        pd.DataFrame([rows[-1]]).to_csv(shard, mode="a", header=hdr, index=False, encoding="utf-8-sig")
    print(f"shard {shard}: +{len(rows)} rows", flush=True)


def mode_merge():
    inv = load_inventory()
    import glob
    parts = sorted(glob.glob(os.path.join(DATA, "video_features_part*.csv")))
    dfs = [pd.read_csv(p, encoding="utf-8-sig") for p in parts]
    df = pd.concat(dfs, ignore_index=True).drop_duplicates("video_path")
    # 摄像头名统一修正: EgoPro/EgoStandard 路径里没有 observation.images.* 目录
    df["camera"] = df["rel_path"].map(
        lambda r: r.split("/")[3].replace("observation.images.", "")
        if "observation.images." in r else os.path.splitext(r.split("/")[-1])[0])
    df["record_id"] = df["rel_path"].map(
        lambda r: r.split("/")[1] if r.startswith("EgoDemo/")
        else f"{r.split('/')[0][:7]}_{r.split('/')[1][:8]}")
    # 光流量纲统一: 不同采样步长的视频不能直接比较 flow_mean，换算成像素/秒
    df["flow_per_s"] = df["flow_mean"] * df["eff_fps"]
    df["flowpeak_per_s"] = df["flowpeak_mean"] * df["eff_fps"]
    df["motion_energy"] = df["flow_mean"] * df["eff_fps"]
    df.to_csv(FEAT, index=False, encoding="utf-8-sig")
    missing = set(inv["video_path"]) - set(df["video_path"])
    print(f"merge: {len(df)}/{len(inv)} videos, missing {len(missing)}")
    if missing:
        print("MISSING:", list(sorted(missing))[:5])


def mode_summary():
    inv = load_inventory()
    feat = pd.read_csv(FEAT, encoding="utf-8-sig")
    summ = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "total_videos": int(len(inv)),
        "feature_coverage": round(len(feat) / len(inv), 4),
        "datasets": {},
    }
    for ds, g in inv.groupby("dataset"):
        gf = feat[feat["dataset"] == ds] if len(feat) else g.iloc[:0]
        summ["datasets"][ds] = {
            "n_videos": int(len(g)),
            "n_records": int(g["record_id"].nunique()),
            "total_duration_s": round(float(g["duration_s"].sum()), 2),
            "mean_fps": round(float(g["fps"].mean()), 2),
            "resolutions": sorted(g[["width", "height"]].drop_duplicates()
                                  .astype(int).values.tolist()),
            "n_featured": int(len(gf)),
            "mean_flow": round(float(gf["flow_mean"].mean()), 4) if len(gf) else None,
            "mean_motion_energy": round(float(gf["motion_energy"].mean()), 2) if len(gf) else None,
            "total_scene_cuts": int(gf["n_scene_cuts"].sum()) if len(gf) else None,
        }
    with open(SUMM, "w", encoding="utf-8") as fh:
        json.dump(summ, fh, ensure_ascii=False, indent=2)
    print(json.dumps(summ, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "inventory":
        mode_inventory()
    elif mode == "features":
        mode_features(sys.argv[2], sys.argv[3])
    elif mode == "merge":
        mode_merge()
    elif mode == "summary":
        mode_summary()
