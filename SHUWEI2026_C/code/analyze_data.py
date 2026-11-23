"""C 题数据的深度分析（P1/P2/P3 三层可用性）。

与 profile_data.py 的分工：profile 只做规模与 schema 盘点；本脚本做**分布层**统计，
用来回答"这份数据能支撑什么模型、样本量够不够、哪一层必须人工构造"。

产物 data/analysis.json + data/analysis_hand_runs.csv。
复现：E:\\Mini\\envs\\mathmodel\\python.exe code\\analyze_data.py
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

WS = pathlib.Path(__file__).resolve().parents[1]
RAW = WS / "data" / "raw"
CON = WS / "data" / "constraints"
OUT = WS / "data" / "analysis.json"
RUNS_OUT = WS / "data" / "analysis_hand_runs.csv"

DATASETS = ("EgoDemo", "EgoPro", "EgoStandard")
MISSING_JUMP = 0.05  # 相邻有效帧间隔超过 50 ms 视为一次数据缺口


def quantiles(x: np.ndarray, qs=(0.0, 0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)) -> dict:
    if x.size == 0:
        return {}
    vals = np.quantile(x, qs)
    names = ["min", "p01", "p10", "p25", "p50", "p75", "p90", "p99", "max"]
    return {n: float(v) for n, v in zip(names, vals)}


def records(ds: str) -> list[pathlib.Path]:
    return sorted([p for p in (RAW / ds).iterdir() if p.is_dir()])


def demo_hand(tb, side_keys):
    """Demo parquet 的 hand 列是 fixed_size_list<fixed_size_list<float>[3]>[21]。"""
    cols = {k: tb.column(k).combine_chunks() for k in side_keys if k in tb.schema.names}
    out = {}
    for k, col in cols.items():
        arr = np.array(col.to_pylist(), dtype=float)  # (T, 21, 3)
        out[k] = arr
    t = np.asarray(tb.column("timestamp").to_pylist(), dtype=float) if "timestamp" in tb.schema.names else None
    return out, t


def hand_runs(ds: str, rec: str, side: str, t: np.ndarray, pos: np.ndarray) -> list[dict]:
    """写两件事：全零帧构成的缺口段（缺失），以及低质量帧比例。"""
    zero = np.all(np.abs(pos.reshape(len(pos), -1)) < 1e-12, axis=1)
    valid = ~zero
    if valid.sum() == 0:
        return [{"dataset": ds, "record": rec, "side": side, "kind": "all_zero",
                 "start_s": float(t[0]), "end_s": float(t[-1]),
                 "duration_s": float(t[-1] - t[0]), "frames": int(len(t))}]
    runs, i, n = [], 0, len(valid)
    while i < n:
        if valid[i]:
            i += 1
            continue
        j = i
        while j < n and not valid[j]:
            j += 1
        runs.append({"dataset": ds, "record": rec, "side": side, "kind": "zero",
                     "start_s": float(t[i]), "end_s": float(t[min(j, n - 1)]),
                     "duration_s": float(t[min(j, n - 1)] - t[i]), "frames": int(j - i)})
        i = j
    dts = np.diff(t[valid])
    if dts.size:
        big = np.nonzero(dts > MISSING_JUMP)[0]
        idx = np.nonzero(valid)[0]
        for b in big:
            k = int(idx[b])
            runs.append({"dataset": ds, "record": rec, "side": side, "kind": "gap",
                         "start_s": float(t[k]), "end_s": float(t[k + 1]),
                         "duration_s": float(t[k + 1] - t[k]), "frames": 0})
    return runs


def kinematic_stats(ds, rec, side, t, pos):
    zero = np.all(np.abs(pos.reshape(len(pos), -1)) < 1e-12, axis=1)
    valid = ~zero
    if valid.sum() < 10:
        return None
    tv = t[valid]
    # 腕部关键点（index 0）与指尖（index 20）的位移速度
    wrist = pos[valid, 0, :]
    dts = np.diff(tv)
    good = dts > 1e-6
    if good.sum() < 5:
        return None
    speed = np.linalg.norm(np.diff(wrist, axis=0)[good], axis=1) / dts[good]
    # 手的高度分布（相对首帧）
    rel_z = wrist[:, 2] - wrist[0, 2]
    return {"dataset": ds, "record": rec, "side": side,
            "frames": int(len(t)), "valid_frames": int(valid.sum()),
            "valid_ratio": float(valid.mean()),
            "span_s": float(tv[-1] - tv[0]),
            "speed_p50": float(np.median(speed)), "speed_p90": float(np.quantile(speed, 0.9)),
            "speed_p99": float(np.quantile(speed, 0.99)),
            "rel_z_p10": float(np.quantile(rel_z, 0.1)), "rel_z_p90": float(np.quantile(rel_z, 0.9))}


def main() -> int:
    analysis: dict = {"scope": "distribution-level statistics for P1/P2/P3", "datasets": {}}
    hand_rows: list[dict] = []
    runs: list[dict] = []
    quality: list[dict] = []
    streams: dict[str, dict[str, int]] = {}

    for ds in DATASETS:
        per = {"records": len(records(ds)), "hand": [], "bad_ratio": [], "span_s": []}
        streams[ds] = {"head_left": 0, "head_right": 0, "left_wrist": 0, "right_wrist": 0}
        for rec in records(ds):
            name = rec.name
            if ds == "EgoDemo":
                tb = pq.read_table(rec / "data" / "chunk-000" / "file-000.parquet")
                hands, t = demo_hand(tb, ("observation.state.hand_left_world",
                                          "observation.state.hand_right_world"))
                if t is None:
                    continue
                for key, side in (("observation.state.hand_left_world", "left"),
                                  ("observation.state.hand_right_world", "right")):
                    if key not in hands:
                        continue
                    pos = hands[key]
                    st = kinematic_stats(ds, name, side, t, pos)
                    if st:
                        per["hand"].append(st)
                        hand_rows.append(st)
                    runs.extend(hand_runs(ds, name, side, t, pos))
                bad = json.loads((rec / "bad_frame_ratio.json").read_text(encoding="utf-8"))
                total = int(bad.get("total_frames") or len(t))
                details = bad.get("hand_bad_frame_details") or []
                ratio = len(details) / total if total else 0.0
                per["bad_ratio"].append(ratio)
                per["span_s"].append(float(t[-1] - t[0]))
                reasons: dict[str, int] = {}
                for d in details:
                    for key in ("left_bad_reason", "right_bad_reason"):
                        r = d.get(key)
                        if r:
                            reasons[r] = reasons.get(r, 0) + 1
                quality.append({"dataset": ds, "record": name, "bad_ratio": ratio,
                                "total_frames": total, "bad_frames": len(details),
                                "reasons": reasons})
            else:
                tables = rec / "tables"
                seg = pd.read_csv(tables / "annotation_semantic_segments.csv")
                start = float(seg["segment.start_time"].min())
                end = float(seg["segment.end_time"].max())
                per["span_s"].append(end - start)
                for side, fn in (("left", "pose_left_hand.csv"), ("right", "pose_right_hand.csv")):
                    pose = pd.read_csv(tables / fn, low_memory=False)
                    tcol = "_offset_from_first_log_s"
                    t = pose[tcol].to_numpy(dtype=float)
                    cols = [f"transforms[{i}].pos.{ax}" for i in range(21) for ax in "xyz"]
                    pos = pose[cols].to_numpy(dtype=float).reshape(len(pose), 21, 3)
                    st = kinematic_stats(ds, name, side, t, pos)
                    if st:
                        per["hand"].append(st)
                        hand_rows.append(st)
                    runs.extend(hand_runs(ds, name, side, t, pos))
                bad = pd.read_csv(tables / "annotation_bad_frame_pose_hand.csv", low_memory=False)
                if len(bad):
                    per["bad_ratio"].append(float(pd.to_numeric(bad["is_bad"], errors="coerce").fillna(0).mean()))
                    quality.append({"dataset": ds, "record": name,
                                    "bad_ratio": per["bad_ratio"][-1],
                                    "reasons": {"has_problem_type_len": bool("problem_type.length" in bad.columns)}})
                else:
                    per["bad_ratio"].append(0.0)
        hand = pd.DataFrame(per["hand"])
        analysis["datasets"][ds] = {
            "records": per["records"],
            "hand": {
                "n_streams": int(len(hand)),
                "valid_ratio_median": float(hand["valid_ratio"].median()) if len(hand) else None,
                "valid_ratio_min": float(hand["valid_ratio"].min()) if len(hand) else None,
                "span_s_median": float(hand["span_s"].median()) if len(hand) else None,
                "wrist_speed_p50_median": float(hand["speed_p50"].median()) if len(hand) else None,
                "wrist_speed_p90_pooled": float(hand["speed_p90"].median()) if len(hand) else None,
                "wrist_speed_p99_median": float(hand["speed_p99"].median()) if len(hand) else None,
                "rel_z_p10_median": float(hand["rel_z_p10"].median()) if len(hand) else None,
                "rel_z_p90_median": float(hand["rel_z_p90"].median()) if len(hand) else None,
            },
            "bad_ratio": {
                "n": len(per["bad_ratio"]),
                "quantiles": quantiles(np.array(per["bad_ratio"], dtype=float)),
            },
            "span_s": quantiles(np.array(per["span_s"], dtype=float)),
            "video_streams": streams[ds],
        }

    # 缺口统计
    run_df = pd.DataFrame(runs)
    analysis["gaps"] = {"zero_runs": 0, "zero_duration_s": {}, "gap_runs": 0,
                        "gap_duration_s": {}, "per_dataset": {}}
    if len(run_df):
        run_df.to_csv(RUNS_OUT, index=False)
        zero = run_df[run_df["kind"] == "zero"]
        gap = run_df[run_df["kind"] == "gap"]
        analysis["gaps"] = {
            "zero_runs": int(len(zero)),
            "zero_duration_s": quantiles(zero["duration_s"].to_numpy(float)) if len(zero) else {},
            "gap_runs": int(len(gap)),
            "gap_duration_s": quantiles(gap["duration_s"].to_numpy(float)) if len(gap) else {},
            "per_dataset": run_df.groupby(["dataset", "kind"]).size().to_dict() if len(run_df) else {},
        }
    # 视频流覆盖：视频未解压（只解压了非视频），按全量审计记录统计
    audit = json.loads((WS / "data" / "video_audit.json").read_text(encoding="utf-8"))
    for item in audit:
        member = item["member"]
        ds = item["dataset"]
        for kind, key in (("head_left", "head_left"), ("head_right", "head_right"),
                          ("left_wrist", "left_wrist"), ("right_wrist", "right_wrist")):
            if key in member:
                streams[ds][kind] += 1
                break
    for ds in DATASETS:
        analysis["datasets"][ds]["video_streams"] = streams[ds]
        analysis["datasets"][ds]["video_audit"] = {
            "n_videos": int(sum(1 for x in audit if x["dataset"] == ds)),
            "frames": int(sum(x["frames"] for x in audit if x["dataset"] == ds)),
            "duration_s": float(sum(x["duration_s"] for x in audit if x["dataset"] == ds)),
        }

    # 区间层
    idx = pd.read_csv(CON / "source_segment_index.csv")
    elig = idx[idx["eligible"] == 1]
    analysis["intervals"] = {}
    for fam, g in elig.groupby("family_id"):
        analysis["intervals"][fam] = {
            "n": int(len(g)), "duration_s": quantiles(g["duration_s"].to_numpy(float)),
            "by_split": g.groupby("split").size().to_dict(),
            "by_dataset": g.groupby("dataset").size().to_dict() if "dataset" in g.columns else {},
        }
    analysis["intervals"]["all"] = {
        "n_indexed": int(len(idx)), "n_eligible": int(len(elig)),
        "duration_s": quantiles(elig["duration_s"].to_numpy(float)),
        "by_split": elig.groupby("split").size().to_dict(),
        "served_by_alpha": {},
    }
    for alpha in (0.75, 1.0, 1.5):
        for beta in (0.0, 0.5, 1.0):
            d = elig["duration_s"].to_numpy(float)
            p = alpha * d + beta
            analysis["intervals"]["all"]["served_by_alpha"][f"a{alpha}_b{beta}"] = {
                "p50": float(np.median(p)), "p90": float(np.quantile(p, 0.9)), "max": float(p.max()),
                "share_over_20s": float((p > 20).mean()),
            }
    # 任务层
    tasks = pd.read_csv(CON / "tasks.csv")
    analysis["tasks"] = {}
    for case, g in tasks.groupby("case_id", sort=True):
        p_med = {f: float(np.median(elig[elig["family_id"] == f]["duration_s"])) + 0.5 for f in ("P", "A", "L")}
        med_sum = float(sum(p_med[f] for f in g["family_id"]))
        analysis["tasks"][case] = {
            "jobs": int(len(g)), "weight_total": float(g["priority_weight"].sum()),
            "weight_by_family": g.groupby("family_id")["priority_weight"].sum().to_dict(),
            "due_range": [float(g["due_s"].min()), float(g["due_s"].max())],
            "release_nonzero": int((g["release_s"] > 0).sum()),
            "precedence_edges": int(g["predecessors"].notna().sum()),
            "zone_counts": g["zone_id"].value_counts().to_dict(),
            "median_service_sum_s": med_sum,
            "fixed_cost": 2.0 * len(g),
        }
    analysis["quality_records"] = quality
    OUT.write_text(json.dumps(analysis, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} {OUT.stat().st_size} B; runs {len(run_df)} rows")
    for ds, d in analysis["datasets"].items():
        print(f"{ds}: valid_ratio {d['hand']['valid_ratio_median']:.3f} "
              f"bad_p50 {d['bad_ratio']['quantiles'].get('p50'):.4f} "
              f"span_p50 {d['span_s'].get('p50'):.1f}s streams {d['video_streams']}")
    print("zero runs", analysis["gaps"]["zero_runs"], "gap runs", analysis["gaps"]["gap_runs"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())