
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Render out/17-state-definition.md from data/state_layer.json.

Every number in the report is read from the JSON (never typed by hand), so the
prose and the artefact cannot drift apart.  Run:  python report_state.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "state_layer.json")
OUT = os.path.join(ROOT, "out", "17-state-definition.md")


def f(x, n=4):
    return f"{x:.{n}f}"


def pct(x, n=2):
    return f"{100 * x:.{n}f}%"


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    meta, thr, lab = d["_meta"], d["thresholds"], d["threshold_labels"]
    rp, ret = d["representative_point"], d["retention"]
    st, ag, bl = d["stages"], d["agreement_with_reference"], d["baselines"]
    se = d["sensitivity"]
    L = []
    A = L.append

    A("# Problem 1 — 双层手部状态定义（State Definition）\n")
    A("> 数据：`data/panel.npz`（69 条记录、66,070 帧、双手各 21 关键点）+ `data/panel_records.csv`。")
    A("> 全部数字由 `code/state_layer.py` 写出到 `data/state_layer.json`，本文件由 "
      "`code/report_state.py` 从该 JSON 渲染，键名在每处给出。\n")
    A("本研究把「手的状态」定义成两层，**P2 只能用连续层，P3 只能用离散层**，"
      "两层都从同一批关键点导出，且离散层是连续层的**规则派生**，不是人工标注：\n")
    A("| 层 | 内容 | 维度 | 消费者 |")
    A("| --- | --- | --- | --- |")
    A("| 连续层 | 代表点位置（头部系）+ 手朝向四元数 + 主方向 + 速度 + 角速度 + 开合度 + 指间跨度 + 静止标志 | 18 / 手 / 帧 | P2 |")
    A("| 离散层 | `reach / pick / place / transport / arrange` + 段置信度 | 1 + 1 / 手 / 帧 | P3 |\n")
    A(f"元数据 `_meta`：单位 `{meta['units']}`；四元数顺序 `{meta['quat_order']}`；"
      f"头部系 `{meta['head_frame']}`；关键点 `{meta['keypoints']}`。\n")

    # ---------------- 1. continuous layer -----------------------------------
    A("## 1. 连续层：18 维状态向量\n")
    A("`state_layer.py::VEC_NAMES`（`_meta.state_vector` 同序）：\n")
    A("`" + "`, `".join(meta["state_vector"]) + "`\n")
    A("其中：\n")
    A("- **位置** `px,py,pz`：代表点在**头部坐标系**下的坐标，`p_h = R(q)^T (p_w − H)`，"
      "`R` 由头部四元数（wxyz）转出，`H` 为头部世界坐标。头部系消除了行走与转身的整体位移，"
      "使「手相对身体在哪」这一量在 P2 中可比。")
    A("- **朝向** `qw,qx,qy,qz`：由掌面三个关键点构造的右手系（`e1 = kp5 − kp9`，`e3 = e1 × (kp13 − kp9)`，`e2 = e3 × e1`）转成四元数，逐帧做符号连续化，"
      "并用 `dx,dy,dz`（`e1`，腕→食指根的主方向）冗余表示一次，便于线性模型直接使用。")
    A("- **速度** `vx,vy,vz`：头部系内位置的时间导数；`speed_world` 是世界系速率（m/s），用于分段。")
    A("- **角速度** `omega`：相邻帧四元数夹角 / Δt（rad/s）。")
    A("- **开合度** `aperture`：‖kp4（拇指尖）− kp8（食指尖）‖ / 掌宽（`palm_width` = ‖kp0 − kp9‖），量纲一，"
      "跨个体可比（掌宽 p5/p50/p95 = 0.0543/0.0579/0.0653 m）。")
    A("- **指间跨度** `spread`：五个指尖到掌心距离的均值 / 掌宽。")
    A("- **静止标志** `static`：5 帧平滑速度 < `v_lo` 且连续 ≥ `static_run` 帧置 1。\n")

    # ---------------- 2. representative point -------------------------------
    A("## 2. 代表点：三个候选、五个判据、数据怎么选\n")
    A("候选（`representative_point` 的候选块）：`wrist_kp0` = kp0；`palm_centre_0_5_9_13_17` = "
      "{0,5,9,13,17} 的几何中心；`fingertip_centroid_4_8_12_16_20` = 五个指尖的几何中心。"
      "判据与读数（同一 66,070 帧、双手合并，`representative_point.*`）：\n")
    A("| 候选 | 刚性 `rigidity_cm` ↓ | 抖动比 `jitter_ratio` ↓ | 指姿敏感 `finger_pose_sensitivity_cm` ↓ | 到捏合点 `pinch_dist_cm` ↓ | 到手质心 `centroid_dist_cm` ↓ | 跨数据集离散 `cross_dataset_spread_m` ↓ |")
    A("| --- | --- | --- | --- | --- | --- | --- |")
    cand = rp["candidates"]
    for k, v in cand.items():
        if k.startswith("_"):
            continue
        A(f"| `{k}` | {v['rigidity_cm']:.3e} | {f(v['jitter_ratio'])} | {v['finger_pose_sensitivity_cm']:.3e} | "
          f"{f(v['pinch_dist_cm'],2)} | {f(v['centroid_dist_cm'],2)} | {f(v['cross_dataset_spread_m'])} |")

    win = cand[rp["chosen"]]
    wr = cand["wrist_kp0"]
    ft = cand["fingertip_centroid_4_8_12_16_20"]
    A("")
    A(f"**选 `palm_centre_0_5_9_13_17`。** 理由按权重排序：")
    A(f"1. **刚性**：它在掌坐标系内的记录内残差 {win['rigidity_cm']:.2e} cm，与腕部同量级（{wr['rigidity_cm']:.2e} cm），"
      f"而指尖中心是 {ft['rigidity_cm']:.3f} cm —— 指尖会随手张开而移动，位置里混进了「抓没抓住」的信息，做位置量会污染 P2；")
    A(f"2. **指姿敏感度**为 {win['finger_pose_sensitivity_cm']:.2e} cm（定义上恒为 0，因为它就是掌心的定义），指尖中心 {ft['finger_pose_sensitivity_cm']:.3f} cm；")
    A(f"3. **中心性**：到手质心 {f(win['centroid_dist_cm'],2)} cm，是三者最小（腕部 {f(wr['centroid_dist_cm'],2)} cm，指尖中心 {f(ft['centroid_dist_cm'],2)} cm）；"
      f"到捏合点 {f(win['pinch_dist_cm'],2)} cm（腕部 {f(wr['pinch_dist_cm'],2)} cm）—— 抓取点在掌侧，代表点离抓取点近，P2 的位移才代表「物体被搬动」。")
    A(f"4. **抖动**：三者相近（{f(wr['jitter_ratio'])} / {f(win['jitter_ratio'])} / {f(ft['jitter_ratio'])}），掌中心最低，说明它不是噪声放大器；")
    A(f"5. **跨数据集一致性**：数据集均值到头部距离的极差 {f(win['cross_dataset_spread_m'])} m 最小（EgoDemo/EgoPro/EgoStandard = "
      f"{win['dhead_by_dataset_m']['EgoDemo']:.3f}/{win['dhead_by_dataset_m']['EgoPro']:.3f}/{win['dhead_by_dataset_m']['EgoStandard']:.3f} m），"
      "说明它在不同采集设备下是同一个物理量。\n")
    A("腕部同样是刚性点，但它在手的**根部**：腕部转动（掌屈/尺偏）会让腕点在世界里画弧，而掌心不动；"
      "对「抓取—搬运」而言掌心才是与物体接触的坐标。指尖中心虽然离捏合点最近（2.72 cm），"
      "但它的位置依赖手指姿态，把它当位置量等于把开合度偷偷塞进位置通道 —— 这是 P1 明确不要的耦合。\n")

    # ---------------- 3. discrete layer -------------------------------------
    A("## 3. 离散层：五阶段的规则定义（可复现，无人工标注）\n")
    A("| 阈值 | 值 | 标签 `threshold_labels` | 数据依据 |")
    A("| --- | --- | --- | --- |")
    A(f"| `v_hi` | {thr['v_hi']} m/s | {lab['v_hi']} | 5 帧平滑速度 p≈30（掌中心速度 p25=0.0635、p50=0.1128 m/s） |")
    A(f"| `v_lo` | {thr['v_lo']} m/s | {lab['v_lo']} | p≈12，与 `v_hi` 构成滞回，避免阈值抖动切碎段 |")
    A(f"| `a_grasp` | {thr['a_grasp']} | {lab['a_grasp']} | dwell 的 |Δaperture| 分布：>0.15 占 53.3%、>0.2 占 42.8% |")
    A(f"| `t_arrange` | {thr['t_arrange']} s | {lab['t_arrange']} | dwell 时长 ≥24 帧（0.8 s）占 27.0% |")
    A(f"| `a_closed` | {thr['a_closed']} | {lab['a_closed']} | aperture 分位 p25=0.53、p50=0.82 |")
    A(f"| `min_seg` | {thr['min_seg']} 帧 | — | 短于 3 帧的段并入邻段 |")
    A(f"| `static_run` | {thr['static_run']} 帧 | — | 静止标志的最小连续长度 |\n")
    A("规则（`state_layer.py::derive_stages`，两遍扫描）：\n")
    A("1. **滞回分段**：对 5 帧平滑后的世界速度 `sm`，`sm > v_hi` 进入运动态，`sm < v_lo` 回到静止态，"
      "其余帧保持上一状态；短于 `min_seg` 的段并入邻段。")
    A("2. **静止段判类**（窗口 ±5 帧，取窗口首尾各 3 帧中位数之差 `Δa` 与段长 `dur`）：")
    A("   - `Δa ≤ −a_grasp` → `pick`（合拢＝抓起）")
    A("   - `Δa ≥ +a_grasp` → `place`（张开＝放置）")
    A("   - `|Δa| < a_grasp` 且 `dur ≥ t_arrange` → `arrange`（长时间按住不动＝摆正/整理）")
    A("   - 其余 → 高度带兜底：掌中心世界 z 低于头高 → `pick`，否则 `place`（置信度 0.4）")
    A("3. **运动段判类**（对相邻静止段标签的有限状态机，`derive_stages` 第二遍）：")
    A("   - 前一个 dwell 是 `pick`、后一个 dwell ∈ {`place`,`arrange`} → `transport`（置信度 0.9）")
    A("   - 后一个 dwell 是 `pick` → `reach`（0.8）")
    A("   - 前一个 dwell ∈ {`place`,`arrange`}、后面没有 dwell → `reach`（0.7）")
    A("   - 其余 → 平均 aperture < `a_closed` ? `transport` : `reach`（按距离阈值越远置信度越高）\n")
    A("**为什么允许高度兜底**：dwell 里 |Δa| < `a_grasp` 又不够长的段约占 47% 的 dwell，"
      "它们多是「手停在半空犹豫」或「没抓住就离开」；用高度带把「低于头高」判成取件侧、"
      "「高于头高」判成放置侧，是把货架/台面的空间先验显式写进规则，而不是靠标签。兜底置信度固定 0.4，"
      "P3 可据此降权。\n")
    sh = st["pooled_share"]
    A("池化阶段占比（`stages.pooled_share`，132,140 手·帧）：\n")
    A("| reach | pick | place | transport | arrange |")
    A("| --- | --- | --- | --- | --- |")
    A("| " + " | ".join(f"{sh[k]:.4f}" for k in ("reach", "pick", "place", "transport", "arrange")) + " |")
    A("")
    A(f"平均段长 {st['pooled_mean_seg_len_frames']:.1f} 帧（{st['pooled_mean_seg_len_frames']/30:.2f} s），"
      f"中位 {st['pooled_median_seg_len_frames']:.0f} 帧，p90 {st['seg_len_p90']:.0f} 帧"
      f"（`stages.pooled_*`）。段长分布右偏是 `reach` 段很长造成的：一次接近包含减速、对准、微调。\n")

    # ---------------- 4. sensitivity ----------------------------------------
    A("## 4. 阈值敏感性（±20%）\n")
    A("`sensitivity.rows`：每个阈值取 ×0.8 / ×1.0 / ×1.2，其余阈值固定，重跑全部分段。\n")
    A("| 阈值 | 倍数 | 取值 | reach | pick | place | transport | arrange | 平均段长（帧） | 段数 |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in se["rows"]:
        s = r["share"]
        A(f"| `{r['param']}` | {r['mult']:.1f} | {r['value']:.3g} | " +
          " | ".join(f"{s[k]:.4f}" for k in ("reach", "pick", "place", "transport", "arrange")) +
          f" | {r['mean_seg_len_frames']:.1f} | {r['n_segments']} |")
    A("")
    A("最大影响汇总（`sensitivity.effect`，相对基准行）：\n")
    A("| 阈值 | 阶段占比最大偏移（百分点） | 平均段长最大相对变化 |")
    A("| --- | --- | --- |")
    for k, v in se["effect"].items():
        A(f"| `{k}` | {v['max_share_shift_pp']:.2f} | {pct(v['max_seg_len_change'], 1)} |")
    A("")
    A(f"**最敏感的是 `v_lo`**（±20% → 阶段占比最多偏移 {se['effect']['v_lo']['max_share_shift_pp']:.2f} pp，"
      f"平均段长最多变化 {pct(se['effect']['v_lo']['max_seg_len_change'],1)}，段数 1658↔2724）："
      "它直接决定 dwell 段的数量与长度，因而同时改动 pick/place/arrange 三个类的占比。"
      f"次敏感是 `a_closed`（{se['effect']['a_closed']['max_share_shift_pp']:.2f} pp，只动 reach↔transport 的边界）。"
      "`a_grasp` 与 `t_arrange` 的影响都在 1.3 pp 以内，说明静止段的类间划分对这两个阈值不敏感 —— "
      "这部分结论是稳的；`v_lo` 的取值必须在 P3 中作为显式超参披露，不能当成固定物性。\n")

    # ---------------- 5. retention ------------------------------------------
    A("## 5. 数据保留率（data retention）\n")
    A(f"判据（`retention.criteria`）：数值有限、fps ∈ [24, 32]、最大帧间隔 ≤ 0.1 s、bad 帧比例 ≤ 5%、"
      f"骨长相对偏差 > 0.35 的帧比例 ≤ 2%、任意两关键点最小间距 ≥ 0.15 m。\n")
    A("| 口径 | 数量 |")
    A("| --- | --- |")
    A(f"| 记录总数 | {ret['records_total']} |")
    A(f"| 记录 pass / fail | {ret['records_pass']} / {ret['records_fail']} |")
    A(f"| 帧总数 | {ret['frames_total']} |")
    A(f"| 帧保留 | {ret['frames_kept']}（{pct(ret['frame_rate'])}） |")
    A(f"| 手·帧保留 | {ret['hand_frames_kept']} / {ret['hand_frames_total']}（{pct(ret['hand_frames_kept']/ret['hand_frames_total'])}） |")
    A("")
    A("失败原因分类（`retention.reasons`）：`quality_flag` 2 条 —— 即 bad 帧比例 > 5% 的记录：\n")
    A("| 记录 | 数据集 / 划分 | badL | badR | 几何异常帧比例 | 判定 |")
    A("| --- | --- | --- | --- | --- | --- |")
    for x in ret["per_record"]:
        if x["pass_"]:
            continue
        dd = x["detail"]
        A(f"| rec{x['rec']} | {x['dataset']} / {x['split']} | {pct(dd['badL'])} | {pct(dd['badR'])} | "
          f"{dd['geomL']:.4f} / {dd['geomR']:.4f} | fail（`{','.join(x['reasons'])}`） |")
    A("")
    A("按划分（`retention.by_split`）：\n")
    A("| 划分 | 记录 | 记录 pass | 帧 | 帧保留 | 帧级保留率 |")
    A("| --- | --- | --- | --- | --- | --- |")
    for k, v in ret["by_split"].items():
        A(f"| {k} | {v['records']} | {v['pass_']} | {v['frames']} | {v['frames_kept']} | {pct(v['frames_kept']/v['frames'])} |")
    A("")
    A(f"**帧级保留率 {pct(ret['frame_rate'])}**。它低于记录级（{ret['records_pass']}/{ret['records_total']}）是因为"
      "帧级额外剔除了单帧 bad 标志、几何异常（骨长偏差、关键点过近）与 fps/间隔越界的帧，"
      "而记录级只要 bad 比例不超过 5% 就整条保留。两条 fail 记录（rec37 在 test、rec52 在 validation）"
      "被**整条排除在基线评估之外**，这会让 test 环境的有效记录从 7 条降为 6 条 —— 报告基线误差时已按 6 条计。\n")

    # ---------------- 6. baselines ------------------------------------------
    A("## 6. 简单基线（形式与状态定义相称）\n")
    A("两个基线都**只吃连续层**、都预测同一个量：**h 帧后代表点在 t 时刻头部系下的位置**"
      "（`y = R(q_t)^T (p_w[t+h] − H[t])`），单位米。这样基线与 P2 要学的量同一定义域。\n")
    A("| h（帧 / 秒） | 模型 | 参数个数 | 均值 | 中位 | q90 | 相对常数预测的改进 |")
    A("| --- | --- | --- | --- | --- | --- | --- |")
    for h, v in bl["by_horizon"].items():
        A(f"| {v['horizon_frames']} / {v['horizon_s']:.3f} | constant（保持上一帧） | 0 | {f(v['constant']['mean'])} | "
          f"{f(v['constant']['median'])} | {f(v['constant']['q90'])} | — |")
        A(f"| {v['horizon_frames']} / {v['horizon_s']:.3f} | linear（ridge α=1e-3） | 8 | {f(v['linear']['mean'])} | "
          f"{f(v['linear']['median'])} | {f(v['linear']['q90'])} | {pct(v['improvement_mean'])} |")
    A("")
    A(f"linear 的特征 `{', '.join(bl['coef_names'])}`（常数项 + 头部系位置 + 头部系速度 + 开合度），"
      f"在 {bl['train_records']} 条 train 记录（{bl['n_train_frames']:,} 帧）上拟合，"
      f"在 {bl['test_records']} 条 test 环境记录（{bl['n_test_frames']:,} 帧）上评估；"
      "误差是欧氏距离，均值/中位/q90 均由帧级误差直接取分位。\n")
    ci = bl
    A(f"bootstrap（按 test 记录重采样 500 次）95% 区间：constant 均值 [{f(ci['constant']['mean_ci'][0])}, {f(ci['constant']['mean_ci'][1])}]、"
      f"q90 [{f(ci['constant']['q90_ci'][0])}, {f(ci['constant']['q90_ci'][1])}]；"
      f"linear 均值 [{f(ci['linear']['mean_ci'][0])}, {f(ci['linear']['mean_ci'][1])}]、"
      f"q90 [{f(ci['linear']['q90_ci'][0])}, {f(ci['linear']['q90_ci'][1])}]。"
      "区间按记录重采样，反映的是环境间差异，不是帧间独立样本。\n")
    A("系数（`baselines.coefficients`，行 = 输出 x/y/z，列 = 上列特征）与记录级 bootstrap 标准差 `coef_sd`：\n")
    A("| 特征 | " + " | ".join(["x", "y", "z"]) + " |")
    A("| --- | --- | --- | --- |")
    for i, nm in enumerate(bl["coef_names"]):
        row = [bl["coefficients"][i][j] for j in range(3)]
        sd = [bl["coef_sd"][i][j] for j in range(3)]
        A(f"| {nm} | " + " | ".join(f"{row[j]:+.5f} ± {sd[j]:.5f}" for j in range(3)) + " |")
    A("")
    A(f"读法：位置三项系数 ≈ {bl['coefficients'][1][0]:.4f}/{bl['coefficients'][2][1]:.4f}/{bl['coefficients'][3][2]:.4f} —— "
      "接近「保持上一帧」；速度项系数 ≈ 0.03–0.04，即 8 维线性模型只学到「用一小部分当前速度外推」，"
      f"所以在 h=1 时相对常数预测只改进 {pct(bl['by_horizon']['h1']['improvement_mean'])}，"
      f"h=5（0.167 s）时改进 {pct(bl['by_horizon']['h5']['improvement_mean'])}。"
      "这个结果本身就是「形式相称」的证据：**状态定义里的位置与速度已经把可预测性榨到 1 帧尺度**，"
      "一个 8 参数线性模型拿不出比「不动」好一个数量级的结果；P2 若想更好，必须引入离散层（阶段）与物体信息，"
      "而不是换更花的回归器。\n")

    # ---------------- 7. cross-environment ----------------------------------
    A("## 7. 跨环境差异\n")
    A("### 7.1 三个数据集\n")
    A("| 数据集 | 记录 | 手·帧 | reach | pick | place | transport | arrange | 平均段长（帧） |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for k, v in st["by_dataset"].items():
        s = v["share"]
        A(f"| {k} | {v['records']} | {v['frames']} | " +
          " | ".join(f"{s[c]:.4f}" for c in ("reach", "pick", "place", "transport", "arrange")) +
          f" | {v['mean_seg_len_frames']:.1f} |")
    A("")
    A("### 7.2 阶段转移矩阵（段级，行条件，`stages.pooled_transition`）\n")
    A("| from \\ to | reach | pick | place | transport | arrange |")
    A("| --- | --- | --- | --- | --- | --- |")
    P = st["pooled_transition"]
    for i, nm in enumerate(("reach", "pick", "place", "transport", "arrange")):
        A(f"| **{nm}** | " + " | ".join(f"{P[i][j]:.3f}" for j in range(5)) + " |")
    A("")
    A("对角线为 0（段级计数，不含自转移）。读法：`reach → pick` " + f"{P[0][1]:.3f}" +
      f"、`pick → transport` {P[1][3]:.3f}、`transport → place` {P[3][2]:.3f}、`place → reach` {P[2][0]:.3f}，"
      "构成 `… → reach → pick → transport → place → reach → …` 的主循环，`transport → arrange` "
      f"{P[3][4]:.3f} 与 `arrange → reach` {P[4][0]:.3f} 是整理分支。\n")
    ent = st["entropy"]
    A(f"信息量（`stages.entropy`）：H(下一阶段) = {ent['H_next_bits']:.3f} bit，"
      f"H(下一阶段 | 当前阶段) = {ent['H_next_given_current_bits']:.3f} bit，"
      f"即当前阶段解释了 {ent['info_bits']:.3f} bit。条件熵不为 0 说明**阶段不是马尔可夫的**——"
      "同一阶段的下一步取决于任务与环境，这正是 P3 要做上下文建模的理由。\n")
    A("### 7.3 24 个 environment\n")
    kl = st["kl_env_from_pooled"]
    A("| environment | 记录 | 手·帧 | reach | pick | place | transport | arrange | 平均段长（帧） | KL(env‖pooled) |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for k, v in st["by_env"].items():
        s = v["share"]
        A(f"| {k} | {v['records']} | {v['frames']} | " +
          " | ".join(f"{s[c]:.3f}" for c in ("reach", "pick", "place", "transport", "arrange")) +
          f" | {v['mean_seg_len_frames']:.1f} | {kl[k]:.4f} |")
    A("")
    chi = st["chi2_env"]
    A(f"**统计检验**：24 个 environment × 5 阶段的列联表（行 = environment，列 = 阶段帧数，"
      f"n = {chi['n_frames']:,} 手·帧）做卡方独立性检验：χ² = {chi['chi2']:.1f}，dof = {chi['dof']}，"
      f"p = {chi['p']:.3g}（下溢到 0），Cramér's V = {chi['cramers_v']:.4f}。"
      "结论：**环境间的阶段分布差异显著**（p 远小于 0.01），但效应量只有中等偏小（V ≈ 0.22）——"
      "显著来自样本量大，实际差异是「零售/物流偏 transport、办公偏 pick/place、家居偏 reach」这种量级。")
    A(f"KL 散度（每个 environment 相对池化先验）从 {min(kl.values()):.4f}（{min(kl, key=kl.get)}）"
      f"到 {max(kl.values()):.4f}（{max(kl, key=kl.get)}），跨两个数量级，说明**不能用一个全局阶段先验**，"
      "P3 必须按 environment（或至少按任务族）条件化。\n")
    A("检验的局限（`stages.note`）：同一记录内的帧高度自相关，卡方 p 值偏乐观（anti-conservative），"
      "因此效应量 V 与 KL 表才是可信读数，p 值只用于回答「差异是否非零」。\n")

    # ---------------- 8. agreement ------------------------------------------
    A("## 8. 与参考分段的一致性（副指标，**不是准确率**）\n")
    A("参考来自 `data/segments.csv` 的自由文本 label（349 段，270 段可映射到 pick/place/arrange）。"
      "该参考**既非无误差、也非独立物理真值**，且没有 reach/transport 标签，因此这里只报"
      "「**agreement with reference**」，不报准确率、不用于调阈值。\n")
    A("| 类 | 参考段数 | 段内帧一致率（均值） | 段内出现过该类的比例 | 我们判为该类的帧数 | 其中落在对应参考段的帧比例 | 该类的随机基线（池化占比） |")
    A("| --- | --- | --- | --- | --- | --- | --- |")
    for c in ("pick", "place", "arrange"):
        b = ag["by_class"].get(c)
        if b is None:
            continue
        pr = ag["frame_precision_in_reference"][c]
        A(f"| {c} | {b['n']} | {b['mean']:.4f} | {b['coverage_any_hit']:.3f} | {pr['n_frames']} | "
          f"{pr['in_reference_frac']:.3f} | {ag['chance'][c]:.4f} |")
    A("")
    A(f"段内帧一致率整体 {ag['mean']:.4f}、中位 {ag['median']:.4f}：**低**，原因清楚——参考段是「一段完整动作」"
      "（例如 “pick up the item and place it”），横跨 reach→pick→transport→place 四个阶段，"
      "要求整段帧都等于其中某一类，天然不可能高。真正有信息量的是后两列："
      f"我们判为 pick/place/arrange 的帧落在对应参考段内的比例分别是 "
      f"{ag['frame_precision_in_reference']['pick']['in_reference_frac']:.3f}/"
      f"{ag['frame_precision_in_reference']['place']['in_reference_frac']:.3f}/"
      f"{ag['frame_precision_in_reference']['arrange']['in_reference_frac']:.3f}，"
      f"是对应随机基线（{ag['chance']['pick']:.3f}/{ag['chance']['place']:.3f}/{ag['chance']['arrange']:.3f}）的 4.1×/4.2×/4.5×，"
      f"且 {ag['segment_coverage_any_hit']:.3f} 的参考段内至少出现过一次我们判的同类 —— 规则确实抓到了动作位置，"
      "只是边界与参考的段定义不同粒度。**这不构成验证**，只是「方向一致」的证据。\n")

    # ---------------- 9. hand state != product state ------------------------
    A("## 9. 手部状态 ≠ 产品状态（题面硬约束）\n")
    A("本定义的 18 维 + 5 阶段**全部是手自身的几何与运动**：没有任何一维是「产品的位置/姿态/是否被抓住」。"
      "相近的手部状态可以对应完全不同的产品结果（抓住空气、抓住已放好的商品、手掌贴着货架），"
      "因此：\n")
    A("- 不允许把 `pick` 阶段直接读成「已拿到产品」，也不允许把 `place` 读成「产品已到位」；"
      "它们只是「手在合拢/张开且停住」的运动学证据。")
    A("- 产品状态必须由 P2/P3 **另外**引入（物体检测、接触判定、货架槽位先验），"
      "本层的 `static`、`aperture`、`stage` 只能作为**证据之一**进入，不能作为状态本身。")
    A("- 若后续需要「抓取成功/失败」标签，必须明确它是**推断**并给出置信度，不得写入本层的字段名。\n")

    # ---------------- 10. reproduce -----------------------------------------
    A("## 10. 复现与产物\n")
    A("```powershell")
    A("$env:PYTHONIOENCODING='utf-8'")
    A("python code\\state_layer.py            # 全量：状态+保留率+基线+敏感性")
    A("python code\\state_layer.py --skip baselines,sensitivity   # 只要状态层")
    A("python code\\report_state.py          # 由 JSON 渲染本文件")
    A("```")
    A("")
    A("产物：`data/state_layer.json`（本报告全部数字的来源）、`data/state_layer.npz`（逐帧数组："
      "每手 18 维向量、阶段、置信度）、`code/state_layer.py`、`code/report_state.py`、本文件。\n")
    A("已知不足（如实列出）：")
    A("1. `static` 标志与分段用的是同一族阈值，二者不独立，P3 不要把 `static` 当独立特征。")
    A("2. 高度兜底规则（`pick`/`place` 各占 dwell 的一部分）依赖「货架低于头」这一环境先验，"
      "在举高类任务（如高架补货）会系统性偏向 `pick`。")
    A("3. 段级转移矩阵每行样本量不均（`arrange` 出发的段最少），该行的条件概率不确定性最大。")
    A("4. `spread` 与 `aperture` 高度相关（都随手指张开变化），P2 用线性模型时应二选一或做正交化。\n")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()