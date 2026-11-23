#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市调专项分析：Kano 需求分类、价格敏感度测试（PSM）、联合分析、结构方程模型（SEM/CFA），以及联合分析的卡片设计。

由 survey_stats.py 按 ANALYSIS_PLAN.json 调度（analyses[].type = kano / psm / conjoint / sem / cfa），
所有数字由脚本算出，模型只负责选方法、写解释。计划条目的写法见 survey_contract.md。

  kano      两道矩阵单选：正向问题（产品有这项功能时您的感受）与反向问题（没有这项功能时您的感受），
            行是功能，选项是“喜欢 / 理应如此 / 无所谓 / 能忍受 / 不喜欢”（按选项文字识别，认不全时按编码顺序）。
            按 Kano 评价表归为 A 魅力、O 期望、M 必备、I 无差异、R 反向、Q 可疑；归类取众数，并列时按 M>O>A>I>R；
            Fong 检验判断前两类的差别是否显著（不显著时是“混合型”，解读要谨慎）；
            Better = (A+O)/(A+O+M+I)，Worse = −(O+M)/(A+O+M+I)，以各功能的平均值为界划四象限。
  psm       Van Westendorp 价格敏感度测试：四道数值题（多少钱会觉得太便宜而怀疑质量 / 便宜划算 / 有点贵 / 太贵不会买）。
            剔除四个价格不是由低到高的作答；“太便宜”“便宜”曲线是认为该价格仍算（太）便宜的累计占比，
            “贵”“太贵”曲线是认为该价格已经（太）贵的累计占比。四个交点：最低可接受价 PMC（太便宜×不便宜）、
            最优价格点 OPP（太便宜×太贵）、无差异价格点 IPP（不便宜×不贵，即便宜×贵）、最高可接受价 PME（太贵×不贵），
            交点在相邻价格之间线性插值。可接受价格区间为 [PMC, PME]。
  conjoint  评分型全轮廓联合分析：一道或几道矩阵量表题，每行是一张产品卡片（属性水平组合来自正交设计）。
            逐个受访者用效应编码做最小二乘，得到各水平的效用值（part-worth）；属性重要性 = 该属性效用极差 ÷
            全部属性极差之和，再对受访者取平均。整体拟合给 Pearson R 与 Kendall τ（各卡片平均评分 vs 预测），
            有检验卡（holdout）时给检验卡命中率；可选市场模拟（最大效用法、BTL 法的偏好份额）。
            整列同分的受访者无法估计效用，剔除并计数。结果里附估计卡片的设计诊断（D 效率、水平平衡），供报告引用。
  sem/cfa   协方差结构方程（极大似然，Wishart 口径：样本协方差用 n−1，χ² = (n−1)·F_ML）。
            每个潜变量第一个题项的载荷固定为 1；外生变量之间自由相关；给出非标准化、标准化估计及标准误、R²、
            CR、AVE、Fornell–Larcker 与 HTMT；拟合指标 χ²/df、RMSEA（90% 置信区间、PCLOSE）、SRMR、GFI、AGFI、
            CFI、TLI、NFI、IFI 及判定；间接效应用 delta 法（Sobel 检验）与蒙特卡洛置信区间（20000 次，固定种子）。
            cfa 只估计测量模型（潜变量两两相关）。

联合分析卡片设计（问卷设计时用，不碰数据）：
  python _utils/survey_methods.py conjoint-design --spec conjoint_spec.json [--holdout 2] [--max-cards 20]
      [--qid Q30] [--rows-per-question 9] [--out CONJOINT_DESIGN.json]
  spec：{"attributes": [{"name": "月费", "levels": ["29 元", "49 元", "69 元"]}, ...]}
  优先用正交表（L4、L8、L9、L12、L16、L18、L25、L27 及其混合水平变形），放不下时用 D 最优交换算法；
  输出卡片、设计诊断（D 效率、水平平衡、属性间最大相关）、建议的矩阵题和分析计划条目。
退出码：0 成功；1 设计不可行；2 输入缺失或格式错误。
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import survey_schema as S  # noqa: E402

SEED = 20261008
MC_DRAWS = 20000


# ───────────────────────── 公共 ─────────────────────────

def row_vars(items: dict, ref) -> list[str]:
    """题号（矩阵题按行展开）、变量名或它们的列表 → 变量名列表。items 为 {题号: 题目}。"""
    refs = ref if isinstance(ref, list) else [ref]
    out = []
    for r in refs:
        if not r:
            continue
        item = items.get(r)
        if item and item.get("type") in S.MATRIX_TYPES:
            out += [row.get("id") for row in item.get("rows") or [] if isinstance(row, dict) and row.get("id")]
        else:
            out.append(r)
    return out


def _numeric(ctx, name: str):
    """数值列；反向计分题按量表两端反转（与信度、因子分析一致）。"""
    s = ctx.series(name)
    var = ctx.vars.get(name) or {}
    if var.get("reverse") and var.get("min") is not None:
        s = (var["min"] + var["max"]) - s
    return s


def _row_label(ctx, name: str) -> str:
    var = ctx.vars.get(name) or {}
    return str(var.get("row_label") or ctx.label(name)).split("｜")[-1].strip()


# ───────────────────────── Kano ─────────────────────────

# 行：正向问题的回答；列：反向问题的回答；顺序都是 喜欢、理应如此、无所谓、能忍受、不喜欢
KANO_TABLE = (("Q", "A", "A", "A", "O"),
              ("R", "I", "I", "I", "M"),
              ("R", "I", "I", "I", "M"),
              ("R", "I", "I", "I", "M"),
              ("R", "R", "R", "R", "Q"))
KANO_NAMES = {"A": "魅力属性", "O": "期望属性", "M": "必备属性", "I": "无差异属性", "R": "反向属性", "Q": "可疑结果"}
KANO_TIE = ("M", "O", "A", "I", "R")
KANO_ANSWERS = ("喜欢", "理应如此", "无所谓", "能忍受", "不喜欢")
# 先认否定（“不喜欢”里也有“喜欢”）
_KANO_WORDS = ((4, r"不喜欢|不满意|讨厌|反感|无法接受|不能接受|不能忍受|难以接受"),
               (0, r"喜欢|满意|惊喜|开心|高兴"),
               (1, r"理所当然|理应|应该|本该|必须|必备|应当|本来就"),
               (2, r"无所谓|无感|中立|都行|没感觉|不在乎"),
               (3, r"忍受|勉强|还能接受|可以接受|能接受|凑合"))
KANO_QUADRANTS = {(True, True): "期望属性", (True, False): "魅力属性", (False, True): "必备属性",
                  (False, False): "无差异属性"}


def kano_answer_map(item: dict) -> tuple[dict | None, str]:
    """选项编码 → 0..4（喜欢、理应如此、无所谓、能忍受、不喜欢）。先按选项文字认，认不全时按编码顺序。"""
    opts = [o for o in item.get("options") or [] if isinstance(o, dict) and "code" in o]
    if len(opts) != 5:
        return None, f"Kano 题需要 5 个选项（{'、'.join(KANO_ANSWERS)}），实际 {len(opts)} 个"
    by_label = {}
    for o in opts:
        for k, pat in _KANO_WORDS:
            if re.search(pat, str(o.get("label", ""))):
                by_label[float(o["code"])] = k
                break
    if len(by_label) == 5 and len(set(by_label.values())) == 5:
        return by_label, "label"
    codes = sorted(float(o["code"]) for o in opts)
    return {c: i for i, c in enumerate(codes)}, "order"


def kano_classify(counts: dict) -> tuple[str, str]:
    """众数归类（Q 不参与），并列时按 M>O>A>I>R。返回 (第一类, 第二类)。"""
    ranked = sorted(KANO_TIE, key=lambda c: (-counts.get(c, 0), KANO_TIE.index(c)))
    return ranked[0], ranked[1]


def a_kano(ctx, a: dict) -> dict:
    fun = row_vars(ctx.items, a.get("functional"))
    dys = row_vars(ctx.items, a.get("dysfunctional"))
    if not fun or len(fun) != len(dys):
        return {"error": "Kano 需要行数相同的正向问题与反向问题（functional / dysfunctional）"}
    labels = a.get("labels") or [_row_label(ctx, f) for f in fun]
    if len(labels) != len(fun):
        return {"error": f"labels 有 {len(labels)} 个，功能有 {len(fun)} 个"}
    maps, by_order = {}, set()
    for name in fun + dys:
        qid = (ctx.vars.get(name) or {}).get("question")
        mapping, how = kano_answer_map(ctx.items.get(qid) or {})
        if mapping is None:
            return {"error": f"{name}：{how}"}
        maps[name] = mapping
        if how == "order":
            by_order.add(qid)
    attrs, n_resp = [], 0
    for f, d, lab in zip(fun, dys, labels):
        fs, ds = ctx.series(f), ctx.series(d)
        ok = fs.notna() & ds.notna()
        counts = {k: 0 for k in "AOMIRQ"}
        for x, y in zip(fs[ok], ds[ok]):
            i, j = maps[f].get(float(x)), maps[d].get(float(y))
            if i is not None and j is not None:
                counts[KANO_TABLE[i][j]] += 1
        total = sum(counts.values())
        if not total:
            return {"error": f"{lab}：没有有效作答"}
        n_resp = max(n_resp, total)
        classified = total - counts["Q"]
        core = counts["A"] + counts["O"] + counts["M"] + counts["I"]
        cat, second = kano_classify(counts)
        x1, x2 = counts[cat], counts[second]
        # Fong 检验：|a−b| < 1.65·√((a+b)(2n−a−b)/(2n)) 时前两类的差别不显著
        limit = 1.65 * math.sqrt((x1 + x2) * (2 * classified - x1 - x2) / (2 * classified)) if classified else None
        better = (counts["A"] + counts["O"]) / core if core else None
        worse = -(counts["O"] + counts["M"]) / core if core else None
        attrs.append({"label": str(lab), "functional_var": f, "dysfunctional_var": d, "n": total,
                      "n_classified": classified, "counts": counts,
                      "pct": {k: v / total * 100 for k, v in counts.items()},
                      "category": cat, "category_label": KANO_NAMES[cat],
                      "second": second, "second_label": KANO_NAMES[second],
                      "fong_significant": bool(limit is not None and abs(x1 - x2) >= limit),
                      "better": better, "worse": worse, "worse_abs": None if worse is None else abs(worse)})
    scored = [x for x in attrs if x["better"] is not None]
    cut_b = sum(x["better"] for x in scored) / len(scored) if scored else None
    cut_w = sum(x["worse_abs"] for x in scored) / len(scored) if scored else None
    for x in scored:
        x["quadrant"] = KANO_QUADRANTS[(x["better"] >= cut_b, x["worse_abs"] >= cut_w)]
    order = {c: i for i, c in enumerate(KANO_TIE + ("Q",))}
    priority = sorted(attrs, key=lambda x: (order[x["category"]], -((x["better"] or 0) + (x["worse_abs"] or 0))))
    out = {"n": n_resp, "attributes": attrs, "better_cut": cut_b, "worse_cut": cut_w,
           "cut_rule": "以各功能 Better 系数与 |Worse| 系数的平均值为界",
           "tie_rule": "众数归类（可疑结果不参与），并列时按 M>O>A>I>R",
           "priority": [x["label"] for x in priority],
           "category_labels": dict(KANO_NAMES)}
    if by_order:
        out["answer_mapping"] = ("选项文字未能逐一识别，按编码顺序对应“" + "、".join(KANO_ANSWERS) + "”："
                                 + "、".join(sorted(by_order)))
    notes = []
    risky = [x["label"] for x in attrs if x["pct"]["Q"] > 10]
    if risky:
        notes.append(f"可疑结果超过 10% 的功能：{'、'.join(risky)}（正反向问题可能被误读）")
    mixed = [x["label"] for x in attrs if not x["fong_significant"]]
    if mixed:
        notes.append(f"前两类差别不显著（Fong 检验，混合型）的功能：{'、'.join(mixed)}")
    if notes:
        out["warning"] = "；".join(notes)
    return out


# ───────────────────────── 价格敏感度测试（PSM） ─────────────────────────

PSM_KEYS = ("too_cheap", "cheap", "expensive", "too_expensive")
PSM_NAMES = {"pmc": "最低可接受价（PMC）", "opp": "最优价格点（OPP）", "ipp": "无差异价格点（IPP）",
             "pme": "最高可接受价（PME）"}


def _crossing(prices, f, g):
    """f（随价格下降）与 g（随价格上升）的第一个交点，相邻价格之间线性插值。返回 (价格, 交点处的比例)。"""
    diff = [a - b for a, b in zip(f, g)]
    if diff and diff[0] <= 0:
        return float(prices[0]), float(f[0])
    for i in range(1, len(prices)):
        if diff[i - 1] > 0 >= diff[i]:
            t = diff[i - 1] / (diff[i - 1] - diff[i])
            price = prices[i - 1] + t * (prices[i] - prices[i - 1])
            return float(price), float(f[i - 1] + t * (f[i] - f[i - 1]))
    return None, None


def a_psm(ctx, a: dict) -> dict:
    import numpy as np
    import pandas as pd
    if not all(a.get(k) for k in PSM_KEYS):
        return {"error": "PSM 需要四道价格题：too_cheap、cheap、expensive、too_expensive"}
    frame = pd.DataFrame({k: ctx.series(a[k]) for k in PSM_KEYS}).dropna()
    answered = int(len(frame))
    ordered = ((frame >= 0).all(axis=1) & (frame["too_cheap"] <= frame["cheap"])
               & (frame["cheap"] <= frame["expensive"]) & (frame["expensive"] <= frame["too_expensive"]))
    valid = frame[ordered]
    n = int(len(valid))
    if n < 30:
        return {"error": f"有效作答只有 {n} 份（四个价格须由低到高），无法做价格敏感度测试"}
    v = {k: valid[k].to_numpy(dtype=float) for k in PSM_KEYS}
    prices = np.unique(np.concatenate(list(v.values())))

    def share(x, at, ge):
        return ((x[None, :] >= at[:, None]) if ge else (x[None, :] <= at[:, None])).mean(axis=1)
    tc, ch = share(v["too_cheap"], prices, True), share(v["cheap"], prices, True)
    ex, te = share(v["expensive"], prices, False), share(v["too_expensive"], prices, False)
    # 四个交点都取在 PSM 图实际画出的四条曲线上（太便宜、不便宜、不贵、太贵）；
    # IPP 写成“不贵×不便宜”，价格与“便宜×贵”相同，交点处占比是图上那个交点的高度
    pairs = {"pmc": (tc, 1 - ch), "opp": (tc, te), "ipp": (1 - ex, 1 - ch), "pme": (1 - ex, te)}
    points, missing = {}, []
    for key, (f, g) in pairs.items():
        price, at = _crossing(prices, f, g)
        if price is None:
            missing.append(PSM_NAMES[key])
        points[key] = {"label": PSM_NAMES[key], "price": price, "pct": None if at is None else at * 100}
    unit = a.get("unit") or (ctx.vars.get(a["cheap"]) or {}).get("unit") or "元"
    out = {"unit": unit, "n": n, "n_answered": answered, "n_inconsistent": answered - n,
           "inconsistent_pct": (answered - n) / answered * 100 if answered else None,
           "price_points": points,
           "acceptable_range": [points["pmc"]["price"], points["pme"]["price"]],
           "optimal_range": sorted(x for x in (points["opp"]["price"], points["ipp"]["price"]) if x is not None),
           "medians": {k: float(np.median(v[k])) for k in PSM_KEYS},
           "means": {k: float(v[k].mean()) for k in PSM_KEYS},
           "curve_rule": "太便宜、便宜：认为该价格仍算（太）便宜的累计占比；贵、太贵：认为该价格已经（太）贵的累计占比；"
                         "交点在相邻价格之间线性插值"}
    refs = []
    for p in a.get("reference_prices") or []:
        p = float(p)
        cells = {"too_cheap_pct": float((v["too_cheap"] >= p).mean() * 100), "cheap_pct": float((v["cheap"] >= p).mean() * 100),
                 "expensive_pct": float((v["expensive"] <= p).mean() * 100),
                 "too_expensive_pct": float((v["too_expensive"] <= p).mean() * 100)}
        cells["acceptable_pct"] = 100 - cells["too_cheap_pct"] - cells["too_expensive_pct"]
        refs.append({"price": p, **cells})
    if refs:
        out["reference_prices"] = refs
    keep = np.arange(len(prices))
    if len(prices) > 200:
        keep = np.unique(np.linspace(0, len(prices) - 1, 200).round().astype(int))
    out["plot"] = {"price": prices[keep].tolist(), "too_cheap": (tc[keep] * 100).tolist(),
                   "not_cheap": ((1 - ch[keep]) * 100).tolist(), "not_expensive": ((1 - ex[keep]) * 100).tolist(),
                   "too_expensive": (te[keep] * 100).tolist()}
    notes = []
    if missing:
        notes.append(f"曲线没有交点：{'、'.join(missing)}")
    if out["inconsistent_pct"] and out["inconsistent_pct"] > 20:
        notes.append(f"四个价格前后矛盾的作答占 {out['inconsistent_pct']:.1f}%，题目说明可能不清楚")
    lo, hi = out["acceptable_range"]
    if lo is not None and hi is not None and lo > hi:
        notes.append("最低可接受价高于最高可接受价，可接受区间为空")
    if notes:
        out["warning"] = "；".join(notes)
    return out


# ───────────────────────── 联合分析 ─────────────────────────

def conjoint_profiles(profiles, attrs: list[dict]) -> tuple[list[list[int]] | None, str | None]:
    """卡片 → 各属性的水平序号（从 0 起）。卡片可写序号列表、水平文字列表或 {属性名: 水平}。"""
    if not attrs:
        return None, "联合分析需要 attributes（属性及其水平）"
    out = []
    for no, prof in enumerate(profiles or [], start=1):
        if isinstance(prof, dict):
            prof = [prof.get(at.get("name")) for at in attrs]
        if not isinstance(prof, (list, tuple)) or len(prof) != len(attrs):
            return None, f"第 {no} 张卡片应给出 {len(attrs)} 个属性的水平"
        row = []
        for value, at in zip(prof, attrs):
            levels = [str(x) for x in at.get("levels") or []]
            if isinstance(value, bool):
                return None, f"第 {no} 张卡片的水平写法不对：{value!r}"
            if isinstance(value, (int, float)) and float(value).is_integer():
                idx = int(value)
            elif str(value) in levels:
                idx = levels.index(str(value))
            else:
                return None, f"第 {no} 张卡片：属性“{at.get('name')}”没有水平 {value!r}"
            if not 0 <= idx < len(levels):
                return None, f"第 {no} 张卡片：属性“{at.get('name')}”的水平序号 {idx} 超出范围（共 {len(levels)} 个水平，从 0 起）"
            row.append(idx)
        out.append(row)
    return out, None


def effects_row(levels: list[int], sizes: list[int]) -> list[float]:
    """效应编码：常数项 + 每个属性 L−1 列，最后一个水平记 −1。"""
    row = [1.0]
    for li, size in zip(levels, sizes):
        row += [-1.0] * (size - 1) if li == size - 1 else [1.0 if j == li else 0.0 for j in range(size - 1)]
    return row


def conjoint_param_count(attrs: list[dict]) -> int:
    return 1 + sum(max(len(at.get("levels") or []) - 1, 0) for at in attrs)


def a_conjoint(ctx, a: dict) -> dict:
    import numpy as np
    from scipy import stats as st
    attrs = a.get("attributes") or []
    cards = row_vars(ctx.items, a.get("ratings"))
    profiles, err = conjoint_profiles(a.get("profiles"), attrs)
    if err:
        return {"error": err}
    if len(profiles) != len(cards):
        return {"error": f"评分题有 {len(cards)} 张卡片，profiles 有 {len(profiles)} 条，必须一一对应"}
    sizes = [len(at["levels"]) for at in attrs]
    if min(sizes) < 2:
        return {"error": "每个属性至少 2 个水平"}
    holdout = sorted({int(h) - 1 for h in a.get("holdout_cards") or [] if 1 <= int(h) <= len(cards)})
    est = [i for i in range(len(cards)) if i not in holdout]
    X = np.array([effects_row(profiles[i], sizes) for i in est])
    k = X.shape[1]
    if len(est) <= k or np.linalg.matrix_rank(X) < k:
        return {"error": f"估计用卡片 {len(est)} 张，要估 {k} 个参数，卡片太少或设计不满秩（各属性水平没有拉开）"}
    Y = np.column_stack([ctx.series(c).to_numpy(dtype=float) for c in cards])
    complete = ~np.isnan(Y).any(axis=1)
    flat = complete & (Y[:, est].std(axis=1) == 0)
    use = complete & ~flat
    Ye = Y[use][:, est]
    n = int(use.sum())
    if n < 10:
        return {"error": f"可用于估计的受访者只有 {n} 人"}
    beta = np.linalg.lstsq(X, Ye.T, rcond=None)[0]                    # k × n
    resid = Ye.T - X @ beta
    sst = ((Ye.T - Ye.mean(axis=1)) ** 2).sum(axis=0)
    r2 = 1 - (resid ** 2).sum(axis=0) / sst
    utils, pos = [], 1
    for size in sizes:
        b = beta[pos:pos + size - 1].T
        utils.append(np.column_stack([b, -b.sum(axis=1)]))
        pos += size - 1
    ranges = np.column_stack([u.max(axis=1) - u.min(axis=1) for u in utils])
    total = ranges.sum(axis=1)
    imp = ranges[total > 0] / total[total > 0, None] * 100
    t975 = float(st.t.ppf(0.975, n - 1))
    out_attrs = []
    for j, (at, u) in enumerate(zip(attrs, utils)):
        levels = []
        for li, lab in enumerate(at["levels"]):
            col = u[:, li]
            m, sd = float(col.mean()), float(col.std(ddof=1))
            half = t975 * sd / math.sqrt(n)
            levels.append({"label": str(lab), "utility": m, "sd": sd, "ci95": [m - half, m + half]})
        means = [x["utility"] for x in levels]
        out_attrs.append({"name": str(at["name"]), "importance_pct": float(imp[:, j].mean()),
                          "importance_sd": float(imp[:, j].std(ddof=1)), "utility_range": max(means) - min(means),
                          "best_level": levels[int(np.argmax(means))]["label"], "levels": levels})
    obs, pred = Ye.mean(axis=0), X @ beta.mean(axis=1)
    pr = st.pearsonr(obs, pred)
    kt = st.kendalltau(obs, pred)
    fit = {"pearson_r": float(pr[0]), "pearson_p": float(pr[1]), "kendall_tau": float(kt[0]), "kendall_p": float(kt[1]),
           "mean_individual_r2": float(r2.mean()), "median_individual_r2": float(np.median(r2))}
    if holdout:
        H = np.array([effects_row(profiles[i], sizes) for i in holdout])
        ph, oh = (H @ beta).T, Y[use][:, holdout]
        if len(holdout) >= 2:
            top = oh.max(axis=1, keepdims=True)
            unique = (oh == top).sum(axis=1) == 1
            hits = ph.argmax(axis=1) == oh.argmax(axis=1)
            fit["holdout_hit_rate_pct"] = float(hits[unique].mean() * 100) if unique.any() else None
            fit["holdout_n"] = int(unique.sum())
        if len(holdout) >= 3:
            ht = st.kendalltau(oh.mean(axis=0), ph.mean(axis=0))
            fit["holdout_tau"] = float(ht[0])
    best_levels = [x["best_level"] for x in out_attrs]
    best_utility = float(beta[0].mean() + sum(max(lv["utility"] for lv in x["levels"]) for x in out_attrs))
    dg = design_diagnostics([profiles[i] for i in est], sizes)
    out = {"n": n, "n_answered": int(complete.sum()), "n_flat": int(flat.sum()), "n_cards": len(cards),
           "n_holdout": len(holdout), "n_params": k, "constant": float(beta[0].mean()),
           "design": {"calibration_cards": dg["runs"], "d_efficiency_pct": dg["d_efficiency"],
                      "max_abs_corr": dg["max_abs_corr"], "balanced": dg["balanced"], "duplicates": dg["duplicates"]},
           "attributes": out_attrs, "fit": fit,
           "best_profile": {"levels": best_levels, "utility": best_utility},
           "rule": "效应编码最小二乘逐人估计；重要性 = 属性效用极差 ÷ 全部极差之和，按受访者平均"}
    scenarios = []
    for sc in a.get("scenarios") or []:
        idx, err = conjoint_profiles([sc.get("levels")], attrs)
        if err:
            return {"error": f"市场模拟方案“{sc.get('name')}”：{err}"}
        u = beta[0] + sum(utils[j][:, idx[0][j]] for j in range(len(attrs)))
        scenarios.append((str(sc.get("name") or f"方案{len(scenarios) + 1}"), idx[0], u))
    if scenarios:
        U = np.column_stack([u for _, _, u in scenarios])
        win = (U == U.max(axis=1, keepdims=True)).astype(float)
        first = (win / win.sum(axis=1, keepdims=True)).mean(axis=0) * 100
        positive = (U > 0).all(axis=1)
        btl = (U[positive] / U[positive].sum(axis=1, keepdims=True)).mean(axis=0) * 100 if positive.any() else None
        out["scenarios"] = [{"name": name, "levels": [attrs[j]["levels"][li] for j, li in enumerate(lv)],
                             "utility": float(u.mean()), "first_choice_pct": float(first[i]),
                             "btl_pct": None if btl is None else float(btl[i])}
                            for i, (name, lv, u) in enumerate(scenarios)]
        out["scenario_rule"] = "最大效用法：每位受访者选效用最高的方案（并列平分）；BTL 法：按效用占比分配"
    notes = []
    if flat.sum():
        notes.append(f"{int(flat.sum())} 人所有卡片打同一分，无法估计，已剔除")
    if fit["mean_individual_r2"] < 0.5:
        notes.append("个人模型平均 R² 低于 0.5，受访者可能没有认真比较卡片")
    if len(est) < 1.5 * k:
        notes.append(f"估计用卡片 {len(est)} 张，不到参数个数 {k} 的 1.5 倍，个人效用估计不稳定")
    if dg["d_efficiency"] < 80:
        notes.append(f"估计卡片的 D 效率只有 {dg['d_efficiency']:.1f}%，各属性的效用估计会互相干扰，建议用正交设计重做卡片")
    if notes:
        out["warning"] = "；".join(notes)
    return out


# ───────────────────────── 联合分析卡片设计 ─────────────────────────

def _gf(q: int):
    """GF(q) 的加法、乘法（q = 2、3、5 为素数域；q = 4 用 α² = α + 1，元素 0、1、α=2、α²=3）。"""
    if q in (2, 3, 5):
        return (lambda a, b: (a + b) % q), (lambda a, b: (a * b) % q)
    if q == 4:
        log = {1: 0, 2: 1, 3: 2}
        exp = {0: 1, 1: 2, 2: 3}
        return (lambda a, b: a ^ b), (lambda a, b: 0 if a == 0 or b == 0 else exp[(log[a] + log[b]) % 3])
    raise ValueError(q)


def _rao_hamming(q: int, m: int) -> list[list[int]]:
    """OA(q^m, (q^m−1)/(q−1), q, 2)：行是 GF(q)^m 的全部向量，列是首个非零分量为 1 的向量，元素为内积。"""
    add, mul = _gf(q)
    vectors = list(itertools.product(range(q), repeat=m))
    cols = [c for c in vectors if any(c) and next(x for x in c if x) == 1]
    rows = []
    for x in vectors:
        row = []
        for c in cols:
            s = 0
            for xi, ci in zip(x, c):
                s = add(s, mul(xi, ci))
            row.append(s)
        rows.append(row)
    return rows


def _split_four(rows, levels, how_many):
    """把前 how_many 个 4 水平列各换成 3 个 2 水平列（4 水平 s → s 的两个二进制位及其异或），仍是正交表。"""
    out_rows = [list(r) for r in rows]
    out_levels = list(levels)
    done = 0
    for c in range(len(levels) - 1, -1, -1):
        if done >= how_many:
            break
        if out_levels[c] != 4:
            continue
        for r in out_rows:
            s = r.pop(c)
            r[c:c] = [s >> 1, s & 1, (s >> 1) ^ (s & 1)]
        out_levels[c:c + 1] = [2, 2, 2]
        done += 1
    return out_rows, out_levels


def _merge_line(rows):
    """L8 的前两列及其和组成一条“线”，合成一个 4 水平列：L8(4¹2⁴)。"""
    out = []
    for r in rows:
        out.append([2 * r[0] + r[1]] + [x for i, x in enumerate(r) if i not in (0, 1, 2)])
    return out, [4] + [2] * (len(rows[0]) - 3)


def _pb12():
    gen = [1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0]
    rows = [gen[-i:] + gen[:-i] if i else list(gen) for i in range(11)]
    return rows + [[0] * 11]


_L18 = """\
11111111 11222222 11333333 12112233 12223311 12331122 13121323 13232131 13313212
21133221 21211332 21322113 22123132 22231213 22312321 23132312 23213123 23321231"""


def orthogonal_arrays() -> list[tuple[str, list[list[int]], list[int]]]:
    """候选正交表：(名称, 行, 各列水平数)，按试验次数从小到大。"""
    arrays = []
    l4 = _rao_hamming(2, 2)
    arrays.append(("L4(2^3)", l4, [2] * 3))
    l8 = _rao_hamming(2, 3)
    # Rao–Hamming 的 L8 列顺序：(0,0,1)、(0,1,0)、(0,1,1)……；把 x1、x2、x1+x2 三列挪到最前再合并
    cols = [c for c in itertools.product(range(2), repeat=3) if any(c) and next(x for x in c if x) == 1]
    order = [cols.index((1, 0, 0)), cols.index((0, 1, 0)), cols.index((1, 1, 0))]
    order += [i for i in range(7) if i not in order]
    l8 = [[r[i] for i in order] for r in l8]
    arrays.append(("L8(2^7)", l8, [2] * 7))
    merged, lv = _merge_line(l8)
    arrays.append(("L8(4^1 2^4)", merged, lv))
    arrays.append(("L9(3^4)", _rao_hamming(3, 2), [3] * 4))
    arrays.append(("L12(2^11)", _pb12(), [2] * 11))
    l16_4 = _rao_hamming(4, 2)
    arrays.append(("L16(4^5)", l16_4, [4] * 5))
    for k in range(1, 5):
        rows, lv = _split_four(l16_4, [4] * 5, k)
        arrays.append((f"L16(4^{5 - k} 2^{3 * k})", rows, lv))
    arrays.append(("L16(2^15)", _rao_hamming(2, 4), [2] * 15))
    l18 = [[int(ch) - 1 for ch in row] for row in _L18.split()]
    arrays.append(("L18(2^1 3^7)", l18, [2] + [3] * 7))
    arrays.append(("L25(5^6)", _rao_hamming(5, 2), [5] * 6))
    arrays.append(("L27(3^13)", _rao_hamming(3, 3), [3] * 13))
    return arrays


def is_orthogonal(rows: list[list[int]], levels: list[int]) -> bool:
    """强度 2 的（比例频数）正交性：任意两列的水平组合频数 = 两列各自频数之积 ÷ 行数。"""
    n = len(rows)
    for i, j in itertools.combinations(range(len(levels)), 2):
        ci, cj, pair = {}, {}, {}
        for r in rows:
            ci[r[i]] = ci.get(r[i], 0) + 1
            cj[r[j]] = cj.get(r[j], 0) + 1
            pair[(r[i], r[j])] = pair.get((r[i], r[j]), 0) + 1
        for a in ci:
            for b in cj:
                if pair.get((a, b), 0) * n != ci[a] * cj[b]:
                    return False
    return True


def _coding(size: int):
    """各水平的正交化对比编码（水平均衡时列均值 0、方差 1，正交设计的信息矩阵为 N·I）。"""
    import numpy as np
    E = np.array([effects_row([li], [size])[1:] for li in range(size)])
    G = E.T @ E / size
    w, V = np.linalg.eigh(G)
    return E @ V @ np.diag(w ** -0.5) @ V.T


def design_diagnostics(profiles: list[list[int]], sizes: list[int]) -> dict:
    import numpy as np
    codes = [_coding(s) for s in sizes]
    X = np.array([[1.0] + [v for li, c in zip(prof, codes) for v in c[li]] for prof in profiles])
    n, p = X.shape
    sign, logdet = np.linalg.slogdet(X.T @ X)
    d_eff = 100 * math.exp(logdet / p) / n if sign > 0 else 0.0
    owner = [j for j, s in enumerate(sizes) for _ in range(s - 1)]
    worst = 0.0
    if n > 2:
        Z = X[:, 1:]
        sd = Z.std(axis=0)
        ok = sd > 0
        R = np.corrcoef(Z[:, ok], rowvar=False) if ok.sum() > 1 else np.eye(1)
        own = [o for o, k in zip(owner, ok) if k]
        for i, j in itertools.combinations(range(len(own)), 2):
            if own[i] != own[j]:
                worst = max(worst, abs(float(R[i, j])))
    balance = []
    for j, s in enumerate(sizes):
        counts = [sum(1 for prof in profiles if prof[j] == li) for li in range(s)]
        balance.append(counts)
    return {"runs": n, "params": p, "d_efficiency": d_eff, "max_abs_corr": worst,
            "level_counts": balance, "balanced": all(len(set(c)) == 1 for c in balance),
            "duplicates": len(profiles) - len({tuple(x) for x in profiles})}


def _assign(sizes: list[int], col_levels: list[int], rng: random.Random):
    """给每个属性找一列：列的水平数 ≥ 属性水平数，优先相等；返回列号列表或 None。"""
    cols = list(range(len(col_levels)))
    rng.shuffle(cols)
    free = set(cols)
    out = [None] * len(sizes)
    for j in sorted(range(len(sizes)), key=lambda x: -sizes[x]):
        options = sorted((c for c in cols if c in free and col_levels[c] >= sizes[j]),
                         key=lambda c: (col_levels[c] - sizes[j], cols.index(c)))
        if not options:
            return None
        out[j] = options[0]
        free.discard(options[0])
    return out


def _d_optimal(sizes: list[int], runs: int, rng: random.Random, starts: int = 6):
    """Fedorov 交换算法：从全因子（太大时随机抽 4000 个）候选里挑 runs 张卡片使 |X'X| 最大，卡片不重复。"""
    import numpy as np
    codes = [_coding(s) for s in sizes]
    total = math.prod(sizes)
    if total <= 4000:
        cands = [list(c) for c in itertools.product(*[range(s) for s in sizes])]
    else:
        seen = set()
        while len(seen) < 4000:
            seen.add(tuple(rng.randrange(s) for s in sizes))
        cands = [list(c) for c in sorted(seen)]
    Xc = np.array([[1.0] + [v for li, c in zip(prof, codes) for v in c[li]] for prof in cands])
    best = None
    for _ in range(starts):
        idx = rng.sample(range(len(cands)), runs)
        for _it in range(40):
            changed = False
            for pos in range(runs):
                X = Xc[idx]
                M = X.T @ X + 1e-9 * np.eye(X.shape[1])
                Minv = np.linalg.inv(M)
                xi = Xc[idx[pos]]
                di = xi @ Minv @ xi
                dc = np.einsum("ij,jk,ik->i", Xc, Minv, Xc)
                dic = Xc @ Minv @ xi
                gain = dc - di - (dc * di - dic ** 2)
                gain[idx] = -np.inf
                j = int(np.argmax(gain))
                if gain[j] > 1e-9:
                    idx[pos] = j
                    changed = True
            if not changed:
                break
        sign, logdet = np.linalg.slogdet(Xc[idx].T @ Xc[idx])
        score = logdet if sign > 0 else -np.inf
        if best is None or score > best[0]:
            best = (score, list(idx))
    return [cands[i] for i in best[1]]


def conjoint_design(attrs: list[dict], *, holdout: int = 2, max_cards: int = 20, seed: int = SEED) -> dict:
    """为评分型联合分析生成卡片：正交表优先，放不下时 D 最优；另抽检验卡。"""
    sizes = [len(at.get("levels") or []) for at in attrs]
    if len(attrs) < 2 or min(sizes) < 2:
        raise ValueError("至少 2 个属性、每个属性至少 2 个水平")
    if max(sizes) > 5:
        raise ValueError("单个属性最多 5 个水平（水平越多，每个水平分到的卡片越少，效用估计越不稳）")
    params = 1 + sum(s - 1 for s in sizes)
    rng = random.Random(seed)
    chosen, method = None, None
    # 候选正交表打分：卡片数 + 2×“并水平”的属性个数（列的水平多于属性时把多出的水平并到已有水平上，
    # 仍正交但水平不均衡），取分最低的；同分取卡片少的
    best = None
    for name, rows, levels in orthogonal_arrays():
        n = len(rows)
        if n < params + 2 or n > max_cards:
            continue
        for _try in range(6):
            cols = _assign(sizes, levels, rng)
            if cols is None:
                break
            perms = [rng.sample(range(levels[c]), levels[c]) for c in cols]
            profs = [[perm[r[c]] % sizes[j] for j, (c, perm) in enumerate(zip(cols, perms))] for r in rows]
            if len({tuple(p) for p in profs}) == len(profs):
                collapsed = sum(levels[c] > s for c, s in zip(cols, sizes))
                score = (n + 2 * collapsed, n)
                if best is None or score < best[0]:
                    best = (score, profs, f"正交表 {name}" + (f"（{collapsed} 个属性并水平）" if collapsed else ""))
                break
    if best:
        chosen, method = best[1], best[2]
    if chosen is None:
        total = math.prod(sizes)
        if total <= max_cards and total >= params + 2:
            chosen, method = [list(c) for c in itertools.product(*[range(s) for s in sizes])], "全因子设计"
        else:
            lo = params + 2
            if lo > max_cards:
                raise ValueError(f"要估 {params} 个参数，至少需要 {lo} 张卡片，超过上限 {max_cards}；请减少属性或水平")
            runs = max(range(lo, max_cards + 1), key=lambda n: (sum(n % s == 0 for s in sizes), -n))
            chosen, method = _d_optimal(sizes, runs, rng), f"D 最优设计（{runs} 张）"
    rng.shuffle(chosen)
    taken = {tuple(p) for p in chosen}
    extra = []
    pool = [list(c) for c in itertools.product(*[range(s) for s in sizes]) if tuple(c) not in taken] \
        if math.prod(sizes) <= 20000 else []
    while len(extra) < holdout:
        cand = pool.pop(rng.randrange(len(pool))) if pool else [rng.randrange(s) for s in sizes]
        if tuple(cand) not in taken:
            taken.add(tuple(cand))
            extra.append(cand)
        if not pool and len(taken) >= math.prod(sizes):
            break
    diag = design_diagnostics(chosen, sizes)
    cards = []
    for no, prof in enumerate(chosen + extra, start=1):
        text = "；".join(f"{at['name']}：{at['levels'][li]}" for at, li in zip(attrs, prof))
        cards.append({"no": no, "levels": prof, "text": text, "holdout": no > len(chosen)})
    return {"schema": "paperkit.survey.conjoint_design/v1", "method": method, "seed": seed,
            "attributes": [{"name": at["name"], "levels": list(at["levels"])} for at in attrs],
            "params": params, "cards": cards, "holdout_cards": [c["no"] for c in cards if c["holdout"]],
            "diagnostics": diag}


def design_questions(design: dict, qid: str, rows_per_question: int = 9, scale=(1, 10)) -> tuple[list[dict], dict]:
    """把卡片排成一道或几道矩阵量表题（每道不超过 rows_per_question 行），并给出分析计划条目。"""
    m = re.match(r"^([A-Za-z]+)(\d+)$", qid)
    prefix, start = (m.group(1), int(m.group(2))) if m else (qid, None)
    cards = design["cards"]
    chunks = [cards[i:i + rows_per_question] for i in range(0, len(cards), rows_per_question)]
    questions, ids = [], []
    for k, chunk in enumerate(chunks):
        q_id = f"{prefix}{start + k}" if start is not None else (qid if k == 0 else f"{qid}_{k + 1}")
        ids.append(q_id)
        questions.append({
            "id": q_id, "type": "matrix_scale",
            "text": "请根据下面每张产品卡片描述的组合，给出您购买（使用）的可能性打分"
                    + ("（续）" if k else ""),
            "scale": {"min": scale[0], "max": scale[1],
                      "labels": {str(scale[0]): "完全不会购买", str(scale[1]): "一定会购买"}},
            "measure": "interval", "role": "conjoint",
            "rows": [{"id": f"{q_id}_r{i + 1}", "label": f"卡片{c['no']}：{c['text']}"} for i, c in enumerate(chunk)]})
    entry = {"type": "conjoint", "ratings": ids if len(ids) > 1 else ids[0],
             "attributes": design["attributes"], "profiles": [c["levels"] for c in cards],
             "holdout_cards": design["holdout_cards"]}
    return questions, entry


# ───────────────────────── 结构方程模型 ─────────────────────────

def sem_spec(a: dict, constructs: dict) -> tuple[dict, list, list, dict, str | None]:
    """计划条目 → (潜变量→题项（第一个为标定题项）, 路径[(源, 目标)], 额外相关[(u, v)], 显示名, 错误)。

    latent 的值可以是题项列表，也可以是问卷里的构念名（取该构念的全部题项）。
    paths 写成 [{"dv": "BI", "ivs": ["PE", "EE"]}] 或 [["BI", ["PE", "EE"]]]；不在 latent 里的变量按观测变量处理。
    """
    latent, labels = {}, {}
    for name, spec in (a.get("latent") or {}).items():
        if isinstance(spec, str):
            items = list(constructs.get(spec) or [])
            labels[name] = spec
        else:
            items = [x for x in spec or [] if x]
        latent[str(name)] = items
    labels.update({str(k): str(v) for k, v in (a.get("labels") or {}).items()})
    paths = []
    for p in a.get("paths") or []:
        if isinstance(p, dict):
            dv, ivs = p.get("dv"), p.get("ivs")
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            dv, ivs = p
        else:
            return latent, [], [], labels, f"路径写法不对：{p!r}"
        for iv in [ivs] if isinstance(ivs, str) else ivs or []:
            if (iv, dv) not in paths:
                paths.append((iv, dv))
    covary = [tuple(c) for c in a.get("covary") or [] if isinstance(c, (list, tuple)) and len(c) == 2]
    if not latent:
        return latent, paths, covary, labels, "没有给出潜变量（latent）"
    seen = {}
    for name, items in latent.items():
        if len(items) < 2:
            return latent, paths, covary, labels, f"潜变量 {name} 只有 {len(items)} 个题项，至少需要 2 个（建议 3 个以上）"
        for x in items:
            if x in seen:
                return latent, paths, covary, labels, f"题项 {x} 同时属于 {seen[x]} 和 {name}"
            seen[x] = name
    for s, d in paths:
        if s == d:
            return latent, paths, covary, labels, f"路径 {s}→{d} 指向自己"
        for v in (s, d):
            if v in seen:
                return latent, paths, covary, labels, f"{v} 是潜变量 {seen[v]} 的题项，不能直接放进结构路径"
    if a.get("type") == "sem" and not paths:
        return latent, paths, covary, labels, "结构方程需要路径（paths）；只检验测量模型请用 cfa"
    return latent, paths, covary, labels, None


def sem_counts(latent: dict, paths: list, covary: list) -> dict:
    """模型规模：观测变量数 p、自由参数数 q、自由度 df = p(p+1)/2 − q（纯 Python，测样本量时也用）。"""
    indicators = [x for items in latent.values() for x in items]
    observed = []
    for s, d in paths:
        for v in (s, d):
            if v not in latent and v not in observed:
                observed.append(v)
    p = len(indicators) + len(observed)
    endo = {d for _, d in paths}
    struct = list(latent) + observed
    exo = [v for v in struct if v not in endo]
    q = (sum(len(items) - 1 for items in latent.values()) + len(paths) + len(indicators)
         + len(exo) + len(exo) * (len(exo) - 1) // 2 + len([v for v in struct if v in endo]) + len(covary))
    return {"p": p, "q": q, "df": p * (p + 1) // 2 - q, "observed": observed}


class SemModel:
    """RAM 形式：变量 = 观测变量（题项、结构里的观测变量）+ 潜变量；Σ = F(I−A)⁻¹P(I−A)⁻ᵀFᵀ。"""

    def __init__(self, latent: dict, paths: list, covary: list):
        import numpy as np
        self.latent = latent
        indicators = [x for items in latent.values() for x in items]
        observed = sem_counts(latent, paths, covary)["observed"]
        self.indicators = indicators
        self.manifest = indicators + observed
        self.names = self.manifest + list(latent)
        self.idx = {n: i for i, n in enumerate(self.names)}
        self.m, self.n = len(self.manifest), len(self.names)
        self.paths = list(paths)
        endo = {d for _, d in paths}
        struct = list(latent) + observed
        self.exo = [v for v in struct if v not in endo]
        self.endo = [v for v in struct if v in endo]
        self.A0 = np.zeros((self.n, self.n))
        self.free = []           # (矩阵, 行, 列, 角色, 变量1, 变量2)
        ix = self.idx
        for lat, items in latent.items():
            self.A0[ix[items[0]], ix[lat]] = 1.0
            for x in items[1:]:
                self.free.append(("A", ix[x], ix[lat], "loading", lat, x))
        for s, d in paths:
            self.free.append(("A", ix[d], ix[s], "path", s, d))
        for x in indicators:
            self.free.append(("P", ix[x], ix[x], "error", x, x))
        for v in self.exo:
            self.free.append(("P", ix[v], ix[v], "variance", v, v))
        for i, u in enumerate(self.exo):
            for w in self.exo[i + 1:]:
                self.free.append(("P", max(ix[u], ix[w]), min(ix[u], ix[w]), "covariance", u, w))
        for v in self.endo:
            self.free.append(("P", ix[v], ix[v], "residual", v, v))
        for u, w in covary:
            self.free.append(("P", max(ix[u], ix[w]), min(ix[u], ix[w]), "residual_cov", u, w))
        self.q = len(self.free)
        self.df = self.m * (self.m + 1) // 2 - self.q
        self.is_var = np.array([f[1] == f[2] and f[0] == "P" for f in self.free])

    def matrices(self, theta):
        import numpy as np
        A = self.A0.copy()
        P = np.zeros((self.n, self.n))
        for value, (mat, i, j, *_rest) in zip(theta, self.free):
            if mat == "A":
                A[i, j] = value
            else:
                P[i, j] = P[j, i] = value
        return A, P

    def implied(self, theta):
        import numpy as np
        A, P = self.matrices(theta)
        B = np.linalg.inv(np.eye(self.n) - A)
        return A, P, B, B @ P @ B.T

    def objective(self, theta, S, logdet_s):
        """F_ML = ln|Σ| + tr(SΣ⁻¹) − ln|S| − p 及其解析梯度。"""
        import numpy as np
        m = self.m
        try:
            A, P, B, C = self.implied(theta)
            L = np.linalg.cholesky(C[:m, :m])
        except np.linalg.LinAlgError:
            return 1e10, np.zeros(self.q)
        Linv = np.linalg.inv(L)
        W = Linv.T @ Linv
        value = 2 * np.log(np.diag(L)).sum() + float(np.trace(S @ W)) - logdet_s - m
        H = np.zeros((self.n, self.n))
        H[:m, :m] = W - W @ S @ W
        GA = 2 * (C @ H @ B).T
        GP = B.T @ H @ B
        grad = np.array([GA[i, j] if mat == "A" else (GP[i, j] if i == j else 2 * GP[i, j])
                         for mat, i, j, *_rest in self.free])
        return float(value), grad

    def delta(self, theta):
        """∂Σ/∂θ（每个参数一个 p×p 矩阵）与全部变量的隐含协方差。"""
        import numpy as np
        A, P, B, C = self.implied(theta)
        m = self.m
        D = np.empty((self.q, m, m))
        for k, (mat, i, j, *_rest) in enumerate(self.free):
            if mat == "A":
                o = np.outer(B[:m, i], C[j, :m])
                D[k] = o + o.T
            else:
                o = np.outer(B[:m, i], B[:m, j])
                D[k] = o if i == j else o + o.T
        return D, C

    def information(self, theta):
        """期望信息矩阵（不含样本量）：Δᵀ(W⊗W)Δ，即 F_ML 的期望 Hessian。"""
        import numpy as np
        D, C = self.delta(theta)
        W = np.linalg.inv(C[:self.m, :self.m])
        WDW = np.einsum("ab,kbc,cd->kad", W, D, W)
        return np.einsum("kab,lab->kl", D, WDW)

    def start(self, S, simple: bool = False):
        """起始值：载荷用 fabin 式比值、残差取方差一半、潜变量方差用标定题项的协方差估计、路径为 0。"""
        import numpy as np
        ix = self.idx
        var = np.diag(S)
        lam, phi = {}, {}
        for lat, items in self.latent.items():
            mk = ix[items[0]]
            for x in items[1:]:
                xi = ix[x]
                ratios = [S[xi, ix[o]] / S[mk, ix[o]] for o in items[1:]
                          if o != x and abs(S[mk, ix[o]]) > 1e-8 * var[mk]]
                guess = float(np.median(ratios)) if ratios else (S[xi, mk] / var[mk] if var[mk] else 1.0)
                lam[(lat, x)] = 1.0 if simple or not np.isfinite(guess) else float(np.clip(guess, -3, 3))
            covs = [S[mk, ix[x]] / lam[(lat, x)] for x in items[1:] if abs(lam[(lat, x)]) > 1e-3]
            est = float(np.mean(covs)) if covs and not simple else 0.6 * var[mk]
            phi[lat] = float(np.clip(est, 0.05 * var[mk], 0.95 * var[mk]))
        proxy = {lat: ix[items[0]] for lat, items in self.latent.items()}
        proxy.update({v: ix[v] for v in self.manifest if v not in self.indicators})

        def var_of(v):
            return phi[v] if v in phi else float(var[ix[v]])
        theta = []
        for mat, i, j, role, u, w in self.free:
            if role == "loading":
                theta.append(lam[(u, w)])
            elif role == "path":
                theta.append(0.0)
            elif role == "error":
                lat = next(name for name, items in self.latent.items() if w in items)
                l2 = 1.0 if self.latent[lat][0] == w else lam[(lat, w)] ** 2
                theta.append(float(max(var[i] - l2 * phi[lat], 0.2 * var[i])))
            elif role == "variance":
                theta.append(var_of(u))
            elif role == "residual":
                theta.append(0.6 * var_of(u))
            elif role == "covariance":
                c = float(S[proxy[u], proxy[w]]) if not simple else 0.0
                bound = 0.6 * math.sqrt(var_of(u) * var_of(w))
                theta.append(float(np.clip(c, -bound, bound)))
            else:
                theta.append(0.0)
        return np.array(theta, dtype=float)

    def lower_bounds(self, S):
        import numpy as np
        scale = float(np.mean(np.diag(S)))
        return np.where(self.is_var, 1e-6 * scale, -np.inf)


def fit_sem(model: SemModel, S, N: int) -> dict:
    """极大似然估计：L-BFGS-B 求解后用 Fisher 得分法收尾；返回 θ、F、梯度、协方差矩阵等。"""
    import numpy as np
    from scipy.optimize import minimize
    sign, logdet_s = np.linalg.slogdet(S)
    if sign <= 0:
        raise ValueError("样本协方差矩阵不正定（有常数列或完全共线的题项）")
    low = model.lower_bounds(S)
    bounds = [(lo if np.isfinite(lo) else None, None) for lo in low]
    best = None
    for simple in (False, True):
        res = minimize(model.objective, model.start(S, simple), args=(S, logdet_s), jac=True, method="L-BFGS-B",
                       bounds=bounds, options={"maxiter": 20000, "maxfun": 40000, "ftol": 1e-15, "gtol": 1e-10,
                                               "maxcor": 30})
        theta = res.x.copy()
        value, grad = model.objective(theta, S, logdet_s)
        for _ in range(60):                         # Fisher 得分法：θ ← θ − I⁻¹∇F（步长减半保证下降）
            try:
                step = np.linalg.solve(model.information(theta), grad)
            except np.linalg.LinAlgError:
                break
            t, moved = 1.0, False
            while t > 1e-6:
                cand = np.maximum(theta - t * step, low)
                v2, g2 = model.objective(cand, S, logdet_s)
                if v2 <= value + 1e-15:
                    moved = True
                    break
                t /= 2
            if not moved:
                break
            small = float(np.max(np.abs(cand - theta))) < 1e-12
            theta, value, grad = cand, v2, g2
            if small:
                break
        free_grad = np.where(theta <= low + 1e-12, np.minimum(grad, 0), grad)
        if best is None or value < best["F"] - 1e-12:
            best = {"theta": theta, "F": value, "grad": free_grad, "iterations": int(res.nit)}
        if float(np.max(np.abs(free_grad))) < 1e-6:
            break
    info = model.information(best["theta"])
    try:
        cov = 2.0 / (N - 1) * np.linalg.inv(info)
        cond = float(np.linalg.cond(info))
    except np.linalg.LinAlgError:
        cov, cond = np.full((model.q, model.q), np.nan), float("inf")
    best.update(cov=cov, info_cond=cond, logdet_s=logdet_s,
                converged=bool(float(np.max(np.abs(best["grad"]))) < 1e-4),
                at_bound=[i for i, (t, lo) in enumerate(zip(best["theta"], low)) if np.isfinite(lo) and t <= lo * 1.0001])
    return best


def _ncx2_lambda(chi2: float, df: int, prob: float) -> float:
    """非中心 χ² 的非中心参数 λ，使 P(χ²_df(λ) ≤ chi2) = prob（cdf 随 λ 递减）；λ=0 时已不到 prob 返回 0。"""
    from scipy import stats as st
    from scipy.optimize import brentq
    if st.chi2.cdf(chi2, df) < prob:
        return 0.0
    hi = max(chi2, 1.0)
    while st.ncx2.cdf(chi2, df, hi) > prob:
        hi *= 2
        if hi > 1e7:
            return hi
    return float(brentq(lambda lam: st.ncx2.cdf(chi2, df, lam) - prob, 1e-10, hi, xtol=1e-10))


FIT_RULES = {  # 指标: (方向, 良好, 可接受)
    "chi2_df": ("le", 3.0, 5.0), "rmsea": ("le", 0.05, 0.08), "srmr": ("le", 0.05, 0.08),
    "gfi": ("ge", 0.95, 0.90), "agfi": ("ge", 0.90, 0.80), "cfi": ("ge", 0.95, 0.90), "tli": ("ge", 0.95, 0.90),
    "nfi": ("ge", 0.95, 0.90), "ifi": ("ge", 0.95, 0.90),
}
FIT_NAMES = {"chi2_df": "χ²/df", "rmsea": "RMSEA", "srmr": "SRMR", "gfi": "GFI", "agfi": "AGFI", "cfi": "CFI",
             "tli": "TLI", "nfi": "NFI", "ifi": "IFI"}


def fit_indices(S, Sigma, N: int, df: int, F: float) -> dict:
    import numpy as np
    from scipy import stats as st
    p = S.shape[0]
    chi2 = (N - 1) * F
    sign, logdet_s = np.linalg.slogdet(S)
    f0 = float(np.log(np.diag(S)).sum() - logdet_s)
    chi2_0, df0 = (N - 1) * f0, p * (p - 1) // 2
    W = np.linalg.inv(Sigma)
    WS = W @ S
    I = np.eye(p)
    gfi = 1 - float(np.trace((WS - I) @ (WS - I)) / np.trace(WS @ WS))
    d = np.sqrt(np.diag(S))
    resid = (S - Sigma) / np.outer(d, d)
    srmr = math.sqrt(float((resid[np.tril_indices(p)] ** 2).mean()))
    out = {"chi2": chi2, "df": df, "p": float(st.chi2.sf(chi2, df)) if df > 0 else None,
           "chi2_df": chi2 / df if df > 0 else None, "baseline_chi2": chi2_0, "baseline_df": df0,
           "srmr": srmr, "gfi": gfi,
           "agfi": 1 - (p * (p + 1) / (2 * df)) * (1 - gfi) if df > 0 else None,
           "nfi": (chi2_0 - chi2) / chi2_0 if chi2_0 > 0 else None,
           "ifi": (chi2_0 - chi2) / (chi2_0 - df) if chi2_0 - df > 0 else None}
    num, den = max(chi2 - df, 0.0), max(chi2_0 - df0, chi2 - df, 0.0)
    out["cfi"] = 1 - num / den if den > 0 else 1.0
    out["tli"] = ((chi2_0 / df0 - chi2 / df) / (chi2_0 / df0 - 1)) if df > 0 and df0 > 0 and chi2_0 / df0 > 1 else None
    if df > 0:
        out["rmsea"] = math.sqrt(num / (df * (N - 1)))
        lo, hi = _ncx2_lambda(chi2, df, 0.95), _ncx2_lambda(chi2, df, 0.05)
        out["rmsea_ci90"] = [math.sqrt(lo / (df * (N - 1))), math.sqrt(hi / (df * (N - 1)))]
        out["pclose"] = float(st.ncx2.sf(chi2, df, 0.05 ** 2 * df * (N - 1)))
    else:
        out.update(rmsea=0.0, rmsea_ci90=None, pclose=None)
    judged, failed = {}, []
    for key, (way, good, ok) in FIT_RULES.items():
        value = out.get(key)
        if value is None:
            continue
        better = (lambda x, c: x <= c) if way == "le" else (lambda x, c: x >= c)
        level = "良好" if better(value, good) else "可接受" if better(value, ok) else "不达标"
        judged[key] = level
        if level == "不达标" and key in {"chi2_df", "rmsea", "srmr", "cfi", "tli"}:
            failed.append(FIT_NAMES[key])
    out["judgement"] = judged
    out["thresholds"] = {k: {"direction": "≤" if w == "le" else "≥", "good": g, "acceptable": a}
                         for k, (w, g, a) in FIT_RULES.items()}
    out["acceptable"] = not failed
    out["failed"] = failed
    return out


def _std_vector(model: SemModel, theta, report: list) -> "np.ndarray":
    """报告项的标准化值：载荷、路径（β）、相关、残差相关。"""
    import numpy as np
    A, P, B, C = model.implied(theta)
    sd = np.sqrt(np.clip(np.diag(C), 1e-300, None))
    ix = model.idx
    vals = []
    for kind, u, w in report:
        if kind == "loading":
            vals.append(A[ix[w], ix[u]] * sd[ix[u]] / sd[ix[w]])
        elif kind == "path":
            vals.append(A[ix[w], ix[u]] * sd[ix[u]] / sd[ix[w]])
        elif kind == "covariance":
            vals.append(P[ix[u], ix[w]] / (sd[ix[u]] * sd[ix[w]]))
        else:   # residual_cov：残差之间的相关
            vals.append(P[ix[u], ix[w]] / math.sqrt(max(P[ix[u], ix[u]] * P[ix[w], ix[w]], 1e-300)))
    return np.array(vals)


def _hypotheses(a: dict) -> dict:
    out = {}
    raw = a.get("hypotheses") or []
    if isinstance(raw, dict):
        raw = [{"id": k, "from": v[0], "to": v[1], "sign": v[2] if len(v) > 2 else None} for k, v in raw.items()]
    for h in raw:
        if isinstance(h, dict) and h.get("from") and h.get("to"):
            out[(h["from"], h["to"])] = {"id": h.get("id"), "sign": h.get("sign")}
    return out


def a_sem(ctx, a: dict) -> dict:
    import numpy as np
    import pandas as pd
    from scipy import stats as st
    latent, paths, covary, labels, err = sem_spec(a, S.constructs(ctx.q))
    if err:
        return {"error": err}
    model = SemModel(latent, paths, covary)
    for v in model.manifest:
        if v not in ctx.df.columns:
            return {"error": f"数据里没有变量 {v}"}
    if model.df < 0:
        return {"error": f"模型不可识别：自由参数 {model.q} 个，多于协方差矩阵的 {model.m * (model.m + 1) // 2} 个不重复元素"}
    frame = pd.DataFrame({v: _numeric(ctx, v) for v in model.manifest}).dropna()
    N = int(len(frame))
    if N < max(50, model.q + 10):
        return {"error": f"有效样本 {N} 份，估计 {model.q} 个参数太少"}
    X = frame.to_numpy(dtype=float)
    Smat = np.cov(X, rowvar=False, ddof=1)
    try:
        fit = fit_sem(model, Smat, N)
    except ValueError as exc:
        return {"error": str(exc)}
    theta, cov = fit["theta"], fit["cov"]
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    A, P, B, C = model.implied(theta)
    Sigma = C[:model.m, :model.m]
    sd_all = np.sqrt(np.clip(np.diag(C), 1e-300, None))
    ix = model.idx

    def lab(v):
        if v in labels:
            return labels[v]
        if v in latent:
            return v
        return _row_label(ctx, v) if v in ctx.vars else ctx.label(v)

    # 要报告标准化值的项（含固定为 1 的标定载荷），用数值雅可比做 delta 法标准误
    report = [("loading", lat, x) for lat, items in latent.items() for x in items]
    report += [("path", s, d) for s, d in paths]
    report += [("covariance", u, w) for _m, _i, _j, role, u, w in model.free if role == "covariance"]
    report += [("residual_cov", u, w) for _m, _i, _j, role, u, w in model.free if role == "residual_cov"]
    std = _std_vector(model, theta, report)
    J = np.zeros((len(report), model.q))
    for k in range(model.q):
        h = 1e-6 * max(1.0, abs(theta[k]))
        up, dn = theta.copy(), theta.copy()
        up[k] += h
        dn[k] -= h
        J[:, k] = (_std_vector(model, up, report) - _std_vector(model, dn, report)) / (2 * h)
    std_se = np.sqrt(np.clip(np.diag(J @ cov @ J.T), 0, None))
    pos = {(role, u, w): k for k, (_m, _i, _j, role, u, w) in enumerate(model.free)}
    z975 = float(st.norm.ppf(0.975))

    def est(role, u, w):
        k = pos.get((role, u, w))
        if k is None:
            return {"b": 1.0, "se": None, "z": None, "p": None, "fixed": True}
        b, s = float(theta[k]), float(se[k])
        z = b / s if s > 0 else None
        return {"b": b, "se": s, "z": z, "p": float(2 * st.norm.sf(abs(z))) if z is not None else None,
                "ci95": [b - z975 * s, b + z975 * s], "fixed": False}
    std_of = {key: (float(v), float(s)) for key, v, s in zip(report, std, std_se)}
    item_r = np.abs(np.corrcoef(X, rowvar=False))
    mcol = {v: i for i, v in enumerate(model.manifest)}
    measurement = {}
    for lat, items in latent.items():
        rows = []
        for x in items:
            e = est("loading", lat, x)
            s, s_se = std_of[("loading", lat, x)]
            rows.append({"item": x, "item_label": lab(x), **e, "std": s, "std_se": s_se,
                         "r2": s ** 2})
        lam = np.array([r["std"] for r in rows])
        cr = float(lam.sum() ** 2 / (lam.sum() ** 2 + (1 - lam ** 2).sum()))
        ave = float((lam ** 2).mean())
        measurement[lat] = {"label": lab(lat), "items": rows, "cr": cr, "ave": ave, "sqrt_ave": math.sqrt(ave)}
    lat_names = list(latent)
    corr = {}
    for i, u in enumerate(lat_names):
        for w in lat_names[i + 1:]:
            corr[(u, w)] = float(C[ix[u], ix[w]] / (sd_all[ix[u]] * sd_all[ix[w]]))
    for u in lat_names:
        others = [abs(v) for (x, y), v in corr.items() if u in (x, y)]
        measurement[u]["max_r_other"] = max(others) if others else None
        measurement[u]["fornell_larcker"] = (measurement[u]["sqrt_ave"] > max(others)) if others else None

    def mono(ix_):
        sub = item_r[np.ix_(ix_, ix_)]
        return float(sub[np.triu_indices(len(ix_), 1)].mean())
    htmt = {}
    for i, u in enumerate(lat_names):
        for w in lat_names[i + 1:]:
            iu, iw = [mcol[x] for x in latent[u]], [mcol[x] for x in latent[w]]
            htmt[f"{lab(u)}｜{lab(w)}"] = float(item_r[np.ix_(iu, iw)].mean() / math.sqrt(mono(iu) * mono(iw)))
    hyp = _hypotheses(a)
    path_rows = []
    for s, d in paths:
        e = est("path", s, d)
        b_std, b_se = std_of[("path", s, d)]
        row = {"from": s, "to": d, "from_label": lab(s), "to_label": lab(d), **e, "beta": b_std, "beta_se": b_se,
               "significant": bool(e["p"] is not None and e["p"] < ctx.alpha)}
        h = hyp.get((s, d))
        if h:
            sign_ok = h.get("sign") not in {"+", "-", "＋", "－"} or (
                (b_std > 0) == (h["sign"] in {"+", "＋"}))
            row.update(hypothesis=h.get("id"), expected_sign=h.get("sign"),
                       supported=bool(row["significant"] and sign_ok))
        path_rows.append(row)
    struct = list(latent) + [v for v in model.manifest if v not in model.indicators]
    endogenous = [{"name": v, "label": lab(v), "r2": float(1 - P[ix[v], ix[v]] / C[ix[v], ix[v]])}
                  for v in model.endo]
    cov_rows = [{"a": u, "b": w, "a_label": lab(u), "b_label": lab(w), **est(role, u, w),
                 "r": std_of[(role, u, w)][0]}
                for _m, _i, _j, role, u, w in model.free if role in {"covariance", "residual_cov"}]
    fitstats = fit_indices(Smat, Sigma, N, model.df, fit["F"])
    out = {"model": a.get("type", "sem"), "estimator": "ML", "n": N, "n_manifest": model.m, "n_params": model.q,
           "df": model.df, "fit": fitstats, "measurement": measurement,
           "latent_correlations": [{"a": u, "b": w, "a_label": lab(u), "b_label": lab(w), "r": v}
                                   for (u, w), v in corr.items()],
           "htmt": htmt, "htmt_max": max(htmt.values()) if htmt else None,
           "convergent_ok": all(m_["cr"] >= 0.7 and m_["ave"] >= 0.5 for m_ in measurement.values()),
           "discriminant_ok": (all(m_["fornell_larcker"] is not False for m_ in measurement.values())
                               and (max(htmt.values()) < 0.85 if htmt else True)),
           "covariances": cov_rows, "converged": fit["converged"], "iterations": fit["iterations"],
           "validity_rule": "CR≥0.7 且 AVE≥0.5 为收敛效度良好；AVE 平方根大于与其他潜变量的相关、HTMT<0.85 为区分效度良好",
           "labels": {v: lab(v) for v in struct}}
    if paths:
        out["paths"] = path_rows
        out["endogenous"] = endogenous
        out.update(_indirect_effects(a, model, theta, cov, paths, lab, std_of, sd_all, ctx.alpha))
    notes = []
    if not fit["converged"]:
        notes.append("估计没有完全收敛，结果仅供参考")
    if fit["at_bound"] or any(abs(r["std"]) > 1 for m_ in measurement.values() for r in m_["items"]):
        notes.append("出现方差估计为 0 或标准化载荷大于 1（Heywood 情形），模型或数据需要检查")
    if fit["info_cond"] > 1e12:
        notes.append("信息矩阵接近奇异，部分参数可能不可识别")
    if N < 200:
        notes.append(f"样本量 {N} 小于 200，结构方程的估计与拟合指标可能不稳定")
    if N < 5 * model.q:
        notes.append(f"样本量与参数之比 {N / model.q:.1f}，低于 5:1")
    short = [lab(lat) for lat, items in latent.items() if len(items) < 3]
    if short:
        notes.append(f"只有 2 个题项的潜变量：{'、'.join(short)}（建议每个潜变量 3 个以上题项）")
    if not fitstats["acceptable"]:
        notes.append(f"拟合指标未达可接受标准：{'、'.join(fitstats['failed'])}")
    if not out["discriminant_ok"]:
        notes.append("区分效度不理想（Fornell–Larcker 或 HTMT 未达标）")
    if notes:
        out["warning"] = "；".join(notes)
    return out


def _indirect_effects(a, model, theta, cov, paths, lab, std_of, sd_all, alpha) -> dict:
    """间接效应：每条中介链的积（delta 法 Sobel 检验 + 蒙特卡洛 95% 置信区间），以及各对变量的总间接效应与总效应。"""
    import numpy as np
    from scipy import stats as st
    path_k = {(s, d): k for k, (_m, _i, _j, role, s, d) in enumerate(model.free) if role == "path"}
    chains = [list(c) for c in a.get("indirect") or [] if isinstance(c, (list, tuple)) and len(c) >= 3]
    if not chains:
        for s, mid in paths:
            for m2, d in paths:
                if m2 == mid and d != s:
                    chains.append([s, mid, d])
    rng = np.random.default_rng(SEED)
    rows = []
    for chain in chains:
        edges = list(zip(chain[:-1], chain[1:]))
        if any(e not in path_k for e in edges):
            rows.append({"chain": chain, "error": "链上有模型里不存在的路径"})
            continue
        ks = [path_k[e] for e in edges]
        vals = theta[ks]
        b = float(np.prod(vals))
        grad = np.array([np.prod(np.delete(vals, i)) for i in range(len(ks))])
        sub = cov[np.ix_(ks, ks)]
        se = float(math.sqrt(max(grad @ sub @ grad, 0.0)))
        draws = rng.multivariate_normal(vals, sub, size=MC_DRAWS, method="cholesky" if np.all(np.linalg.eigvalsh(sub) > 0) else "svd")
        prod = draws.prod(axis=1)
        lo, hi = np.percentile(prod, [2.5, 97.5])
        beta = float(np.prod([std_of[("path", s, d)][0] for s, d in edges]))
        z = b / se if se > 0 else None
        rows.append({"chain": chain, "label": "→".join(lab(v) for v in chain), "b": b, "se": se, "z": z,
                     "p": float(2 * st.norm.sf(abs(z))) if z is not None else None,
                     "ci95": [float(lo), float(hi)], "beta": beta, "significant": bool(lo > 0 or hi < 0)})
    # 总效应：结构部分 T = (I − A_s)⁻¹ − I，总间接效应 = T − A_s；蒙特卡洛抽全部路径参数
    struct = sorted({v for e in paths for v in e}, key=lambda v: model.idx[v])
    si = {v: i for i, v in enumerate(struct)}
    ks = [path_k[e] for e in paths]
    k = len(struct)

    def total(vec):
        As = np.zeros(vec.shape[:-1] + (k, k))
        for col, (s, d) in enumerate(paths):
            As[..., si[d], si[s]] = vec[..., col]
        T = np.linalg.inv(np.eye(k) - As) - np.eye(k)
        return T, T - As
    sub = cov[np.ix_(ks, ks)]
    draws = rng.multivariate_normal(theta[ks], sub, size=MC_DRAWS,
                                    method="cholesky" if np.all(np.linalg.eigvalsh(sub) > 0) else "svd")
    T_hat, ind_hat = total(theta[ks])
    T_mc, ind_mc = total(draws)
    effects = []
    for s in struct:
        for d in struct:
            i, j = si[d], si[s]
            if s == d or abs(ind_hat[i, j]) < 1e-12 and not np.any(np.abs(ind_mc[:, i, j]) > 1e-12):
                continue
            scale = sd_all[model.idx[s]] / sd_all[model.idx[d]]
            lo_i, hi_i = np.percentile(ind_mc[:, i, j], [2.5, 97.5])
            lo_t, hi_t = np.percentile(T_mc[:, i, j], [2.5, 97.5])
            direct = (s, d) in path_k
            d_row = {"b": float(theta[path_k[(s, d)]]), "beta": std_of[("path", s, d)][0]} if direct else None
            if direct:
                k_ = path_k[(s, d)]
                zd = theta[k_] / math.sqrt(cov[k_, k_]) if cov[k_, k_] > 0 else None
                d_row["p"] = float(2 * st.norm.sf(abs(zd))) if zd is not None else None
            sig = bool(lo_i > 0 or hi_i < 0)
            if not sig:
                kind = "间接效应不显著"
            elif not direct:
                kind = "间接效应显著（模型未设直接路径）"
            elif d_row.get("p") is not None and d_row["p"] < alpha:
                kind = "部分中介"
            else:
                kind = "完全中介"
            effects.append({"from": s, "to": d, "from_label": lab(s), "to_label": lab(d), "direct": d_row,
                            "indirect": {"b": float(ind_hat[i, j]), "beta": float(ind_hat[i, j] * scale),
                                         "ci95": [float(lo_i), float(hi_i)], "significant": sig},
                            "total": {"b": float(T_hat[i, j]), "beta": float(T_hat[i, j] * scale),
                                      "ci95": [float(lo_t), float(hi_t)]},
                            "mediation": kind})
    return {"indirect": rows, "effects": effects,
            "indirect_rule": f"间接效应 = 路径系数之积；delta 法（Sobel）标准误；蒙特卡洛 {MC_DRAWS} 次抽样的 95% 置信区间不含 0 为显著"}


DISPATCH = {"kano": a_kano, "psm": a_psm, "conjoint": a_conjoint, "sem": a_sem, "cfa": a_sem}


# ───────────────────────── 附录统计表 ─────────────────────────

def _f(x, d=2):
    return "—" if x is None else f"{x:.{d}f}"


def _p(p) -> str:
    return "—" if p is None else "<0.001" if p < 0.001 else f"{p:.3f}"


def _stars(p) -> str:
    return "" if p is None else "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def markdown_tables(aid: str, r: dict) -> list[str]:
    """kano / psm / conjoint / sem / cfa 的附录统计表（Markdown 行）。"""
    t = r.get("type")
    lines: list[str] = []
    if t == "kano":
        lines += [f"### {aid} Kano 需求分类（n = {r['n']}）", "",
                  "| 功能 | 魅力 A | 期望 O | 必备 M | 无差异 I | 反向 R | 可疑 Q | 归类 | Better | Worse |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for x in r["attributes"]:
            pc = x["pct"]
            cat = x["category_label"] + ("" if x["fong_significant"] else "（混合）")
            lines.append(f"| {x['label']} | " + " | ".join(_f(pc[k], 1) for k in "AOMIRQ")
                         + f" | {cat} | {_f(x['better'])} | {_f(x['worse'])} |")
        lines += ["", "注：A–Q 列为各类占比（%）；归类取众数（并列时按 M>O>A>I>R），Fong 检验前两类差别不显著的标“混合”；"
                      "Better = (A+O)/(A+O+M+I)，Worse = −(O+M)/(A+O+M+I)。"
                      f"四象限以 Better 均值 {_f(r.get('better_cut'))}、|Worse| 均值 {_f(r.get('worse_cut'))} 为界。", ""]
    elif t == "psm":
        u = r.get("unit") or "元"
        lines += [f"### {aid} 价格敏感度测试（n = {r['n']}，单位：{u}）", "",
                  "| 价格点 | 价格 | 交点处占比(%) |", "|---|---|---|"]
        for key in ("pmc", "opp", "ipp", "pme"):
            pt = r["price_points"][key]
            lines.append(f"| {pt['label']} | {_f(pt['price'])} | {_f(pt['pct'], 1)} |")
        lo, hi = r["acceptable_range"]
        opt = r.get("optimal_range") or []
        lines += ["", f"可接受价格区间 {_f(lo)}～{_f(hi)} {u}"
                      + (f"；最优价格区间 {_f(opt[0])}～{_f(opt[-1])} {u}" if len(opt) == 2 else "")
                      + f"。剔除四个价格前后矛盾的作答 {r['n_inconsistent']} 份（{_f(r.get('inconsistent_pct'), 1)}%）。", ""]
        if r.get("reference_prices"):
            lines += ["| 参考价格 | 觉得太便宜(%) | 觉得便宜(%) | 觉得贵(%) | 觉得太贵(%) | 可接受(%) |", "|---|---|---|---|---|---|"]
            for x in r["reference_prices"]:
                lines.append(f"| {_f(x['price'])} | {_f(x['too_cheap_pct'], 1)} | {_f(x['cheap_pct'], 1)} | "
                             f"{_f(x['expensive_pct'], 1)} | {_f(x['too_expensive_pct'], 1)} | {_f(x['acceptable_pct'], 1)} |")
            lines.append("")
    elif t == "conjoint":
        lines += [f"### {aid} 联合分析：属性重要性与水平效用（n = {r['n']}）", "",
                  "| 属性 | 相对重要性(%) | 水平 | 效用值 | 95% 置信区间 |", "|---|---|---|---|---|"]
        for at in sorted(r["attributes"], key=lambda x: -x["importance_pct"]):
            for k, lv in enumerate(at["levels"]):
                head = f"| {at['name']} | {_f(at['importance_pct'], 1)} " if k == 0 else "|  |  "
                lines.append(head + f"| {lv['label']} | {_f(lv['utility'], 3)} | [{_f(lv['ci95'][0], 3)}, {_f(lv['ci95'][1], 3)}] |")
        fit = r["fit"]
        extra = (f"；检验卡命中率 {_f(fit['holdout_hit_rate_pct'], 1)}%" if fit.get("holdout_hit_rate_pct") is not None else "")
        dg = r.get("design") or {}
        head = (f"估计卡片 {dg['calibration_cards']} 张（D 效率 {_f(dg['d_efficiency_pct'], 1)}%"
                f"{'，各水平出现次数相同' if dg.get('balanced') else ''}）、检验卡 {r['n_holdout']} 张；") if dg else ""
        lines += ["", f"{head}常数项 {_f(r['constant'], 3)}；Pearson R = {_f(fit['pearson_r'], 3)}（p = {_p(fit['pearson_p'])}），"
                      f"Kendall τ = {_f(fit['kendall_tau'], 3)}（p = {_p(fit['kendall_p'])}）；个人模型平均 R² = "
                      f"{_f(fit['mean_individual_r2'], 3)}{extra}。整列同分剔除 {r['n_flat']} 人。", ""]
        if r.get("scenarios"):
            lines += ["| 方案 | 组合 | 平均效用 | 最大效用法份额(%) | BTL 份额(%) |", "|---|---|---|---|---|"]
            for s in r["scenarios"]:
                lines.append(f"| {s['name']} | {'，'.join(map(str, s['levels']))} | {_f(s['utility'], 3)} | "
                             f"{_f(s['first_choice_pct'], 1)} | {_f(s['btl_pct'], 1)} |")
            lines.append("")
    elif t in {"sem", "cfa"}:
        name = "结构方程模型" if t == "sem" else "验证性因子分析"
        fit = r["fit"]
        lines += [f"### {aid} {name}：拟合指标（n = {r['n']}）", "", "| 指标 | 数值 | 参考标准 | 判定 |", "|---|---|---|---|"]
        for key in ("chi2_df", "rmsea", "srmr", "gfi", "agfi", "cfi", "tli", "nfi", "ifi"):
            if fit.get(key) is None:
                continue
            th = fit["thresholds"][key]
            value = _f(fit[key], 3)
            if key == "rmsea" and fit.get("rmsea_ci90"):
                value += f"（90% CI {_f(fit['rmsea_ci90'][0], 3)}～{_f(fit['rmsea_ci90'][1], 3)}）"
            rule = f"{th['direction']}{th['good']:g} 良好，{th['direction']}{th['acceptable']:g} 可接受"
            lines.append(f"| {FIT_NAMES[key]} | {value} | {rule} | {fit['judgement'].get(key, '—')} |")
        lines += ["", f"χ² = {_f(fit['chi2'], 2)}，df = {fit['df']}，p = {_p(fit.get('p'))}；估计方法：极大似然（ML）。", "",
                  f"#### {aid} 测量模型", "",
                  "| 潜变量 | 题项 | 标准化载荷 | 非标准化载荷 | 标准误 | p | CR | AVE |", "|---|---|---|---|---|---|---|---|"]
        for lat, m in r["measurement"].items():
            for k, it in enumerate(m["items"]):
                head = f"| {m['label']} " if k == 0 else "|  "
                tail = f" | {_f(m['cr'], 3)} | {_f(m['ave'], 3)} |" if k == 0 else " |  |  |"
                lines.append(head + f"| {it['item_label']} | {_f(it['std'], 3)} | {_f(it['b'], 3)} | "
                             f"{'固定为 1' if it.get('fixed') else _f(it['se'], 3)} | {_p(it['p']) if not it.get('fixed') else '—'}" + tail)
        lines += ["", "| 潜变量 | AVE 平方根 | 与其他潜变量的最大相关 | Fornell–Larcker |", "|---|---|---|---|"]
        for m in r["measurement"].values():
            fl = "—" if m.get("fornell_larcker") is None else "满足" if m["fornell_larcker"] else "不满足"
            lines.append(f"| {m['label']} | {_f(m['sqrt_ave'], 3)} | {_f(m.get('max_r_other'), 3)} | {fl} |")
        if r.get("htmt_max") is not None:
            lines += ["", f"HTMT 最大值 {_f(r['htmt_max'], 3)}。{r['validity_rule']}"]
        lines.append("")
        if r.get("paths"):
            lines += [f"#### {aid} 结构路径", "", "| 假设 | 路径 | 非标准化系数 | 标准误 | 标准化系数 β | z | p | 结论 |",
                      "|---|---|---|---|---|---|---|---|"]
            for pth in r["paths"]:
                verdict = ("支持" if pth.get("supported") else "不支持") if pth.get("hypothesis") else (
                    "显著" if pth["significant"] else "不显著")
                lines.append(f"| {pth.get('hypothesis') or '—'} | {pth['from_label']}→{pth['to_label']} | {_f(pth['b'], 3)} | "
                             f"{_f(pth['se'], 3)} | {_f(pth['beta'], 3)}{_stars(pth['p'])} | {_f(pth['z'], 2)} | {_p(pth['p'])} | {verdict} |")
            lines += ["", "R²：" + "，".join(f"{e['label']} {_f(e['r2'], 3)}" for e in r.get("endogenous") or []) + "。", ""]
        if r.get("indirect"):
            lines += [f"#### {aid} 中介效应", "", "| 中介路径 | 间接效应 | 标准误 | 95% 置信区间（蒙特卡洛） | 标准化间接效应 | 结论 |",
                      "|---|---|---|---|---|---|"]
            for ind in r["indirect"]:
                if ind.get("error"):
                    continue
                lines.append(f"| {ind['label']} | {_f(ind['b'], 3)} | {_f(ind['se'], 3)} | [{_f(ind['ci95'][0], 3)}, "
                             f"{_f(ind['ci95'][1], 3)}] | {_f(ind['beta'], 3)} | {'显著' if ind['significant'] else '不显著'} |")
            lines.append("")
        if r.get("effects"):
            lines += ["| 自变量→因变量 | 直接效应 β | 总间接效应 β | 总效应 β | 类型 |", "|---|---|---|---|---|"]
            for e in r["effects"]:
                direct = _f(e["direct"]["beta"], 3) if e.get("direct") else "—"
                lines.append(f"| {e['from_label']}→{e['to_label']} | {direct} | {_f(e['indirect']['beta'], 3)} | "
                             f"{_f(e['total']['beta'], 3)} | {e['mediation']} |")
            lines += ["", f"注：{r.get('indirect_rule', '')}", ""]
    return lines


# ───────────────────────── 计划体检与样本量（纯 Python） ─────────────────────────

def plan_issues(a: dict, q: dict, kind_of) -> list[tuple[str, str, str]]:
    """新方法的计划体检：[(规则, 严重度, 说明)]。kind_of(name) 返回 categorical / numeric / multi / None。"""
    items = {i.get("id"): i for i in S.questions(q)}
    aid, t = a.get("id", "?"), a.get("type")
    out = []
    if t == "kano":
        fun, dys = row_vars(items, a.get("functional")), row_vars(items, a.get("dysfunctional"))
        if not fun or len(fun) != len(dys):
            out.append(("plan_kano_pairs", "error", f"分析 {aid}（Kano）的正向题与反向题行数必须相同"))
        owners = {row.get("id"): it for it in items.values() for row in it.get("rows") or [] if isinstance(row, dict)}
        for name in fun + dys:
            it = owners.get(name) or items.get(name)
            if not it:
                out.append(("plan_unknown_var", "error", f"分析 {aid} 用到的变量 {name} 不存在"))
                continue
            if it.get("type") not in {"matrix_single", "single"}:
                out.append(("plan_kano_type", "error", f"分析 {aid}：{name} 应是矩阵单选（五个 Kano 选项）"))
                continue
            mapping, how = kano_answer_map(it)
            if mapping is None:
                out.append(("plan_kano_options", "error", f"分析 {aid}：{how}"))
            elif how == "order":
                out.append(("plan_kano_options", "warning",
                            f"分析 {aid}：{it.get('id')} 的选项文字没能逐一认出 Kano 五档，将按编码顺序对应"
                            f"“{'、'.join(KANO_ANSWERS)}”，请确认选项顺序"))
    elif t == "psm":
        for key in PSM_KEYS:
            name = a.get(key)
            if not name:
                out.append(("plan_psm_missing", "error", f"分析 {aid}（PSM）缺少 {key} 价格题"))
            elif kind_of(name) != "numeric":
                out.append(("plan_measure_mismatch", "error", f"分析 {aid}（PSM）的 {name} 应是数值题（填价格）"))
    elif t == "conjoint":
        attrs = a.get("attributes") or []
        cards = row_vars(items, a.get("ratings"))
        profiles, err = conjoint_profiles(a.get("profiles"), attrs)
        if err:
            out.append(("plan_conjoint_profiles", "error", f"分析 {aid}（联合分析）：{err}"))
        elif len(profiles) != len(cards):
            out.append(("plan_conjoint_cards", "error",
                        f"分析 {aid}：评分题有 {len(cards)} 张卡片，profiles 有 {len(profiles)} 条，必须一一对应"))
        else:
            for name in cards:
                if kind_of(name) != "numeric":
                    out.append(("plan_measure_mismatch", "error", f"分析 {aid}：卡片评分 {name} 应是量表（矩阵量表题的行）"))
                    break
            hold = {int(h) - 1 for h in a.get("holdout_cards") or []}
            est = [p for i, p in enumerate(profiles) if i not in hold]
            k = conjoint_param_count(attrs)
            if len(est) <= k:
                out.append(("plan_conjoint_too_few", "error", f"分析 {aid}：估计用卡片 {len(est)} 张，要估 {k} 个参数，至少要 {k + 1} 张"))
            elif len(est) < k + 2:
                out.append(("plan_conjoint_too_few", "warning", f"分析 {aid}：估计用卡片只比参数多 {len(est) - k} 张，个人效用不稳"))
            if len({tuple(p) for p in profiles}) < len(profiles):
                out.append(("plan_conjoint_duplicate", "error", f"分析 {aid}：有重复的卡片"))
            sizes = [len(at.get("levels") or []) for at in attrs]
            for j, at in enumerate(attrs):
                counts = [sum(1 for p in est if p[j] == li) for li in range(sizes[j])]
                if min(counts) == 0:
                    out.append(("plan_conjoint_level", "error", f"分析 {aid}：属性“{at.get('name')}”有水平没出现在估计卡片里"))
            if len(cards) > 27:
                out.append(("plan_conjoint_burden", "warning", f"分析 {aid}：{len(cards)} 张卡片太多，受访者容易疲劳"))
    elif t in {"sem", "cfa"}:
        latent, paths, covary, _labels, err = sem_spec(a, S.constructs(q))
        if err:
            out.append(("plan_sem_spec", "error", f"分析 {aid}（{t}）：{err}"))
            return out
        names = [x for v in latent.values() for x in v] + [v for e in paths for v in e if v not in latent]
        for name in dict.fromkeys(names):
            if kind_of(name) != "numeric":
                out.append(("plan_measure_mismatch", "error", f"分析 {aid}：{name} 应是量表或数值变量"))
        counts = sem_counts(latent, paths, covary)
        if counts["df"] < 0:
            out.append(("plan_sem_identified", "error",
                        f"分析 {aid}：模型不可识别（自由参数 {counts['q']} 个，多于 {counts['p'] * (counts['p'] + 1) // 2} 个协方差元素）"))
        short = [k for k, v in latent.items() if len(v) < 3]
        if short:
            out.append(("plan_sem_items", "warning", f"分析 {aid}：潜变量 {'、'.join(short)} 不足 3 个题项"))
    return out


def sample_requirement(a: dict, q: dict) -> dict:
    """新方法的最低有效样本量（survey_sample_size 调用）。"""
    t = a.get("type")
    if t == "kano":
        return {"min_valid_n": 100, "recommended_valid_n": 150,
                "basis": "Kano 各功能的类别占比误差约 ±10%（95% 置信）需约 100 份；Fong 检验区分相邻两类推荐 150 份以上"}
    if t == "psm":
        return {"min_valid_n": 100, "recommended_valid_n": 200,
                "basis": "价格敏感度测试的累计曲线需约 100 份有效作答才平稳，推荐 200 份（剔除前后矛盾作答后）"}
    if t == "conjoint":
        k = conjoint_param_count(a.get("attributes") or [])
        return {"min_valid_n": 100, "recommended_valid_n": 200,
                "basis": f"评分型联合分析逐人估计 {k} 个参数，汇总的效用与重要性通常需约 100 份，推荐 200 份"}
    if t in {"sem", "cfa"}:
        latent, paths, covary, _labels, err = sem_spec(a, S.constructs(q))
        if err:
            return {"min_valid_n": None, "basis": f"模型设定有误：{err}"}
        qn = sem_counts(latent, paths, covary)["q"]
        return {"min_valid_n": max(200, 5 * qn), "recommended_valid_n": max(200, 10 * qn),
                "basis": f"{'结构方程' if t == 'sem' else '验证性因子分析'}估计 {qn} 个参数：样本至少 200 且不低于参数的 5 倍，推荐 10 倍（Kline）"}
    return {"min_valid_n": None, "basis": "未知分析类型，未测算"}


# ───────────────────────── 命令行：联合分析卡片设计 ─────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="市调专项分析工具")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("conjoint-design", help="生成联合分析卡片（正交设计）")
    d.add_argument("--spec", required=True, help='JSON：{"attributes": [{"name": ..., "levels": [...]}, ...]}')
    d.add_argument("--holdout", type=int, default=2)
    d.add_argument("--max-cards", type=int, default=20)
    d.add_argument("--qid", default="Q30", help="评分矩阵题的题号（卡片多时顺延成几道题）")
    d.add_argument("--rows-per-question", type=int, default=9)
    d.add_argument("--scale-max", type=int, default=10)
    d.add_argument("--seed", type=int, default=SEED)
    d.add_argument("--out", default="CONJOINT_DESIGN.json")
    args = ap.parse_args(argv)
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"❌ 读不了 {args.spec}：{exc}")
        return 2
    attrs = spec.get("attributes") if isinstance(spec, dict) else None
    if not attrs or not all(isinstance(at, dict) and at.get("name") and at.get("levels") for at in attrs):
        print("❌ spec 里需要 attributes：[{\"name\": 属性名, \"levels\": [水平, ...]}, ...]")
        return 2
    try:
        design = conjoint_design(attrs, holdout=args.holdout, max_cards=args.max_cards, seed=args.seed)
    except ValueError as exc:
        print(f"❌ {exc}")
        return 1
    questions, entry = design_questions(design, args.qid, args.rows_per_question, (1, args.scale_max))
    design["questions"] = questions
    design["plan_entry"] = entry
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(design, ensure_ascii=False, indent=2), encoding="utf-8")
    dg = design["diagnostics"]
    print(f"✅ {design['method']}：{dg['runs']} 张估计卡片 + {len(design['holdout_cards'])} 张检验卡，"
          f"D 效率 {dg['d_efficiency']:.1f}%，属性间最大相关 {dg['max_abs_corr']:.2f}，"
          f"{'水平均衡' if dg['balanced'] else '水平不完全均衡'} → {out}")
    for c in design["cards"]:
        print(f"  卡片{c['no']}{'（检验卡）' if c['holdout'] else ''}：{c['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
