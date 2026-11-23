"""C 题数据总盘点：把三套原始记录、质量标记、语义段、任务与采样约束压成一份可核对的 JSON。

用法：
    E:\\Mini\\envs\\mathmodel\\python.exe code\\profile_data.py            # 写 data/data_profile.json
    E:\\Mini\\envs\\mathmodel\\python.exe code\\profile_data.py --print    # 同时打印摘要

只读 data/raw 与 data/constraints，不改任何原始文件；所有数字都可由本脚本重算。
口径说明（写进报告时必须带着）：
  - EgoDemo 的时间列是 `timestamp`（秒，从 0 起），EgoPro/EgoStandard 是 `_offset_from_first_log_s`。
  - 三套的帧率都标称 30 Hz；本脚本按相邻时间差的中位数实测，而不是采信元数据。
  - 质量标记是「人手观测」的质量，不是商品遮挡或操作成功。
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics as st
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CON = ROOT / "data" / "constraints"
OUT = ROOT / "data" / "data_profile.json"

META = ["_message_index", "_log_time_ns", "_publish_time_ns", "_sequence",
        "_offset_from_first_log_s", "header.ts", "header.sender", "header.count"]


def _q(a: list[float], p: float) -> float:
    if not a:
        return float("nan")
    return float(np.quantile(np.asarray(a, dtype=float), p))


def _desc(a: list[float]) -> dict:
    if not a:
        return {"n": 0}
    return {"n": len(a), "min": float(min(a)), "p05": _q(a, .05), "p25": _q(a, .25),
            "median": float(st.median(a)), "p75": _q(a, .75), "p95": _q(a, .95),
            "max": float(max(a)), "mean": float(st.fmean(a))}


def _dt_stats(t: np.ndarray) -> dict:
    d = np.diff(np.asarray(t, dtype=float))
    d = d[np.isfinite(d)]
    if d.size == 0:
        return {"n": 0}
    return {"median_s": float(np.median(d)), "mean_s": float(d.mean()),
            "p99_s": float(np.quantile(d, .99)), "max_s": float(d.max()),
            "neg": int((d < -1e-9).sum()), "zero": int((np.abs(d) < 1e-9).sum())}


# ---------------------------------------------------------------- EgoDemo
def profile_demo(rec: pathlib.Path, split_row: dict) -> dict:
    import pyarrow.parquet as pq

    info = json.loads((rec / "meta" / "info.json").read_text(encoding="utf-8"))
    ann = json.loads((rec / "annotation.json").read_text(encoding="utf-8"))
    bad = json.loads((rec / "bad_frame_ratio.json").read_text(encoding="utf-8"))

    tb = pq.read_table(rec / "data" / "chunk-000" / "file-000.parquet",
                       columns=["timestamp", "frame_index",
                                "observation.state.hand_left_world",
                                "observation.state.hand_right_world",
                                "observation.state.head_world"])
    t = np.array(tb.column("timestamp").to_pylist(), dtype=float)
    n_rows = int(tb.num_rows)

    hands = {}
    for side in ("left", "right"):
        # parquet 的 fixed_size_list 落到 pandas 是 object 列（每格一个 21x3 的 object 数组），
        # np.asarray 会报 "only 0-dimensional arrays"，必须走 pyarrow to_pylist。
        arr = np.array(tb.column(f"observation.state.hand_{side}_world")
                       .combine_chunks().to_pylist(), dtype=float)  # (N,21,3)
        nan_frac = float(np.isnan(arr).any(axis=2).mean())
        # 代表点：21 个关键点的几何中心（与题目「几何中心」口径一致）
        cen = np.nanmean(arr, axis=1)
        # 逐关键点平均速度，用来看哪个点动得最多（选代表点的依据）
        sp = np.linalg.norm(np.diff(arr, axis=0), axis=2)  # (N-1,21)
        kp_speed = np.nanmean(sp, axis=0)
        step = np.linalg.norm(np.diff(cen, axis=0), axis=1)
        hands[side] = {
            "nan_keypoint_frame_frac": round(nan_frac, 5),
            "centroid_bbox_m": [round(float(np.nanmin(cen[:, i])), 3) for i in range(3)]
                             + [round(float(np.nanmax(cen[:, i])), 3) for i in range(3)],
            "centroid_span_m": [round(float(np.nanmax(cen[:, i]) - np.nanmin(cen[:, i])), 3) for i in range(3)],
            "speed_m_per_s": _desc([float(x) / max(1e-6, float(np.median(np.diff(t))))
                                    for x in step[np.isfinite(step)]]),
            "jump_gt_0p2m": int((step > 0.2).sum()),
            "keypoint_speed_argmax": int(np.nanargmax(kp_speed)),
            "keypoint_speed_top3": [int(i) for i in np.argsort(-np.nan_to_num(kp_speed))[:3]],
            "keypoint_speed_spread": round(float(np.nanmax(kp_speed) - np.nanmin(kp_speed)), 5),
        }

    det = bad.get("hand_bad_frame_details", [])
    reasons = {}
    side_bad = {"left": set(), "right": set()}
    for d in det:
        for side, key in (("left", "left_bad_reason"), ("right", "right_bad_reason")):
            r = d.get(key)
            if r:
                side_bad[side].add(int(d["frame"]))
                reasons[r] = reasons.get(r, 0) + 1

    segs = ann.get("subtask_annotations", [])
    seg_dur = [float(s["end_time"]) - float(s["start_time"]) for s in segs]
    return {
        "kind": "demo", "record": rec.name, **split_row,
        "rows": int(n_rows), "frames_declared": info.get("total_frames"),
        "fps_declared": info.get("fps"), "duration_s": round(float(t.max() - t.min()), 3),
        "dt": _dt_stats(t),
        "hand": hands,
        "bad": {"total_frames": bad.get("total_frames"),
                "bad_left": len(side_bad["left"]), "bad_right": len(side_bad["right"]),
                "bad_any": len(side_bad["left"] | side_bad["right"]),
                "ratio_any": round(len(side_bad["left"] | side_bad["right"]) / max(1, n_rows), 5),
                "reasons": reasons},
        "segments": {"n": len(segs), "duration_s": _desc(seg_dur),
                     "total_s": round(sum(seg_dur), 3),
                     "min_s": round(min(seg_dur), 3) if seg_dur else None},
        "has_wrist_video": any("left_wrist" in k for k in info.get("features", {})),
    }


# ---------------------------------------------------------------- EgoPro / EgoStandard
def _read_pose(path: pathlib.Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    df = pd.read_csv(path, usecols=lambda c: c.startswith("transforms[") or c == "_offset_from_first_log_s")
    n = int(df["transforms.length"].iloc[0]) if "transforms.length" in df else 21
    t = df["_offset_from_first_log_s"].to_numpy(dtype=float)
    pos = np.stack([df[f"transforms[{k}].pos.{ax}"].to_numpy(dtype=float) for k in range(n) for ax in "xyz"],
                   axis=1).reshape(len(df), n, 3)
    return t, pos, np.array([n])


def profile_mcap(rec: pathlib.Path, dataset: str, split_row: dict) -> dict:
    seg = pd.read_csv(rec / "tables" / "annotation_semantic_segments.csv")
    badf = rec / "tables" / "annotation_bad_frame_pose_hand.csv"
    bdf = pd.read_csv(badf)
    is_bad = bdf["is_bad"].astype(str).str.lower().isin(("true", "1")).to_numpy()

    hands, rows = {}, {}
    for side in ("left", "right"):
        t, pos, n = _read_pose(rec / "tables" / f"pose_{side}_hand.csv")
        rows[side] = len(pos)
        cen = np.nanmean(pos, axis=1)
        step = np.linalg.norm(np.diff(cen, axis=0), axis=1)
        sp = np.linalg.norm(np.diff(pos, axis=0), axis=2)
        kp_speed = np.nanmean(sp, axis=0)
        hands[side] = {
            "keypoints": int(n[0]),
            "nan_keypoint_frame_frac": round(float(np.isnan(pos).any(axis=2).mean()), 5),
            "centroid_span_m": [round(float(np.nanmax(cen[:, i]) - np.nanmin(cen[:, i])), 3) for i in range(3)],
            "speed_m_per_s": _desc([float(x) / max(1e-6, float(np.median(np.diff(t))))
                                    for x in step[np.isfinite(step)]]),
            "jump_gt_0p2m": int((step > 0.2).sum()),
            "keypoint_speed_top3": [int(i) for i in np.argsort(-np.nan_to_num(kp_speed))[:3]],
            "keypoint_speed_spread": round(float(np.nanmax(kp_speed) - np.nanmin(kp_speed)), 5),
        }
        hands[side]["t0"] = float(t[0])
        hands[side]["dt"] = _dt_stats(t)

    # 注意：MCAP 只导出 problem_type.length（数组长度），具体类型码未导出，
    # 因此这里只能统计"每个坏帧标了几类问题"，不能当"哪一类问题"用。
    plen = {}
    if "problem_type.length" in bdf.columns:
        vc = bdf.loc[is_bad, "problem_type.length"].astype(str).value_counts()
        plen = {str(k): int(v) for k, v in vc.items() if str(k) not in ("nan", "None", "")}
    seg_dur = (seg["segment.end_time"] - seg["segment.start_time"]).astype(float).tolist()
    return {
        "kind": "mcap", "dataset": dataset, "record": rec.name, **split_row,
        "rows": rows, "duration_s": round(float(bdf["_offset_from_first_log_s"].max()), 3),
        "dt": _dt_stats(bdf["_offset_from_first_log_s"].to_numpy(dtype=float)),
        "hand": hands,
        "bad": {"rows": int(len(bdf)), "bad_frames": int(is_bad.sum()),
                "ratio": round(float(is_bad.mean()), 5), "problem_type_len": plen},
        "has_wrist_video": any((rec / "videos" / f"{ch}_frames.csv").exists()
                               for ch in ("left_wrist", "right_wrist")),
        "segments": {"n": int(len(seg)), "duration_s": _desc(seg_dur),
                     "total_s": round(sum(seg_dur), 3),
                     "min_s": round(min(seg_dur), 3) if seg_dur else None},
        "table_rows_equal": len({len(bdf), *rows.values()}) == 1,
    }


# ---------------------------------------------------------------- 运行段（自然遮挡）
def occlusion_runs(flags: np.ndarray, times: np.ndarray, min_len: int = 1) -> list[dict]:
    runs, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            if i - start >= min_len:
                runs.append({"start_s": float(times[start]), "end_s": float(times[i - 1]),
                             "frames": int(i - start),
                             "dur_s": float(times[i - 1] - times[start])})
            start = None
    if start is not None and len(flags) - start >= min_len:
        runs.append({"start_s": float(times[start]), "end_s": float(times[-1]),
                     "frames": int(len(flags) - start),
                     "dur_s": float(times[-1] - times[start])})
    return runs


# ---------------------------------------------------------------- 任务与采样
def profile_tasks() -> dict:
    tasks = pd.read_csv(CON / "tasks.csv")
    cond = json.loads((CON / "common_conditions.json").read_text(encoding="utf-8-sig"))
    seg = pd.read_csv(CON / "source_segment_index.csv")
    zones = pd.read_csv(CON / "service_zones.csv")
    fam = pd.read_csv(CON / "job_families.csv")

    dur = seg["duration_s"].astype(float)
    eligible = seg["eligible"].astype(int) == 1
    cases = {}
    for cid, g in tasks.groupby("case_id"):
        c = cond["cases"][[x["case_id"] for x in cond["cases"]].index(cid)]
        pred = {}
        for _, r in g.iterrows():
            p = str(r["predecessors"]).strip()
            pred[r["job_id"]] = [x.strip() for x in p.replace(";", ",").split(",") if x.strip()] if p and p.lower() != "nan" else []
        # 前驱闭包（每个 job 之前必须先完成多少个）
        chain_len = {}
        def depth(j, seen=()):
            if j in chain_len:
                return chain_len[j]
            if j in seen:
                return 0
            d = 0
            for p in pred.get(j, []):
                d = max(d, 1 + depth(p, seen + (j,)))
            chain_len[j] = d
            return d
        for j in pred:
            depth(j)
        # 用各 family 的中位时长做一条「乐观下界」：只用于判断时间窗是否紧，不是真调度结果
        med = {f: float(seg.loc[(seg.family_id == f) & eligible, "duration_s"].median()) for f in fam.family_id}
        svc = {r.job_id: med.get(r.family_id, 0.0) + cond["service"]["beta_s"] for _, r in g.iterrows()}
        chain_min = {}
        def chain_time(j):
            if j in chain_min:
                return chain_min[j]
            own = svc[j]
            if pred.get(j):
                own += max(chain_time(p) for p in pred[j])
            chain_min[j] = own
            return own
        for j in svc:
            chain_time(j)
        cases[cid] = {
            "jobs": int(len(g)), "horizon_s": c["horizon_s"],
            "cost_budget": c["cost_budget"], "observation_limit": c["observation_limit"],
            "family_mix": {k: int(v) for k, v in g["family_id"].value_counts().items()},
            "zone_mix": {k: int(v) for k, v in g["zone_id"].value_counts().items()},
            "weight": {"sum": float(g["priority_weight"].sum()), "by_job": g["priority_weight"].tolist()},
            "release": {"min": float(g["release_s"].min()), "max": float(g["release_s"].max()),
                        "nonzero": int((g["release_s"] > 0).sum())},
            "due": {"min": float(g["due_s"].min()), "median": float(g["due_s"].median()),
                    "max": float(g["due_s"].max())},
            "precedence_edges": int(sum(len(v) for v in pred.values())),
            "max_chain": int(max(chain_len.values())),
            "optimistic_chain_s": round(float(max(chain_min.values())), 2),
            "optimistic_sum_s": round(float(sum(svc.values())), 2),
            "tightness_sum_over_H": round(float(sum(svc.values()) / c["horizon_s"]), 3),
            "due_before_H_all": bool((g["due_s"] <= c["horizon_s"]).all()),
        }
    return {
        "cases": cases,
        "segments": {
            "rows": int(len(seg)), "eligible": int(eligible.sum()),
            "eligible_ge_1p2": int((eligible & (dur >= 1.2 - 1e-9)).sum()),
            "duration_s": _desc(dur[eligible].tolist()),
            "by_family": {k: {"n": int(v), "median_s": round(float(dur[(seg.family_id == k) & eligible].median()), 3),
                              "eligible": int((eligible & (seg.family_id == k)).sum())}
                          for k, v in seg["family_id"].value_counts().items()},
            "by_split": {k: int((seg.split == k).sum()) for k in ("train", "validation", "test")},
            "by_dataset": {k: int((seg.dataset == k).sum()) for k in seg["dataset"].unique()},
            "records": int(seg.episode_uuid.nunique()),
            "units_per_record": _desc(seg.groupby("episode_uuid").size().tolist()),
        },
        "zones": zones.to_dict(orient="records"),
        "families": fam.to_dict(orient="records"),
        "seeds": {"n": len(cond["validation_seeds"]), "first": cond["validation_seeds"][0],
                  "last": cond["validation_seeds"][-1]},
    }


def _record_meta(rec: pathlib.Path, dataset: str) -> dict:
    """录制目录 -> 规范标识。目录名只是录制名，record_split 用的是 episode_uuid。"""
    keys = ("episode_uuid", "environment_id", "scene_id", "operator_id")
    if dataset == "EgoDemo":
        ep = pd.read_parquet(rec / "meta" / "episodes" / "chunk-000" / "file-000.parquet")
        return {k: str(ep[k].iloc[0]) for k in keys}
    md = pd.read_csv(rec / "session_metadata.csv")
    g = dict(zip(md["field"].astype(str), md["value"].astype(str)))
    return {"episode_uuid": g.get("task_info.episode_uuid", ""),
            "environment_id": g.get("task_info.environment_id", ""),
            "scene_id": g.get("task_info.scene_id", ""),
            "operator_id": g.get("operator.operator_id", "")}


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="show", action="store_true")
    args = ap.parse_args()

    split = pd.read_csv(CON / "record_split.csv")
    split_by_uuid = {r.episode_uuid: {"episode_uuid": r.episode_uuid, "dataset": r.dataset,
                                      "environment_id": r.environment_id, "scene_id": r.scene_id,
                                      "operator_id": r.operator_id, "split": r.split}
                     for r in split.itertuples()}

    records = []
    demo_dir = RAW / "EgoDemo"
    for rec in sorted([p for p in demo_dir.iterdir() if p.is_dir()]):
        # EgoDemo 的目录名 E001 是录制名，真 uuid 在 meta/episodes 的 episode_uuid 列
        meta = _record_meta(rec, "EgoDemo")
        row = dict(meta, split=split_by_uuid.get(meta["episode_uuid"], {}).get("split"))
        records.append(profile_demo(rec, {k: row.get(k) for k in
                                          ("episode_uuid", "environment_id", "scene_id", "operator_id", "split")}))

    for ds in ("EgoPro", "EgoStandard"):
        for rec in sorted([p for p in (RAW / ds).iterdir() if p.is_dir()]):
            meta = _record_meta(rec, ds)
            row = dict(meta, split=split_by_uuid.get(meta["episode_uuid"], {}).get("split"))
            records.append(profile_mcap(rec, ds, {k: row.get(k) for k in
                                                  ("episode_uuid", "environment_id", "scene_id", "operator_id", "split")}))

    # 自然遮挡段
    runs = {"demo": [], "mcap": []}
    for r in records:
        rec_path = (RAW / ("EgoDemo" if r["kind"] == "demo" else r["dataset"]) / r["record"])
        if r["kind"] == "demo":
            bad = json.loads((rec_path / "bad_frame_ratio.json").read_text(encoding="utf-8"))
            tot = int(r["rows"]) if r["rows"] else 0
            flags = np.zeros(tot, dtype=bool)
            for d in bad.get("hand_bad_frame_details", []):
                if d.get("left_bad_reason") or d.get("right_bad_reason"):
                    f = int(d["frame"])
                    if 0 <= f < tot:
                        flags[f] = True
            times = np.arange(tot, dtype=float) / float(r["fps_declared"] or 30.0)
            runs["demo"] += [{"record": r["record"], **x} for x in occlusion_runs(flags, times)]
        else:
            b = pd.read_csv(rec_path / "tables" / "annotation_bad_frame_pose_hand.csv",
                            usecols=["_offset_from_first_log_s", "is_bad"])
            flags = b["is_bad"].astype(str).str.lower().isin(("true", "1")).to_numpy()
            runs["mcap"] += [{"record": f'{r["dataset"]}/{r["record"][:8]}', **x}
                             for x in occlusion_runs(flags, b["_offset_from_first_log_s"].to_numpy(dtype=float))]

    def runsum(rs):
        d = [x["dur_s"] for x in rs]
        return {"n": len(rs), "duration_s": _desc(d),
                "ge_0p2": int(sum(1 for x in d if x >= .2)),
                "ge_1s": int(sum(1 for x in d if x >= 1.0)),
                "ge_3s": int(sum(1 for x in d if x >= 3.0)),
                "records_with_runs": len({x["record"] for x in rs})}

    # 聚合
    by_ds = {}
    for ds in ("EgoDemo", "EgoPro", "EgoStandard"):
        rs = [r for r in records if r.get("dataset", "EgoDemo" if r["kind"] == "demo" else None) == ds]
        if not rs:
            rs = [r for r in records if r["kind"] == "demo"] if ds == "EgoDemo" else []
        if not rs:
            continue
        by_ds[ds] = {
            "records": len(rs),
            "rows_total": int(sum(r["rows"] if isinstance(r["rows"], int) else sum(r["rows"].values()) for r in rs)),
            "duration_total_s": round(float(sum(r["duration_s"] for r in rs)), 2),
            "duration_median_s": round(float(st.median([r["duration_s"] for r in rs])), 2),
            "bad_ratio_median": round(float(st.median([(r["bad"]["ratio_any"] if r["kind"] == "demo" else r["bad"]["ratio"]) for r in rs])), 5),
            "bad_ratio_max": round(float(max([(r["bad"]["ratio_any"] if r["kind"] == "demo" else r["bad"]["ratio"]) for r in rs])), 5),
            "segments_total": int(sum(r["segments"]["n"] for r in rs)),
            "segments_median_dur_s": round(float(st.median([r["segments"]["duration_s"]["median"] for r in rs if r["segments"]["n"]])), 2),
            "dt_median_s": round(float(st.median([r["dt"]["median_s"] for r in rs])), 5),
            "dt_neg_total": int(sum(r["dt"].get("neg", 0) for r in rs)),
            "split": {k: int(sum(1 for r in rs if r.get("split") == k)) for k in ("train", "validation", "test")},
            "environments": len({r.get("environment_id") for r in rs if r.get("environment_id")}),
            "table_rows_equal_all": all(r.get("table_rows_equal", True) for r in rs),
        }

    prof = {
        "generated_by": "code/profile_data.py",
        "source": {"raw": str(RAW), "constraints": str(CON)},
        "counts": {"records": len(records),
                   "by_dataset": {k: sum(1 for r in records if (r.get("dataset") or ("EgoDemo" if r["kind"] == "demo" else "")) == k)
                                  for k in ("EgoDemo", "EgoPro", "EgoStandard")},
                   "environments": len({r.get("environment_id") for r in records if r.get("environment_id")}),
                   "operators": len({r.get("operator_id") for r in records if r.get("operator_id")}),
                   "scenes": len({r.get("scene_id") for r in records if r.get("scene_id")})},
        "by_dataset": by_ds,
        "occlusion": {"demo": runsum(runs["demo"]), "mcap": runsum(runs["mcap"])},
        "tasks": profile_tasks(),
        "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(prof, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}  {OUT.stat().st_size} B")
    if args.show:
        print(json.dumps({k: prof[k] for k in ("counts", "by_dataset", "occlusion")},
                         ensure_ascii=False, indent=1))
        print(json.dumps(prof["tasks"]["cases"], ensure_ascii=False, indent=1))
        print(json.dumps(prof["tasks"]["segments"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
