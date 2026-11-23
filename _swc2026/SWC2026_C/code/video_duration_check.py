
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""video_duration_check.py — 用视频独立核验标注时长。

对 EgoPro / EgoStandard（有 tables/ 与 videos/*_frames.csv，可帧级对齐）：
1. 读取 annotation_semantic_segments.csv 的每段 start/end（标注时长 d 的来源）
2. 在 left_wrist/right_wrist 视频上按 10 Hz 解帧差信号 → 动作起止点检测
3. 标注边界 ↔ 检测边界配对，得到边界偏移与「视频测得时长」
4. 配对对比：Pearson/Spearman、中位偏差、Bland-Altman、|偏差|>20% 比例
5. 附带：视频运动信号 vs 手部姿态速度的相关性（证明信号有效）

用法:
  python video_duration_check.py calib 0 2      # 前 2 条记录，打印信号诊断
  python video_duration_check.py run 0 38       # 分批
  python video_duration_check.py merge
"""
import json
import os
import shutil
import sys

import cv2
import numpy as np
import pandas as pd

cv2.setNumThreads(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = r"Restocking_Problem_and_Data_EN\Raw_Data"
OUT = os.path.join(DATA, "video_duration_check.json")
SHARD = os.path.join(DATA, "video_duration_pairs.csv")

SAMPLE_HZ = 10.0
DOWNSCALE_W = 256
FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
MATCH_TOL = 2.0     # 边界配对容差 (s)


def records():
    out = []
    for ds in ["EgoPro", "EgoStandard"]:
        base = os.path.join(RAW, ds)
        for rec in sorted(os.listdir(base)):
            d = os.path.join(base, rec)
            if not os.path.isdir(d):
                continue
            if not os.path.exists(os.path.join(d, "tables", "annotation_semantic_segments.csv")):
                continue
            out.append((ds, rec, d))
    return out


def load_segments(d):
    sdf = pd.read_csv(os.path.join(d, "tables", "annotation_semantic_segments.csv"), encoding="utf-8-sig")
    return [(float(r["segment.start_time"]), float(r["segment.end_time"]),
             str(r.get("segment.subtask_description", ""))) for _, r in sdf.iterrows()]


def load_offsets(d, cam):
    p = os.path.join(d, "videos", f"{cam}_frames.csv")
    df = pd.read_csv(p, encoding="utf-8-sig")
    t = df["_offset_from_first_log_s"].to_numpy(np.float64)
    return t - t[0]


def motion_signal(path, offsets):
    """ffmpeg 解码到 10Hz 灰度小图，返回 (times, 帧差信号)。"""
    import subprocess
    w, h = DOWNSCALE_W, 0
    r = subprocess.run([FFMPEG, "-v", "error", "-threads", "2", "-i", path,
                        "-vf", f"fps={SAMPLE_HZ},scale={DOWNSCALE_W}:-2",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    if not r.stdout:
        return np.array([]), np.array([])
    # 高度: 用已知 fps/时长估不出，改从 ffprobe 拿
    import json as _json
    pr = subprocess.run([FFMPEG.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error",
                         "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "json", path], capture_output=True, text=True)
    st = _json.loads(pr.stdout)["streams"][0]
    h = int(round(int(st["height"]) * DOWNSCALE_W / int(st["width"])))
    fsz = DOWNSCALE_W * h
    n = len(r.stdout) // fsz
    arr = np.frombuffer(r.stdout[:n * fsz], np.uint8).reshape(n, h, DOWNSCALE_W).astype(np.int16)
    d = np.abs(np.diff(arr, axis=0)).mean(axis=(1, 2)).astype(np.float64)
    ts = (np.arange(len(d)) + 1) / SAMPLE_HZ
    return ts, d


def smooth(x, win):
    if len(x) < 3:
        return x
    k = max(1, int(win))
    return np.convolve(x, np.ones(k) / k, mode="same")


def find_dips(ts, sig):
    """动作停顿点（手部速度局部极小）= 潜在动作单元边界。"""
    from scipy.signal import find_peaks
    sm = smooth(sig, 5)                     # 0.5s
    prom = 0.12 * (np.percentile(sm, 95) - np.percentile(sm, 10))
    pk, _ = find_peaks(-sm, distance=8, prominence=max(prom, 1e-6))
    return ts[pk], sm


def detect_activity(ts, sig):
    """返回 (activity_runs[(t0,t1)], transitions[t])"""
    if len(sig) < 6:
        return [], []
    s = smooth(sig, max(3, int(len(sig) * 0.02)))
    lo, hi = np.percentile(s, 20), np.percentile(s, 90)
    if hi <= lo * 1.05:
        return [], []
    thr_hi = lo + 0.45 * (hi - lo)
    thr_lo = lo + 0.20 * (hi - lo)
    active = np.zeros(len(s), bool)
    on = False
    for i, v in enumerate(s):
        if not on and v > thr_hi:
            on = True
        elif on and v < thr_lo:
            on = False
        active[i] = on
    runs = []
    i = 0
    while i < len(active):
        if active[i]:
            j = i
            while j + 1 < len(active) and active[j + 1]:
                j += 1
            if ts[j] - ts[i] >= 0.4:      # 短于此视为噪声
                runs.append((float(ts[i]), float(ts[j])))
            i = j + 1
        else:
            i += 1
    # 合并间隔 <0.8s 的 run
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 0.8:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(list(r) if False else (r[0], r[1]))
    merged = [list(m) for m in merged]
    trans = []
    for k in range(1, len(merged)):
        trans.append(0.5 * (merged[k - 1][1] + merged[k][0]))
    return [tuple(m) for m in merged], trans


def pose_speed(d, times):
    """手部姿态合速度 (m/s)，按视觉采样时刻插值。"""
    try:
        df = pd.read_csv(os.path.join(d, "tables", "pose_left_hand.csv"), encoding="utf-8-sig")
    except Exception:
        return None, None
    cols = [f"transforms[{i}].pos.{a}" for i in range(21) for a in "xyz"]
    L = df[cols].to_numpy(np.float32).reshape(len(df), 21, 3)
    t = df["_offset_from_first_log_s"].to_numpy(np.float64)
    t = t - t[0]
    # 指尖(20) 与 腕(0) 的平均速度
    v = np.linalg.norm(np.diff(L, axis=0), axis=2).mean(axis=1) / np.maximum(np.diff(t), 1e-6)
    # 平滑
    k = max(1, int(len(v) * 0.01))
    v = np.convolve(v, np.ones(k) / k, mode="same")
    return t[:-1], v


def process(ds, rec, d):
    segs = load_segments(d)
    if not segs:
        return None
    per_cam = []
    have = set(os.path.splitext(f)[0] for f in os.listdir(os.path.join(d, "videos")))
    cams = [c for c in ["left_wrist", "right_wrist"] if c in have]
    if not cams:
        cams = [c for c in ["head_left", "head_right"] if c in have]
    for cam in cams:
        mp4 = os.path.join(d, "videos", f"{cam}.mp4")
        if not os.path.exists(mp4):
            continue
        off = load_offsets(d, cam)
        ts, s = motion_signal(mp4, off)
        if len(ts) < 10:
            continue
        s = (s - np.median(s)) / (np.percentile(s, 95) - np.median(s) + 1e-9)
        per_cam.append((cam, ts, s))
    if not per_cam:
        return None
    t_end = min(t[-1] for _, t, _ in per_cam)
    grid = np.arange(0.1, t_end, 0.1)
    stack = [np.interp(grid, t, s) for _, t, s in per_cam]
    sig = np.mean(stack, axis=0)
    sig_ts = grid
    runs, _runs_trans = detect_activity(sig_ts, sig)
    trans, _sm = find_dips(sig_ts, sig)
    video_end = float(t_end)

    seg_rows = []
    for k, (a, b, label) in enumerate(segs):
        offs, raws = [], []
        for tb in (a, b):
            if len(trans):
                j = int(np.argmin(np.abs(np.asarray(trans) - tb)))
                dd = float(trans[j] - tb)
                raws.append(dd)
                offs.append(dd if abs(dd) <= MATCH_TOL else None)
            else:
                raws.append(None); offs.append(None)
        act = 0.0
        for r in runs:
            act += max(0.0, min(b, r[1]) - max(a, r[0]))
        cover = act / max(b - a, 1e-6)
        meas = None
        if offs[0] is not None and offs[1] is not None:
            j0 = int(np.argmin(np.abs(np.asarray(trans) - a)))
            j1 = int(np.argmin(np.abs(np.asarray(trans) - b)))
            if j1 > j0:
                meas = float(trans[j1] - trans[j0])
        seg_rows.append(dict(dataset=ds, sample=rec, seg=k, a=a, b=b, dur=b - a,
                             label=label, off_start=offs[0], off_end=offs[1],
                             off_start_raw=raws[0], off_end_raw=raws[1],
                             measured=meas, active_cover=round(cover, 3),
                             active_s=round(act, 3),
                             n_runs=len(runs)))
    # 随机基线：同样数量的随机边界到最近停顿点的距离
    rng = np.random.default_rng(42)
    rand_off = []
    for _ in range(30):
        rb = rng.uniform(0, video_end, size=max(1, 2 * len(segs)))
        if len(trans):
            rand_off.extend(np.abs(np.asarray(trans)[np.argmin(np.abs(trans[None, :] - rb[:, None]), axis=1)] - rb).tolist())
    pt, pv = pose_speed(d, sig_ts)
    r_pose = None
    if pt is not None and len(pt) > 10:
        idx = np.clip(np.searchsorted(pt, sig_ts), 0, len(pv) - 1)
        if len(pv) > 20:
            r_pose = float(np.corrcoef(pv[idx], sig)[0, 1])
    return dict(dataset=ds, sample=rec, video_end=video_end,
                seg_end=float(segs[-1][1]), seg_sum=float(sum(b - a for a, b, _ in segs)),
                n_segs=len(segs), n_runs=len(runs), n_trans=len(trans),
                cams=[c for c, _, _ in per_cam], r_pose=r_pose,
                rand_dip_med=round(float(np.median(rand_off)), 3) if rand_off else None,
                sig_p50=round(float(np.median(sig)), 3),
                sig_runs_json=json.dumps([[round(x, 2), round(y, 2)] for x, y in runs]),
                rows=seg_rows)


def mode_calib(lo, hi):
    for ds, rec, d in records()[int(lo):int(hi)]:
        r = process(ds, rec, d)
        if not r:
            continue
        print(f"== {ds} {rec}")
        print(f"   video_end={r['video_end']:.1f} seg_end={r['seg_end']:.1f} segs={r['n_segs']} "
              f"runs={r['n_runs']} trans={r['n_trans']} r_pose={r['r_pose']}")
        print("   segs(annot):", [(round(x['a'],1), round(x['b'],1)) for x in r['rows']][:12])
        print("   runs(video):", r['sig_runs_json'][:400])
        print("   covers:", [x['active_cover'] for x in r['rows']][:12])


def mode_run(lo, hi):
    recs = records()[int(lo):int(hi)]
    rows, meta = [], []
    jl = os.path.join(DATA, "video_duration_raw.jsonl")
    done = set()
    if os.path.exists(jl):
        for line in open(jl, encoding="utf-8"):
            try:
                done.add(json.loads(line)["sample"])
            except Exception:
                pass
    for ds, rec, d in recs:
        if rec in done:
            continue
        try:
            r = process(ds, rec, d)
        except Exception as e:
            print("ERR", ds, rec, repr(e)); continue
        if not r:
            print("SKIP", ds, rec); continue
        print(f"{ds} {rec[:8]} segs={r['n_segs']} vlen={r['video_end']:.1f} segend={r['seg_end']:.1f} runs={r['n_runs']} trans={r['n_trans']} r_pose={r['r_pose']}", flush=True)
        with open(jl, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        meta.append({k: v for k, v in r.items() if k != "rows"})
        rows.extend(r["rows"])
    pd.DataFrame(rows).to_csv(SHARD, index=False, encoding="utf-8-sig")
    pd.DataFrame(meta).to_csv(os.path.join(DATA, "video_duration_records.csv"), index=False, encoding="utf-8-sig")
    print(f"rows={len(rows)} -> {SHARD}")


def mode_merge():
    jl = os.path.join(DATA, "video_duration_raw.jsonl")
    recs = [json.loads(l) for l in open(jl, encoding="utf-8") if l.strip()]
    seg_df = pd.DataFrame([r for x in recs for r in x["rows"]])
    rec_df = pd.DataFrame([{k: v for k, v in x.items() if k != "rows"} for x in recs])
    seg_df.to_csv(os.path.join(DATA, "video_duration_pairs.csv"), index=False, encoding="utf-8-sig")
    rec_df.to_csv(os.path.join(DATA, "video_duration_records.csv"), index=False, encoding="utf-8-sig")
    m = seg_df.dropna(subset=["measured"]).copy()
    m["diff"] = m["measured"] - m["dur"]
    m["rel"] = m["diff"] / m["dur"]
    out = {
        "records": int(len(rec_df)),
        "segments_total": int(len(seg_df)),
        "segments_with_measured": int(len(m)),
        "measure_rate": round(len(m) / max(len(seg_df), 1), 3),
    }
    if len(m) > 2:
        from scipy import stats as st
        out["pearson_r"] = round(float(st.pearsonr(m["dur"], m["measured"])[0]), 3)
        out["spearman_r"] = round(float(st.spearmanr(m["dur"], m["measured"])[0]), 3)
        out["median_diff_s"] = round(float(m["diff"].median()), 3)
        out["mean_diff_s"] = round(float(m["diff"].mean()), 3)
        out["mad_s"] = round(float((m["diff"] - m["diff"].median()).abs().median()), 3)
        out["pct_rel_gt20"] = round(float((m["rel"].abs() > 0.20).mean()), 3)
        out["pct_rel_gt50"] = round(float((m["rel"].abs() > 0.50).mean()), 3)
        sd = float(m["diff"].std())
        out["ba_loa"] = [round(float(m["diff"].mean() - 1.96 * sd), 3),
                         round(float(m["diff"].mean() + 1.96 * sd), 3)]
        out["abs_diff_median_s"] = round(float(m["diff"].abs().median()), 3)
    for ds, g in m.groupby("dataset"):
        out.setdefault("by_dataset", {})[ds] = {
            "n_matched": int(len(g)),
            "pearson_r": round(float(np.corrcoef(g["dur"], g["measured"])[0, 1]), 3),
            "median_diff_s": round(float((g["measured"] - g["dur"]).median()), 3),
            "pct_rel_gt20": round(float(((g["measured"] - g["dur"]).abs() / g["dur"] > 0.2).mean()), 3),
        }
    # 标注边界 ↔ 最近动作停顿点（全体，不限容差）
    for col in ["off_start", "off_end"]:
        o = seg_df[col].dropna()
        out[f"{col}_matched_median_s"] = round(float(o.median()), 3) if len(o) else None
    for col in ["off_start_raw", "off_end_raw"]:
        o = seg_df[col].dropna().abs()
        out[f"{col}_abs_median_s"] = round(float(o.median()), 3) if len(o) else None
        out[f"{col}_pct_within_0.3s"] = round(float((o <= 0.3).mean()), 3) if len(o) else None
        out[f"{col}_pct_within_0.5s"] = round(float((o <= 0.5).mean()), 3) if len(o) else None
    rr = rec_df["rand_dip_med"].dropna()
    out["random_boundary_abs_median_s"] = round(float(rr.median()), 3) if len(rr) else None
    both = seg_df[["off_start_raw", "off_end_raw"]].abs().mean(axis=1)
    out["boundary_abs_median_all_s"] = round(float(both.median()), 3)
    if len(rr):
        out["boundary_vs_random_ratio"] = round(float(both.median() / rr.median()), 3)
    # 活动覆盖率
    ac = seg_df["active_cover"]
    out["active_cover_median"] = round(float(ac.median()), 3)
    out["active_s_over_dur_median"] = round(float((seg_df["active_s"] / seg_df["dur"].replace(0, np.nan)).median()), 3)
    # 视频与标注总长
    rec_df["end_diff"] = rec_df["video_end"] - rec_df["seg_end"]
    out["video_vs_segend_median_s"] = round(float(rec_df["end_diff"].median()), 3)
    out["video_vs_segend_maxabs_s"] = round(float(rec_df["end_diff"].abs().max()), 3)
    out["r_pose_median"] = round(float(rec_df["r_pose"].dropna().median()), 3) if rec_df["r_pose"].notna().any() else None
    out["run_ratio_median"] = round(float((rec_df["n_runs"] / rec_df["n_segs"]).median()), 3)
    # 标注时长是否量化在整数/5 秒网格
    grid = {}
    for ds, g in seg_df.groupby("dataset"):
        durs = g["dur"].to_numpy()
        grid[ds] = {
            "n": int(len(durs)),
            "pct_integer_s": round(float(np.mean(np.abs(durs - np.round(durs)) < 1e-6)), 3),
            "pct_multiple_of_5s": round(float(np.mean(np.abs(durs / 5 - np.round(durs / 5)) < 1e-6)), 3),
            "pct_multiple_of_10s": round(float(np.mean(np.abs(durs / 10 - np.round(durs / 10)) < 1e-6)), 3),
        }
    out["annotation_quantization"] = grid
    out["scope_note"] = ("EgoPro+EgoStandard 38 条记录有 videos/*_frames.csv，可帧级对齐；"
                         "EgoDemo 31 条只有 mp4、无时间戳表，不参与边界级核验")
    out["alignment"] = {
        "records_aligned": int(len(rec_df)),
        "records_total_pose_datasets": 38,
        "align_rate": round(len(rec_df) / 38, 3),
        "ego_demo_records_excluded": 31,
    }
    out["generated_at"] = pd.Timestamp.now().isoformat()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "calib":
        mode_calib(sys.argv[2], sys.argv[3])
    elif mode == "run":
        mode_run(sys.argv[2], sys.argv[3])
    elif mode == "merge":
        mode_merge()
