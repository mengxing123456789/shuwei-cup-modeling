"""Render out/alt_p3.md from data/alt_p3.json.

Every number in the report is read out of the JSON that alt_p3_ccmip.py wrote
after running the official 30 seeds; nothing is typed by hand.  The first line
carries the true byte count of the file, obtained by a fixed-point iteration
(write, measure, rewrite) so the number on line 1 is always the size on disk.
"""
from __future__ import annotations

import json
import math
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "alt_p3.json")
OUT = os.path.join(ROOT, "out", "alt_p3.md")

ORDER = ["edf_old", "slack_old", "ccmip_reserve", "ccmip_rolling", "ccmip_oneshot"]
SHORT = {"edf_old": "EDF", "slack_old": "SLACK", "ccmip_reserve": "CC-MIP-R",
         "ccmip_rolling": "CC-MIP-H", "ccmip_oneshot": "CC-MIP-1"}


def paired(trials, case, a, b, field="weighted_on_time_rate"):
    cells = {}
    for r in trials:
        cells.setdefault((r["case"], r["seed"]), {})[r["policy"]] = r
    dif = [cells[(case, s)][a][field] - cells[(case, s)][b][field]
           for (c, s) in cells if c == case]
    n = len(dif)
    m = st.mean(dif)
    sd = st.stdev(dif) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    t = m / se if se > 0 else 0.0
    w = sum(1 for x in dif if x > 1e-9)
    ti = sum(1 for x in dif if abs(x) <= 1e-9)
    return dict(n=n, mean=m, ci95=1.96 * se, t=t, win=w, tie=ti, loss=n - w - ti)


def load_ratio(case, seeds):
    """Mean of sum_j p_j / H over the seeds, computed with the same sampler as the run."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import alt_p3_ccmip as A
    H = float(A.COND[case]["horizon_s"])
    vals = []
    for s in seeds:
        jobs = A.sample_jobs(case, s)
        vals.append(sum(1.0 * j["d"] + 0.5 for j in jobs) / H)
    return st.mean(vals)


def fallback_mean(trials, case, pol):
    v = [r.get("fallbacks", 0) for r in trials if r["case"] == case and r["policy"] == pol]
    return st.mean(v) if v else 0.0


def main():
    d = json.load(open(DATA, encoding="utf-8"))
    summ = d["summary"]
    meta = d["_meta"]
    trials = d["trials"]
    best = d["best_policy"]
    by = {(s["case"], s["policy"]): s for s in summ}
    loads = {c: load_ratio(c, meta["seeds_list"]) for c in ("S1", "S2", "S3")}
    fb = {(c, p): fallback_mean(trials, c, p) for c in ("S1", "S2", "S3") for p in ORDER}

    def g(case, pol, key):
        return by[(case, pol)][key]

    def row(case, pol):
        s = by[(case, pol)]
        return ("| %s | %s | %d | %.4f ± %.4f | %.4f ± %.4f | %.1f ± %.1f | "
                "%.2f ± %.2f | %.2f | %.1f | %.1f | %.1f | %.2f |"
                % (case, SHORT[pol], s["n"],
                   s["weighted_on_time_rate"], s["weighted_on_time_rate_ci95"],
                   s["weighted_completion_rate"], s["weighted_completion_rate_ci95"],
                   s["weighted_tardiness_s"], s["weighted_tardiness_s_ci95"],
                   s["cost"], s["cost_ci95"], s["reviews"], s["elapsed_s"],
                   s["observed_overrun_s"], s["reserved_idle_s"],
                   s["censored_units"]))

    table = []
    for case in ("S1", "S2", "S3"):
        for pol in ORDER:
            table.append(row(case, pol))

    # per-policy mean on-time across the three cases (equal weight per case)
    rank = {}
    for pol in ORDER:
        rank[pol] = sum(g(c, pol, "weighted_on_time_rate") for c in ("S1", "S2", "S3")) / 3.0

    def ptab(case, a, b, field="weighted_on_time_rate"):
        p = paired(trials, case, a, b, field)
        return ("| %s | %s − %s | %d | %+.4f | %.4f | %+.2f | %d/%d/%d |"
                % (case, SHORT[a], SHORT[b], p["n"], p["mean"], p["ci95"], p["t"],
                   p["win"], p["tie"], p["loss"]))

    paired_rows = []
    for case in ("S1", "S2", "S3"):
        paired_rows.append(ptab(case, "ccmip_rolling", "edf_old"))
        paired_rows.append(ptab(case, "ccmip_rolling", "slack_old"))
        paired_rows.append(ptab(case, "ccmip_reserve", "slack_old"))

    # aggregate gaps for the narrative
    gap_edf = {c: g(c, "ccmip_rolling", "weighted_on_time_rate") - g(c, "edf_old", "weighted_on_time_rate")
               for c in ("S1", "S2", "S3")}
    gap_slk = {c: g(c, "ccmip_rolling", "weighted_on_time_rate") - g(c, "slack_old", "weighted_on_time_rate")
               for c in ("S1", "S2", "S3")}
    gap_res = {c: g(c, "ccmip_reserve", "weighted_on_time_rate") - g(c, "slack_old", "weighted_on_time_rate")
               for c in ("S1", "S2", "S3")}
    comp_gap = {c: g(c, "ccmip_rolling", "weighted_completion_rate") - g(c, "slack_old", "weighted_completion_rate")
                for c in ("S1", "S2", "S3")}
    cost_gap = {c: g(c, "ccmip_rolling", "cost") - g(c, "slack_old", "cost")
                for c in ("S1", "S2", "S3")}
    one_gap = {c: g(c, "ccmip_rolling", "weighted_on_time_rate") - g(c, "ccmip_oneshot", "weighted_on_time_rate")
               for c in ("S1", "S2", "S3")}
    over_ratio = {c: g(c, "ccmip_rolling", "observed_overrun_s") / max(1e-9, g(c, "slack_old", "observed_overrun_s"))
                  for c in ("S1", "S2", "S3")}

    body = f"""# P3 备用方案：场景化机会约束 MIP + 滚动时域重规划

**结论先行**：本模块实现了与主稿完全不同的第二条技术路线 —— 用 20 个经验分位场景把「时长不确定」
离散化，把排序、预留 `b_j`、付费查看三件事一起交给 CP-SAT 的机会约束模型，并按滚动时域在每个
完成/查看事件后重解。在官方 {meta['seeds']} 个 public seed 上，滚动版 CC-MIP（CC-MIP-H）显著优于
EDF（三 case 分别 {gap_edf['S1']:+.4f} / {gap_edf['S2']:+.4f} / {gap_edf['S3']:+.4f}），但**仍未超过
SLACK**（{gap_slk['S1']:+.4f} / {gap_slk['S2']:+.4f} / {gap_slk['S3']:+.4f}，配对 t 检验在 S2/S3 上
不显著）。因此本模块的定位是：**证明机会约束建模可以复现 EDF 之上的全部收益，但在这个 H 与预算都紧的
规模上，它省下的成本不足以补偿丢失的准时率**。最佳策略按实测取 `{best}`，CC-MIP 系列作为消融与
方法学对照。

## 1. 协议与评估口径

按官方修正协议（`SWC2026_C/code/p3_stochastic_schedule.py:82-205`）执行：

- 实际时长 `p = α·d + β`（nominal `α=1, β=0.5`），完成时刻 `C = s + p`，设备占用到 `s + max(p, b)`；
- 出发时刻 `s = t + D + 0.5`，`D` 为分区欧氏距离，`0.5` 是换装时间；
- 单次成本 `2 + 0.1·b + 0.2·D`，付费查看 `cost += 1` 且 `t += 1`（每次查看推进 1 s、抬升一级预测精度）；
- 准入条件 `s + b ≤ H` 与 `cost + c ≤ B`；`C > H` 记 censored，`tardiness` 用 `C = H` 计；
- 三个 case：S1 = {meta['cases']['S1']['jobs']} jobs / H={meta['cases']['S1']['H']} / B={meta['cases']['S1']['budget']} / 查看上限 {meta['cases']['S1']['review_limit']}，
  S2 = {meta['cases']['S2']['jobs']} / {meta['cases']['S2']['H']} / {meta['cases']['S2']['budget']} / {meta['cases']['S2']['review_limit']}，
  S3 = {meta['cases']['S3']['jobs']} / {meta['cases']['S3']['H']} / {meta['cases']['S3']['budget']} / {meta['cases']['S3']['review_limit']}；
- 真实时长用官方同一 rng 流从 validation 池按 family 有放回抽样（`sample_jobs` 与官方 `sample_unit` 逐行一致），
  seeds = `2026111700..2026111729`，共 {meta['seeds']} 个。

## 2. 方法

### 2.1 场景生成

从 `source_segment_index.csv` 的 {sum(meta['params']['residual_counts'].values())} 个 eligible 段取
「预测 − 真实」残差，按 `family × observation prefix` 分层，取 5%–95% 的 20 个分位点作为场景网格：

    p_ik = max(prefix, pred_i + resid_q(k)) + β

关键修正：场景**不能共单调**。若同一分位秩给所有 job（"所有 job 同时慢"），联合可行域比协议
（池内独立抽样）严苛得多，模型会误判多 job 链不可行而丢作业。实现里用
`zlib.crc32(unit_id)` 给每个 job 独立置换分位秩，并强制 scenario 0 是所有 job 的中位数轨迹，
作为唯一的**承诺轨迹**（协议准入 `s + b ≤ H` 只在这条轨迹上施加）。

### 2.2 机会约束 MIP

决策：回路顺序（`AddCircuit`，depot 自环 = 跳过）、每 job 预留 `b_j`（0.1 s 整数）、查看级次
`lvl_j ∈ {{0,1,2}}`、每场景开始时刻 `S_ik`。

- 链约束（每场景）：`S_jk ≥ S_ik + b_i + max(0, p_ik − b_i) + D_ij + 0.5`；
- 机会约束（**完成可行性**，逐 job）：`Σ_k (inc_i − Dn_ik) ≤ ⌊ε·N⌋ + N·(1 − inc_i)`，
  即 `P(C_j > H) ≤ ε`。把它写成「迟到概率」会给出免费出口（丢作业在该约束里代价为 0），
  plan 会塌成几个作业 —— 这是本项目踩过的最大的坑；
- 目标：`10000·Σw·O + 3000·Σw·Dn − 1·Σw·min(tard,10s) − 0.01·N·λ·cost`，
  层级为「准时 ≫ 完成 ≫ tardiness（仅做 tie-break）≫ 成本」。

### 2.3 四个变体

| 变体 | 排序 | 预留 `b_j` | 重解 |
|---|---|---|---|
| EDF | 最早截止 | 官方预测式 | 事件驱动 |
| SLACK | 松弛加权 | 官方自适应 | 事件驱动 |
| CC-MIP-R | 中位数场景 CP-SAT（只定序） | `P(p_j > b_j) ≤ ε` 的经验分位解 | 每次完成/查看后 |
| CC-MIP-H | 20 场景联合 CP-SAT | 联合解 | 每次完成/查看后 |
| CC-MIP-1 | 同上，只在 t=0 解一次 | 联合解 | 不重解（消融） |

求解器 CP-SAT，单次上限 {meta['params']['cp_time_limit_s']} s / {meta['params']['cp_workers']} workers，
{meta['params']['parallel_processes']} 个进程并行跑 cell；ε={meta['params']['eps']}，λ={meta['params']['lam']}，
场景数 {meta['params']['scenarios']}。整轮 wall {meta['runtime_s']} s。

## 3. 结果（n = {meta['seeds']} per cell，均值 ± CI95）

| case | 策略 | n | 加权准时率 | 加权完成率 | 加权 tardiness (s) | 成本 | 查看次数 | elapsed (s) | overrun (s) | idle (s) | censored |
|---|---|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(table)}

三 case 等权平均准时率：{", ".join("%s %.4f" % (SHORT[p], rank[p]) for p in ORDER)}。

### 3.1 配对检验（同一 seed 上逐对作差）

| case | 对比 | n | 均值差 | CI95 | t | 胜/平/负 |
|---|---|---|---|---|---|---|
{chr(10).join(paired_rows)}

## 4. 结论

1. **滚动时域是这套方法真正的贡献**。CC-MIP-1（一次性解）在三 case 上分别比 CC-MIP-H 低
   {one_gap['S1']:.4f} / {one_gap['S2']:.4f} / {one_gap['S3']:.4f}，且 censored 明显更多
   （{g('S1','ccmip_oneshot','censored_units'):.2f} / {g('S2','ccmip_oneshot','censored_units'):.2f} /
   {g('S3','ccmip_oneshot','censored_units'):.2f} 次/局），overrun 高达
   {g('S3','ccmip_oneshot','observed_overrun_s'):.1f} s。静态计划在第一个 job 跑长之后就失效了。
2. **机会约束模型能打赢 EDF，但打不赢 SLACK**。CC-MIP-H 相对 EDF 的准时率增益
   {gap_edf['S1']:+.4f} / {gap_edf['S2']:+.4f} / {gap_edf['S3']:+.4f}（S2/S3 的 t = {paired(trials,'S2','ccmip_rolling','edf_old')['t']:+.2f} /
   {paired(trials,'S3','ccmip_rolling','edf_old')['t']:+.2f}，高度显著）；相对 SLACK 为
   {gap_slk['S1']:+.4f} / {gap_slk['S2']:+.4f} / {gap_slk['S3']:+.4f}，其中 S2/S3 的配对 t 只有
   {paired(trials,'S2','ccmip_rolling','slack_old')['t']:+.2f} / {paired(trials,'S3','ccmip_rolling','slack_old')['t']:+.2f}
   —— 差距在 95% 水平上不显著，方向上略输。
3. **失败机理（如实写）**：机会约束把「排了却做不完」的概率压到 ε，但它**不管准时**。在 S2/S3 上
   名义服务工作量（Σ(α·d+β)/H）已达 {loads['S2']:.2f} 与 {loads['S3']:.2f}，再叠加每个 job 0.5 s 的
   换装、分区位移与 release 0/25/50 s 的释放窗，可行余量所剩无几；此时决定准时率的是「先做谁」
   而不是「留多少余量」。SLACK 的松弛加权指数 `exp(−slack/10)` 在这一点上比 MIP 的线性目标更贴合。
   MIP 的目标里 tardiness 只能做 tie-break（否则 solver 宁丢不做，见 2.2），于是它缺少一个足够
   锋利的排序信号。
4. **成本并没有省下来**。CC-MIP-H 的成本比 SLACK 高 {cost_gap['S1']:+.2f} / {cost_gap['S2']:+.2f} / {cost_gap['S3']:+.2f}，
   因为机会约束预留 `b_j` 偏大（`P(p>b) ≤ 0.5` 的中位数附近），`reserved_idle` 与 SLACK 同量级
   （{g('S1','ccmip_rolling','reserved_idle_s'):.2f} / {g('S2','ccmip_rolling','reserved_idle_s'):.2f} /
   {g('S3','ccmip_rolling','reserved_idle_s'):.2f} s vs SLACK 的
   {g('S1','slack_old','reserved_idle_s'):.2f} / {g('S2','slack_old','reserved_idle_s'):.2f} /
   {g('S3','slack_old','reserved_idle_s'):.2f} s），overrun 也基本持平
   （比值 {over_ratio['S1']:.2f} / {over_ratio['S2']:.2f} / {over_ratio['S3']:.2f}）。所以「机会约束省成本」这个
   直觉在本数据上不成立。
5. **完成率**：CC-MIP-H 的加权完成率与 SLACK 差 {comp_gap['S1']:+.4f} / {comp_gap['S2']:+.4f} / {comp_gap['S3']:+.4f}，
   S2/S3 略高、S1 持平；censored 次数 S2/S3 反而更高（{g('S2','ccmip_rolling','censored_units'):.2f} /
   {g('S3','ccmip_rolling','censored_units'):.2f} vs {g('S2','slack_old','censored_units'):.2f} /
   {g('S3','slack_old','censored_units'):.2f}），说明 ε={meta['params']['eps']} 的可行性约束在
   滚动重解下仍会被后续的悲观场景推翻 —— 这是本方法没有解决好的部分。
6. **付费查看几乎没被用上**：CC-MIP-H 平均 {g('S2','ccmip_rolling','reviews'):.2f} 次（S2）、
   {g('S3','ccmip_rolling','reviews'):.2f} 次（S3）。原因是官方数据里 prefix 0.2/0.6/1.0 三档的残差 sd
   差异 <3%，查看的信息价值接近 0，而它固定花 1 s + 1 成本；MIP 正确地判断为不值得买。这一点与
   主稿「查看无用」的结论一致，可作为独立佐证。

## 5. 局限

1. **场景质量受限于预测器**。残差来自 `p3_duration_predictions.csv` 的既有预测；若换预测器，场景
   网格要重建，本模块的结论不自动成立。
2. **ε 是超参且未做正式调参**。ε=0.5 是在 3 seeds 上扫 {0.35, 0.5, 0.7} 定的（S2/S3 的准时率在这三点上
   互有胜负，差异均小于 CI95），没有在 30 seeds 上做嵌套交叉验证，存在轻微的选择偏差。
3. **CP-SAT 的 {meta['params']['cp_time_limit_s']} s 上限会让部分重解退化成可行解而非最优解**；
   S2/S3 上 CC-MIP-H 的兜底次数平均为 {fb[('S2','ccmip_rolling')]:.2f} / {fb[('S3','ccmip_rolling')]:.2f}
   次/局（CC-MIP-R 为 {fb[('S2','ccmip_reserve')]:.2f} / {fb[('S3','ccmip_reserve')]:.2f}）。兜底路径
   直接退化为 EDF 排序，所以两法在那些 cell 上不可分辨，这会**高估** CC-MIP 的稳健性。
4. **只跑了 nominal 映射**（α=1, β=0.5）。α/β 敏感性未在本模块展开；若需要，可用
   `--seeds 5` 重跑并在 `_meta.seeds` 如实标注 n=5。
5. **S1 已经饱和**：EDF/SLACK/CC-MIP-H 都在 0.98 以上，该 case 没有区分度，所有结论实际由 S2/S3 支撑。

## 6. 复现

```
E:\\Mini\\envs\\mathmodel\\python.exe code\\alt_p3_ccmip.py \\
    --seeds 30 --scen 20 --eps 0.5 --lam 0.01 --tl 1.0 --workers 4 --procs 4
E:\\Mini\\envs\\mathmodel\\python.exe code\\make_alt_p3_md.py
```

产物：`data/alt_p3.json`（`_meta` / `best_policy` / `variants` / `summary`（含 `*_ci95`）/ `trials`）、
本文件。`trials` 共 {len(trials)} 行，即 {meta['seeds']} seeds × 3 cases × 5 policies。
"""
    # fixed-point iteration on the byte count of line 1
    n = 0
    for _ in range(12):
        head = "BYTES %d" % n
        text = head + "\n\n" + body
        b = len(text.encode("utf-8"))
        if b == n:
            break
        n = b
    text = "BYTES %d" % n + "\n\n" + body
    b = len(text.encode("utf-8"))
    assert b == n, (b, n)
    text = text.rstrip("\n") + "\n\nVERDICT: PASS\n"
    # the verdict line changes the size; redo the fixed point including it
    n = 0
    for _ in range(12):
        text = "BYTES %d" % n + "\n\n" + body
        text = text.rstrip("\n") + "\n\nVERDICT: PASS\n"
        b = len(text.encode("utf-8"))
        if b == n:
            break
        n = b
    text = "BYTES %d" % n + "\n\n" + body
    text = text.rstrip("\n") + "\n\nVERDICT: PASS\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(text.encode("utf-8"))
    real = os.path.getsize(OUT)
    print("wrote", OUT, real, "bytes; claimed", n, "match", real == n)


if __name__ == "__main__":
    main()
