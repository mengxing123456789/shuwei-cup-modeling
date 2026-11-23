
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""C 题数字对账的可复算脚本（只读 data/，只写 data/audit_recompute.json）。

覆盖：
  1. P1-b 训练/验证/测试窗口数（05 的 46,276 能否复算）
  2. P2 “ridge 基线”到底是 ridge 还是 CV（05 的 2.34/0.84/77.7%）
  3. P3 05 四个头条数字落在哪个 alpha/beta 单元格
  4. 旧协议 p3_scheduling 与修正协议 p3_stochastic_schedule 的同一策略对照
  5. 视频体积、verify_numbers/make_numbers 的静态可运行性
  6. 审计期间新增资产与脚本 mtime 关系
"""
import glob
import json
import math
import os
import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CODE = os.path.join(ROOT, "code")
CVIDEO = r"Restocking_Problem_and_Data_EN"  # raw package (mp4s) lives here; E: copy removed 2026-11-20


def J(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def mtime(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")


def find_rows(rows, field, target, tol=5e-4):
    return [r for r in rows if isinstance(r.get(field), (int, float)) and abs(r[field] - target) < tol]


out = {}

# ---------------------------------------------------------------- 1. P1-b 窗口
z = np.load(os.path.join(DATA, "state.npz"))
rec = z["rec"].astype(np.int64)
meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
split_of = dict(zip(meta["rec"].astype(int), meta["split"].astype(str)))
T = 15
win = {}
for r in np.unique(rec):
    n = int((rec == r).sum())
    s = split_of[int(r)]
    win[s] = win.get(s, 0) + max(0, n - T + 1)
out["p1b_windows"] = {
    "counts": win,
    "total": int(sum(win.values())),
    "frames": int(len(rec)),
    "note": "state.npz rec + panel_records.split；T=15，stride=1；05 的 46,276 可复算",
}
out["p1b_window_check"] = {
    "claimed": 46276,
    "recomputed_train": win.get("train"),
    "match": win.get("train") == 46276,
}

# ---------------------------------------------------------------- 2. P2 基线口径
p2p = J("p2_prediction.json")
p2c = J("p2_crossover.json")
p2g = J("p2_gpu.json")
by = {(r["method"], round(float(r["L_s"]), 3)): r for r in p2p["by_length"]}
row6 = [r for r in p2c["rows"] if r["L_frames"] == 6][0]
out["p2_baselines"] = {
    "cv_cap300_from_crossover_L6": {
        "cv_rmse_m": row6["cv_rmse_m"],
        "cv_median_m": row6["cv_median_m"],
        "n_windows": row6["n_windows"],
    },
    "cv_cap400_from_prediction_L0p2": {
        "rmse_m": by[("cv", 0.2)]["rmse"],
        "mae_m": by[("cv", 0.2)]["mae"],
        "within_2cm": by[("cv", 0.2)]["within_2cm"],
        "n_windows": by[("cv", 0.2)]["n_windows"],
    },
    "ridge_cap400_from_prediction_L0p2": {
        "rmse_m": by[("ridge", 0.2)]["rmse"],
        "mae_m": by[("ridge", 0.2)]["mae"],
        "within_2cm": by[("ridge", 0.2)]["within_2cm"],
        "n_windows": by[("ridge", 0.2)]["n_windows"],
    },
    "gpu_v1_L0p2": [r for r in p2g["rows"] if r["L_frames"] == 6 and r["variant"] == "v1"][0],
    "gpu_v2_L0p2": [r for r in p2g["rows"] if r["L_frames"] == 6 and r["variant"] == "v2"][0],
    "baseline_ridge_meta": p2g["_meta"]["baseline_ridge"],
}
r0 = out["p2_baselines"]["ridge_cap400_from_prediction_L0p2"]
v1 = out["p2_baselines"]["gpu_v1_L0p2"]
v2 = out["p2_baselines"]["gpu_v2_L0p2"]
cv = out["p2_baselines"]["cv_cap300_from_crossover_L6"]
out["p2_deltas"] = {
    "v1_vs_true_ridge_x": r0["rmse_m"] / v1["test_rmse_m"],
    "v2_vs_true_ridge_x": r0["rmse_m"] / v2["test_rmse_m"],
    "v1_vs_05_cv_x": cv["cv_rmse_m"] / v1["test_rmse_m"],
    "v2_vs_05_cv_x": cv["cv_rmse_m"] / v2["test_rmse_m"],
    "within2_true_ridge_pct": 100 * r0["within_2cm"],
    "within2_v2_pct": 100 * v2["test_within_2cm"],
    "note": "05 的 1.7x/4.3x 分母 2.34 是 CV(cap300)，不是 ridge；ridge 实际 2.00 cm",
}

# ---------------------------------------------------------------- 3. P3 05 头条数字的单元格
p3 = J("p3_scheduling.json")
targets = [0.6556, 0.5813, 0.8556, 0.7948, 0.6097, 0.8292, 0.5427, 0.7854]
p3_hits = {}
for t in targets:
    p3_hits[str(t)] = [
        {
            "case": r["case"], "alpha": r["alpha"], "beta": r["beta"], "policy": r["policy"],
            "eta": r["weighted_on_time_rate"], "reviews": r["reviews"],
        }
        for r in find_rows(p3["summary"], "weighted_on_time_rate", t)
    ]
out["p3_target_rows"] = p3_hits

nom = {(r["case"], r["policy"]): r for r in p3["summary"]
       if abs(r["alpha"] - 1) < 1e-9 and abs(r["beta"] - 0.5) < 1e-9}
out["p3_nominal"] = {
    f"{c}/{p}": {"eta": r["weighted_on_time_rate"], "ci95": r["weighted_on_time_rate_ci95"],
                 "completion": r["weighted_completion_rate"], "tardiness": r["weighted_tardiness_s"],
                 "cost": r["cost"], "reviews": r["reviews"]}
    for (c, p), r in nom.items()
}

# ---------------------------------------------------------------- 4. 修正协议对照
p3s = J("p3_stochastic_schedule.json")
stoch = {(r["case"], r["policy"]): r for r in p3s["summary"]}
pairs = [
    ("S1", "edf", "edf_old"), ("S2", "edf", "edf_old"), ("S3", "edf", "edf_old"),
    ("S1", "slack", "slack_old"), ("S2", "slack", "slack_old"), ("S3", "slack", "slack_old"),
    ("S2", "slack", "risk_fusion"), ("S3", "slack", "risk_fusion"),
]
out["p3_old_vs_corrected"] = []
for case, old_pol, new_pol in pairs:
    o = nom[(case, old_pol)]
    n = stoch[(case, new_pol)]
    out["p3_old_vs_corrected"].append({
        "case": case,
        "old_policy": old_pol,
        "corrected_policy": new_pol,
        "old_protocol_eta": o["weighted_on_time_rate"],
        "corrected_eta": n["weighted_on_time_rate"],
        "diff": n["weighted_on_time_rate"] - o["weighted_on_time_rate"],
        "old_reviews": o["reviews"],
        "corrected_reviews": n["reviews"],
        "corrected_tardiness": n["weighted_tardiness_s"],
        "corrected_cost": n["cost"],
    })
out["p3_corrected_paired"] = p3s["paired_vs_slack_old"]
out["p3_protocol_meta"] = {
    "old": p3["_meta"].get("protocol", "??"),
    "corrected": p3s["_meta"].get("protocol"),
}

# ---------------------------------------------------------------- 5. 体积 / 运行性
mp4 = glob.glob(os.path.join(CVIDEO, "**", "*.mp4"), recursive=True)
out["video"] = {
    "n_mp4": len(mp4),
    "bytes": int(sum(os.path.getsize(p) for p in mp4)),
    "gb": round(sum(os.path.getsize(p) for p in mp4) / 1e9, 3),
}
allraw = glob.glob(os.path.join(CVIDEO, "**", "*"), recursive=True)
out["video"]["gb_all_files"] = round(
    sum(os.path.getsize(p) for p in allraw if os.path.isfile(p)) / 1e9, 3)

out["static_checks"] = {
    "p3_scheduling_has_review_gain_sensitivity": "review_gain_sensitivity" in p3,
    "make_numbers_references_review_gain_sensitivity": "review_gain_sensitivity" in
        open(os.path.join(CODE, "make_numbers.py"), encoding="utf-8").read(),
    "run_all_steps": ["build_panel.py", "p1_state.py", "p1_model.py", "p2_predict.py",
                      "p2_crossover.py", "p2_interval.py", "p3_schedule.py",
                      "make_numbers.py", "verify_numbers.py"],
    "run_all_has_gpu_or_v4": any(k in open(os.path.join(CODE, "run_all.py"), encoding="utf-8").read()
                                for k in ("train_gpu", "p3_stochastic", "p3_final_duration", "p3_visual")),
}

# ---------------------------------------------------------------- 6. 新增资产
new = ["best_p1a.json", "pre_norm.json", "pre_split.json", "pre_p2_prereg.json",
       "best_p1b.json", "pre_p2_ssl.json"]
gen = {
    "best_p1a.json": "best_p1a_seg.py",
    "pre_norm.json": "pre_split.py",
    "pre_split.json": "pre_split.py",
    "pre_p2_prereg.json": "pre_p2_prereg.py",
    "best_p1b.json": "best_p1b.py",
    "pre_p2_ssl.json": "pre_ssl.py",
}
out["new_assets"] = []
for fn in new:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    g = os.path.join(CODE, gen.get(fn, ""))
    out["new_assets"].append({
        "file": fn,
        "json_mtime": mtime(p),
        "size": os.path.getsize(p),
        "generator": gen.get(fn),
        "generator_mtime": mtime(g) if os.path.exists(g) else "??",
        "artifact_older_than_code": os.path.exists(g) and os.path.getmtime(p) < os.path.getmtime(g),
    })

# ---------------------------------------------------------------- 7. P1-a 基线复现
b1a = J("best_p1a.json")
seg = J("p1_segmentation.json")
out["p1a_reproduction"] = {
    "original_ward_ari": seg["by_method"]["ward"]["ari"]["mean"],
    "new_ward_base_ari": b1a["methods"]["ward_base"]["mean"]["ari"],
    "delta": b1a["methods"]["ward_base"]["mean"]["ari"] - seg["by_method"]["ward"]["ari"]["mean"],
    "best_candidate": max(b1a["methods"].items(), key=lambda kv: kv[1]["mean"]["ari"])[0],
    "best_candidate_ari": max(v["mean"]["ari"] for v in b1a["methods"].values()),
    "deltas": b1a["delta_ari_vs_baseline"],
}

with open(os.path.join(DATA, "audit_recompute.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("P1b windows", out["p1b_windows"]["counts"], "total", out["p1b_windows"]["total"])
print("P1b 46276 match", out["p1b_window_check"]["match"])
print("P2 true ridge 0.2 rmse", r0["rmse_m"], "cv cap300", cv["cv_rmse_m"])
print("P2 ratios v1/v2 vs ridge", out["p2_deltas"]["v1_vs_true_ridge_x"],
      out["p2_deltas"]["v2_vs_true_ridge_x"])
print("P3 hits", {k: [(h["case"], h["alpha"], h["beta"], h["policy"]) for h in v]
                 for k, v in p3_hits.items() if v})
print("video GB", out["video"])
print("static", out["static_checks"])
print("new assets")
for a in out["new_assets"]:
    print(" ", a)
print("P1a", out["p1a_reproduction"]["original_ward_ari"], out["p1a_reproduction"]["new_ward_base_ari"])