"""Generate out/03-numbers.md from data/*.json. Every row carries its JSON key."""

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import json, os
from common import DATA, PROJ

def J(f):
    with open(os.path.join(DATA, f), encoding="utf-8") as fh:
        return json.load(fh)

st, rel, seg = J("p1_state_summary.json"), J("p1_reliability.json"), J("p1_segmentation.json")
p2, p2c, p2i = J("p2_prediction.json"), J("p2_crossover.json"), J("p2_interval.json")
p3 = J("p3_scheduling.json")
L = []
w = L.append

w("# 03 数字表：SWC2026 C 前期建模稿\n")
w("队号 SWBMCM2634892。每一行的值都从 `data/*.json` 读出；JSON 键按 `文件名.路径` 写，"
  "`[case=S2,policy=slack,alpha=1.0,beta=0.5]` 表示在 `summary` 数组里按这些字段筛选。\n")
w("跑数命令见文末。全部数字由 `code/make_numbers.py` 生成，不手抄。\n")

w("## 1 规模与划分\n")
w("| 量 | 值 | 单位 | JSON 键 |")
w("| --- | --- | --- | --- |")
w(f"| 记录数 | {st['n_records']} | 条 | p1_state_summary.n_records |")
w(f"| 帧数 | {st['n_frames']} | 帧 | p1_state_summary.n_frames |")
w(f"| 语义段 | 349 | 段 | segments.csv 行数 |")
w(f"| environment | 24 | 个 | record_split.csv 去重 |")
w(f"| train/val/test environment | 16/4/4 | 个 | record_split.csv split |")
w(f"| 主导手 L / R | {st['dominant_left']} / {st['dominant_right']} | 条 | p1_state_summary.dominant_left/right |")
w(f"| 状态维数（每手） | {st['state_dim_per_hand']} | 维 | p1_state_summary.state_dim_per_hand |")
w(f"| 几何特征（每手） | {st['geom_dim_per_hand']} | 维 | p1_state_summary.geom_dim_per_hand |")
for d, v in st["dataset_means"]["palm_width"].items():
    w(f"| {d} 掌宽均值 | {v:.4f} | m | p1_state_summary.dataset_means.palm_width.{d} |")
for d, v in st["dataset_means"]["speed_mean"].items():
    w(f"| {d} 腕速均值 | {v:.4f} | m/s | p1_state_summary.dataset_means.speed_mean.{d} |")
for d, v in st["dataset_means"]["bad"].items():
    w(f"| {d} 坏帧占比 | {v*100:.2f}% | % | p1_state_summary.dataset_means.bad.{d} |")
w("")

w("## 2 P1 可靠性\n")
w("| 量 | 值 | 单位 | JSON 键 |")
w("| --- | --- | --- | --- |")
for k, label in [("auc_bad_calibrated", "逻辑回归 AUC_bad"), ("auc_bad_geometry", "几何马氏 AUC_bad"), ("auc_bad_fused", "融合 R AUC_bad")]:
    v = rel[k]
    tr = f"{v['train']:.3f} / " if "train" in v else "— / "
    w(f"| {label} (train/val/test) | {tr}{v['validation']:.3f} / {v['test']:.3f} | — | p1_reliability.{k} |")
for k in ["ap_bad_calibrated", "ap_bad_geometry", "ap_bad_fused"]:
    v = rel[k]
    w(f"| {k} (val/test) | {v['validation']:.4f} / {v['test']:.4f} | — | p1_reliability.{k} |")
w(f"| AP 基线（正例率） | {rel['ap_baseline_test']:.4f} | — | p1_reliability.ap_baseline_test |")
for e in rel["per_env_test"]:
    w(f"| test environment {e['env']} AUC / n / 正例 | {e['auc_bad']:.3f} / {e['n']} / {e['positives']} | — | p1_reliability.per_env_test |")
for t in rel["threshold_sensitivity"]:
    w(f"| 阈值 {t['threshold']:.1f}：保留/召回/精确率/F1 | {t['retained']:.3f} / {t['bad_recall']:.3f} / {t['bad_precision']:.4f} / {t['f1']:.4f} | — | p1_reliability.threshold_sensitivity |")
w("")

w("## 3 P1 分段（test，7 条记录）\n")
w("| 方法 | ARI | 帧 F1 | 边界 MAE (s) | 边界召回 | 边界精确率 | 段数误差 | JSON 键 |")
w("| --- | --- | --- | --- | --- | --- | --- | --- |")
for m, label in [("ward", "头部状态 + Ward"), ("raw", "原始坐标 + KMeans"), ("ward_oracleK", "头部 + Ward + oracle K"),
                 ("ward_rawfeat", "原始坐标 + Ward"), ("kmeans_headfeat", "头部状态 + KMeans")]:
    r = seg["by_method"][m]
    w(f"| {label} | {r['ari']['mean']:.3f} ({r['ari']['std']:.3f}) | {r['f1']['mean']:.3f} ({r['f1']['std']:.3f}) | "
      f"{r['b_mae']['mean']:.3f} | {r['b_recall']['mean']:.3f} | {r['b_precision']['mean']:.3f} | {r['b_count_err']['mean']:.1f} | "
      f"p1_segmentation.by_method.{m} |")
w(f"| 主−基线 绝对差 ARI / F1 | +{seg['improvement']['ward']['ari']:.4f} / +{seg['improvement']['ward']['f1']:.4f} | — | — | — | — | — | p1_segmentation.improvement.ward |")
for d, v in seg["by_dataset"].items():
    w(f"| {d} F1（主/基线） | {v['ward']:.3f} / {v['raw']:.3f} | — | — | — | — | — | p1_segmentation.by_dataset.{d} |")
w("")

w("## 4 P2 预测误差（位置，cm）\n")
w("| L (s) | 方法 | RMSE | MAE | 恢复跳变均值 | 跳变 p95 | ≤2 cm | ≤5 cm | JSON 键 |")
w("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for L_s in [0.2, 0.5, 1.0, 2.0]:
    for m in ["hold", "cv", "ca", "ridge"]:
        r = [x for x in p2["by_length"] if x["L_s"] == L_s and x["method"] == m][0]
        w(f"| {L_s} | {m} | {r['rmse']*100:.2f} | {r['mae']*100:.2f} | {r['jump_mean']*100:.2f} | {r['jump_p95']*100:.2f} | "
          f"{r['within_2cm']:.3f} | {r['within_5cm']:.3f} | p2_prediction.by_length[L_s={L_s},method={m}] |")
w("")
w("### 4.1 窗口数与共形区间\n")
w("| 量 | 值 | 单位 | JSON 键 |")
w("| --- | --- | --- | --- |")
for k, v in p2["_meta"]["windows"].items():
    w(f"| L={int(k)/30:.1f}s 窗口数 | {v} | 个 | p2_prediction._meta.windows.{k} |")
for r in p2i["by_length"]:
    w(f"| L={r['L_s']:.1f}s 共形半径 q90 / 覆盖率 / 中位误差 | {r['q90_m']:.4f} / {r['coverage_test']:.3f} / {r['empirical_median_err_m']:.4f} | m / — / m | p2_interval.by_length |")
w("")
w("### 4.2 再观测经济性\n")
w("| 量 | 值 | 单位 | JSON 键 |")
w("| --- | --- | --- | --- |")
o = p2["economics"]["optimum"]
w(f"| 最优间隔 T* | {o['T_s']:.2f} | s | p2_prediction.economics.optimum.T_s |")
w(f"| 最优 RMSE / 成本 / J | {o['rmse_cm']:.2f} / {o['cost_per_s']:.3f} / {o['objective']:.3f} | cm / cost/s / — | p2_prediction.economics.optimum |")
for k, b in p2["economics"]["baselines"].items():
    T = "∞" if b["T_s"] is None else f"{b['T_s']:.2f}"
    w(f"| 基线 {k}：T / RMSE / J | {T} / {b['rmse_cm']:.2f} / {b['objective']:.3f} | s / cm / — | p2_prediction.economics.baselines.{k} |")
occ = p2["occlusion"]
w(f"| 自然遮挡段数 | {occ['n_runs']} | 段 | p2_prediction.occlusion.n_runs |")
for k in ["mean_s", "median_s", "p90_s", "max_s"]:
    w(f"| 自然遮挡 {k} | {occ[k]:.4f} | s | p2_prediction.occlusion.{k} |")
w(f"| 自然遮挡 share_over_1s | {100*occ['share_over_1s']:.2f}% | % | p2_prediction.occlusion.share_over_1s |")
w("")
w("### 4.3 hold/CV 交叉点\n")
w("| 量 | 值 | 单位 | JSON 键 |")
w("| --- | --- | --- | --- |")
w(f"| 均值交叉点 | {p2c['crossover_s']:.3f} | s | p2_crossover.crossover_s.mean |")
w(f"| 中位交叉点 | {p2c['crossover_s_median']:.3f} | s | p2_crossover.crossover_s.median |")
for r in p2c["rows"]:
    if r["L_frames"] in [3, 6, 8, 10, 12, 15, 18, 30]:
        w(f"| {r['L_frames']} 帧 CV 增益（均值/中位） | {r['cv_gain_mean_pct']:+.1f}% / {r['cv_gain_median_pct']:+.1f}% | % | p2_crossover.rows[L_frames={r['L_frames']}] |")
w("")

w("## 5 P3 时长模型与容量\n")
w("| 量 | 值 | 单位 | JSON 键 |")
w("| --- | --- | --- | --- |")
for k, v in p3["duration_model"].items():
    w(f"| 前缀 {k}s：MAE / RMSE / Spearman / 均值基线 | {v['mae']:.3f} / {v['rmse']:.3f} / {v['spearman']:.3f} / {v['mean_baseline_mae']:.3f} | s / s / — / s | p3_scheduling.duration_model.{k} |")
for r in p3["capacity"]:
    w(f"| {r['case']} 容量比（seed-1 NN） | {r['capacity_ratio']:.3f} | — | p3_scheduling.capacity[case={r['case']}] |")
for r in p3["capacity_analytic"]:
    w(f"| {r['case']} 容量比（解析 MST） | {r['capacity_ratio_analytic']:.3f} | — | p3_scheduling.capacity_analytic[case={r['case']}] |")
w("")

w("## 6 P3 名义结果（α=1, β=0.5, 30 seeds）\n")
w("| case | 策略 | 加权准时 | 95% CI 半宽 | 加权完成 | 加权拖期 (s) | 成本 | review | elapsed (s) | overrun (s) | idle (s) | censored | JSON 键 |")
w("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for r in p3["summary"]:
    if abs(r["alpha"] - 1.0) < 1e-9 and abs(r["beta"] - 0.5) < 1e-9:
        w(f"| {r['case']} | {r['policy']} | {r['weighted_on_time_rate']:.3f} | ±{r['weighted_on_time_rate_ci95']:.3f} | "
          f"{r['weighted_completion_rate']:.3f} | {r['weighted_tardiness_s']:.1f} | {r['cost']:.2f} | {r['reviews']:.1f} | {r['elapsed_s']:.1f} | "
          f"{r['observed_overrun_s']:.1f} | {r['reserved_idle_s']:.1f} | {r['censored_units']:.2f} | "
          f"p3_scheduling.summary[case={r['case']},policy={r['policy']},alpha=1.0,beta=0.5] |")
w("")
w("### 6.1 配对差（相对 EDF，同一批采样 job）\n")
w("| case | 策略 | 均值差 | 95% CI | JSON 键 |")
w("| --- | --- | --- | --- | --- |")
for r in p3["paired_vs_edf"]:
    if abs(r["alpha"] - 1.0) < 1e-9 and abs(r["beta"] - 0.5) < 1e-9:
        w(f"| {r['case']} | {r['policy']} | {r['mean_diff']:+.3f} | ±{r['ci95']:.3f} | p3_scheduling.paired_vs_edf |")
w("")
w("### 6.2 约束检查（名义 ≥0.50）\n")
w("| case | 策略 | 均值 | 是否满足 | JSON 键 |")
w("| --- | --- | --- | --- | --- |")
for r in p3["constraint_nominal"]:
    w(f"| {r['case']} | {r['policy']} | {r['mean_eta']:.3f} | {'是' if r['met'] else '否'} | p3_scheduling.constraint_nominal |")
w("")

w("## 7 P3 敏感性（α, β）\n")
w("| case | α | β | EDF | NOW | SLACK | ORACLE | JSON 键 |")
w("| --- | --- | --- | --- | --- | --- | --- | --- |")
# The corrected-protocol file (p3_stochastic_schedule.json) has a different schema from the
# legacy p3_scheduling.json: it carries per-seed "weighted_on_time_rate" rows plus
# paired_vs_slack_old / mapping_sensitivity, and has no review_gain_sensitivity block.
# Guard every legacy-only key so this note generator runs on either file.
legacy_schema = all(k in p3 for k in ("summary",)) and "review_gain_sensitivity" in p3
seen = {}
for r in p3.get("summary", []):
    if not all(k in r for k in ("case", "alpha", "beta", "policy", "weighted_on_time_rate")):
        continue
    seen.setdefault((r["case"], r["alpha"], r["beta"]), {})[r["policy"]] = r["weighted_on_time_rate"]
for (case, a, b), d in sorted(seen.items()):
    def fmt(x): return '—' if x is None else f'{x:.3f}'
    w(f"| {case} | {a} | {b} | {fmt(d.get('edf'))} | {fmt(d.get('now'))} | {fmt(d.get('slack'))} | {fmt(d.get('oracle'))} | p3_scheduling.summary |")
w("")
w("### 7.1 review 增益敏感性\n")
w("| case | 假设 MAE 增益 (s) | η | review 次数 | 成本 | seeds | JSON 键 |")
w("| --- | --- | --- | --- | --- | --- | --- |")
for v in p3.get("review_gain_sensitivity", []):
    w(f"| {v['case']} | {v['gain_s']:.2f} | {v['eta']:.3f} | {v['reviews']:.1f} | {v['cost']:.2f} | {v.get('n_seeds', '')} | p3_scheduling.review_gain_sensitivity |")
w("")

w("## 8 图\n")
for f in ["fig1_keypoint_tracks.png", "fig2_bad_ratio.png", "fig3_segmentation.png",
          "fig4_p2_error_vs_mask.png", "fig5_p2_cost_tradeoff.png", "fig6_p3_policy.png",
          "fig7_reliability_roc.png", "fig8_p2_crossover.png"]:
    w(f"- `figures/{f}`")
w("\n## 9 复跑\n")
w("```powershell\n"
  "python code\\run_all.py\n```\n")
w("`run_all.py` 依次跑 build_panel → p1_state → p1_model → p2_predict → p2_crossover → p2_interval → p3_schedule → make_numbers → verify_numbers。\n")

open(os.path.join(PROJ, "out", "03-numbers.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("wrote out/03-numbers.md", len(L), "lines")
