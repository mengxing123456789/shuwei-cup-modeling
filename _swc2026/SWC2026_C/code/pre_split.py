
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 预训练判决实验 —— 固化划分 + 写死结论门槛（在跑任何训练之前）。

产出：
  data/pre_split.json       每环境记录数 / 帧数 / 各档位窗口数；三重不交叉断言
  data/pre_p2_prereg.json   预注册：对照、种子、指标、判定门槛、超参、失败判定
"""
import json
import os
import time

import pandas as pd

from common import DATA
from pre_common import LENS, CTX, build_cache, clean_starts

SPLIT_OUT = os.path.join(DATA, "pre_split.json")
PREREG_OUT = os.path.join(DATA, "pre_p2_prereg.json")


def wcount(cache, records, span):
    n = 0
    for r in records:
        _, idx = clean_starts(cache, int(r), span)
        n += len(idx)
    return int(n)


def main():
    cache = build_cache()
    recs = cache["recs"]
    rows = []
    for env, g in recs.groupby("env"):
        splits = sorted(g.split.unique())
        assert len(splits) == 1, f"环境 {env} 跨 split: {splits}"
        row = dict(env=env, split=splits[0], n_records=int(len(g)),
                   records=[int(x) for x in g.rec],
                   frames=int(g.n.sum()), dur_s=round(float(g.dur.sum()), 2))
        for L in LENS:
            row[f"windows_L{L}"] = wcount(cache, g.rec.to_numpy(), CTX + L)
        row["windows_ssl_32"] = wcount(cache, g.rec.to_numpy(), 32)
        rows.append(row)

    # 分 split 汇总
    totals = {}
    for s in ["train", "validation", "test"]:
        sub = [r for r in rows if r["split"] == s]
        totals[s] = dict(
            n_envs=len(sub), n_records=int(sum(r["n_records"] for r in sub)),
            frames=int(sum(r["frames"] for r in sub)),
            windows={f"L{L}": int(sum(r[f"windows_L{L}"] for r in sub)) for L in LENS},
        )

    # 预训练窗口数（win=32，干净窗）
    totals["train"]["windows_ssl_32"] = int(sum(r["windows_ssl_32"] for r in rows
                                                if r["split"] == "train"))

    env_sets = {s: {r["env"] for r in rows if r["split"] == s}
                for s in ["train", "validation", "test"]}
    rec_sets = {s: {x for r in rows if r["split"] == s for x in r["records"]}
                for s in ["train", "validation", "test"]}
    checks = dict(
        env_disjoint=not (env_sets["train"] & env_sets["validation"]
                          or env_sets["train"] & env_sets["test"]
                          or env_sets["validation"] & env_sets["test"]),
        record_disjoint=not (rec_sets["train"] & rec_sets["validation"]
                             or rec_sets["train"] & rec_sets["test"]
                             or rec_sets["validation"] & rec_sets["test"]),
        counts=(len(env_sets["train"]), len(env_sets["validation"]), len(env_sets["test"])),
        n_records=(len(rec_sets["train"]), len(rec_sets["validation"]), len(rec_sets["test"])),
    )
    assert checks["env_disjoint"] and checks["record_disjoint"]
    assert checks["counts"] == (16, 4, 4), checks["counts"]

    out = dict(
        _meta=dict(
            source="data/panel_records.csv 的 split 列（官方 record_split.csv，按 environment）",
            ctx_frames=CTX, lens_frames=LENS, fps=30.0,
            prefix_seconds=[0.2, 0.6, 1.0],
            note="窗口 = CTX 帧观测 + L 帧目标；只保留主导手 bad 标记为 0 的连续窗；"
                 "预训练只允许 train 环境的帧；val 只用于早停/校准；test 只评估一次",
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        ),
        envs=rows, totals=totals, checks=checks,
    )
    with open(SPLIT_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"saved -> {SPLIT_OUT}")
    print(json.dumps(totals, ensure_ascii=False, indent=1))
    print("checks", checks)

    prereg = dict(
        _meta=dict(written_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                   note="在任何训练开始之前写死；跑完不许改门槛"),
        question="自监督预训练是否给 P2 前缀轨迹预测带来可复现的增益？",
        arms={
            "C0": "同骨架从零训练（关键对照）",
            "C1": "现成 GRU 基线，直接引用 data/p2_gpu.json 的 v2 行（80 维输入）",
            "C2": "预训练编码器冻结 + 线性探针（岭回归，alpha 在 val 上选）",
            "C3": "预训练编码器 + 全量微调（与 C0 完全同配方，只差初始化）",
        },
        ssl_tasks={
            "A": "掩码重构：连续 3-8 帧、覆盖 15-25%，重构 42 个关键点(126) + 头部位姿(7)",
            "B": "时序对比：同记录不同窗为正，跨记录为负；多正例 InfoNCE，tau=0.10",
        },
        seeds=[20261120, 20261121, 20261122],
        horizons_frames=LENS,
        horizons_s=[round(x / 30.0, 3) for x in LENS],
        metrics=["RMSE(cm)", "median(cm)", "q90(cm)", "每帧 RMSE 曲线",
                 "端点 80%/90% 覆盖率（val 校准）", "PIT 10 桶直方图"],
        decision=dict(
            rule="C3 相对 C0，在 1.0 s(30 帧) 与 2.0 s(60 帧) 两档 RMSE 改善均 ≥10%，"
                 "且 3 个种子逐种子同向（改善>0），判为『预训练有增益』；否则判无增益。",
            primary_contrast="C3 vs C0（同骨架、同配方、同种子，仅初始化不同）",
            secondary="C2 用于判断增益是否体现在线性可读特征上；C1 仅作外部参照",
            report="逐任务 A/B 分别判定，任一任务达标即记为有增益并注明任务",
        ),
        training=dict(
            epochs=25, batch=512, train_stride=5, lr_max=1.5e-3, weight_decay=1e-4,
            grad_clip=2.0, scheduler="OneCycle", early_stop_patience=7,
            optimizer="AdamW", target_unit="cm",
            seed_control="C0/C3 使用完全相同的优化器、调度、批序与早停规则",
        ),
        ssl=dict(
            window_lengths=[24, 32, 48, 64], batch=64, steps=700,
            lr_max=1.5e-3, weight_decay=1e-4, tau=0.10, proj_dim=64,
            mask_spans="3-8 帧连续，总覆盖 15-25%",
            eval_every=50, early_stop_on="val 自监督损失",
        ),
        environment=dict(gpu="RTX 4060 Laptop 8GB", torch="2.14.1+cu126",
                         single_run_cap_min=10),
        failure_modes_to_report=["过拟合曲线", "best_epoch", "学习率敏感性",
                                 "数据量（55 条 train 记录 / 4.7 万帧）",
                                 "任务-下游不匹配"],
    )
    with open(PREREG_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(prereg, f, ensure_ascii=False, indent=1)
    print(f"saved -> {PREREG_OUT}")


if __name__ == "__main__":
    main()