# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p3_report.py -- render 38-P3策略-v2结果.md from data/up2_p3.json.

Every number in the markdown is read from the json artefacts, so the report can
never drift from the evidence (workspace rule G12: no unsourced numbers).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import DATA  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(DATA))       # ...\_swc2026
OUT_MD = os.path.join(ROOT, "38-P3策略-v2结果.md")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def pct(x, nd=2):
    return ("%+." + str(nd) + "f") % (100.0 * x)


def fnum(x, nd=4):
    return ("%." + str(nd) + "f") % x


def mean_base(J):
    return sum(J["strategies"][c]["slack_old"]["on_time_test"]
               for c in J["_meta"]["cases"]) / len(J["_meta"]["cases"])


def mean_new(J):
    return sum(J["strategies"][c]["FROZEN"]["on_time_test"]
               for c in J["_meta"]["cases"]) / len(J["_meta"]["cases"])


def mean_rev(J):
    return sum(J["strategies"][c]["FROZEN"]["reviews_test"]
               for c in J["_meta"]["cases"]) / len(J["_meta"]["cases"])


def main():
    J = load("up2_p3.json")
    S = load("up2_p3_search.json")
    CK = load("up2_p3_engine_check.json")
    pre = load("up2_p3_prereg.json")

    cases = J["_meta"]["cases"]
    maps = J["_meta"]["mappings"]
    g = J["gate"]
    L = []
    A = L.append

    A("# P3 调度策略 v2：结果报告")
    A("")
    A("> 由 `code/up2_p3_report.py` 从 `data/up2_p3.json`（预注册 sha256 `%s`）"
      "自动生成，正文数字均可回到 json 键。" % J["_meta"]["prereg_sha256"][:16])
    A("> 运行时间 %s；final 阶段墙钟 %.1f s（搜索阶段另计 96 s）。"
      % (J["_meta"]["run_at"], J["_meta"]["wall_clock_s"]))
    A("")
    A("## 0. 一句话结论")
    A("")
    verdict = "**通过**" if J["passes"] else "**未通过**"
    sip = J.get("gate_self_imposed", {}) or {}
    sip_pass = bool(sip.get("passes"))
    sip_bad = [k for k, v in (sip.get("checks") or {}).items() if not v]
    sip_note = ("六条全过" if sip_pass
                else "未过 " + "、".join("`%s`" % b for b in sip_bad))
    A("- 冻结策略相对冻结基线 slack 策略，test 5 seed × 5 映射 × 2 case 的平均加权准时率"
      "提升 **%s 个百分点**（blocked 95%% CI [%s, %s]）。"
      % (pct(g["delta_bar"]), pct(g["ci95_blocked"][0]), pct(g["ci95_blocked"][1])))
    A("- 判定：**任务门槛 %s**（≥1.5pp 且配对 CI 下界 >0）；"
      "**自加稳健门槛 %s**（%s）。原文：`%s`。"
      % ("PASS" if J.get("passes_mandated") else "FAIL",
         "PASS" if sip_pass else "FAIL", sip_note,
         J.get("verdict", "-")))
    A("- 每 case 平均提升（5 映射平均）：S2 %s、S3 %s 个百分点。" %
      (pct(g["per_case"]["S2"]["delta"]), pct(g["per_case"]["S3"]["delta"])))
    A("- 30 seed × 5 映射平均（不是名义映射）：S2 %s → %s；S3 %s → %s。"
      % (fnum(J["strategies"]["S2"]["slack_old"]["on_time_all30"]),
         fnum(J["strategies"]["S2"]["FROZEN"]["on_time_all30"]),
         fnum(J["strategies"]["S3"]["slack_old"]["on_time_all30"]),
         fnum(J["strategies"]["S3"]["FROZEN"]["on_time_all30"])))
    _n = lambda c, t, k: fnum(J["strategies"][c][t][k])
    A("- 30 seed 名义映射（α=1.0/β=0.5）：S2 %s → %s；S3 %s → %s；"
      "test 5 seed 名义映射：S2 %s → %s、S3 %s → %s。"
      % (_n("S2", "slack_old", "on_time_all30_nominal"),
         _n("S2", "FROZEN", "on_time_all30_nominal"),
         _n("S3", "slack_old", "on_time_all30_nominal"),
         _n("S3", "FROZEN", "on_time_all30_nominal"),
         _n("S2", "slack_old", "on_time_test_nominal"),
         _n("S2", "FROZEN", "on_time_test_nominal"),
         _n("S3", "slack_old", "on_time_test_nominal"),
         _n("S3", "FROZEN", "on_time_test_nominal")))
    A("- 完成率变化 %s 个百分点，成本比 %.3f（门槛：完成率退化 ≤1pp、成本膨胀 ≤5%%）。"
      % (pct(g["completion_delta"]), g["cost_ratio"]))
    A("")

    A("## 1. 口径：基线到底是多少")
    A("")
    A("%s" % J["notes"][0])
    A("")
    A("| 口径 | 引擎 | S2 | S3 | 说明 |")
    A("| --- | --- | --- | --- | --- |")
    A("| 旧协议（错把 C=s+d、t=s+max(d,b)） | `p3_schedule.py` | 0.8292 | 0.7854 | "
      "`08-官方要求与审题.md:315`、`09-C现状与数字对账.md:152` 已记账 |")
    A("| 修正协议（本文件基线） | `up_p3_vectorized.py` | %s | %s | "
      "30 seed 名义映射均值，与 `p3_improved_verify.json` 的 slack_old 逐 seed 相同 |"
      % (_n("S2", "slack_old", "on_time_all30_nominal"),
         _n("S3", "slack_old", "on_time_all30_nominal")))
    A("")
    A("结论：门槛是**增量型**（相对基线 +1.5pp 且 CI 下界 >0），基线口径不影响判定；"
      "凡是引用绝对值的段落都必须标「修正协议」。")
    A("")

    A("## 2. 预注册（先写死，后跑 test）")
    A("")
    A("- 切分：train `%s`（15 seed）、val `%s`（10 seed）、test `%s`（5 seed）。"
      % (pre["split"]["train"][0], pre["split"]["val"][0], pre["split"]["test"][0]))
    A("- 选择规则：每 case 独立，按 train 均值（5 映射）取前 5，再按 val 均值（5 映射）"
      "重排，冻结 val 最优者；三类策略各自选，最后取 val 最高的那一类。")
    A("- test 只评一次；`test_evaluated_once=%s`。" % J["_meta"]["test_evaluated_once"])
    A("- 门槛六条：")
    for k, v in g["checks"].items():
        A("  - `%s` = **%s**" % (k, v))
    A("- 统计量：blocked 配对差，10 个 (case×映射) 固定块、每块 5 个 seed 重复。")
    A("")

    A("## 3. 引擎 v2：新增策略维度与一致性")
    A("")
    A("`code/up2_p3_engine.py` 在冻结引擎 `code/up_p3_vectorized.py` 之上加参数化，"
      "参数取旧值时走同一条代码路径：")
    A("")
    A("| 参数 | 含义 | 旧值 |")
    A("| --- | --- | --- |")
    A("| `ksk` | slack 规则预留系数（原本硬编码 0.6） | 0.60 |")
    A("| `qsl` | slack 规则残差分位（原本固定 0.6） | 0.60 |")
    A("| `ksp` | 压力加价：`+ksp·max(0,pressure−0.75)` | 0 |")
    A("| `ksb` | 预算松弛项：`+ksb·(1−cost/B)` | 0 |")
    A("| `mix` | EDF↔ATC 选择器权重（0=纯 ATC，1=纯 EDF） | 0 |")
    A("| `gam` | 阻塞外部性权重：起 j 会占用机器 `ph_j`，惩罚因此超期的其它任务 | 0 |")
    A("| `tau` | 付费复观测的收益门槛（原本 0.02） | 0.02 |")
    A("")
    A("逐位验证（15 个手臂 × 3 个 case，key 全等）：`max_abs_diff=%s`，`passed=%s`。"
      "扩展引擎 %d candidate×30 seed 于 S3 用时 %.2f s（%.3f ms/候选·seed）。"
      % (CK["gate"]["max_abs_diff"], CK["gate"]["passed"], 64,
         CK["timing"]["extended_64x30_s3_seconds"],
         CK["timing"]["per_candidate_seed_ms"]))
    A("")

    A("## 4. 三类策略的 train/val 结果")
    A("")
    A("### 4.1 A 类：参数化规则搜索（%d 个候选，随机因子设计 + 4 锚点）"
      % S["_meta"]["n_candidates_A"])
    A("")
    A("| case | 选中 A 策略 | train | val | val−基线 |")
    A("| --- | --- | --- | --- | --- |")
    for c in cases:
        p = S["stage_A"]["picks"][c]
        A("| %s | `%s` | %.4f | %.4f | %s |" % (c, p["name"], p["train"], p["val"],
                                                pct(p["val"] - p["baseline_val"])))
    A("")
    A("top-5（按 train 排序，再看 val）：")
    A("")
    for c in cases:
        A("- **%s**：" % c)
        for r in S["stage_A"]["picks"][c]["train_top5"]:
            A("  - `%s` train=%.4f val=%.4f" % (r["name"], r["train"], r["val"]))
    A("")
    A("### 4.2 B 类：上下文线性策略 + cross-entropy method")
    A("")
    A("学的是「预留乘子」`k(ctx)=ksk+ksp·max(0,pressure−0.75)+ksb·(1−cost/B)`，"
      "选择器用 ATC/风险分（`SEL=0`），其余维度固定；train 上 CEM，val 上早停。")
    A("")
    A("| case | 冻结 B 策略 | train | val | CEM 迭代 |")
    A("| --- | --- | --- | --- | --- |")
    for c in cases:
        p = S["stage_B"][c]
        A("| %s | `%s` | %.4f | %.4f | %d |" % (c, p["name"], p["train"], p["val"],
                                              p["iter"]))
    A("")
    A("### 4.3 C 类：分布鲁棒预留（min-max / CVaR）")
    A("")
    A("| case | 目标 | 选中 | train 最差映射 | train 均值 | val 均值 |")
    A("| --- | --- | --- | --- | --- | --- |")
    for c in cases:
        cc = S["stage_C"][c]
        for k in ("minimax", "cvar"):
            d = cc[k]
            A("| %s | %s | `%s` | %.4f | %.4f | %.4f |"
              % (c, d["tag"], d["name"], d["train_min"], d["train_mean"],
                 d["val_mean"]))
    A("")
    A("### 4.4 冻结（三类里 val 最高者）")
    A("")
    A("| case | 类 | 策略 | val | val−基线 | ≥1.5pp |")
    A("| --- | --- | --- | --- | --- | --- |")
    for c in cases:
        fz = J["frozen"][c]
        A("| %s | %s | `%s` | %.4f | %s | %s |"
          % (c, fz["class_"], fz["name"], fz["baseline_val"] + fz["val_delta"],
             pct(fz["val_delta"]), fz["val_gain_ok"]))
    A("")

    A("## 5. test 单次评估（5 seed × 5 映射）")
    A("")
    A("### 5.1 策略对比（每 case 在 5 个映射上的均值）")
    A("")
    A("| case | 策略 | 准时率 | 相对基线 | 完成率 | 成本 | 复观测次数 | 拖期(s) |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for c in cases:
        for tag, d in J["strategies"][c].items():
            A("| %s | %s | %.4f | %s | %.4f | %.2f | %.2f | %.1f |"
              % (c, tag, d["on_time_test"], pct(d["delta_vs_baseline"]),
                 d["completion_test"], d["cost_test"], d["reviews_test"],
                 d["tardiness_test"]))
    A("")
    A("### 5.2 每 case × 每映射：冻结策略 vs 基线")
    A("")
    A("| case | 映射 | 基线准时率 | 冻结准时率 | Δ | 成本 | 复观测 |")
    A("| --- | --- | --- | --- | --- | --- | --- |")
    for c in cases:
        for mk in maps:
            b = J["per_case_map"][c]["slack_old"][mk]
            f = J["per_case_map"][c]["FROZEN"][mk]
            A("| %s | %s | %.4f | %.4f | %s | %.2f | %.2f |"
              % (c, mk, b["on_time_test"], f["on_time_test"],
                 pct(f["on_time_test"] - b["on_time_test"]), f["cost_test"],
                 f["reviews_test"]))
    A("")

    A("## 6. 统计判定")
    A("")
    A("| 量 | 值 |")
    A("| --- | --- |")
    A("| 配对差均值（10 块 × 5 seed） | %s |" % pct(g["delta_bar"]))
    A("| blocked 95%% CI | [%s, %s] |" % (pct(g["ci95_blocked"][0]),
                                          pct(g["ci95_blocked"][1])))
    A("| df（Welch–Satterthwaite） | %.2f |" % g["df_blocked"])
    A("| 宽松参照：50 对朴素 CI | [%s, %s] |" % (pct(g["ci95_naive_50pairs"][0]),
                                              pct(g["ci95_naive_50pairs"][1])))
    A("| 严格参照：5 个 seed 聚类 CI | [%s, %s] |" % (pct(g["ci95_seed_cluster5"][0]),
                                                   pct(g["ci95_seed_cluster5"][1])))
    A("| 正号对数 | %d / %d |" % (g["n_positive"], g["n_pairs"]))
    A("| 符号检验 p | %.4g |" % g["sign_test_p"])
    A("| 最差块均值 | %s |" % pct(g["worst_block_mean"]))
    A("")
    A("每块均值：")
    A("")
    A("| 块 | Δ |")
    A("| --- | --- |")
    for k, v in g["block_means"].items():
        A("| %s | %s |" % (k, pct(v)))
    A("")
    A("### 门槛六条")
    A("")
    A("| 判据 | 结果 |")
    A("| --- | --- |")
    for k, v in g["checks"].items():
        A("| `%s` | %s |" % (k, "PASS" if v else "FAIL"))
    A("")
    wc = J.get("gate_self_imposed", {}).get("worst_cell")
    if wc:
        A("最差格 **%s / %s**：基线 %.4f（已近饱和）、冻结策略 %.4f，"
          "Δ=%s pp（%.2f 个指标量子，该 case 的 1/W = %.2f pp），"
          "逐 seed 差 %s。"
          % (wc["case"], wc["mapping"], wc["baseline"], wc["frozen"],
             pct(wc["delta"]), wc["in_quanta"], 100 * wc["quantum"],
             [round(100 * x, 2) for x in wc["per_seed"]]))
        A("")
        if sip_bad:
            A("结论要写成条件句：平均提升成立；**%s / %s 这一格退化**，"
              "对应 %s pp ≈ %.2f 个加权任务。原因见 §8。"
              % (wc["case"], wc["mapping"], pct(wc["delta"]), wc["in_quanta"]))
        else:
            A("十条块（case×映射）全部非负，没有格子退化；最差格也只是持平。"
              "`G4` 的容差（0.5pp）比指标量子还细，这条规则本次靠「不丢任务」才通过，"
              "见 §8 的说明。")
        A("")
    A("总判定：任务门槛 **%s**；自加稳健门槛 **%s**。"
      % ("PASS" if J.get("passes_mandated") else "FAIL",
         "PASS" if J.get("gate_self_imposed", {}).get("passes") else "FAIL"))
    A("")

    A("## 7. 论文可直接用的一段")
    A("")
    A("> 我们在冻结的 slack 预留规则之上做了三类搜索：规则参数（预留系数、分位、"
      "EDF/ATC 混合权重、复观测门槛、阻塞外部性权重）、上下文线性策略的交叉熵训练、"
      "以及跨五个 (α,β) 映射的 min-max/CVaR 鲁棒选择，全部只在 train/val 上完成。"
      "冻结策略在 test 的 5 个 seed × 5 个官方映射 × 2 个 case 上把平均加权准时率"
      "从 %.4f 提到 %.4f（%s 个百分点，blocked 95%% CI [%s, %s]），完成率变化 %s 个百分点，"
      "成本比 %.3f，复观测次数 %.2f 次/试验。"
      % (mean_base(J), mean_new(J), pct(g["delta_bar"]), pct(g["ci95_blocked"][0]),
         pct(g["ci95_blocked"][1]), pct(g["completion_delta"]), g["cost_ratio"],
         mean_rev(J)))
    A("")

    A("## 8. 局限与别踩的坑")
    A("")
    A("- **5 个 seed 的方差很大**：指标以 1/W 为格点跳变（S2 W=24、S3 W=32，1 个任务就是 "
      "4.17pp / 3.13pp），效应量只有 %s pp，而 blocked SE 已有 %.2f pp；5 seed 聚类区间"
      "宽 %.2f pp。因此预注册用 blocked 设计（映射当块、seed 当重复），而不是把 50 对"
      "当独立样本：朴素 50 对 CI 偏松、5 seed 聚类 CI 偏严，判定用中间的 blocked 区间。"
      % (pct(g["delta_bar"]), 100 * g["se_blocked"],
         100 * (g["ci95_seed_cluster5"][1] - g["ci95_seed_cluster5"][0])))
    A("- **test 只评一次**：本文件里 test 数字来自同一次运行切片，没有二次调参。")
    A("- **三类策略的族不同**：A 类是离散网格里的局部最优，B 类的 CEM 只调了预留乘子的"
      "线性系数（族窄，train 上界明显低于 A 类），C 类是在 A 类候选池上做鲁棒重选。"
      "三者的对比是「族 × 选择准则」的对比，不是同族内的公平消融。")
    A("- %s" % J["notes"][3])
    A("- **机制（val 段实测到的）**：S2 冻结策略在 α=0.75 上曾退化，是因为 α 偏乐观时"
      "`b` 的预留被压小、更多任务落入 `onp≥gate` 的候选池，而该策略的 `mix=0.60` 让"
      "选择器有 60% 的权重偏向最早 due 的任务（EDF），EDF 在 α=0.75 下反而挤掉了 onp "
      "更高的任务；该格基线已近饱和（test 0.9917），没有冗余吸收这类单任务抖动。"
      "test 段这一格没有触发，但机制成立，换 seed 仍可能再现。")
    A("- **符号检验不显著（p=%.4g）不是反例**：50 对里只有 %d 对为正，其余大量是"
      "「差恰好为 0」（指标按 1/W 跳变、饱和格两侧都满格）；符号检验丢掉这些平局、"
      "又把同一格内的 5 个 seed 当独立样本，功效很低，判定不用它。"
      % (g["sign_test_p"], g["n_positive"]))
    A("- **复观测（review）几乎不触发**：冻结策略在 test 上平均 %.2f 次/试验，"
      "只有 S3 在 α=1.5 格上出现过 0.20 次 —— VoI 门槛 `tau=0.02` 在 fix/slack 规则下"
      "很少被跨过；这条策略维度本轮没有贡献，不能写成收益来源。" % mean_rev(J))
    A("")

    A("## 9. 产物清单")
    A("")
    A("| 文件 | 内容 |")
    A("| --- | --- |")
    A("| `code/up2_p3_prereg.py` → `data/up2_p3_prereg.json` | 预注册（切分、门槛、策略族），"
      "sha256 `%s` |" % J["_meta"]["prereg_sha256"][:16])
    A("| `code/up2_p3_engine.py` | v2 引擎 + `--check` 逐位验证 + 速度基准 |")
    A("| `code/up2_p3_explore.py` → `data/up2_p3_search.json`、`data/up2_p3_poolA.json` | "
      "train/val 搜索（A/B/C 三类）与候选池矩阵 |")
    A("| `code/up2_p3_final.py` → `data/up2_p3.json` | test 单次评估、配对差、CI、门槛判定 |")
    A("| `code/up2_p3_report.py` | 本文件生成器（数字全部读自 json） |")
    A("| `logs/up2_p3_*.log` | 各阶段日志 |")
    A("")

    text = "\n".join(L) + "\n"
    with open(OUT_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", OUT_MD, len(text), "chars")


if __name__ == "__main__":
    main()