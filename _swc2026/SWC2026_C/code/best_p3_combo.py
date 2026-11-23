
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P3 组合参数（只动策略参数，不动协议常数 kap）。

best_p3_sens.py 的单因子结果显示：gate=0.70 与 late_tol=20 各自都能提升 S3，
q_hi=0.55 对 S3 略升、对 S2 略降。本脚本把这三者组合起来，仍按
「前 15 个种子看均值、后 15 个种子留出」的协议报，并与默认 risk_fusion 同种子配对。

kap 不进组合：它是协议常数（s = t + D + kap 是模拟器允许的最早启动时刻），
调它不是策略改进而是改环境，只在 best_p3_sens.json 的敏感性表里报。

输出 data/best_p3_combo.json。
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from best_p3_sens import CASES, SEEDS, ci95, eval_policy, simulate, summarize  # noqa: E402

COMBOS = [
    ("risk:gate=.70,late_tol=20", "risk_fusion", dict(GATE=.70, LATE_TOL_RISK=20.)),
    ("risk:gate=.70,q_hi=.55", "risk_fusion", dict(GATE=.70, Q_HI=.55)),
    ("risk:gate=.70,late_tol=20,q_hi=.55", "risk_fusion",
     dict(GATE=.70, LATE_TOL_RISK=20., Q_HI=.55)),
    ("slack:latetol=20,qbuf=.40", "slack_fusion", dict(LATE_TOL_SLACK=20., QBUF=.40)),
]


def main():
    base = eval_policy("risk_fusion", {})
    bs = summarize(base)
    print(f"default risk_fusion  S2 {bs['S2']['mean']:.4f}±{bs['S2']['ci95']:.4f} | "
          f"S3 {bs['S3']['mean']:.4f}±{bs['S3']['ci95']:.4f}")
    rows, paired = [], {}
    tune, hold = np.arange(15), np.arange(15, 30)
    for tag, pol, par in COMBOS:
        r = eval_policy(pol, par)
        s = summarize(r)
        row = dict(tag=tag, policy=pol, params=par, summary=s,
                   tune15_mean={c: float(r[c]["on_time"][tune].mean()) for c in CASES},
                   holdout15_mean={c: float(r[c]["on_time"][hold].mean()) for c in CASES})
        rows.append(row)
        p = {}
        for c in CASES:
            d = r[c]["on_time"] - base[c]["on_time"]
            p[c] = dict(delta_all30=float(d.mean()), ci95_all30=float(ci95(d)),
                        delta_holdout15=float(d[hold].mean()),
                        ci95_holdout15=float(ci95(d[hold])),
                        wins=int((d > 1e-12).sum()), losses=int((d < -1e-12).sum()))
        paired[tag] = p
        print(f"  {tag:36s} S2 {s['S2']['mean']:.4f}±{s['S2']['ci95']:.4f} | "
              f"S3 {s['S3']['mean']:.4f}±{s['S3']['ci95']:.4f} | "
              f"ΔS3 {p['S3']['delta_all30']:+.4f}±{p['S3']['ci95_all30']:.4f}")
    out = dict(_meta=dict(
        purpose="P3 组合参数（gate / late_tol / q_hi），只动策略参数不动协议常数 kap",
        protocol="30 官方种子；前 15 种子看均值、后 15 种子留出；配对差 = 组合 - 默认 risk_fusion，同种子",
        source_grid="data/best_p3_sens.json（单因子），本文件只报组合",
        baseline_summary=bs, oracle_reference="S2 0.8569 / S3 0.7896（data/p3_stochastic_schedule.json）"),
        combos=rows, paired_vs_default=paired)
    p = os.path.join(HERE, "..", "data", "best_p3_combo.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("saved ->", p)


if __name__ == "__main__":
    main()