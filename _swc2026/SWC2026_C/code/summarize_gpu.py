
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""把 p1b_gpu.json / p2_gpu.json 汇总成对照表（写 data/gpu_summary.json + 控制台）。"""
import json
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DATA = os.path.abspath(DATA)

p1 = json.load(open(os.path.join(DATA, "p1b_gpu.json"), encoding="utf-8"))
p2 = json.load(open(os.path.join(DATA, "p2_gpu.json"), encoding="utf-8"))

print("=" * 78)
print("P1-b  观测可靠性（标注坏帧 = badL|badR）")
print("=" * 78)
b = p1["_meta"]["baseline_cpu_test"]
print(f"  CPU 基线   AUC 校准 {b['auc_calibrated']:.4f} / 几何 {b['auc_geometry']:.4f} / "
      f"融合 {b['auc_fused']:.4f}   AP {b['ap_fused']:.4f}")
print(f"  GPU TCN    AUC {p1['test_auc']:.4f}   AP {p1['test_ap']:.4f}   "
      f"AP lift {p1['test_ap_lift']:.2f}x   best_epoch {p1['best_epoch']}")
print(f"  AUC 提升   {p1['test_auc'] - b['auc_fused']:+.4f}  "
      f"({(p1['test_auc'] / b['auc_fused'] - 1) * 100:+.1f}% 相对)")
print("  分环境：")
for e in p1["per_env_test"]:
    print(f"    {e['env']:38s} n={e['n']:6d} pos={e['positives']:4d} AUC={e['auc_bad']:.4f}")

print()
print("=" * 78)
print("P2  缺失观测下的轨迹预测（头坐标系手腕，位移量）")
print("=" * 78)
ridge = {
    6: ("RMSE 2.34 cm / 中位 0.84 cm", "ridge CV（crossover.json, cap 300）"),
    30: ("中位 15.30 cm / q90 101.9 cm", "ridge 保形（interval.json）"),
    60: ("中位 57.62 cm / q90 406.9 cm", "ridge 保形（interval.json）"),
}
rows = {}
for r in p2["rows"]:
    rows[(r["L_frames"], r["variant"])] = r
print(f"{'档位':>12} {'试验档':>6}  {'ridge(CPU)':>22}  {'GPU v1(同输入)':>18}  {'GPU v2(80维)':>18}")
for L in sorted({r["L_frames"] for r in p2["rows"]}):
    v0 = ridge.get(L, ("—", ""))[0]
    a = rows[(L, "v1")]
    c = rows[(L, "v2")]
    print(f"{L:>3d} 帧={L/30:.2f}s      {v0:>22}  "
          f"{100*a['test_rmse_m']:>7.2f}/{100*a['test_median_err_m']:<4.2f} cm     "
          f"{100*c['test_rmse_m']:>7.2f}/{100*c['test_median_err_m']:<4.2f} cm")
print()
print("  详细：按需看 data/p2_gpu.json 的 test_rmse_per_frame_m（逐帧误差曲线）")
print(f"  GPU 总训练时长 {p2['total_seconds']} 秒（8 组：4 档位 x 2 变体 x 40 epoch）")

out = {
    "_meta": {
        "note": "GPU 训练汇总；对照 CPU 基线见各块 baseline 字段",
        "env": {"gpu": "NVIDIA GeForce RTX 4060 Laptop 8.59 GB",
                "torch": "2.14.1+cu126", "cuda": "12.6", "capability": "8.9",
                "python": "python"},
        "caveat": "ridge 基线在 cap 300-400 窗口子集上评估，GPU 在全滑窗上评估；"
                  "同一 record 划分，方向稳健，倍数按量级读",
    },
    "p1b": p1,
    "p2": p2,
}
fp = os.path.join(DATA, "gpu_summary.json")
with open(fp, "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"  saved -> {fp}")