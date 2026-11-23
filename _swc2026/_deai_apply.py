# AI 辅助：DeepSeek Harness 助手生成。按 `18-去AI味检测报告-C题out.md` 的拟改清单执行最小改写。
# -*- coding: utf-8 -*-
"""只做报告里列为「拟改」的那几处：翻案腔、提示语冒号、前置话题壳、顿号并列、过长前置定语。
不改事实、不改数字、不改结构；每处替换断言原文恰好出现一次，任何一条 MISS 就整体不写盘。
"""
from __future__ import annotations

import pathlib
import sys

OUT = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\out")

EDITS = {
    "01-model.md": [
        # 顿号并列
        ("本文只立模型、给公式、报已算出的数",
         "本文只立模型，给出公式，报告已算出的数"),
        # 翻案腔
        ("它不是把坐标「变小」，而是把**绝对位置**换成**相对头部的任务位置**",
         "它把**绝对位置**换成**相对头部的任务位置**"),
        # 提示语冒号
        ("结论：**$R$ 只能当权重，不能当过滤器**；",
         "**$R$ 只能当权重，不能当过滤器**；"),
        # 顿号并列
        ("但不同环境的遮挡模式、相机高度、手部尺度不同",
         "但不同环境的遮挡模式与相机高度不同，手部尺度也不同"),
        # 提示语冒号
        ("P1 的答案是：用头部坐标系",
         "P1 用头部坐标系"),
        # 顿号并列
        ("隐空间维数、重构损失、聚类层的三套超参没有验证集可调",
         "隐空间维数、重构损失与聚类层各有一套超参，都没有验证集可调"),
        # 顿号并列
        ("统一切窗口、训练、评估", "统一切窗口、训练与评估"),
        # 提示语冒号
        ("**结论：0.2 s 内 CV 可用", "**0.2 s 内 CV 可用"),
        # 翻案腔
        ("所以 P2 的结论不是「预测能替代观测」，而是「预测只能撑 0.3 s 左右，之后必须再观测」。",
         "所以 P2 的结论是预测只能撑 0.3 s 左右，之后必须再观测。"),
        # 提示语冒号
        ("P2 的答案是：在 0.2 s 的缺口上", "P2 在 0.2 s 的缺口上"),
        # 提示语冒号 + 顿号并列
        ("P3 的答案是：在单设备、预算、review 次数约束下，用「权重 / 预测时长 × 松弛衰减」排序、按 60% 分位预留、敢丢低权重 job 的 SLACK 策略，",
         "P3 在单设备、预算与 review 次数约束下，用 SLACK 策略：按「权重 / 预测时长 × 松弛衰减」排序，预留取 60% 分位，低权重 job 敢丢，"),
        # 顿号并列
        ("$p$ 未知、$b$ 连续、路线有 setup、review 有延迟",
         "$p$ 未知，$b$ 是连续量，路线带 setup、review 有延迟"),
        # 翻案腔 + 过长前置定语
        ("不是「归一化一定更好」，而是证明提升来自「头部特征 × 链式 Ward」的交互：",
         "提升来自「头部特征 × 链式 Ward」的交互："),
        # 翻案腔
        ("它的价值不是「高 AUC」，而是「在没有标签的新环境里仍高于随机」，",
         "它的价值在于没有标签的新环境里仍高于随机，"),
        # 翻案腔
        ("端到端不是「把三个模型串起来」，而是「后一级的决策参数由前一级的误差分布决定」。",
         "端到端因此指后一级的决策参数由前一级的误差分布决定。"),
        # 顿号并列（表内，只调标点）
        ("原始 21×3、AE、DTW", "原始 21×3、AE 与 DTW"),
    ],
    "15-benchmark.md": [
        # 翻案腔（保留三档与成本信息）
        ('观测不是有/无，而是"三档前缀+延迟+单位成本"；',
         '观测按"三档前缀+延迟+单位成本"分级；'),
    ],
    "17-state-definition.md": [
        # 顿号并列
        ("三个候选、五个判据、数据怎么选", "三个候选与五个判据，以及数据怎么选"),
        # 前置话题壳
        ("而掌心不动；对「抓取—搬运」而言掌心才是与物体接触的坐标。",
         "而掌心不动；掌心才是与物体接触的坐标。"),
        # 提示语冒号
        ("。结论：**环境间的阶段分布差异显著**", "。**环境间的阶段分布差异显著**"),
        # 顿号并列
        ("（抓住空气、抓住已放好的商品、手掌贴着货架）",
         "（抓住空气，或抓住已放好的商品，或手掌贴着货架）"),
    ],
}


def main() -> int:
    plan = []
    miss = []
    for name, pairs in EDITS.items():
        p = OUT / name
        src = p.read_text(encoding="utf-8")
        for old, new in pairs:
            n = src.count(old)
            if n != 1:
                miss.append((name, old[:36], n))
            else:
                src = src.replace(old, new, 1)
                plan.append((name, old[:36]))
        p_new = src
        plan.append(("__write__", name, p_new))

    if miss:
        for m in miss:
            print("MISS %s  count=%d  %r" % m)
        print("refusing to write anything")
        return 1

    writes = [x for x in plan if x[0] == "__write__"]
    for _, name, text in writes:
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")
    print("applied %d edits across %d files" % (len(plan) - len(writes), len(writes)))
    for w in writes:
        print("  wrote", w[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())