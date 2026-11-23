#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样本量测算与压力测试：按分析计划逐项算"至少要多少有效样本"，取最紧的约束。

只用标准库，结果可复现（固定随机种子）。依据：
  比例估计     n0 = z²·p(1−p)/e²，有限总体校正 n = n0/(1+(n0−1)/N)，乘设计效应
  两组比较     正态近似功效公式（α=0.05 双侧，功效 0.8）
  方差分析     Cohen (1988) / G*Power 功效表（f=0.25 中效应、f=0.10 小效应）
  相关         Fisher z 近似
  多元回归     Green (1991)：n ≥ 50+8k（整体）且 n ≥ 104+k（单个系数）
  Logistic     每个自变量至少 10 个事件（Peduzzi et al., 1996）
  因子分析     n ≥ max(100, 5×题项)，推荐 10×题项
  结构方程     n ≥ max(200, 5×自由参数)，推荐 10×自由参数（Kline）；验证性因子分析同
  Kano/PSM/联合分析  经验下限约 100 份，推荐 150–200 份
  聚类         推荐 70×变量数（Dolnicar et al., 2014）
  交叉表       只给参考、不定总样本量：蒙特卡洛算“期望频数 <5 的格子超过 20% 的概率不高于 20%”（Cochran 规则）
               要多少份，写进 cells_ok_n；达不到时合并小类别或改用 Fisher 精确检验
  进阶分析     转化漏斗：有分组时每组 ≥100，否则按比例误差；对应分析：每组 ≥50；多选共现：≥150，推荐 300；
               分类树：2^深度 × 叶子最少人数 × 1.25；分布对比：每组 ≥30（无分组时 100）；
               调节效应：检出 f²=0.02 的交互项（α=0.05，功效 0.8）；回收进度：无要求

用法：
  python _utils/survey_sample_size.py --plan ANALYSIS_PLAN.json --questionnaire QUESTIONNAIRE.json \
      [--invalid-rate 0.15] [--margin 0.05] [--confidence 0.95] \
      [--population N] [--deff 1.0] [--target 400] [--out SAMPLE_SIZE_PLAN.json]
类别分布只用配额（设计目标），没有配额按大致均衡估计。预调查的画像试答是模拟的，不当先验（--prior 仍可传，会被忽略）：
曾用 6 份模拟作答的分布当先验，某个分组“预计占 9%”被写进附录，6×5 交叉表据此要求至少 2631 份有效样本。
退出码：0 成功；2 输入缺失。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from statistics import NormalDist

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import survey_methods as SM  # noqa: E402
import survey_schema as S  # noqa: E402

SEED = 20261008
SIMULATIONS = 2000
UNIFORM_CONCENTRATION = 10.0
PREVIEW_CONCENTRATION = 20.0
N_GRID_MAX = 5000
# 每组所需样本（α=0.05，功效 0.8），k = 组数
ANOVA_PER_GROUP = {
    "medium": {2: 64, 3: 53, 4: 45, 5: 40, 6: 35, 7: 32, 8: 30},
    "small": {2: 394, 3: 323, 4: 274, 5: 240, 6: 215, 7: 195, 8: 179},
}
EFFECTS = {"ttest": {"medium": 0.5, "small": 0.3}, "correlation": {"medium": 0.3, "small": 0.2}}


def z(p: float) -> float:
    return NormalDist().inv_cdf(p)


def proportion_n(margin=0.05, confidence=0.95, p=0.5, population=None, deff=1.0) -> dict:
    zz = z(1 - (1 - confidence) / 2)
    n0 = zz ** 2 * p * (1 - p) / margin ** 2
    n = n0 / (1 + (n0 - 1) / population) if population and population > 0 else n0
    return {"n0": math.ceil(n0), "n_after_fpc": math.ceil(n), "deff": deff, "n": math.ceil(n * deff),
            "margin": margin, "confidence": confidence, "p": p, "population": population}


def two_group_n(d: float, ratio: float, alpha=0.05, power=0.8) -> tuple[int, int]:
    """返回 (n1, n2)，ratio = n2/n1。"""
    zz = z(1 - alpha / 2) + z(power)
    n1 = zz ** 2 * (1 + 1 / ratio) / d ** 2 + 1  # +1 为 t 分布小样本校正
    n1 = math.ceil(n1)
    return n1, math.ceil(n1 * ratio)


def correlation_n(r: float, alpha=0.05, power=0.8) -> int:
    c = 0.5 * math.log((1 + r) / (1 - r))
    return math.ceil(((z(1 - alpha / 2) + z(power)) / c) ** 2 + 3)


def _dirichlet(rng: random.Random, alphas: list[float]) -> list[float]:
    draws = [rng.gammavariate(a, 1.0) for a in alphas]
    total = sum(draws) or 1.0
    return [d / total for d in draws]


def _code(value) -> str:
    try:
        f = float(value)
        return str(int(f)) if f.is_integer() else str(f)
    except (TypeError, ValueError):
        return str(value)


class Priors:
    """各变量的类别分布：配额（设计目标）> 大致均衡。

    预调查的画像试答是模拟的（几份、刻意挑的边缘画像），不能当分布的依据，prior 参数只为兼容旧命令保留、不使用。
    分析计划里 recode/binary 派生的分组变量（年龄段、是否独居等）按来源题的分布推算——
    曾因认不出派生变量，分组比较和交叉表一律"无法测算"，最需要样本量的小组反而漏算。
    """

    def __init__(self, q: dict, prior: dict | None = None, derived: list | None = None):
        self.q = q
        self.items = {i.get("id"): i for i in S.questions(q)}
        self.quota = {}
        for quota in q.get("quotas") or []:
            if isinstance(quota, dict) and quota.get("question"):
                self.quota[quota["question"]] = {str(k): float(v) for k, v in (quota.get("targets") or {}).items()}
        self.prior_ignored = bool((prior or {}).get("distributions"))
        self.derived = {d["name"]: d for d in derived or []
                        if isinstance(d, dict) and d.get("name") and d.get("op") in {"recode", "binary"}}

    def _derived_alphas(self, spec: dict) -> tuple[list[str], list[float], str]:
        if spec["op"] == "binary":
            p, source = self._condition_share(spec.get("condition") or "")
            return ["0", "1"], [max((1 - p) * PREVIEW_CONCENTRATION, 1e-3), max(p * PREVIEW_CONCENTRATION, 1e-3)], source
        cats = self.categories(spec["name"])
        mapping = {_code(k): _code(v) for k, v in (spec.get("map") or {}).items()}
        src_cats, src_alphas, source = self.alphas(spec.get("source") or "")
        sums = {c: 0.0 for c in cats}
        for c, a in zip(src_cats, src_alphas):
            if mapping.get(c) in sums:          # 没映射的来源类别（如"不愿透露"）记为缺失
                sums[mapping[c]] += a
        if not cats or not any(sums.values()):
            return cats, [UNIFORM_CONCENTRATION for _ in cats], "uniform"
        return cats, [max(sums[c], 1e-3) for c in cats], source

    def _condition_share(self, expr: str) -> tuple[float, str]:
        """简单条件（==、!=、in、not）按来源题分布算占比；复杂条件按 50% 估计。"""
        try:
            node = S.parse_logic(expr)
        except S.LogicError:
            return 0.5, "uniform"

        def share(n):
            if n[0] == "not":
                inner = share(n[1])
                return None if inner is None else (1 - inner[0], inner[1])
            if n[0] == "in" or (n[0] == "cmp" and n[1] in {"==", "!="}):
                ref = n[1] if n[0] == "in" else n[2]
                item = self.items.get(ref)
                if not item or item.get("type") not in {"single", "scale"}:
                    return None
                wanted = {_code(v) for v in (n[2] if n[0] == "in" else [n[3]])}
                cats, alphas, source = self.alphas(ref)
                total = sum(alphas) or 1.0
                p = sum(a for c, a in zip(cats, alphas) if c in wanted) / total
                return (1 - p if n[0] == "cmp" and n[1] == "!=" else p), source
            return None

        got = share(node)
        return got if got else (0.5, "uniform")

    def categories(self, name: str) -> list[str]:
        spec = self.derived.get(name)
        if spec:
            if spec["op"] == "binary":
                return ["0", "1"]
            return sorted({_code(v) for v in (spec.get("map") or {}).values()}, key=lambda c: float(c))
        item = self.items.get(name)
        if item:
            vals = S.valid_values(item)
            if vals:
                return [str(v) for v in vals]
        for var in S.variables(self.q):
            if var["name"] == name and var.get("values"):
                return list(var["values"].keys())
        return []

    def alphas(self, name: str) -> tuple[list[str], list[float], str]:
        if name in self.derived:
            return self._derived_alphas(self.derived[name])
        cats = self.categories(name)
        if not cats:
            return [], [], "unknown"
        if name in self.quota:
            shares = self.quota[name]
            total = sum(shares.get(c, 0.0) for c in cats) or 1.0
            # 配额是设计目标：用很集中的 Dirichlet 表示"基本按配额来"
            return cats, [max(shares.get(c, 0.0) / total, 1e-3) * 200 for c in cats], "quota"
        # 没有配额：大致均衡但不确定（每类集中度 10），避免平坦分布把小类别估得过小
        return cats, [UNIFORM_CONCENTRATION for _ in cats], "uniform"

    def shares(self, name: str) -> list[float]:
        cats, alphas, _ = self.alphas(name)
        total = sum(alphas) or 1.0
        return [a / total for a in alphas]

    def planned(self, name: str) -> tuple[list[str], list[float], list[str]]:
        """分组比较用的类别和占比：有配额的题只算配额里列了目标的类别。配额外的类别（团队后加的“不愿透露”“其他”）
        人数很少、比较时不单列，不能拿它当“最小组”推总样本量（10-15 小白实测：性别题照 AI 建议加了“不愿透露”、
        配额仍是男女各半，最小组按 0.1% 算，最低有效样本从 417 份变成 100100 份）。返回 (类别, 占比, 不单列的类别)。"""
        cats = self.categories(name)
        quota = self.quota.get(name) if name not in self.derived else None
        if quota:
            keep = [c for c in cats if quota.get(c, 0.0) > 0]
            if 2 <= len(keep) < len(cats):
                total = sum(quota[c] for c in keep)
                return keep, [quota[c] / total for c in keep], [c for c in cats if c not in keep]
        return cats, self.shares(name), []

    def labels(self, name: str, codes: list[str]) -> str:
        item = self.items.get(name) or {}
        names = {_code(o.get("code")): str(o.get("label") or "") for o in item.get("options") or [] if isinstance(o, dict)}
        return "、".join(f"“{names.get(c) or c}”" for c in codes)


def crosstab_requirement(priors: Priors, row: str, col: str, rng: random.Random) -> dict:
    """交叉表只给参考（advisory），不决定总样本量：格子太稀时的通行做法是合并小类别或改用 Fisher 精确检验，
    不是把总样本量抬到每个格子都够 5 份。曾把这个数当最低有效样本量，一张 6×5 表就要求 2631 份，
    团队收满几百份也点不过“数据够了”。达到“格子大多够用”要多少份写进 cells_ok_n。"""
    rc, ra, rs = priors.alphas(row)
    cc, ca, cs = priors.alphas(col)
    if len(rc) < 2 or len(cc) < 2:
        return {"min_valid_n": None, "basis": "变量类别不足两类，无法做交叉表", "sources": [rs, cs]}
    size = f"{row}×{col} 共 {len(rc)}×{len(cc)} 格"
    remedy = "达不到时把占比小的类别合并后再做 χ² 检验，或改用 Fisher 精确检验；不据此要求总样本量"
    draws = [(_dirichlet(rng, ra), _dirichlet(rng, ca)) for _ in range(SIMULATIONS)]

    def sparse_prob(n: int) -> float:
        bad = 0
        for p, q in draws:
            cells = [n * a * b for a in p for b in q]
            small = sum(e < 5 for e in cells) / len(cells)
            if small > 0.2 or min(cells) < 1:
                bad += 1
        return bad / len(draws)

    lo, hi = 20, N_GRID_MAX
    if sparse_prob(hi) > 0.2:
        return {"min_valid_n": None, "advisory": True, "cells_ok_n": None, "sources": [rs, cs],
                "basis": f"{size}：即使有 {N_GRID_MAX} 份有效样本，仍很可能有期望频数不足 5 的格子；{remedy}",
                "note": "建议分析前把占比小的类别合并（如把相邻档位并成三档），再做 χ² 检验，或改用 Fisher 精确检验"}
    while lo < hi:
        mid = (lo + hi) // 2
        if sparse_prob(mid) <= 0.2:
            hi = mid
        else:
            lo = mid + 1
    return {"min_valid_n": None, "advisory": True, "cells_ok_n": lo, "sources": [rs, cs],
            "basis": f"{size}：有效样本约 {lo} 份时，期望频数<5 的格子超过 20% 的概率才不高于 20%；{remedy}"}


def _unplanned_note(priors: Priors, group: str, dropped: list[str]) -> str:
    return f"；{priors.labels(group, dropped)}没有配额目标、人数很少，比较时不单列（合并或剔除）" if dropped else ""


def group_requirement(priors: Priors, group: str, kind: str, effect: str) -> dict:
    _cats, _alphas, source = priors.alphas(group)
    cats, shares, dropped = priors.planned(group)
    k = len(cats)
    if k < 2:
        return {"min_valid_n": None, "basis": f"分组变量 {group} 少于两类"}
    smallest = min(shares)
    unplanned = _unplanned_note(priors, group, dropped)
    if kind == "ttest" and k == 2:
        ratio = shares[1] / shares[0] if shares[0] else 1.0
        d = EFFECTS["ttest"][effect]
        n1, n2 = two_group_n(d, ratio)
        total = n1 + n2
        return {"min_valid_n": total, "source": source,
                "basis": f"两组占比约 {shares[0]:.0%}/{shares[1]:.0%}，检出 d={d} 的差异（α=0.05，功效 0.8）需每组约 {n1}/{n2} 份"
                         + unplanned}
    k_used = min(max(k, 2), 8)
    per_group = ANOVA_PER_GROUP[effect][k_used]
    total = math.ceil(per_group / smallest) if smallest > 0 else None
    f = 0.25 if effect == "medium" else 0.10
    note = "组数超过 8 组按 8 组近似；建议合并类别" if k > 8 else ""
    return {"min_valid_n": total, "source": source, "note": note,
            "basis": f"{k} 组、最小组预计占 {smallest:.0%}，检出 f={f} 的差异需每组约 {per_group} 份" + unplanned}


def count_predictors(q: dict, names: list[str], priors: "Priors | None" = None) -> int:
    vars_ = {v["name"]: v for v in S.variables(q)}
    total = 0
    for name in names:
        var = vars_.get(name)
        if priors is not None and name in priors.derived:
            total += max(len(priors.categories(name)) - 1, 1)   # 派生类别变量按虚拟变量计
        elif var and var.get("kind") == "categorical":
            total += max(len(var.get("values") or {}) - 1, 1)
        else:
            total += 1
    return total


def advanced_requirement(a: dict, q: dict, priors: Priors, prop: dict) -> dict:
    """survey_advanced.py 的进阶分析：按各自最吃样本的环节估算。"""
    t = a.get("type")

    def per_group(group, each, what):
        _cats, shares, dropped = priors.planned(group) if group and priors.categories(group) else ([], [], [])
        if len(shares) < 2:
            return None
        smallest = min(shares)
        return {"min_valid_n": math.ceil(each / smallest) if smallest > 0 else None,
                "basis": f"{what}：{group} 最小组预计占 {smallest:.0%}，每组至少 {each} 份" + _unplanned_note(priors, group, dropped)}
    if t == "funnel":
        got = per_group(a.get("group"), 100, "分组漏斗要比较各组每一阶段的转化率")
        return got or {"min_valid_n": prop["n"], "basis": f"各阶段比例误差 ±{prop['margin']:.0%}（{prop['confidence']:.0%} 置信）"}
    if t == "correspondence":
        got = per_group(a.get("row"), 50, "对应分析每组的选择比例要稳定")
        return got or {"min_valid_n": 200, "basis": "对应分析的列联表要有足够的格子频数，一般需约 200 份"}
    if t == "cooccurrence":
        return {"min_valid_n": 150, "recommended_valid_n": 300,
                "basis": "多选共现做两两 Fisher 检验并算提升度，选项同时被选的人数要够，至少约 150 份、推荐 300 份"}
    if t == "tree":
        depth, leaf = int(a.get("max_depth", 3)), int(a.get("min_leaf", 30))
        return {"min_valid_n": math.ceil(2 ** depth * leaf * 1.25),
                "basis": f"分类树最大深度 {depth}、叶子至少 {leaf} 人：最多 {2 ** depth} 个叶子，叶子大小不均时再留 25% 余量"}
    if t == "distribution":
        got = per_group(a.get("group"), 30, "分组核密度与分位数要稳定")
        return got or {"min_valid_n": 100, "basis": "核密度与分位数估计稳定通常需要约 100 份"}
    if t == "moderation":
        k = count_predictors(q, [a.get("x"), a.get("w")] + list(a.get("controls") or []), priors) + 1
        n = math.ceil((z(0.975) + z(0.8)) ** 2 / 0.02) + k + 1
        return {"min_valid_n": n, "basis": f"检出小效应的交互项（f²=0.02，α=0.05，功效 0.8），共 {k} 个自变量"}
    if t == "timeline":
        return {"min_valid_n": None, "basis": "回收进度只做描述，没有样本量要求"}
    return {"min_valid_n": None, "basis": "未知分析类型，未测算"}


def analysis_requirements(plan: dict, q: dict, priors: Priors, effect: str, rng: random.Random, prop: dict) -> list[dict]:
    cons = S.constructs(q)
    out = []
    for a in plan.get("analyses") or []:
        if not isinstance(a, dict):
            continue
        aid, t = a.get("id", "?"), a.get("type")
        rec: dict = {"id": aid, "type": t}
        if t == "describe":
            rec.update(min_valid_n=prop["n"], basis=f"比例估计误差 ±{prop['margin']:.0%}（{prop['confidence']:.0%} 置信）")
        elif t == "crosstab":
            rec.update(crosstab_requirement(priors, a.get("row"), a.get("col"), rng))
        elif t in {"ttest", "anova"}:
            rec.update(group_requirement(priors, a.get("group"), t, effect))
        elif t == "correlation":
            r = EFFECTS["correlation"][effect]
            rec.update(min_valid_n=correlation_n(r), basis=f"检出 r={r} 的相关（α=0.05，功效 0.8）")
        elif t == "regression":
            k = count_predictors(q, (a.get("ivs") or []) + (a.get("controls") or []), priors)
            rec.update(min_valid_n=max(50 + 8 * k, 104 + k), basis=f"{k} 个自变量（类别变量按虚拟变量计），Green 规则")
        elif t == "logistic":
            k = count_predictors(q, (a.get("ivs") or []) + (a.get("controls") or []), priors)
            dv_shares = priors.shares(a.get("dv")) if priors.categories(a.get("dv")) else [0.5, 0.5]
            p_event = min(dv_shares) if dv_shares else 0.5
            rec.update(min_valid_n=math.ceil(10 * k / max(p_event, 0.05)),
                       basis=f"{k} 个自变量，较少一类预计占 {p_event:.0%}，每个自变量至少 10 个事件")
        elif t == "efa":
            p = len(a.get("items") or [])
            rec.update(min_valid_n=max(100, 5 * p), recommended_valid_n=max(100, 10 * p),
                       basis=f"{p} 个题项：最少 5 倍、推荐 10 倍")
        elif t in SM.DISPATCH:
            rec.update(SM.sample_requirement(a, q))
        elif t in {"funnel", "correspondence", "cooccurrence", "tree", "distribution", "moderation", "timeline"}:
            rec.update(advanced_requirement(a, q, priors, prop))
        elif t == "reliability":
            items = a.get("items") or cons.get(a.get("construct"), [])
            rec.update(min_valid_n=100, basis=f"{len(items)} 题信度分析，α 估计稳定通常需要约 100 份")
        elif t == "cluster":
            m = len(a.get("vars") or [])
            rec.update(min_valid_n=max(100, 10 * m), recommended_valid_n=70 * m,
                       basis=f"{m} 个聚类变量：推荐 70 倍变量数")
        elif t == "nps":
            rec.update(min_valid_n=math.ceil(z(0.975) ** 2 * 0.6 / 0.1 ** 2), basis="NPS 误差 ±10 分（推荐者、贬损者各约 30% 时）")
        elif t == "ipa":
            rec.update(min_valid_n=math.ceil(z(0.975) ** 2 * 1.0 / 0.15 ** 2), basis="各属性均值误差 ±0.15 分（5 级量表、标准差约 1）")
        else:
            rec.update(min_valid_n=None, basis="未知分析类型，未测算")
        rec.setdefault("recommended_valid_n", rec.get("min_valid_n"))
        out.append(rec)
    return out


RULES_VERSION = 2   # 2：交叉表只给参考、不当先验用模拟作答（1 是旧算法）


def build_plan(plan: dict, q: dict, prior: dict | None = None, *, invalid_rate=0.15, margin=0.05, confidence=0.95,
               population=None, deff=1.0, target=None, effect="medium", seed=SEED) -> dict:
    rng = random.Random(seed)
    priors = Priors(q, prior, plan.get("derived"))
    prop = proportion_n(margin, confidence, 0.5, population, deff)
    analyses = analysis_requirements(plan, q, priors, effect, rng, prop)
    needs = [a for a in analyses if isinstance(a.get("min_valid_n"), int) and not a.get("advisory")]
    binding = max(needs, key=lambda a: a["min_valid_n"]) if needs else None
    valid_n = max([prop["n"]] + [a["min_valid_n"] for a in needs])
    recommended = max([valid_n] + [a.get("recommended_valid_n") or 0 for a in needs])
    collect = math.ceil(valid_n / (1 - invalid_rate)) if invalid_rate < 1 else None
    # 回收数与有效数成对折算：建议回收按建议有效样本算（曾一律按最低有效样本算，附录写成
    # “建议有效样本不少于 780 份、回收不少于 471 份”，回收数比有效数还少）
    collect_rec = math.ceil(recommended / (1 - invalid_rate)) if invalid_rate < 1 else None
    result = {
        "schema": "paperkit.survey.sample_size/v1",
        "rules_version": RULES_VERSION,
        "assumptions": {"alpha": 0.05, "power": 0.8, "effect": effect, "invalid_rate": invalid_rate,
                        "seed": seed, "simulations": SIMULATIONS,
                        "prior_note": "各类别的占比按配额（设计目标）估计，没有配额的按大致均衡估计；预调查的模拟试答不作依据"},
        "proportion": prop,
        "analyses": analyses,
        "binding": {"id": binding["id"], "type": binding["type"], "min_valid_n": binding["min_valid_n"]} if binding else None,
        "min_valid_n": valid_n,
        "min_collect_n": collect,
        "recommended_valid_n": recommended,
        "recommended_collect_n": collect_rec,
        "unresolved": [a["id"] for a in analyses if a.get("min_valid_n") is None and not a.get("advisory")],
        # 只给参考、不定总样本量的分析（交叉表格子要多少份才大多够 5）
        "advisories": [{"id": a["id"], "type": a["type"], "cells_ok_n": a.get("cells_ok_n"), "basis": a.get("basis")}
                       for a in analyses if a.get("advisory")],
    }
    if target:
        short = [a["id"] for a in needs if a["min_valid_n"] > target]
        result["at_target"] = {"target_valid_n": target, "underpowered": short,
                               "ok": not short and target >= prop["n"]}
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="样本量测算与压力测试")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--questionnaire", required=True)
    ap.add_argument("--prior", help="已不使用：预调查的模拟试答不当先验，传了也会忽略")
    ap.add_argument("--invalid-rate", type=float, default=0.15)
    ap.add_argument("--margin", type=float, default=0.05)
    ap.add_argument("--confidence", type=float, default=0.95)
    ap.add_argument("--population", type=float)
    ap.add_argument("--deff", type=float, default=1.0)
    ap.add_argument("--target", type=int)
    ap.add_argument("--effect", choices=["medium", "small"], default="medium")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default="SAMPLE_SIZE_PLAN.json")
    args = ap.parse_args(argv)
    try:
        plan = S.load_json(args.plan)
        q = S.load_questionnaire(args.questionnaire)
        prior = S.load_json(args.prior) if args.prior and Path(args.prior).is_file() else None
    except S.SchemaError as exc:
        print(f"❌ {exc}")
        return 2
    result = build_plan(plan, q, prior, invalid_rate=args.invalid_rate, margin=args.margin,
                        confidence=args.confidence, population=args.population, deff=args.deff,
                        target=args.target, effect=args.effect, seed=args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for a in result["analyses"]:
        need = a.get("min_valid_n")
        what = ("只作参考，不定总样本量" if a.get("advisory") else "无法测算") if need is None else f"至少 {need} 份"
        print(f"  {a['id']} {a['type']}: {what} —— {a.get('basis', '')}")
    b = result["binding"]
    print(f"✅ 有效样本至少 {result['min_valid_n']} 份（最紧约束：{b['id'] if b else '比例估计'}），"
          f"按无效率 {args.invalid_rate:.0%} 至少回收 {result['min_collect_n']} 份；兼顾各项分析的推荐样本量，"
          f"建议有效 {result['recommended_valid_n']} 份、回收 {result['recommended_collect_n']} 份 → {out}")
    if result.get("at_target") and not result["at_target"]["ok"]:
        print(f"⚠️ 目标 {args.target} 份不足以支撑：{'、'.join(result['at_target']['underpowered']) or '比例估计精度'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
