# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# AI 辅助：DeepSeek Harness 助手生成的前沿实验（官方动作集上的 (误差, 请求数) 支配分析）。
# -*- coding: utf-8 -*-
"""P2 的决策对象：在官方动作集上枚举四个协议允许的策略，报 (误差, 请求数) 前沿。

官方协议（common_conditions.json -> observation）给出：prefix_seconds [0.2,0.6,1.0]、
delay_s 1.0、cost 1.0、max_per_job 2。一个作业在 3 s 内到期，于是 "何时请求" 变成
一个链式选择：请求一次就把可用的预测提前量削掉 1 s。因此策略不是 "用多长的前缀"，
而是 "在给定剩余提前量下，花钱买前缀是否值得"。

这里**不发明 cost 到厘米的换算**（那是原稿被审的地方）。前沿就是 (RMSE, 请求数)，
支配关系与任何 λ 无关：

  * 免费等待：不做请求，把预测挪到 s+1 再报 → 提前量 2 s，前缀仍 0.2 s
  * 付费 0.6：请求一次 → 提前量 2 s，前缀 0.6 s，成本 1
  * 付费 1.0：请求一次 → 提前量 2 s，前缀 1.0 s，成本 1
  * 两次请求：提前量 1 s，前缀 1.0 s，成本 2
  * 不等待不请求：提前量 3 s，前缀 0.2 s

每条给逐记录 RMS，配对差与 CI（同一批窗口配对，cluster = 记录）。

输出 data/p2_frontier.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

import p2_predict as P
from common import DATA

SEEDS_NOTE = "deterministic ridge; no randomness, so the CI is over records, not seeds"

POLICIES = [
    # name, ctx_frames, lead_frames, requests
    ("no_wait_no_request", 6, 90, 0),
    ("free_wait", 6, 60, 0),
    ("paid_0p6", 18, 60, 1),
    ("paid_1p0", 30, 60, 1),
    ("paid_twice_1p0", 30, 30, 2),
]


def per_record(ctx_frames, lead):
    """Fit the frozen recipe at (ctx, lead) and return {record: [errors...]} on test."""
    P.CTX = ctx_frames
    tr = {lead: P.windows("train", lead)}
    sc, mdl = P.train_ridge(tr, lead)
    out = {}
    for ctx, tgt, _post, key in P.windows("test", lead):
        pr = P.ridge_predict(sc, mdl, ctx, lead)
        e = np.linalg.norm(pr - tgt, axis=1)  # (n_windows, lead)
        out.setdefault(str(key), []).append(e)
    return {k: np.concatenate(v, axis=0) for k, v in out.items()}


def rms_of(byrec):
    allsq = np.concatenate([(v ** 2).ravel() for v in byrec.values()])
    return float(np.sqrt(allsq.mean()) * 100)  # cm


def per_record_rms(byrec):
    return {k: float(np.sqrt((v ** 2).mean()) * 100) for k, v in byrec.items()}


def main():
    t0 = time.time()
    errs = {}
    for name, c, h, _r in POLICIES:
        errs[name] = per_record(c, h)
        print(f"  {name:20s} c={c:2d} h={h:2d}  rms={rms_of(errs[name]):.3f} cm  "
              f"records={len(errs[name])}")

    recs = sorted(set.intersection(*(set(v) for v in errs.values())))
    table = []
    for name, c, h, requests in POLICIES:
        table.append({
            "policy": name, "ctx_frames": c, "ctx_s": round(c / 30, 2),
            "lead_frames": h, "lead_s": round(h / 30, 2),
            "requests": requests, "cost_units": float(requests),
            "rms_cm": round(rms_of(errs[name]), 4),
        })

    def paired(a, b):
        """b - a per record, on record-level RMS (cm)."""
        ra, rb = per_record_rms(errs[a]), per_record_rms(errs[b])
        d = np.array([rb[k] - ra[k] for k in recs], float)
        half = float(1.96 * d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")
        return {"from": a, "to": b, "delta_cm": float(d.mean()), "ci95": half,
                "lower": float(d.mean() - half), "upper": float(d.mean() + half),
                "n_records": len(d), "improved": int((d < 0).sum()),
                "worsened": int((d > 0).sum()), "per_record": d.tolist()}

    comparisons = {}
    for a, b in (("no_wait_no_request", "free_wait"),
                 ("free_wait", "paid_0p6"),
                 ("free_wait", "paid_1p0"),
                 ("paid_1p0", "paid_twice_1p0"),
                 ("no_wait_no_request", "paid_1p0")):
        comparisons[f"{a}__to__{b}"] = paired(a, b)
        c = comparisons[f"{a}__to__{b}"]
        print(f"  {a} -> {b}: {c['delta_cm']:+.4f} cm  +/- {c['ci95']:.4f}  "
              f"improved {c['improved']}/{c['n_records']}")

    # dominance: a policy is dominated when another has both lower error and no more cost
    dom = []
    for s in table:
        killers = [o["policy"] for o in table
                   if o["rms_cm"] < s["rms_cm"] and o["cost_units"] <= s["cost_units"]
                   and o["policy"] != s["policy"]]
        dom.append({"policy": s["policy"], "rms_cm": s["rms_cm"],
                    "cost_units": s["cost_units"], "dominated_by": killers})

    out = {
        "_meta": {
            "script": "p2_frontier.py",
            "protocol": "official observation set: prefix [0.2,0.6,1.0] s, delay 1.0 s, "
                        "cost 1.0 per request, max 2 per job, deadline 3.0 s",
            "predictor": "frozen ridge recipe of p2_predict.py, fitted per (ctx, lead) on train, "
                         "test evaluated once",
            "no_lambda": "no cost-to-centimetre conversion is assumed; dominance over "
                         "(rms_cm, cost_units) is lambda-free",
            "cluster": "record (7 test records)",
            "seed_note": SEEDS_NOTE,
        },
        "table": table,
        "comparisons": comparisons,
        "dominance": dom,
        "seconds": round(time.time() - t0, 1),
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (Path(str(DATA)) / "p2_frontier.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    print("\nfrontier (cost units = requests):")
    for s in sorted(table, key=lambda x: x["rms_cm"]):
        print(f"  {s['policy']:20s} {s['rms_cm']:.3f} cm  cost {s['cost_units']:.0f}"
              f"  lead {s['lead_s']:.2f}s prefix {s['ctx_s']:.2f}s")
    print("\ndominated:")
    for d in dom:
        print(f"  {d['policy']:20s} <- {d['dominated_by'] or 'frontier'}")


main()