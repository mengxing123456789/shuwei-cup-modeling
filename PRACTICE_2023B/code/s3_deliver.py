# -*- coding: utf-8 -*-
"""s3 求解交付驱动：计时 / 约束绑定 / 边界解 / ±10% 扰动。

本文件是 s3 棒次新增的**只读驱动**：不修改 solve.py / model_skeleton.py / numlib.py，
只调用它们并把四类证据落盘到 data/results_*.json。

复算：  python code\\s3_deliver.py
约束：  全程禁用 BLAS（A@B / np.dot / np.linalg.*），线性代数只走 numlib。
"""
from __future__ import annotations

import copy
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parent
ROOT = CODE.parent
DATA = ROOT / "data"
sys.path.insert(0, str(CODE))

import model_skeleton as M          # noqa: E402
import numlib as NL                 # noqa: E402
import solve as S                   # noqa: E402

REPS = 5                            # 计时重复次数（取中位）
SIGNS = (+1, -1)
DELTA = 0.10                        # ±10%
# 放宽后的查询网格：含设计边界 r=0.10 / 1.00 与三档外推
GRID_WIDE = [0.10, 0.15, 0.25, 0.35, 0.45, 0.55, 0.70, 0.90,
             1.00, 1.20, 1.50, 2.00, 3.00]
COMBO3 = ("CS", "CE", "LG")
SOLVE_SRC = (CODE / "solve.py").read_text(encoding="utf-8")


# ------------------------------------------------------------------ 基础设施
def dump(name: str, obj) -> Path:
    p = DATA / name
    p.write_bytes((json.dumps(obj, ensure_ascii=False, indent=1,
                              default=lambda x: float(x)
                              if isinstance(x, (np.floating, np.integer))
                              else bool(x) if isinstance(x, np.bool_) else x)
                   + "\n").encode("utf-8"))
    return p


def snapshot() -> dict:
    return copy.deepcopy({k: v["value"] for k, v in M.MS.PARAMS.items()})


BASE = snapshot()


def restore() -> None:
    for k, v in BASE.items():
        M.MS.PARAMS[k]["value"] = copy.deepcopy(v)


def setp(key: str, val) -> None:
    M.MS.PARAMS[key]["value"] = val


def scaled(val, f):
    if isinstance(val, list):
        return [x * f for x in val]
    if isinstance(val, dict):
        return {k: x * f for k, x in val.items()}
    return val * f


def run_all(ai, aii):
    r1 = S.q1(ai)
    r2 = S.q2(aii, ai)
    r3 = S.q3(ai, aii)
    r4 = S.q4(ai, aii, None)          # q4 签名第三参 r1 未被读取
    r5 = S.q5(ai)
    return r1, r2, r3, r4, r5


# ------------------------------------------------------------------ 头条结论
def headlines(r1, r2, r3, r4, r5, tier_thr=5.0) -> dict:
    h = {}
    for cs in COMBO3:
        for p, v in r1["combos"][cs]["products"].items():
            h[f"Q1.{cs}.{p}.sig"] = bool(v["trend_significant"])
    for cs in COMBO3:
        for g, v in r2["combos"][cs]["gases"].items():
            h[f"Q2.{cs}.{g}.tier"] = "major" if v["span"] >= tier_thr else "minor"
    for grp in ("products", "gases"):
        for k, v in r3[grp].items():
            h[f"Q3.{grp}.{k}.flip"] = bool(v.get("sign_changes", 0) > 0
                                           or v["n_exceed"] == 0)
    for cs in COMBO3:
        for p, v in r4["selectivity"][cs]["gamma_centered"].items():
            h[f"Q4.{cs}.{p}.gsign"] = "+" if v > 0 else ("-" if v < 0 else "0")
    for cs in COMBO3:
        h[f"Q5.{cs}.extrap"] = bool(r5["combos"][cs]["is_extrapolation"])
    return h


def numerics(r1, r2, r3, r4, r5) -> dict:
    d = {}
    for cs in COMBO3:
        for p, v in r1["combos"][cs]["products"].items():
            d[f"Q1.{cs}.{p}.span_over_thr"] = float(v["span_over_thr"])
            d[f"Q1.{cs}.{p}.delta_end"] = float(v["delta_end"])
        for g, v in r2["combos"][cs]["gases"].items():
            d[f"Q2.{cs}.{g}.span"] = float(v["span"])
            d[f"Q2.{cs}.{g}.span_over_thr"] = float(v["span_over_thr"])
        for i, b in enumerate(r2["bridge"][cs]["beta_bridge"]):
            d[f"Q2.{cs}.beta_bridge[{i}]"] = float(b)
        for p, v in r4["selectivity"][cs]["gamma_centered"].items():
            d[f"Q4.{cs}.{p}.gamma"] = float(v)
        cb = r4["carbon_balance"][cs]
        d[f"Q4.{cs}.carbon_end"] = float(cb["carbon_mmol_per_g"][-1])
        d[f"Q4.{cs}.carbon_pct"] = float(cb["delta_end_pct"])
        q = r5["combos"][cs]
        for p in q["point"]:
            for i, val in enumerate(q["point"][p]):
                d[f"Q5.{cs}.{p}[{i}]"] = float(val)
    for k, v in r4["kinetics"]["k_required_per_s"].items():
        d[f"Q4.k_required.{k}"] = float(v)
    d["Q4.log10A_lo"] = float(r4["kinetics"]["ridge_n1"][0]["log10_A"])
    d["Q4.log10A_hi"] = float(r4["kinetics"]["ridge_n1"][-1]["log10_A"])
    return d


def diffnum(a: dict, b: dict, top=6):
    rows = []
    for k in a:
        den = max(abs(a[k]), 1e-12)
        rows.append((abs(b[k] - a[k]) / den, k, a[k], b[k]))
    rows.sort(reverse=True)
    return [{"key": k, "base": base, "new": new, "rel": r}
            for r, k, base, new in rows[:top]]


def flipnum(h0: dict, h1: dict):
    return [{"key": k, "base": h0[k], "new": h1[k]}
            for k in h0 if h0[k] != h1[k]]


# ------------------------------------------------------------------ 1 计时
def part_timing(ai, aii):
    M.selftest(verbose=False)                     # warmup
    specs = [
        ("selftest", lambda: M.selftest(verbose=False)),
        ("load_annex_i", lambda: M.load_annex_i()),
        ("load_annex_ii", lambda: M.load_annex_ii()),
        ("q1", lambda: S.q1(ai)),
        ("q2", lambda: S.q2(aii, ai)),
        ("q3", lambda: S.q3(ai, aii)),
        ("q4", lambda: S.q4(ai, aii, None)),
        ("q5", lambda: S.q5(ai)),
        ("pipeline_q1_to_q5", lambda: run_all(ai, aii)),
    ]
    calls = []
    for name, fn in specs:
        fn()                                      # 每个 call 各一次 warmup
        runs = []
        for _ in range(REPS):
            t0 = time.perf_counter()
            fn()
            runs.append((time.perf_counter() - t0) * 1000.0)
        runs_sorted = sorted(runs)
        calls.append({
            "name": name,
            "reps": REPS,
            "runs_ms": [round(x, 3) for x in runs],
            "median_ms": round(runs_sorted[len(runs) // 2], 3),
            "min_ms": round(min(runs), 3),
            "max_ms": round(max(runs), 3),
            "stdev_ms": round(float(np.std(np.array(runs))), 3),
        })
    return {
        "meta": {
            "clock": "time.perf_counter",
            "reps": REPS,
            "warmup": "每个 call 先跑 1 次不计入",
            "unit": "ms",
            "median_rule": "排序后取 runs[len//2]（奇数样本真中位）",
            "serial": True,
            "note": ("BLAS 被禁（见 numlib），故 numpy 不并行；单次测量噪声本机实测可到 ±56%，"
                     "故报中位不报单次"),
            "interpreter": sys.version.split()[0],
            "numpy": np.__version__,
        },
        "calls": calls,
    }


# ------------------------------------------------------------------ 2 约束绑定
def leverage(w):
    w = np.asarray(w, dtype=float)
    n = len(w)
    wb = float(w.mean())
    sxx = float(((w - wb) ** 2).sum())
    return [float(1.0 / n + (wi - wb) ** 2 / sxx) for wi in w], n, wb, sxx


def part_binding(ai, aii, r1, r2, r3, r4):
    src = []

    # B1 C1 四产物闭合（Annex I）
    st = M.selftest(verbose=False)
    src.append({
        "id": "C1", "from": "Annex I 每列四产物之和",
        "statement": "Σ_p S_p = 1（四产物闭合）",
        "binding": "active",
        "measure": {"max_abs_sum_minus_100": float(st["max_abs_sum_minus_100"]),
                    "n_columns": int(st["n_cols_annex_i"]),
                    "dof_before": 4, "dof_after": 3},
        "effect": "等式在机器精度内成立（1.42e-14），把四产物从 4 维压到 3 维；"
                  "任何单产物 R² 都不能单独作为证据。",
    })

    # B2 C2 ILR 参数化
    src.append({
        "id": "C2", "from": "自设（成分数据标准参数化）",
        "statement": "拟合在 v = ilr(S) ∈ R^3 进行，不直接拟合 S",
        "binding": "active",
        "measure": {cs: {"n_obs": int(r1["combos"][cs]["ilr"]["n_obs"]),
                         "k_par": int(r1["combos"][cs]["ilr"]["k_par"]),
                         "df": int(r1["combos"][cs]["ilr"]["n_obs"])
                               - int(r1["combos"][cs]["ilr"]["k_par"])}
                    for cs in COMBO3},
        "effect": "自由度 3×n 而非 4×n；df = 21/18/18 是后面 F 检验与失拟判定的分母。",
    })

    # B3 C3 掺比网格：端点杠杆
    lev = {}
    for cs in COMBO3:
        h, n, wb, sxx = leverage(ai[{"CS": "DFA/CS", "CE": "DFA/CE",
                                     "LG": "DFA/LG"}[cs]]["w"])
        w = ai[{"CS": "DFA/CS", "CE": "DFA/CE", "LG": "DFA/LG"}[cs]]["w"]
        lev[cs] = {"n": n, "w_bar": round(wb, 6), "sxx": round(sxx, 6),
                   "leverage": [round(x, 4) for x in h],
                   "w": [round(float(x), 6) for x in w],
                   "h_min": round(min(h), 4), "h_max": round(max(h), 4),
                   "h_at_first": round(h[0], 4), "h_at_last": round(h[-1], 4)}
    src.append({
        "id": "C3", "from": "题面 L74–L75（八档掺比，不等距）",
        "statement": "r 只能取 0.1…1.0 八个观测档（CS 另有 r=0）",
        "binding": "active-at-endpoints",
        "measure": lev,
        "effect": ("两端点杠杆最高：CS 首点 h=%.4f、末点 h=%.4f，中点最低 h=%.4f。"
                   "解对 w=0 与 w=0.5 两端的观测最敏感，中间档几乎不约束斜率。"
                   % (lev["CS"]["h_at_first"], lev["CS"]["h_at_last"], lev["CS"]["h_min"])),
    })

    # B4 C4 反例档禁用
    labs = set()
    for d in list(ai.values()) + list(aii.values()):
        labs |= set(d["labels"])
    bad = [l for l in ("5/100", "7/100") if l in labs]
    src.append({
        "id": "C4", "from": "题面 L78（5/100、7/100 为反例）",
        "statement": "r=0.05 与 r=0.07 不得作实验点",
        "binding": "vacuous",
        "measure": {"forbidden_labels_present_in_annex": bad,
                    "n_rows_removed": 0, "all_labels": sorted(labs)},
        "effect": "附件里根本不存在这两档 → 该约束没有删掉任何一行观测，属空约束；"
                  "它只禁止把 r=0.05/0.07 写进 Q5 网格。",
    })

    # B5 C5 跨附件只对齐交集
    bridge = {cs: {"n_levels_used": len(r2["bridge"][cs]["labels"]),
                   "labels": r2["bridge"][cs]["labels"],
                   "n_levels_annex1": len(ai[{"CS": "DFA/CS", "CE": "DFA/CE",
                                              "LG": "DFA/LG"}[cs]]["labels"]),
                   "n_levels_annex2": len(aii[{"CS": "DFA/CS", "CE": "DFA/CE",
                                               "LG": "DFA/LG"}[cs]]["labels"])}
              for cs in COMBO3}
    src.append({
        "id": "C5", "from": "Annex I 与 Annex II 档位不同",
        "statement": "跨附件只对齐 {20,40,50,80,100}（CS 另有 0/100）",
        "binding": "active",
        "measure": bridge,
        "effect": ("CS 丢掉 10/100、30/100、60/100 三档才与 Annex II 对齐；CE/LG 八档全丢三档。"
                   "beta_bridge 只在交集上定义，不能当全域质量闭合。"),
    })

    # B6 C6 CE/LG 无零基线
    cs_d = r1["combos"]["CS"]["products"]["Tar"]
    y0 = cs_d["y"][0]
    y1 = cs_d["y"][1]
    src.append({
        "id": "C6", "from": "Annex I（CE/LG 无 0/100 行）",
        "statement": "CE/LG 没有纯生物质基线，百分比只能相对 10/100 档",
        "binding": "active-on-interpretation",
        "measure": {"CS_Tar_pct_vs_0/100": float(cs_d["delta_end_pct"]),
                    "CS_Tar_pct_vs_10/100": float(100.0 * (cs_d["y"][-1] - y1) / y1),
                    "CE_Tar_pct_vs_10/100": float(r1["combos"]["CE"]["products"]["Tar"]["delta_end_pct"]),
                    "LG_Tar_pct_vs_10/100": float(r1["combos"]["LG"]["products"]["Tar"]["delta_end_pct"])},
        "effect": ("CS 的 Tar 变化可报两个基准（−37.7%% 对纯棉秆 / %.1f%% 对 10/100），"
                   "CE 的 +31.6%% 与 LG 的 −54.7%% 只有 10/100 这一个基准。"
                   "三组合的百分数因此不可横向比较。"
                   % float(100.0 * (cs_d["y"][-1] - y1) / y1)),
    })

    # B7 A7 量级阈值 5.0：可行带
    spans = []
    for cs in COMBO3:
        for g, v in r2["combos"][cs]["gases"].items():
            spans.append((cs, g, float(v["span"]),
                          "major" if v["span"] >= 5.0 else "minor",
                          float(v["span_over_thr"])))
    minor = [s for s in spans if s[3] == "minor"]
    major = [s for s in spans if s[3] == "major"]
    lo = max(s[2] for s in minor)
    hi = min(s[2] for s in major)
    src.append({
        "id": "A7", "from": "自设（01-model.md L112–L121 C3/A7）",
        "statement": "span ≥ 5 mL/g(daf) 判主量级",
        "binding": "active-near-edge",
        "measure": {
            "band_keeping_all_tiers": [round(lo, 4), round(hi, 4)],
            "headroom_lo_pct": round(100.0 * (5.0 - lo) / 5.0, 2),
            "headroom_hi_pct": round(100.0 * (hi - 5.0) / 5.0, 2),
            "cells_within_20pct": [{"combo": s[0], "gas": s[1], "span": s[2],
                                    "tier": s[3], "gap_pct": round(100.0 * abs(s[2] - 5.0) / 5.0, 2)}
                                   for s in spans if abs(s[2] - 5.0) / 5.0 <= 0.20],
            "contradiction_cells": [{"combo": s[0], "gas": s[1], "span": s[2],
                                     "tier": s[3], "span_over_thr": s[4]}
                                    for s in spans if s[3] == "minor" and s[4] > 5.0],
        },
        "effect": ("全部分栏不变的阈值区间是 (%.2f, %.2f]；声明值 5.0 距上边界只剩 %.1f%%，"
                   "所以 CS 的 CO（5.40）与 LG 的 CO（5.71）是贴线解：阈值抬到 5.5 就把 CS CO 打回次量级。"
                   "另有 %d 个格子在次量级里却有 span_over_thr>5（如 CE 的 CH4，2.50 判次量级但比值 14.88），"
                   "说明「分栏」与「是否谈趋势」是两套判据，不能互相代证。"
                   % (lo, hi, 100.0 * (hi - 5.0) / 5.0,
                      len([s for s in spans if s[3] == "minor" and s[4] > 5.0]))),
    })

    # B8 T_py 自设：只绑 A，不绑 k
    kin = r4["kinetics"]
    T = kin["T_py_K"]
    Rg = kin["R"]
    shifts = []
    for Ea in (100.0, 250.0):
        d = (Ea * 1000.0 / (Rg * math.log(10.0))) * (1.0 / (0.9 * T) - 1.0 / T)
        shifts.append({"Ea_kJ_mol": Ea, "dlog10A_for_T_minus10pct": round(d, 4)})
    src.append({
        "id": "T_py", "from": "自设（题面 L145–L146 只说同一温度，未给数值）",
        "statement": "T_py = 800 K",
        "binding": "active-on-A-only",
        "measure": {"k_required_per_s": kin["k_required_per_s"],
                    "k_required_independent_of_T": True,
                    "dlog10A_when_T_10pct_lower": shifts},
        "effect": ("k(T)·t 只由 α 与 t 定（k_need = kt/t_s，公式里没有 T），"
                   "T 只进入脊线的 A。故 T_py 的自设误差不污染 k，只平移 log10A："
                   "T 降 10%% 时 Ea=100 的 log10A 掉 %.3f。"
                   % abs(shifts[0]["dlog10A_for_T_minus10pct"])),
    })

    # B9 eps_rel 判据：可行带
    ratios = []
    for cs in COMBO3:
        for p, v in r1["combos"][cs]["products"].items():
            ratios.append(("Q1", cs, p, float(v["span_over_thr"]),
                           bool(v["trend_significant"])))
        for g, v in r2["combos"][cs]["gases"].items():
            ratios.append(("Q2", cs, g, float(v["span_over_thr"]),
                           bool(v["trend_significant"])))
    eps0 = float(M.MS.v("eps_rel"))
    star_sig = [eps0 * r[3] for r in ratios if r[4]]
    star_non = [eps0 * r[3] for r in ratios if not r[4]]
    band_lo = max(star_non) if star_non else 0.0
    band_hi = min(star_sig) if star_sig else float("inf")
    src.append({
        "id": "eps_rel", "from": "题面 L77（平行实验相对误差 ≈5%）",
        "statement": "三条阈值路径共用 eps_rel = 0.05",
        "binding": "active",
        "measure": {
            "eps_band_keeping_all_significance": [round(band_lo, 6), round(band_hi, 6)],
            "band_width_pct_of_eps": round(100.0 * (band_hi - band_lo) / eps0, 2),
            "tightest_significant": min([{"path": r[0], "combo": r[1], "key": r[2],
                                          "span_over_thr": round(r[3], 4),
                                          "eps_flip": round(eps0 * r[3], 6)}
                                         for r in ratios if r[4]],
                                        key=lambda x: x["span_over_thr"]),
            "tightest_nonsignificant": max([{"path": r[0], "combo": r[1], "key": r[2],
                                             "span_over_thr": round(r[3], 4),
                                             "eps_flip": round(eps0 * r[3], 6)}
                                            for r in ratios if not r[4]],
                                           key=lambda x: x["span_over_thr"]),
        },
        "effect": ("比值与 eps_rel 成反比，故每个格子有一个翻转点 eps* = 0.05·ratio。"
                   "全部显著性判定不变的区间是 (%.4f, %.4f)，宽度只占声明值的 %.1f%%。"
                   "判据在 5%% 处不是「宽松」而是「刚好」。" % (band_lo, band_hi,
                                                              100.0 * (band_hi - band_lo) / eps0)),
    })

    # B10 Annex II 行和
    rs = {cs: [float(min(r2["combos"][cs]["row_sum"])),
               float(max(r2["combos"][cs]["row_sum"]))] for cs in COMBO3}
    bb = {cs: [float(min(r2["bridge"][cs]["beta_bridge"])),
               float(max(r2["bridge"][cs]["beta_bridge"]))] for cs in COMBO3}
    src.append({
        "id": "AnnexII", "from": "Annex II（体积 mL/g(daf)，行和 ≠ 100）",
        "statement": "Annex II 只作相对组成 φ，不做绝对质量闭合",
        "binding": "active",
        "measure": {"row_sum_range": rs, "beta_bridge_range": bb},
        "effect": ("行和落在 68.00–153.25，既不等于 100 也不等于 Annex I 的 Syngas；"
                   "beta_bridge 只有 0.570–0.713，说明两附件量纲不同。"
                   "把 Annex II 当绝对产率会系统性高估气相。"),
    })

    # B11 C8 无重复实验 → 禁解析式敏感性
    src.append({
        "id": "C8", "from": "附件（每档单次，无平行样）",
        "statement": "无重复实验 → 不允许「±10% 扰动重解」冒充统计敏感性",
        "binding": "active-as-prohibition",
        "measure": {"replicates_in_annex": 0,
                    "substitute": "5% 输入噪声 MC(4000) + 留一交叉验证 + 参数 ±10% 真跑"},
        "effect": ("本棒按此约束把敏感性拆成两件独立的事：统计不确定性走 MC 与 LOO（results_q5.json），"
                   "参数鲁棒性走真跑扰动（results_perturb.json），两者分母不同、不合并。"),
    })

    return {
        "meta": {
            "question": "约束在解处是否起作用（逐来源）",
            "rule": "active=解落在该约束的边界或等式上；active-at-endpoints=只在设计端点起作用；"
                    "active-near-edge=声明值离翻转点不足 20%；vacuous=没有删掉任何观测",
            "note": "本题无不等式约束组，故不存在「一个 True 概括全部」的 binding 标量",
        },
        "sources": src,
    }


# ------------------------------------------------------------------ 3 边界解
def part_boundary(ai, r5_base):
    wmap = {cs: ai[{"CS": "DFA/CS", "CE": "DFA/CE", "LG": "DFA/LG"}[cs]]["w"]
            for cs in COMBO3}
    setp("grid_pred_ASSUMED", list(GRID_WIDE))
    try:
        r5w = S.q5(ai)
    finally:
        restore()
    out = {"meta": {
        "question": "解是否在搜索网格边界",
        "grid_declared_r": BASE["grid_pred_ASSUMED"],
        "grid_widened_r": GRID_WIDE,
        "star_rule": "★ = 查询点恰好落在该组合观测支撑的端点（w=w_min 或 w=w_max）；"
                     "★★ = 查询点离开支撑，属外推，值仅供参考",
        "w_map": {cs: "w = r/(1+r)，r=1.00 → w=0.5 只是 50 wt% 掺灰，不是纯脱硫灰"
                      for cs in COMBO3},
    }, "combos": {}}
    for cs in COMBO3:
        w = wmap[cs]
        wmin, wmax = float(w.min()), float(w.max())
        q = r5w["combos"][cs]
        rows = []
        for i, r in enumerate(GRID_WIDE):
            wq = r / (1.0 + r)
            if wq > wmax + 1e-12 or wq < wmin - 1e-12:
                mark = "★★"
            elif abs(wq - wmax) < 1e-12 or abs(wq - wmin) < 1e-12:
                mark = "★"
            else:
                mark = ""
            rows.append({"r": r, "w": round(wq, 6), "mark": mark,
                         "point": {p: round(float(q["point"][p][i]), 4)
                                   for p in q["point"]},
                         "lo": {p: round(float(q["lo"][p][i]), 4) for p in q["lo"]},
                         "hi": {p: round(float(q["hi"][p][i]), 4) for p in q["hi"]}})
        # 与声明网格重叠处必须逐位一致
        cross = []
        for i, r in enumerate(BASE["grid_pred_ASSUMED"]):
            j = GRID_WIDE.index(r)
            for p in q["point"]:
                cross.append(abs(float(q["point"][p][j])
                                 - float(r5_base["combos"][cs]["point"][p][i])))
        out["combos"][cs] = {
            "w_min": round(wmin, 6), "w_max": round(wmax, 6),
            "n_boundary_star": sum(1 for x in rows if x["mark"] == "★"),
            "n_extrapolation_star2": sum(1 for x in rows if x["mark"] == "★★"),
            "max_abs_diff_on_overlap": max(cross),
            "rows": rows,
        }
    return out


# ------------------------------------------------------------------ 4 ±10% 扰动
SOURCES = [
    # (source, key, class)  class: model / query / never-read
    ("eps_rel", "eps_rel", "model"),
    ("V_m", "V_m_ASSUMED", "model"),
    ("T_py", "T_py_ASSUMED", "model"),
    ("t_hold", "t_hold_ASSUMED", "model"),
    ("alpha", "alpha_target", "model"),
    ("Ea_lo", "Ea_ASSUMED_RANGE", "model"),
    ("Ea_hi", "Ea_ASSUMED_RANGE", "model"),
    ("tier_thr", "tier_thr", "model"),
    ("grid_r0", "grid_pred_ASSUMED", "query"),
    ("grid_r1", "grid_pred_ASSUMED", "query"),
    ("grid_r2", "grid_pred_ASSUMED", "query"),
    ("grid_r3", "grid_pred_ASSUMED", "query"),
    ("grid_r4", "grid_pred_ASSUMED", "query"),
    ("grid_r5", "grid_pred_ASSUMED", "query"),
    ("grid_r6", "grid_pred_ASSUMED", "query"),
    ("beta_heat", "beta_heat_ASSUMED", "never-read"),
    ("Q_carrier", "Q_carrier_ASSUMED", "never-read"),
    ("d_p", "d_p_ASSUMED", "never-read"),
    ("m_sample", "m_sample_ASSUMED", "never-read"),
    ("dfa_CaO", "dfa_comp_ASSUMED", "never-read"),
    ("dfa_SiO2", "dfa_comp_ASSUMED", "never-read"),
]
ALPHA0 = 0.95
TIER0 = 5.0


def kinetics_with_alpha(alpha, kin):
    """按 solve.py L392–L404 的同一算式重算，仅把 alpha 换掉（q4 里 alpha 是字面量）。"""
    t_s = kin["t_hold_s"]
    R = kin["R"]
    T = kin["T_py_K"]
    if alpha >= 1.0:
        return {"ok": False, "why": "alpha>=1：n=1 需 ln(1-α)、n=2 需 1/(1-α)-1，均无定义"}
    kt = {"n=0": alpha, "n=1": -math.log(1.0 - alpha), "n=2": 1.0 / (1.0 - alpha) - 1.0}
    k_need = {k: v / t_s for k, v in kt.items()}
    ridge = []
    for p in kin["ridge_n1"]:
        Ea = p["Ea_kJ_mol"]
        A = k_need["n=1"] * math.exp(Ea * 1000.0 / (R * T))
        ridge.append({"Ea_kJ_mol": Ea, "A_per_s": A, "log10_A": math.log10(A)})
    return {"ok": True, "kt_required": kt, "k_required_per_s": k_need,
            "n_order_confounding": kt["n=2"] / kt["n=1"], "ridge_n1": ridge}


def part_perturb(ai, aii, h0, n0):
    runs = []
    for name, key, cls in SOURCES:
        for s in SIGNS:
            f = 1.0 + DELTA * s
            rec = {"source": name, "key": key, "class": cls,
                   "sign": "+" if s > 0 else "-", "factor": f}
            try:
                if cls == "never-read":
                    rec["referenced_in_solve_py"] = (key in SOLVE_SRC)
                    r1, r2, r3, r4, r5 = run_all(ai, aii)
                    rec["mode"] = "run"
                elif name == "alpha":
                    r1, r2, r3, r4, r5 = run_all(ai, aii)
                    kk = kinetics_with_alpha(ALPHA0 * f, r4["kinetics"])
                    rec["mode"] = "recompute(q4 里 alpha 是字面量)"
                    if not kk["ok"]:
                        rec["feasible"] = False
                        rec["infeasible_reason"] = kk["why"]
                        rec["n_flips"] = None
                        rec["flips"] = []
                        rec["top_rel_changes"] = []
                        rec["max_rel_change"] = None
                        runs.append(rec)
                        continue
                    r4 = copy.deepcopy(r4)
                    r4["kinetics"].update({"k_required_per_s": kk["k_required_per_s"],
                                           "kt_required": kk["kt_required"],
                                           "n_order_confounding": kk["n_order_confounding"],
                                           "ridge_n1": kk["ridge_n1"]})
                elif name == "tier_thr":
                    r1, r2, r3, r4, r5 = run_all(ai, aii)
                    rec["mode"] = "run(分栏由 span 重判)"
                elif name.startswith("grid_r"):
                    g = list(BASE["grid_pred_ASSUMED"])
                    i = int(name[-1])
                    g[i] = g[i] * f
                    setp("grid_pred_ASSUMED", g)
                    r1, r2, r3, r4, r5 = run_all(ai, aii)
                    rec["mode"] = "run(只移动查询点)"
                    rec["grid_after"] = g
                elif name in ("Ea_lo", "Ea_hi"):
                    lo, hi = BASE["Ea_ASSUMED_RANGE"]
                    if name == "Ea_lo":
                        lo = lo * f
                    else:
                        hi = hi * f
                    setp("Ea_ASSUMED_RANGE", [lo, hi])
                    r1, r2, r3, r4, r5 = run_all(ai, aii)
                    rec["mode"] = "run"
                    rec["Ea_range_after"] = [lo, hi]
                else:
                    setp(key, scaled(BASE[key], f))
                    r1, r2, r3, r4, r5 = run_all(ai, aii)
                    rec["mode"] = "run"
            finally:
                restore()

            thr = TIER0 * f if name == "tier_thr" else TIER0
            h1 = headlines(r1, r2, r3, r4, r5, tier_thr=thr)
            n1 = numerics(r1, r2, r3, r4, r5)

            reasons = []
            for cs in COMBO3:
                if r5["combos"][cs]["is_extrapolation"]:
                    reasons.append(f"{cs} 预测点离开观测支撑（外推）")
                if max(abs(x - 100.0) for x in r5["combos"][cs]["row_sum_point"]) > 1e-6:
                    reasons.append(f"{cs} 预测行和偏离 100")
                for p, vals in r5["combos"][cs]["point"].items():
                    if any((not math.isfinite(v)) or v <= 0.0 for v in vals):
                        reasons.append(f"{cs}.{p} 出现非正或非有限组成")
            rec["feasible"] = (len(reasons) == 0)
            rec["infeasible_reason"] = "；".join(reasons) if reasons else None

            fl = flipnum(h0, h1)
            rec["n_flips"] = len(fl)
            rec["flips"] = fl
            rec["top_rel_changes"] = diffnum(n0, n1, top=4)
            rec["max_rel_change"] = rec["top_rel_changes"][0]["rel"] if n1 else 0.0
            runs.append(rec)

    n_all = len(runs)
    infeas = [r for r in runs if not r["feasible"]]
    never = [r for r in runs if r["class"] == "never-read"]
    query = [r for r in runs if r["class"] == "query"]
    model = [r for r in runs if r["class"] == "model"]
    model_feas = [r for r in model if r["feasible"]]
    return {
        "meta": {
            "question": "参数 ±10% 后结论是否翻转",
            "n_attempted": n_all,
            "n_sources": len(SOURCES),
            "delta": DELTA,
            "signs": list(SIGNS),
            "denominator_rule": ("三类分开记：never-read 参数从未被 solve.py 读取 → 分母剔除；"
                                 "query 类只移动查询点、模型不变 → 不参与「结论翻转」分母；"
                                 "model 类才是真扰动。不可行的单次单列，不进任何分母。"),
            "counts": {
                "attempted": n_all,
                "never_read": len(never),
                "query_move": len(query),
                "model_perturb": len(model),
                "model_infeasible": len(infeas),
                "model_feasible": len(model_feas),
                "flip_denominator": len(model_feas),
                "model_runs_with_flip": len([r for r in model_feas if r["n_flips"] > 0]),
            },
            "headline_keys": len(h0),
        },
        "runs": runs,
        "infeasible": [{"source": r["source"], "sign": r["sign"],
                        "reason": r["infeasible_reason"]} for r in infeas],
    }


# ------------------------------------------------------------------ main
def main() -> int:
    ai = M.load_annex_i()
    aii = M.load_annex_ii()

    t = part_timing(ai, aii)
    p_t = dump("results_timing.json", t)

    r1, r2, r3, r4, r5 = run_all(ai, aii)
    b = part_binding(ai, aii, r1, r2, r3, r4)
    p_b = dump("results_binding.json", b)

    bd = part_boundary(ai, r5)
    p_bd = dump("results_boundary.json", bd)

    h0 = headlines(r1, r2, r3, r4, r5)
    n0 = numerics(r1, r2, r3, r4, r5)
    pt = part_perturb(ai, aii, h0, n0)
    p_pt = dump("results_perturb.json", pt)

    print("=== 计时（median_ms）")
    for c in t["calls"]:
        print(f"  {c['name']:<20} {c['median_ms']:>9.3f}  (min {c['min_ms']:.3f} "
              f"max {c['max_ms']:.3f} stdev {c['stdev_ms']:.3f})")
    print("=== 约束绑定（逐来源）")
    for s in b["sources"]:
        print(f"  {s['id']:<10} {s['binding']}")
    print("=== 边界解")
    for cs in COMBO3:
        c = bd["combos"][cs]
        print(f"  {cs} w∈[{c['w_min']},{c['w_max']}] ★{c['n_boundary_star']} "
              f"★★{c['n_extrapolation_star2']} 重叠处最大差 {c['max_abs_diff_on_overlap']:.3e}")
    print("=== 扰动")
    cc = pt["meta"]["counts"]
    print(f"  尝试 {cc['attempted']} 次：never-read {cc['never_read']} / "
          f"query {cc['query_move']} / model {cc['model_perturb']}")
    print(f"  model 不可行 {cc['model_infeasible']}，可行 {cc['model_feasible']}，"
          f"其中翻转 {cc['model_runs_with_flip']}")
    for r in pt["infeasible"]:
        print(f"    不可行: {r['source']}{r['sign']} —— {r['reason']}")
    print("=== 落盘")
    for p in (p_t, p_b, p_bd, p_pt):
        print(f"  {p.name}  {p.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
