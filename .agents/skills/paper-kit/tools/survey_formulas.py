#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市调报告的公式清单与公式核查（2026-10-21 用户：“市调的写作，发现公式很少啊，并且没有公式编号，不详细”“市调报告要从
根源上去解决，公式要足够，比如结构方程，信效度分析那些什么的”。一份 60 页、用了信度、效度、验证性因子分析、结构方程、
Logistic、调节、聚类、Kano 等十几种方法的报告，全文只有样本量 1 个公式、没有编号：技能只点名了样本量公式，合规检查不查
公式，数字溯源还会把公式里的常数报成“找不到”，写得越多越吃亏）。

按 ANALYSIS_PLAN.json 里实际做了（STATISTICAL_RESULTS.json 有结果、没报错）的分析给出报告要写的公式：
· 每种方法的标准公式（LaTeX），与统计脚本的实际算法一致：样本量按比例估计（有总体规模时做有限总体校正）；t 检验一律用
  Welch 法；方差分析方差不齐时改用 Welch 方差分析；回归用 HC3 稳健标准误、类别变量按虚拟变量进入；Logistic 报 OR 与
  McFadden R²；调节效应先均值中心化、用 HC3 与 z 临界值算 Johnson–Neyman 区间；K-means 先做 z 标准化、用轮廓系数定类数；
  结构方程用最大似然估计，拟合指标按 survey_methods.fit_indices 的算法，间接效应用 delta 法（Sobel）与蒙特卡洛置信区间；
· 本研究自己的模型式：结构方程按 latent、paths、hypotheses 写出每一条结构方程（内生潜变量作自变量的系数记 β，外生的记 γ，
  下标是假设编号），回归、Logistic、调节按 dv、ivs、controls 写出模型式（变量名取自分析计划、统计结果和选题简报）；
· 每组公式后面那段“式中，……”（逐个说明符号，只写符号和常数），放在哪一节，本研究的取值（写进后面的结果段落）。

报告里每组公式前一行写 `<!-- 公式：名字 -->`（导出 Word 时注释会删掉），公式写成行间公式并带 `\\tag{n}`，后面紧跟
“式中，……”。编号随手写，写完由 survey_numbering.py 按出现顺序统一重编（没写编号的行间公式也会补上）。

用法：
  python _utils/survey_formulas.py                        # 写 results/公式清单.md 和 results/FORMULAS.json
  python _utils/survey_formulas.py --check paper/main.md  # 核查报告：做了的方法写没写公式、编号、式中说明
退出码：0 通过；1 核查没通过（--check）；2 缺输入文件。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from statistics import NormalDist

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MARK = "<!-- 公式：{key} -->"
MARK_RE = re.compile(r"<!--\s*公式\s*[:：]\s*([A-Za-z0-9_\-]+)\s*-->")
TAG_RE = re.compile(r"\\tag\{([^{}]*)\}")
WHERE = {"设计": "研究设计", "实施": "样本与数据质量", "结果": "分析各章"}
TYPE_NAMES = {"funnel": "分组漏斗分析", "crosstab": "交叉分析", "ttest": "两组均值比较", "anova": "多组均值比较",
              "regression": "回归分析", "logistic": "Logistic 回归", "sem": "结构方程模型", "cfa": "验证性因子分析",
              "efa": "探索性因子分析", "cluster": "聚类分析", "correlation": "相关分析", "moderation": "调节效应分析",
              "correspondence": "对应分析", "kano": "Kano 分析", "psm": "价格敏感度测试", "conjoint": "联合分析",
              "describe": "比例估计", "reliability": "信度分析", "tree": "分类树", "cooccurrence": "共现分析"}


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
    except (OSError, ValueError):
        return None


def sym(code) -> str:
    """变量代号写成正体：ATT → \\mathrm{ATT}，Q3_r1 → \\mathrm{Q3\\_r1}；% & # 转义（不然 % 把后面的公式注释掉）"""
    text = re.sub(r"[\\{}$]", "", str(code))
    for ch in "_%&#":
        text = text.replace(ch, "\\" + ch)
    return r"\mathrm{" + text + "}"


def _sub(code) -> str:
    return "_{" + sym(code) + "}"


def _f(x, d=3):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return "—"


def _p(p) -> str:
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "—"
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def names_of(ws: Path, plan: dict | None, results: dict | None) -> dict:
    """变量代号 → 中文名：分析计划里的潜变量、统计结果里的派生变量与各项标签、选题简报的构念、问卷题目（截短）"""
    out: dict[str, str] = {}

    def put(code, name):
        if code is not None and isinstance(name, str) and name.strip():
            out.setdefault(str(code), name.strip())
    for a in (plan or {}).get("analyses") or []:
        for code, name in ((a.get("latent") or {}) if isinstance(a, dict) and isinstance(a.get("latent"), dict) else {}).items():
            put(code, name)
    for code, d in ((results or {}).get("derived") or {}).items():
        if isinstance(d, dict):
            put(code, d.get("label"))
    for r in ((results or {}).get("results") or {}).values():
        if not isinstance(r, dict):
            continue
        for code, name in (r.get("labels") or {}).items() if isinstance(r.get("labels"), dict) else ():
            put(code, name)
        for role in ("dv", "x", "w"):
            put(r.get(role), r.get(f"{role}_label"))
        coefs = r.get("coefficients")
        rows = coefs.items() if isinstance(coefs, dict) else ((c.get("name"), c) for c in coefs or [] if isinstance(c, dict))
        for code, c in rows:
            if isinstance(c, dict) and code and "=" not in str(code) and not str(code).startswith("__"):
                put(code, c.get("label"))
    brief = _load(ws / "SURVEY_BRIEF.json") or {}
    for c in brief.get("constructs") or []:
        if isinstance(c, dict):
            put(c.get("code"), c.get("name"))
    q = _load(ws / "QUESTIONNAIRE.json") or {}
    for item in q.get("questions") or []:
        if isinstance(item, dict) and item.get("id"):
            text = re.sub(r"[（(].*?[)）]|[？?。：:]", "", str(item.get("text") or "")).strip()
            put(item["id"], text[:16] + ("…" if len(text) > 16 else ""))
            for row in item.get("rows") or []:
                if isinstance(row, dict):
                    put(row.get("id"), row.get("label"))
    return out


def _named(codes, names: dict) -> str:
    """“$\\mathrm{ATT}$ 为转售态度、$\\mathrm{SN}$ 为主观规范”"""
    return "、".join(f"${sym(c)}$ 为{names.get(str(c), str(c))}" for c in codes)


def _listed(codes, names: dict) -> str:
    """“转售态度（$\\mathrm{ATT}$）、主观规范（$\\mathrm{SN}$）”：列在“……为”后面用"""
    return "、".join(f"{names.get(str(c), str(c))}（${sym(c)}$）" for c in codes)


def _dummies(r: dict) -> list[str]:
    """按虚拟变量进入模型的类别变量（系数名写成“SEX=2”的那些），按出现顺序"""
    coefs = r.get("coefficients")
    keys = list(coefs) if isinstance(coefs, dict) else [c.get("name") for c in coefs or [] if isinstance(c, dict)]
    return list(dict.fromkeys(str(k).split("=")[0] for k in keys if k and "=" in str(k)))


def _wrap(lhs: str, terms: list[str], per_line: int = 4) -> str:
    """项多时拆成几行（aligned）：一行放不下的长式子在 Word 里不会自动折行"""
    if len(terms) <= per_line + 1:
        return lhs + "=" + "+".join(terms)
    lines = [terms[i:i + per_line] for i in range(0, len(terms), per_line)]
    rows = [lhs + "={}&" + "+".join(lines[0])] + ["&+" + "+".join(part) for part in lines[1:]]
    return r"\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}"


def entry(key, title, chapter, where, latex, symbols, then="", required=True) -> dict:
    return {"key": key, "title": title, "chapter": chapter, "where": where, "latex": list(latex), "symbols": symbols,
            "then": then, "required": required}


# ───────────────────────── 设计：样本量 ─────────────────────────

def f_sample_size(design: dict) -> dict:
    p = design.get("proportion") or {}
    assumed = design.get("assumptions") or {}
    conf = float(p.get("confidence") or 0.95)
    z = NormalDist().inv_cdf(1 - (1 - conf) / 2)
    latex = [r"n_{0}=\frac{z_{\alpha/2}^{2}\,p\,(1-p)}{e^{2}}"]
    fpc = bool(p.get("population")) or float(p.get("deff") or 1) != 1
    if fpc:
        latex.append(r"n=\mathrm{deff}\times\frac{n_{0}}{1+\left(n_{0}-1\right)/N}")
    latex.append(r"n_{\min}=\max_{j}\,n_{j},\qquad n_{\mathrm{c}}=\left\lceil\frac{n_{\min}}{1-r}\right\rceil")
    symbols = (r"式中，$n_{0}$ 为按比例估计所需的有效样本量；$z_{\alpha/2}$ 为置信水平对应的标准正态分位数；$p$ 为总体比例的预估值，"
               r"未知时取使 $p(1-p)$ 最大的值；$e$ 为允许误差；"
               + (r"$N$ 为总体规模，$\mathrm{deff}$ 为设计效应，$n$ 为校正后的样本量；" if fpc else "")
               + r"$n_{j}$ 为第 $j$ 项分析（分组比较、模型估计等）所需的最少有效样本量，$n_{\min}$ 取其中最大者；$r$ 为预计无效率；"
               r"$n_{\mathrm{c}}$ 为计划回收的问卷数；$\lceil\cdot\rceil$ 表示向上取整。")
    binding = design.get("binding") if isinstance(design.get("binding"), dict) else {}
    then = (f"本研究取值：置信水平 {conf * 100:g}%、z = {z:.2f}、允许误差 e = {_f(p.get('margin'), 2)}、p = {_f(p.get('p'), 1)}，"
            f"$n_0$ = {p.get('n0', '—')}；各项分析中要求最高的是{TYPE_NAMES.get(str(binding.get('type')), '其中一项分析')}，"
            f"至少需要有效样本 {design.get('min_valid_n', '—')} 份；按预计无效率 {_f((assumed.get('invalid_rate') or 0) * 100, 0)}% 计算，"
            f"至少回收 {design.get('min_collect_n', '—')} 份。")
    return entry("sample_size", "样本量测算", "设计", "抽样设计与样本量", latex, symbols, then)


# ───────────────────────── 实施：信度与效度 ─────────────────────────

def f_reliability(items: list) -> dict:
    vals = "；".join(f"{r.get('construct') or ''} α = {_f(r.get('alpha'))}" for _, r in items[:12] if r.get("alpha") is not None)
    return entry("cronbach_alpha", "信度：Cronbach's α 系数与校正的题项—总分相关", "实施", "信度与效度检验", [
        r"\alpha=\frac{k}{k-1}\left(1-\frac{\sum_{i=1}^{k}\sigma_{i}^{2}}{\sigma_{T}^{2}}\right)",
        r"r_{i,T-i}=\mathrm{corr}\left(x_{i},\,T-x_{i}\right)"],
        r"式中，$k$ 为量表的题项数；$\sigma_{i}^{2}$ 为第 $i$ 个题项得分的方差；$T$ 为量表总分，$\sigma_{T}^{2}$ 为其方差；"
        r"$r_{i,T-i}$ 为校正的题项—总分相关（CITC），即题项 $i$ 与其余题项之和的相关系数。$\alpha$ 越接近 1，题项之间的内部一致性"
        r"越高，一般以不低于 0.7 为可接受；CITC 低于 0.3、删除后 $\alpha$ 明显上升的题项需要讨论。",
        f"本研究取值：{vals}。" if vals else "")


def f_efa(r: dict) -> list:
    bart = r.get("bartlett") or {}
    out = [entry("kmo_bartlett", "效度：KMO 检验与 Bartlett 球形检验", "实施", "信度与效度检验", [
        r"\mathrm{KMO}=\frac{\sum_{i\neq j}r_{ij}^{2}}{\sum_{i\neq j}r_{ij}^{2}+\sum_{i\neq j}a_{ij}^{2}}",
        r"\chi^{2}=-\left[(n-1)-\frac{2p+5}{6}\right]\ln\left|\mathbf{R}\right|,\qquad df=\frac{p(p-1)}{2}"],
        r"式中，$r_{ij}$ 为题项 $i$ 与 $j$ 的简单相关系数；$a_{ij}$ 为控制其余题项后的偏相关系数；$n$ 为样本量；$p$ 为题项数；"
        r"$\left|\mathbf{R}\right|$ 为题项相关矩阵的行列式。KMO 越接近 1 越适合做因子分析（一般要求不低于 0.7）；"
        r"Bartlett 检验显著说明相关矩阵不是单位阵，题项之间存在共同因子。",
        f"本研究取值：KMO = {_f(r.get('kmo'))}，Bartlett χ² = {_f(bart.get('chi2'))}，df = {_f(bart.get('df'), 0)}，"
        f"p {_p(bart.get('p'))}。" if r.get("kmo") is not None else ""),
        entry("factor_model", "探索性因子分析的因子模型", "实施", "信度与效度检验", [
            r"x_{i}=\sum_{j=1}^{m}\lambda_{ij}F_{j}+\varepsilon_{i},\qquad h_{i}^{2}=\sum_{j=1}^{m}\lambda_{ij}^{2}"],
            r"式中，$x_{i}$ 为第 $i$ 个标准化题项；$F_{j}$ 为第 $j$ 个公因子；$\lambda_{ij}$ 为方差最大旋转后的因子载荷；$m$ 为公因子个数"
            r"（特征根大于 1 与平行分析共同确定）；$\varepsilon_{i}$ 为特殊因子；$h_{i}^{2}$ 为题项 $i$ 的共同度。", required=False)]
    cm = r.get("common_method") if isinstance(r.get("common_method"), dict) else None
    if cm:
        pct = cm.get("harman_first_pct")
        out.append(entry("harman", "共同方法偏差：Harman 单因子检验", "实施", "信度与效度检验", [
            r"\mathrm{VE}_{1}=\frac{\lambda_{1}}{p}\times100\%"],
            r"式中，$\lambda_{1}$ 为未旋转时第一个公因子的特征根；$p$ 为全部量表题项数；$\mathrm{VE}_{1}$ 为第一个公因子解释的方差比例，"
            r"低于 40% 说明不存在单一因子解释大部分变异的严重共同方法偏差。",
            f"本研究取值：第一个公因子解释了 {_f(pct, 1)}% 的方差。" if pct is not None else ""))
    return out


def f_cfa(r: dict, names: dict) -> list:
    fit = r.get("fit") or {}
    # 潜变量按测量模型里的列（结构方程的 labels 还含进入结构部分的观测变量，比如控制变量：不能写成潜变量）
    measured = r.get("measurement") if isinstance(r.get("measurement"), dict) else {}
    latent = [str(c) for c in measured] or [str(c) for c in (r.get("labels") or {})]
    return [entry("cfa_model", "验证性因子分析的测量模型", "实施", "信度与效度检验", [
        r"\mathbf{x}=\boldsymbol{\Lambda}_{x}\boldsymbol{\xi}+\boldsymbol{\delta}"],
        r"式中，$\mathbf{x}$ 为观测题项向量；$\boldsymbol{\xi}$ 为潜变量向量" + (f"，包括{_listed(latent, names)}" if latent else "")
        + r"；$\boldsymbol{\Lambda}_{x}$ 为因子载荷矩阵；$\boldsymbol{\delta}$ 为测量误差向量。模型用最大似然法估计，"
        r"拟合指标的公式见结构方程一节（没做结构方程时写在本节）。",
        f"本研究取值：χ²/df = {_f(fit.get('chi2_df'))}，RMSEA = {_f(fit.get('rmsea'))}，CFI = {_f(fit.get('cfi'))}，"
        f"TLI = {_f(fit.get('tli'))}，SRMR = {_f(fit.get('srmr'))}。" if fit else ""),
        entry("cr_ave", "收敛效度：组合信度与平均方差提取量", "实施", "信度与效度检验", [
            r"\mathrm{CR}=\frac{\left(\sum_{i=1}^{k}\lambda_{i}\right)^{2}}{\left(\sum_{i=1}^{k}\lambda_{i}\right)^{2}+\sum_{i=1}^{k}\left(1-\lambda_{i}^{2}\right)}",
            r"\mathrm{AVE}=\frac{1}{k}\sum_{i=1}^{k}\lambda_{i}^{2}"],
            r"式中，$\lambda_{i}$ 为潜变量第 $i$ 个题项的标准化因子载荷；$k$ 为该潜变量的题项数；$1-\lambda_{i}^{2}$ 为题项的标准化误差方差。"
            r"一般要求标准化载荷不低于 0.5、CR 不低于 0.7、AVE 不低于 0.5。"),
        entry("discriminant", "区分效度：Fornell–Larcker 准则与 HTMT", "实施", "信度与效度检验", [
            r"\sqrt{\mathrm{AVE}_{j}}>\left|\phi_{jl}\right|,\qquad \forall\,l\neq j",
            r"\mathrm{HTMT}_{jl}=\frac{\bar{r}_{jl}}{\sqrt{\bar{r}_{jj}\,\bar{r}_{ll}}}"],
            r"式中，$\phi_{jl}$ 为潜变量 $j$ 与 $l$ 的相关系数；$\bar{r}_{jl}$ 为两个潜变量各自题项之间相关系数的均值（异质—异方法相关）；"
            r"$\bar{r}_{jj}$、$\bar{r}_{ll}$ 为同一潜变量内部题项相关系数的均值。每个潜变量 AVE 的平方根大于它与其他潜变量的相关、"
            r"HTMT 小于 0.85（宽松标准 0.90）时，区分效度成立。",
            f"本研究取值：HTMT 最大值 {_f(r.get('htmt_max'))}。" if r.get("htmt_max") is not None else "")]


# ───────────────────────── 结果：结构方程 ─────────────────────────

def sem_paths(a: dict, r: dict) -> list[tuple[str, list[str]]]:
    """每条结构方程：[(因变量, [自变量…])]。先用统计结果里实际估计的路径（from → to），没有再按分析计划：{dv, ivs} 和
    [dv, ivs] 两种写法、ivs 写成一个代号都认（和 survey_methods 认的一样；10-21 复查：以前只认 {dv, ivs: [...]}，
    写成 [dv, ivs] 的整条丢掉，ivs 写成一个代号的被拆成一个个字母）"""
    grouped: dict[str, list[str]] = {}
    rows = [p for p in r.get("paths") or [] if isinstance(p, dict) and p.get("from") and p.get("to")]
    pairs = [(str(p["to"]), str(p["from"])) for p in rows]
    if not pairs:
        for p in a.get("paths") or []:
            if isinstance(p, dict):
                dv, ivs = p.get("dv"), p.get("ivs")
            elif isinstance(p, (list, tuple)) and len(p) == 2:
                dv, ivs = p
            else:
                continue
            pairs += [(str(dv), str(iv)) for iv in ([ivs] if isinstance(ivs, str) else ivs or []) if dv and iv]
    for dv, iv in pairs:
        if iv not in grouped.setdefault(dv, []):
            grouped[dv].append(iv)
    return [(dv, ivs) for dv, ivs in grouped.items() if ivs]


def f_sem(a: dict, r: dict, names: dict) -> list:
    paths = sem_paths(a, r)
    dvs = [dv for dv, _ivs in paths]
    hyp = {(str(h.get("from")), str(h.get("to"))): str(h.get("id"))
           for h in a.get("hypotheses") or [] if isinstance(h, dict) and h.get("id")}
    hyp.update({(str(p["from"]), str(p["to"])): str(p["hypothesis"]) for p in r.get("paths") or []
                if isinstance(p, dict) and p.get("from") and p.get("to") and p.get("hypothesis")})
    latent = [str(c) for c in (a.get("latent") or {})] if isinstance(a.get("latent"), dict) else []
    exo = [c for c in latent if c not in dvs]
    eqs = []
    for dv, ivs in paths:
        terms = []
        for iv in ivs:
            coef = r"\beta" if iv in dvs else r"\gamma"
            terms.append(coef + _sub(hyp.get((iv, dv), iv)) + r"\," + sym(iv))
        eqs.append(_wrap(sym(dv), terms + [r"\zeta" + _sub(dv)]))
    fit = r.get("fit") or {}
    out = [entry("sem_structural", "结构方程模型的测量模型与结构模型", "结果", "基于结构方程模型的作用机制分析", [
        r"\mathbf{x}=\boldsymbol{\Lambda}_{x}\boldsymbol{\xi}+\boldsymbol{\delta},\qquad \mathbf{y}=\boldsymbol{\Lambda}_{y}\boldsymbol{\eta}+\boldsymbol{\varepsilon}",
        r"\boldsymbol{\eta}=\mathbf{B}\boldsymbol{\eta}+\boldsymbol{\Gamma}\boldsymbol{\xi}+\boldsymbol{\zeta}"] + eqs,
        r"式中，$\boldsymbol{\xi}$ 为外生潜变量向量，$\boldsymbol{\eta}$ 为内生潜变量向量；$\mathbf{x}$、$\mathbf{y}$ 为对应的观测题项；"
        r"$\boldsymbol{\Lambda}_{x}$、$\boldsymbol{\Lambda}_{y}$ 为因子载荷矩阵；$\boldsymbol{\delta}$、$\boldsymbol{\varepsilon}$ 为测量误差；"
        r"$\mathbf{B}$ 为内生潜变量之间的路径系数矩阵，$\boldsymbol{\Gamma}$ 为外生潜变量对内生潜变量的路径系数矩阵，"
        r"$\boldsymbol{\zeta}$ 为结构方程的残差。"
        + (f"本研究的外生潜变量为{_listed(exo, names)}，内生潜变量为{_listed(dict.fromkeys(dvs), names)}；"
           r"后面各式逐条写出结构方程，$\gamma$、$\beta$ 分别为外生、内生潜变量的路径系数，下标为对应的研究假设编号，"
           r"$\zeta$ 为残差。" if eqs else ""),
        "路径系数、显著性与假设是否成立放在路径系数表里，正文逐条解读。"),
        entry("sem_estimation", "最大似然估计的拟合函数", "结果", "基于结构方程模型的作用机制分析", [
            r"F_{\mathrm{ML}}=\ln\left|\boldsymbol{\Sigma}(\boldsymbol{\theta})\right|+\mathrm{tr}\left[\mathbf{S}\,\boldsymbol{\Sigma}(\boldsymbol{\theta})^{-1}\right]-\ln\left|\mathbf{S}\right|-p,\qquad \chi^{2}=(N-1)\,\hat{F}_{\mathrm{ML}}"],
            r"式中，$\mathbf{S}$ 为样本协方差矩阵；$\boldsymbol{\Sigma}(\boldsymbol{\theta})$ 为模型隐含的协方差矩阵，$\boldsymbol{\theta}$ 为待估参数；"
            r"$p$ 为观测变量个数；$N$ 为样本量；$\hat{F}_{\mathrm{ML}}$ 为拟合函数的最小值。", required=False)]
    out += f_fit(fit, "结果", "基于结构方程模型的作用机制分析")
    chains = [c for c in a.get("indirect") or [] if isinstance(c, list) and len(c) >= 3]
    if chains:
        text = "；".join("→".join(names.get(str(c), str(c)) for c in chain) for chain in chains)
        out.append(entry("sem_indirect", "中介（间接）效应", "结果", "基于结构方程模型的作用机制分析", [
            r"\mathrm{IE}=a\,b,\qquad z=\frac{a\,b}{\sqrt{b^{2}s_{a}^{2}+a^{2}s_{b}^{2}}}"],
            r"式中，$a$ 为自变量到中介变量的路径系数，$b$ 为中介变量到结果变量的路径系数；$s_{a}$、$s_{b}$ 为两者的标准误；"
            r"$\mathrm{IE}$ 为间接效应（链上各路径系数之积），$z$ 为 Sobel 检验统计量。另按路径系数估计值的抽样分布做蒙特卡洛抽样，"
            r"取间接效应的 95% 置信区间，区间不含 0 即间接效应显著。", f"本研究检验的中介链：{text}。"))
    return out


def f_fit(fit: dict, chapter: str, where: str) -> list:
    return [entry("sem_fit", "模型拟合指标", chapter, where, [
        r"\mathrm{RMSEA}=\sqrt{\frac{\max\left(\chi^{2}-df,\,0\right)}{df\,(N-1)}}",
        r"\mathrm{CFI}=1-\frac{\max\left(\chi^{2}-df,\,0\right)}{\max\left(\chi_{0}^{2}-df_{0},\,\chi^{2}-df,\,0\right)}",
        r"\mathrm{TLI}=\frac{\chi_{0}^{2}/df_{0}-\chi^{2}/df}{\chi_{0}^{2}/df_{0}-1}",
        r"\mathrm{SRMR}=\sqrt{\frac{2}{p(p+1)}\sum_{i=1}^{p}\sum_{j=1}^{i}\left(\frac{s_{ij}-\hat{\sigma}_{ij}}{\sqrt{s_{ii}\,s_{jj}}}\right)^{2}}"],
        r"式中，$\chi^{2}$、$df$ 为所设模型的卡方值与自由度；$\chi_{0}^{2}$、$df_{0}$ 为各观测变量互不相关的基准模型的卡方值与自由度；"
        r"$N$ 为样本量；$p$ 为观测变量个数；$s_{ij}$、$\hat{\sigma}_{ij}$ 为样本协方差与模型隐含协方差。参考标准："
        r"$\chi^{2}/df$ 不超过 3（5 以内可接受），RMSEA、SRMR 不超过 0.05（0.08 以内可接受），CFI、TLI 不低于 0.95（0.90 以上可接受）。",
        f"本研究取值：χ²/df = {_f(fit.get('chi2_df'))}，RMSEA = {_f(fit.get('rmsea'))}，SRMR = {_f(fit.get('srmr'))}，"
        f"CFI = {_f(fit.get('cfi'))}，TLI = {_f(fit.get('tli'))}；未达标的指标如实写。" if fit else ""),
        entry("sem_fit_more", "其他拟合指标：GFI、AGFI、NFI、IFI", chapter, where, [
            r"\mathrm{GFI}=1-\frac{\mathrm{tr}\left[\left(\hat{\boldsymbol{\Sigma}}^{-1}\mathbf{S}-\mathbf{I}\right)^{2}\right]}{\mathrm{tr}\left[\left(\hat{\boldsymbol{\Sigma}}^{-1}\mathbf{S}\right)^{2}\right]},\qquad \mathrm{AGFI}=1-\frac{p(p+1)}{2\,df}\left(1-\mathrm{GFI}\right)",
            r"\mathrm{NFI}=\frac{\chi_{0}^{2}-\chi^{2}}{\chi_{0}^{2}},\qquad \mathrm{IFI}=\frac{\chi_{0}^{2}-\chi^{2}}{\chi_{0}^{2}-df}"],
            r"式中，$\hat{\boldsymbol{\Sigma}}$ 为模型隐含的协方差矩阵，$\mathbf{S}$ 为样本协方差矩阵，$\mathbf{I}$ 为单位矩阵，其余符号同上。"
            r"GFI、NFI、IFI 不低于 0.95（0.90 以上可接受），AGFI 不低于 0.90（0.80 以上可接受）。",
            f"本研究取值：GFI = {_f(fit.get('gfi'))}，AGFI = {_f(fit.get('agfi'))}，NFI = {_f(fit.get('nfi'))}，IFI = {_f(fit.get('ifi'))}。"
            if fit else "", required=False)]


# ───────────────────────── 结果：回归类模型 ─────────────────────────

def _terms(codes: list[str], coef: str, start: int = 1) -> list[str]:
    return [coef + "_{" + str(i) + r"}\," + sym(c) for i, c in enumerate(codes, start=start)]


def _cat_text(cats: list[str], names: dict) -> str:
    if not cats:
        return ""
    return (f"$D_{{m}}$ 为类别变量（{'、'.join(names.get(c, c) for c in cats)}）以对照组为基准的虚拟变量，"
            r"$\delta_{m}$ 为其系数；")


def f_regression(a: dict, r: dict, names: dict) -> list:
    cats = _dummies(r)
    all_vars = [str(v) for v in (a.get("ivs") or [])] + [str(v) for v in (a.get("controls") or [])]
    cont = [v for v in all_vars if v not in cats]
    dv = str(a.get("dv") or "Y")
    terms = [r"\beta_{0}"] + _terms(cont, r"\beta") + ([r"\sum_{m}\delta_{m}D_{m}"] if cats else []) + [r"\varepsilon"]
    return [entry("ols", "多元线性回归模型与决定系数", "结果", "影响因素分析", [
        _wrap(sym(dv), terms),
        r"R^{2}=1-\frac{SS_{E}}{SS_{T}},\qquad \bar{R}^{2}=1-\left(1-R^{2}\right)\frac{n-1}{n-q-1}"],
        f"式中，${sym(dv)}$ 为{r.get('dv_label') or names.get(dv, dv)}，{_named(cont, names)}；" + _cat_text(cats, names)
        + r"$\beta_{0}$ 为截距，$\beta_{j}$ 为偏回归系数，表示控制其他变量后该变量每增加一个单位因变量的平均变化；$\varepsilon$ 为随机误差；"
        r"$SS_{E}$、$SS_{T}$ 为残差平方和与总平方和，$n$ 为样本量，$q$ 为自变量（含虚拟变量）个数，$\bar{R}^{2}$ 为调整后的决定系数。"
        r"系数用最小二乘法估计，标准误用 HC3 异方差稳健估计。",
        f"本研究取值：R² = {_f(r.get('r2'))}，调整后 R² = {_f(r.get('adj_r2'))}，n = {r.get('n', '—')}。" if r.get("r2") is not None else ""),
        entry("vif", "多重共线性：方差膨胀因子", "结果", "影响因素分析", [r"\mathrm{VIF}_{j}=\frac{1}{1-R_{j}^{2}}"],
              r"式中，$R_{j}^{2}$ 为第 $j$ 个自变量对其余自变量回归的决定系数；VIF 小于 5（宽松标准 10）时可认为不存在严重的多重共线性。"),
        entry("hc3", "HC3 异方差稳健标准误", "结果", "影响因素分析", [
            r"\widehat{\mathrm{Var}}_{\mathrm{HC3}}\left(\hat{\boldsymbol{\beta}}\right)=\left(\mathbf{X}^{\top}\mathbf{X}\right)^{-1}\mathbf{X}^{\top}\boldsymbol{\Omega}\mathbf{X}\left(\mathbf{X}^{\top}\mathbf{X}\right)^{-1},\qquad \boldsymbol{\Omega}=\mathrm{diag}\left(\frac{\hat{e}_{i}^{2}}{\left(1-h_{ii}\right)^{2}}\right)"],
            r"式中，$\mathbf{X}$ 为设计矩阵；$\hat{e}_{i}$ 为第 $i$ 个样本的残差；$h_{ii}$ 为帽子矩阵 $\mathbf{X}\left(\mathbf{X}^{\top}\mathbf{X}\right)^{-1}\mathbf{X}^{\top}$ "
            r"的第 $i$ 个对角元。HC3 标准误在残差方差不相等时仍然有效。", required=False)]


def f_regression_more(index: int, a: dict, r: dict, names: dict) -> dict:
    """第二个及以后的回归模型（换了因变量）：只写模型式，决定系数、共线性、稳健标准误的公式第一个模型已经写过
    （10-21 复查：以前只给第一个回归出公式，第二个模型的式子报告里没有）"""
    cats = _dummies(r)
    all_vars = [str(v) for v in (a.get("ivs") or [])] + [str(v) for v in (a.get("controls") or [])]
    cont = [v for v in all_vars if v not in cats]
    dv = str(a.get("dv") or "Y")
    label = r.get("dv_label") or names.get(dv, dv)
    terms = [r"\beta_{0}"] + _terms(cont, r"\beta") + ([r"\sum_{m}\delta_{m}D_{m}"] if cats else []) + [r"\varepsilon"]
    return entry(f"ols_{index}", f"第 {index} 个回归模型（因变量：{label}）", "结果", "影响因素分析", [_wrap(sym(dv), terms)],
                 f"式中，${sym(dv)}$ 为{label}，{_named(cont, names)}；" + _cat_text(cats, names)
                 + r"其余符号的含义与第一个回归模型相同。",
                 f"本研究取值：R² = {_f(r.get('r2'))}，调整后 R² = {_f(r.get('adj_r2'))}，n = {r.get('n', '—')}。"
                 if r.get("r2") is not None else "")


def f_logistic(a: dict, r: dict, names: dict) -> list:
    cats = _dummies(r)
    all_vars = [str(v) for v in (a.get("ivs") or [])] + [str(v) for v in (a.get("controls") or [])]
    cont = [v for v in all_vars if v not in cats]
    dv = str(a.get("dv") or "Y")
    lhs = r"\ln\frac{P\left(" + sym(dv) + r"=1\right)}{1-P\left(" + sym(dv) + r"=1\right)}"
    terms = [r"\beta_{0}"] + _terms(cont, r"\beta") + ([r"\sum_{m}\delta_{m}D_{m}"] if cats else [])
    event = r.get("event_label") or "事件发生"
    return [entry("logit", "二元 Logistic 回归模型与优势比", "结果", "行为决定因素分析", [_wrap(lhs, terms), r"\mathrm{OR}_{j}=e^{\beta_{j}}"],
                  f"式中，${sym(dv)}$ 为{r.get('dv_label') or names.get(dv, dv)}，$P({sym(dv)}=1)$ 为“{event}”的概率；"
                  f"{_named(cont, names)}；" + _cat_text(cats, names)
                  + r"$\beta_{j}$ 为回归系数，用最大似然法估计；$\mathrm{OR}_{j}$ 为优势比，表示该变量增加一个单位时事件发生的优势"
                  r"变为原来的倍数，大于 1 为促进、小于 1 为抑制。"),
            entry("mcfadden", "Logistic 回归的整体检验与 McFadden 伪 R²", "结果", "行为决定因素分析", [
                r"G^{2}=-2\left(\ln L_{0}-\ln L_{M}\right),\qquad R_{\mathrm{McF}}^{2}=1-\frac{\ln L_{M}}{\ln L_{0}}"],
                r"式中，$\ln L_{M}$ 为所设模型的对数似然值，$\ln L_{0}$ 为只含截距的模型的对数似然值；$G^{2}$ 为似然比统计量，"
                r"服从自由度为自变量个数的 $\chi^{2}$ 分布，显著说明模型整体有解释力；McFadden 伪 $R^{2}$ 一般 0.2–0.4 即表示拟合较好。",
                f"本研究取值：McFadden R² = {_f(r.get('mcfadden_r2'))}，似然比检验 p {_p(r.get('llr_p'))}，n = {r.get('n', '—')}。"
                if r.get("mcfadden_r2") is not None else "")]


def f_moderation(items: list, names: dict) -> list:
    a, r = items[0]
    x, w, dv = str(a.get("x") or "X"), str(a.get("w") or "W"), str(a.get("dv") or "Y")
    xt, wt = r"\tilde{" + sym(x) + "}", r"\tilde{" + sym(w) + "}"
    controls = [str(c) for c in (a.get("controls") or [])]
    terms = ([r"b_{0}", r"b_{1}\," + xt, r"b_{2}\," + wt, r"b_{3}\," + xt + r"\," + wt]
             + ([r"\sum_{k}c_{k}Z_{k}"] if controls else []) + [r"\varepsilon"])
    others = list(dict.fromkeys(str(b.get("w")) for b, _ in items[1:] if b.get("w") and str(b.get("w")) != w))

    def label(code: str, role: str) -> str:
        return r.get(f"{role}_label") or names.get(code, code)
    return [entry("moderation", "调节效应模型、简单斜率与 Johnson–Neyman 区间", "结果", "调节效应分析", [
        _wrap(sym(dv), terms), r"\theta\left(\tilde{W}\right)=b_{1}+b_{3}\tilde{W}",
        r"\frac{\left(b_{1}+b_{3}\tilde{W}\right)^{2}}{\widehat{\mathrm{Var}}\left(b_{1}\right)+2\tilde{W}\,\widehat{\mathrm{Cov}}\left(b_{1},b_{3}\right)+\tilde{W}^{2}\,\widehat{\mathrm{Var}}\left(b_{3}\right)}=z_{0.975}^{2}"],
        f"式中，${sym(dv)}$ 为{label(dv, 'dv')}，${xt}$ 为均值中心化后的{label(x, 'x')}，${wt}$（即 $\\tilde{{W}}$）为均值中心化后的调节变量"
        f"{label(w, 'w')}" + (f"，$Z_{{k}}$ 为控制变量（{'、'.join(names.get(c, c) for c in controls)}）" if controls else "")
        + r"；$b_{3}$ 为交互项系数，显著即调节效应成立；$\theta(\tilde{W})$ 为调节变量取某一水平时自变量的简单斜率，"
        r"取调节变量低于均值一个标准差、等于均值、高于均值一个标准差三个水平报告；第三式解出的 $\tilde{W}$（加回均值）即 "
        r"Johnson–Neyman 区间的端点，据此划出简单斜率在 5% 水平上显著的调节变量取值范围。标准误用 HC3 稳健估计。"
        + (f"另{len(others)}项调节分析把调节变量换成{'、'.join(names.get(o, o) for o in others)}，模型形式相同。" if others else ""),
        f"本研究取值：交互项系数 b = {_f(r.get('interaction_b'))}，p {_p(r.get('interaction_p'))}。" if r.get("interaction_b") is not None else ""),
        entry("moderation_f_change", "交互项的增量检验", "结果", "调节效应分析", [
            r"\Delta R^{2}=R_{\mathrm{full}}^{2}-R_{\mathrm{reduced}}^{2},\qquad F_{\Delta}=\frac{\Delta R^{2}}{\left(1-R_{\mathrm{full}}^{2}\right)/\left(n-q-1\right)}"],
            r"式中，$R_{\mathrm{full}}^{2}$、$R_{\mathrm{reduced}}^{2}$ 为含与不含交互项的模型的决定系数；$n$ 为样本量；$q$ 为完整模型的自变量个数；"
            r"$F_{\Delta}$ 服从自由度为 $(1,\,n-q-1)$ 的 $F$ 分布。", required=False)]


# ───────────────────────── 结果：差异与关联检验 ─────────────────────────

def f_crosstab() -> dict:
    return entry("chi_square", "卡方独立性检验与 Cramér's V", "结果", "群体差异分析", [
        r"\chi^{2}=\sum_{i=1}^{R}\sum_{j=1}^{C}\frac{\left(O_{ij}-E_{ij}\right)^{2}}{E_{ij}},\qquad E_{ij}=\frac{n_{i\cdot}\,n_{\cdot j}}{n}",
        r"V=\sqrt{\frac{\chi^{2}}{n\left[\min(R,C)-1\right]}}"],
        r"式中，$O_{ij}$、$E_{ij}$ 为第 $i$ 行第 $j$ 列的实际频数与期望频数；$n_{i\cdot}$、$n_{\cdot j}$ 为行、列合计；$n$ 为总样本量；"
        r"$R$、$C$ 为行数与列数，自由度为 $(R-1)(C-1)$；$V$ 为 Cramér's V 效应量（0.1、0.3、0.5 分别对应弱、中、强关联）。"
        r"期望频数小于 5 的格子过多时改用 Fisher 精确检验。")


def f_ttest() -> dict:
    return entry("t_test", "两组均值比较：Welch t 检验与效应量", "结果", "群体差异分析", [
        r"t=\frac{\bar{x}_{1}-\bar{x}_{2}}{\sqrt{\frac{s_{1}^{2}}{n_{1}}+\frac{s_{2}^{2}}{n_{2}}}},\qquad \nu=\frac{\left(\frac{s_{1}^{2}}{n_{1}}+\frac{s_{2}^{2}}{n_{2}}\right)^{2}}{\frac{\left(s_{1}^{2}/n_{1}\right)^{2}}{n_{1}-1}+\frac{\left(s_{2}^{2}/n_{2}\right)^{2}}{n_{2}-1}}",
        r"d=\frac{\bar{x}_{1}-\bar{x}_{2}}{s_{p}},\qquad s_{p}=\sqrt{\frac{(n_{1}-1)s_{1}^{2}+(n_{2}-1)s_{2}^{2}}{n_{1}+n_{2}-2}}"],
        r"式中，$\bar{x}_{1}$、$\bar{x}_{2}$ 为两组均值；$s_{1}^{2}$、$s_{2}^{2}$ 为两组方差；$n_{1}$、$n_{2}$ 为两组样本量；$\nu$ 为 Welch–Satterthwaite "
        r"校正后的自由度；$s_{p}$ 为合并标准差；$d$ 为 Cohen's d（0.2、0.5、0.8 分别对应小、中、大效应）。Welch t 检验不要求两组方差"
        r"相等，同时报告 Levene 检验（中位数版）的结果。")


def f_levene() -> dict:
    return entry("levene", "方差齐性：Levene 检验（中位数版）", "结果", "群体差异分析", [
        r"W=\frac{n-k}{k-1}\cdot\frac{\sum_{g=1}^{k}n_{g}\left(\bar{z}_{g\cdot}-\bar{z}_{\cdot\cdot}\right)^{2}}{\sum_{g=1}^{k}\sum_{i=1}^{n_{g}}\left(z_{gi}-\bar{z}_{g\cdot}\right)^{2}},\qquad z_{gi}=\left|x_{gi}-\tilde{x}_{g}\right|"],
        r"式中，$x_{gi}$ 为第 $g$ 组第 $i$ 个样本的取值，$\tilde{x}_{g}$ 为第 $g$ 组的中位数；$\bar{z}_{g\cdot}$、$\bar{z}_{\cdot\cdot}$ 为组内与总的均值；"
        r"$k$ 为组数，$n$ 为总样本量；$W$ 服从自由度为 $(k-1,\,n-k)$ 的 $F$ 分布，显著说明各组方差不齐。", required=False)


def f_anova(items: list) -> list:
    welch = any(str(r.get("test_used") or "").startswith("welch") for _, r in items)
    latex = [r"F=\frac{SS_{B}/(k-1)}{SS_{W}/(n-k)},\qquad SS_{B}=\sum_{g=1}^{k}n_{g}\left(\bar{x}_{g}-\bar{x}\right)^{2},\quad SS_{W}=\sum_{g=1}^{k}\sum_{i=1}^{n_{g}}\left(x_{gi}-\bar{x}_{g}\right)^{2}",
             r"\eta^{2}=\frac{SS_{B}}{SS_{B}+SS_{W}}"]
    if welch:
        latex.append(r"F_{\mathrm{W}}=\frac{\sum_{g}w_{g}\left(\bar{x}_{g}-\bar{x}_{w}\right)^{2}/(k-1)}{1+\frac{2(k-2)}{k^{2}-1}\sum_{g}\frac{\left(1-w_{g}/\sum_{h}w_{h}\right)^{2}}{n_{g}-1}},\qquad w_{g}=\frac{n_{g}}{s_{g}^{2}}")
    return [entry("anova", "多组均值比较：单因素方差分析与效应量", "结果", "群体差异分析", latex,
                  r"式中，$k$ 为组数；$n$ 为总样本量；$n_{g}$、$\bar{x}_{g}$ 为第 $g$ 组的样本量与均值；$\bar{x}$ 为总均值；$SS_{B}$、$SS_{W}$ 为组间、"
                  r"组内离差平方和；$\eta^{2}$ 为效应量（0.01、0.06、0.14 分别对应小、中、大效应）。"
                  + (r"$s_{g}^{2}$ 为第 $g$ 组方差，$w_{g}$ 为权重，$\bar{x}_{w}=\sum_{g}w_{g}\bar{x}_{g}/\sum_{g}w_{g}$ 为加权均值，$F_{\mathrm{W}}$ 为 "
                     r"Welch 方差分析统计量。" if welch else "")
                  + r"Levene 检验方差齐时用经典方差分析、事后比较用 Tukey HSD；方差不齐时改用 Welch 方差分析、事后比较用 Games–Howell 法。")]


def f_correlation(method: str) -> dict:
    if method == "spearman":
        # 和 Pearson 各一组（两种都做了的都要写，10-21 复查）：标记名不同，公式核查分得开
        return entry("correlation_spearman", "Spearman 秩相关系数", "结果", "变量关系分析", [
            r"\rho=1-\frac{6\sum_{i=1}^{n}d_{i}^{2}}{n\left(n^{2}-1\right)}"],
            r"式中，$d_{i}$ 为第 $i$ 个样本在两个变量上的秩次之差；$n$ 为样本量；有相同秩次时按秩次的 Pearson 相关计算。")
    return entry("correlation", "Pearson 相关系数", "结果", "变量关系分析", [
        r"r=\frac{\sum_{i=1}^{n}\left(x_{i}-\bar{x}\right)\left(y_{i}-\bar{y}\right)}{\sqrt{\sum_{i=1}^{n}\left(x_{i}-\bar{x}\right)^{2}\sum_{i=1}^{n}\left(y_{i}-\bar{y}\right)^{2}}}"],
        r"式中，$x_{i}$、$y_{i}$ 为第 $i$ 个样本两个变量的取值；$\bar{x}$、$\bar{y}$ 为均值；$n$ 为样本量；$r$ 介于 $-1$ 与 1 之间，"
        r"绝对值越大关联越强。")


def f_holm() -> dict:
    return entry("holm", "多重比较的 Holm 校正", "结果", "第一次用到多重比较校正的那一节", [
        r"p_{(i)}^{\mathrm{Holm}}=\max_{j\le i}\left\{\min\left[\left(m-j+1\right)p_{(j)},\,1\right]\right\}"],
        r"式中，$m$ 为同时检验的次数；$p_{(1)}\le p_{(2)}\le\cdots\le p_{(m)}$ 为从小到大排列的原始 $p$ 值；$p_{(i)}^{\mathrm{Holm}}$ 为校正后的 "
        r"$p$ 值，与显著性水平比较。", required=False)


# ───────────────────────── 结果：专项方法 ─────────────────────────

def f_cluster(r: dict) -> dict:
    return entry("kmeans", "K-means 聚类与轮廓系数", "结果", "人群划分", [
        r"z_{ij}=\frac{x_{ij}-\bar{x}_{j}}{s_{j}}",
        r"J=\sum_{c=1}^{K}\sum_{\mathbf{z}_{i}\in C_{c}}\left\|\mathbf{z}_{i}-\boldsymbol{\mu}_{c}\right\|^{2}",
        r"s(i)=\frac{b(i)-a(i)}{\max\left\{a(i),\,b(i)\right\}}"],
        r"式中，$x_{ij}$ 为第 $i$ 个样本在第 $j$ 个聚类变量上的取值，$\bar{x}_{j}$、$s_{j}$ 为该变量的均值与标准差，$z_{ij}$ 为标准化值；"
        r"$K$ 为类数，$C_{c}$ 为第 $c$ 类，$\boldsymbol{\mu}_{c}$ 为其中心，$J$ 为类内离差平方和（K-means 使之最小）；"
        r"$a(i)$ 为样本 $i$ 到本类其他样本的平均距离，$b(i)$ 为到最近的其他类的平均距离；全部样本 $s(i)$ 的均值越大分类越清晰，"
        r"据此确定类数 $K$。",
        f"本研究取值：K = {r.get('k', '—')}，平均轮廓系数 {_f(r.get('silhouette'))}。" if r.get("silhouette") is not None else "")


def f_tree(r: dict) -> dict:
    return entry("cart_gini", "分类树的分裂准则（基尼不纯度）", "结果", "分类规则分析", [
        r"G(t)=1-\sum_{k=1}^{K}p_{k}^{2}(t),\qquad \Delta G=G(t)-\frac{n_{L}}{n_{t}}G\left(t_{L}\right)-\frac{n_{R}}{n_{t}}G\left(t_{R}\right)"],
        r"式中，$p_{k}(t)$ 为节点 $t$ 中第 $k$ 类样本的比例；$t_{L}$、$t_{R}$ 为分裂后的左右子节点，$n_{t}$、$n_{L}$、$n_{R}$ 为对应的样本数；"
        r"每次选使 $\Delta G$ 最大的变量与切分点分裂，并用分层 K 折交叉验证评估分类准确率与 AUC。",
        f"本研究取值：交叉验证准确率 {_f((r.get('cv_accuracy') or 0) * 100, 1)}%，AUC 为 {_f(r.get('cv_auc'))}。"
        if r.get("cv_accuracy") is not None else "")


def f_cooccurrence() -> dict:
    return entry("cooccurrence", "多选项共现：Jaccard 系数、提升度与 φ 系数", "结果", "共现结构分析", [
        r"J(A,B)=\frac{n_{AB}}{n_{A}+n_{B}-n_{AB}},\qquad \mathrm{Lift}(A,B)=\frac{n\,n_{AB}}{n_{A}\,n_{B}}",
        r"\varphi=\frac{n\,n_{AB}-n_{A}n_{B}}{\sqrt{n_{A}n_{B}\left(n-n_{A}\right)\left(n-n_{B}\right)}}"],
        r"式中，$n$ 为作答人数；$n_{A}$、$n_{B}$ 为选择 $A$、$B$ 的人数；$n_{AB}$ 为同时选择两项的人数；提升度大于 1 表示两项同时被选的"
        r"频率高于相互独立时的期望；$\varphi$ 为两个选项是否被选的相关系数，显著性用 Fisher 精确检验并做 Holm 校正。")


def f_correspondence() -> dict:
    return entry("ca_inertia", "对应分析的总惯量与奇异值分解", "结果", "对应分析", [
        r"\mathbf{S}=\mathbf{D}_{r}^{-1/2}\left(\mathbf{P}-\mathbf{r}\mathbf{c}^{\top}\right)\mathbf{D}_{c}^{-1/2}=\mathbf{U}\boldsymbol{\Sigma}\mathbf{V}^{\top},\qquad \mathrm{In}=\frac{\chi^{2}}{n}=\sum_{k}\sigma_{k}^{2}"],
        r"式中，$\mathbf{P}$ 为对应表的相对频数矩阵，$\mathbf{r}$、$\mathbf{c}$ 为行、列边际比例，$\mathbf{D}_{r}$、$\mathbf{D}_{c}$ 为以它们为对角元的矩阵；"
        r"对标准化残差矩阵 $\mathbf{S}$ 做奇异值分解，$\sigma_{k}$ 为第 $k$ 个奇异值，$\sigma_{k}^{2}$ 为第 $k$ 维的主惯量，$\mathrm{In}$ 为总惯量；"
        r"前两维主惯量之和占总惯量的比例即二维图的解释度。")


def f_funnel() -> list:
    return [entry("funnel", "转化漏斗的阶段转化率", "结果", "转化漏斗分析", [
        r"c_{k}=\frac{N_{k}}{N_{k-1}},\qquad C_{k}=\frac{N_{k}}{N_{1}}=\prod_{j=2}^{k}c_{j}"],
        r"式中，$N_{k}$ 为到达第 $k$ 个阶段的人数；$c_{k}$ 为第 $k$ 阶段相对上一阶段的转化率；$C_{k}$ 为相对第一阶段的累计转化率。"
        r"各群体在每个阶段的到达率差异用卡方检验，并做 Holm 校正。"),
        entry("wilson", "比例的 Wilson 置信区间", "结果", "转化漏斗分析", [
            r"\frac{\hat{p}+\frac{z^{2}}{2n}\pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n}+\frac{z^{2}}{4n^{2}}}}{1+\frac{z^{2}}{n}}"],
            r"式中，$\hat{p}$ 为样本比例；$n$ 为分母人数；$z$ 为置信水平对应的标准正态分位数（95% 置信区间取 1.96）。", required=False)]


def f_kano() -> dict:
    return entry("kano_better_worse", "Kano 模型的 Better–Worse 系数", "结果", "需求优先级分析", [
        r"\mathrm{Better}=\frac{A+O}{A+O+M+I},\qquad \mathrm{Worse}=-\frac{O+M}{A+O+M+I}"],
        r"式中，$A$、$O$、$M$、$I$ 分别为把某项功能归为魅力属性、期望属性、必备属性、无差异属性的人数；Better 系数越大，"
        r"提供该功能带来的满意度提升越大，Worse 系数的绝对值越大，不提供该功能造成的不满越大；以各功能两系数的均值为界划分四象限，"
        r"确定功能的提供顺序。")


def f_psm() -> dict:
    return entry("psm", "价格敏感度测试（PSM）的四个价格点", "结果", "价格分析", [
        r"F_{\mathrm{TC}}\left(\mathrm{PMC}\right)=1-F_{\mathrm{C}}\left(\mathrm{PMC}\right),\qquad F_{\mathrm{TE}}\left(\mathrm{PME}\right)=1-F_{\mathrm{E}}\left(\mathrm{PME}\right)",
        r"F_{\mathrm{TC}}\left(\mathrm{OPP}\right)=F_{\mathrm{TE}}\left(\mathrm{OPP}\right),\qquad F_{\mathrm{C}}\left(\mathrm{IPP}\right)=F_{\mathrm{E}}\left(\mathrm{IPP}\right)"],
        r"式中，$F_{\mathrm{TC}}$、$F_{\mathrm{C}}$ 为认为“太便宜”“便宜”的累计比例（价格越低比例越高），$F_{\mathrm{E}}$、$F_{\mathrm{TE}}$ 为认为“贵”“太贵”的"
        r"累计比例（价格越高比例越高），$1-F_{\mathrm{C}}$、$1-F_{\mathrm{E}}$ 即认为“不便宜”“不贵”的比例；PMC、PME 为可接受价格区间的下限与上限，"
        r"OPP 为最优价格点，IPP 为无差异价格点，各价格点取两条曲线的交点，交点在相邻两个价格之间线性插值。")


def f_conjoint() -> dict:
    return entry("conjoint", "联合分析的效用模型与属性重要性", "结果", "产品组合偏好分析", [
        r"U_{s}=\beta_{0}+\sum_{a=1}^{A}\sum_{\ell=1}^{L_{a}}\beta_{a\ell}\,x_{sa\ell}",
        r"I_{a}=\frac{\max_{\ell}\beta_{a\ell}-\min_{\ell}\beta_{a\ell}}{\sum_{a'=1}^{A}\left(\max_{\ell}\beta_{a'\ell}-\min_{\ell}\beta_{a'\ell}\right)}\times100\%"],
        r"式中，$U_{s}$ 为受访者对卡片 $s$ 的总效用（评分）；$x_{sa\ell}$ 为卡片 $s$ 在属性 $a$ 上取第 $\ell$ 个水平的效应编码；"
        r"$\beta_{a\ell}$ 为该水平的成分效用；$A$ 为属性个数，$L_{a}$ 为属性 $a$ 的水平数；$I_{a}$ 为属性 $a$ 的相对重要性。"
        r"模型拟合用 Pearson R 与 Kendall τ，并用保留卡检验预测准确性。")


def f_nps() -> dict:
    return entry("nps", "净推荐值", "结果", "推荐意愿分析", [
        r"\mathrm{NPS}=\frac{N_{\mathrm{P}}-N_{\mathrm{D}}}{N}\times100"],
        r"式中，$N_{\mathrm{P}}$ 为推荐者人数（打 9–10 分），$N_{\mathrm{D}}$ 为贬损者人数（打 0–6 分），$N$ 为作答总人数。")


# ───────────────────────── 按本研究挑公式 ─────────────────────────

def used_analyses(plan: dict | None, results: dict | None) -> list[tuple[dict, dict]]:
    """做了的分析：计划里有、结果里有、没报错（计划改了没重跑的不算）"""
    res = (results or {}).get("results") or {}
    out = []
    for a in (plan or {}).get("analyses") or []:
        if not isinstance(a, dict) or not a.get("id"):
            continue
        r = res.get(a["id"])
        if isinstance(r, dict) and not r.get("error"):
            out.append((a, r))
    return out


def build(ws: Path) -> list[dict]:
    plan = _load(ws / "ANALYSIS_PLAN.json")
    results = _load(ws / "STATISTICAL_RESULTS.json")
    design = _load(ws / "SAMPLE_SIZE_PLAN.json")
    names = names_of(ws, plan, results)
    by_type: dict[str, list] = {}
    for a, r in used_analyses(plan, results):
        by_type.setdefault(str(a.get("type") or r.get("type") or ""), []).append((a, r))
    out: list[dict] = []
    if isinstance(design, dict) and isinstance(design.get("proportion"), dict):
        out.append(f_sample_size(design))
    if "reliability" in by_type:
        out.append(f_reliability(by_type["reliability"]))
    if "efa" in by_type:
        out += f_efa(by_type["efa"][0][1])
    if "cfa" in by_type or "sem" in by_type:
        out += f_cfa((by_type.get("cfa") or by_type["sem"])[0][1], names)
    if "sem" in by_type:
        a, r = by_type["sem"][0]
        out += f_sem(a, r, names)
    elif "cfa" in by_type:
        out += f_fit(by_type["cfa"][0][1].get("fit") or {}, "实施", "信度与效度检验")
    if "regression" in by_type:
        a, r = by_type["regression"][0]
        out += f_regression(a, r, names)
        out += [f_regression_more(i, a2, r2, names) for i, (a2, r2) in enumerate(by_type["regression"][1:], start=2)]
    if "logistic" in by_type:
        a, r = by_type["logistic"][0]
        out += f_logistic(a, r, names)
    if "moderation" in by_type:
        out += f_moderation(by_type["moderation"], names)
    if "crosstab" in by_type or "funnel" in by_type:
        out.append(f_crosstab())
    if "ttest" in by_type:
        out.append(f_ttest())
    if "anova" in by_type:
        out += f_anova(by_type["anova"])
    if "ttest" in by_type or "anova" in by_type:
        out.append(f_levene())
    if "correlation" in by_type:
        methods = dict.fromkeys("spearman" if str(a.get("method") or "") == "spearman" else "pearson"
                                for a, _r in by_type["correlation"])
        out += [f_correlation(method) for method in methods]
    if {"correlation", "funnel", "cooccurrence"} & set(by_type):
        out.append(f_holm())
    if "cluster" in by_type:
        out.append(f_cluster(by_type["cluster"][0][1]))
    if "tree" in by_type:
        out.append(f_tree(by_type["tree"][0][1]))
    if "cooccurrence" in by_type:
        out.append(f_cooccurrence())
    if "correspondence" in by_type:
        out.append(f_correspondence())
    if "funnel" in by_type:
        out += f_funnel()
    if "kano" in by_type:
        out.append(f_kano())
    if "psm" in by_type:
        out.append(f_psm())
    if "conjoint" in by_type:
        out.append(f_conjoint())
    if "nps" in by_type:
        out.append(f_nps())
    return out


def markdown(entries: list[dict]) -> str:
    lines = ["# 报告公式清单（按本研究实际做了的分析生成）", "",
             "每种方法第一次出现时，在介绍这种方法的段落里写它的公式：先用一句话引出（如“信度采用 Cronbach's α 系数衡量，计算公式为：”），"
             "再把下面一组公式原样复制过去——公式前一行的 `<!-- 公式：… -->` 一起复制，公式核查靠它认；公式后面紧跟“式中，……”一段"
             "逐个说明符号（只写符号和常数），再另起一段写本研究的结果（“本研究取值”一行给的数可以直接用）。编号照抄即可，写完运行 "
             "`survey_numbering.py` 会按出现顺序统一重编，正文引用写“式（3）”。标“必写”的每组都要写进正文；“选写”的按篇幅和论证需要写。", ""]
    n = 0
    for chapter in ("设计", "实施", "结果"):
        group = [e for e in entries if e["chapter"] == chapter]
        if not group:
            continue
        lines += [f"## {WHERE[chapter]}", ""]
        for e in group:
            lines += [f"### {e['title']}（{'必写' if e['required'] else '选写'}；放在：{e['where']}）", "", MARK.format(key=e["key"])]
            for latex in e["latex"]:
                n += 1
                lines += ["$$", latex + r" \tag{" + str(n) + "}", "$$"]
            lines += [e["symbols"], ""]
            if e["then"]:
                lines += [e["then"], ""]
    return "\n".join(lines).rstrip() + "\n"


# ───────────────────────── 核查报告 ─────────────────────────

def display_blocks(text: str) -> list[dict]:
    """行间公式：`$$…$$` 写在同一行，或 `$$` 开头到 `$$` 结尾的几行（规则和 Word 导出引擎一致：开块那一行以 `$$` 开头，
    之后第一行以 `$$` 开头或以 `$$` 结尾的就是闭合行）。返回 [{start, end, latex, tail}]，行号从 0 起、按 text.split("\\n") 数；
    tail 是闭合 `$$` 后面的文字（如 `$$ (3)` 的“(3)”）。代码块里的不算。"""
    lines, out, i, fence, comment = text.split("\n"), [], 0, False, False
    while i < len(lines):
        s = lines[i].strip()
        if comment:                                   # HTML 注释里的不算（注释掉的旧公式，10-21 复查：以前也给编了号）
            comment = "-->" not in s
            i += 1
            continue
        if s.startswith("<!--") and "-->" not in s[4:]:
            comment = True
            i += 1
            continue
        if s.startswith("```"):
            fence = not fence
            i += 1
            continue
        if fence or not s.startswith("$$"):
            i += 1
            continue
        rest = s[2:]
        single = re.match(r"^(.+?)\$\$\s*(.*)$", rest)
        if single and single.group(1).strip():
            out.append({"start": i, "end": i, "latex": single.group(1), "tail": single.group(2).strip()})
            i += 1
            continue
        j, body = i + 1, [rest]
        while j < len(lines) and not (lines[j].strip().startswith("$$") or lines[j].strip().endswith("$$")):
            body.append(lines[j])
            j += 1
        tail = ""
        if j < len(lines):
            end = lines[j].strip()
            if end.startswith("$$"):
                tail = end[2:].strip()
            else:
                body.append(end[:-2])
        out.append({"start": i, "end": min(j, len(lines) - 1), "latex": "\n".join(body).strip(), "tail": tail,
                    "open": j >= len(lines)})
        i = j + 1
    return out


def tail_label(tail: str) -> str | None:
    """闭合 `$$` 后面写的编号，认法和 Word 导出引擎一样（md_to_docx.js 的 extractTailLabel）：`\\tag{8}`、括号里的
    `(6)`/`（6）`（后面还可以有字）、裸编号 `8`。10-21 复查：以前只认整个尾巴就是“(6)”，`$$ \\tag{8}`、`$$ 8` 被当成没编号"""
    t = (tail or "").strip()
    if not t:
        return None
    m = (re.search(r"\\tag\{([^}]*)\}", t) or re.search(r"[(（]\s*([^)）]{1,24}?)\s*[)）]", t)
         or re.match(r"^([0-9][0-9A-Za-z.\-′']*)$", t))
    return (m.group(1).strip() or None) if m else None


def tail_rest(tail: str) -> str:
    """闭合 `$$` 后面除了编号以外的字（`$$ (6) 说明` 的“说明”）：编号整理改写公式时不能丢"""
    t = (tail or "").strip()
    for pattern in (r"\\tag\{[^}]*\}", r"[(（]\s*[^)）]{1,24}?\s*[)）]", r"^[0-9][0-9A-Za-z.\-′']*$"):
        if re.search(pattern, t):
            return re.sub(pattern, "", t, count=1).strip()
    return t


def body_of(text: str) -> str:
    """正文（参考文献之前）"""
    return re.split(r"(?m)^#{1,3}\s*参考文献\s*$", text, maxsplit=1)[0]


def check(text: str, entries: list[dict]) -> list[str]:
    """报告里公式的问题（说成人话，按出现顺序）：公式没编号、做了的方法缺必写的公式、公式组后面没有“式中”说明"""
    problems = []
    body = body_of(text)
    lines = body.split("\n")
    blocks = display_blocks(body)
    starts = {b["start"]: b for b in blocks}
    for b in blocks:
        if b.get("open"):
            problems.append(f"第 {b['start'] + 1} 行开始的行间公式没有结尾的 $$：后面的正文都会被当成公式，补上单独一行的 $$")
        elif not TAG_RE.search(b["latex"]) and not tail_label(b["tail"]):
            problems.append(f"第 {b['start'] + 1} 行的公式没有编号：运行 survey_numbering.py 会给行间公式按出现顺序补上编号")
    marks: dict[str, int] = {}
    for no, line in enumerate(lines):
        for m in MARK_RE.finditer(line):
            marks.setdefault(m.group(1), no)

    def next_text(k: int) -> int:
        while k < len(lines) and not lines[k].strip():
            k += 1
        return k
    for e in entries:
        if not e["required"]:
            continue
        at = marks.get(e["key"])
        if at is None:
            problems.append(f"缺少「{e['title']}」的公式（做了这类分析就要写）：从 results/公式清单.md 把这一组连同前一行的 "
                            f"<!-- 公式：{e['key']} --> 复制到“{e['where']}”一节，后面写“式中，……”和本研究的结果")
            continue
        k, steps = next_text(at + 1), 0
        while k < len(lines) and k not in starts and steps < 2:      # 标记和公式之间允许一两行引出的话
            k, steps = next_text(k + 1), steps + 1
        if k not in starts:
            problems.append(f"第 {at + 1} 行的 <!-- 公式：{e['key']} --> 后面没有行间公式：标记写在这组公式的前一行，"
                            "公式用 $$ 单独成段写")
            continue
        last = starts[k]["end"]
        while next_text(last + 1) in starts:                           # 一组几个公式连着写
            last = starts[next_text(last + 1)]["end"]
        following = [ln.strip() for ln in lines[last + 1:] if ln.strip()][:2]
        # “式中”“其中”“上式中”“各式中”都算逐个说明符号（10-21 复查：写成“其中，……”的被报成没有说明）
        if not any(re.match(r"(?:上述|以上)?(?:各|上)?式中|其中", ln) for ln in following):
            problems.append(f"「{e['title']}」的公式后面没有逐个说明符号：公式后面紧跟一段“式中，……”（从公式清单复制后按需要补充）")
    return problems


def report_problems(ws: Path, main_rel: str = "paper/main.md") -> list[str]:
    """后端“报告撰写”交卷前的公式检查（survey_flow.report_structure_problems 调用）：没有分析结果或还没有正文时不查"""
    entries = build(Path(ws))
    if not entries:
        return []
    try:
        text = (Path(ws) / main_rel).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []
    return check(text, entries)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="市调报告的公式清单与公式核查")
    ap.add_argument("--ws", default=".")
    ap.add_argument("--out", default="results/公式清单.md")
    ap.add_argument("--json", default="results/FORMULAS.json")
    ap.add_argument("--check", metavar="MAIN_MD")
    args = ap.parse_args(argv)
    ws = Path(args.ws)
    if not (ws / "ANALYSIS_PLAN.json").is_file() or not (ws / "STATISTICAL_RESULTS.json").is_file():
        print("❌ 缺少 ANALYSIS_PLAN.json 或 STATISTICAL_RESULTS.json：先跑完统计分析")
        return 2
    entries = build(ws)
    if args.check:
        path = Path(args.check)
        if not path.is_file():
            print(f"❌ 找不到 {path}")
            return 2
        text = path.read_text(encoding="utf-8-sig")
        problems = check(text, entries)
        for p in problems:
            print(f"❌ {p}")
        total = len(display_blocks(body_of(text)))
        need = sum(1 for e in entries if e["required"])
        print(f"{'✅' if not problems else '❌'} 正文行间公式 {total} 个；按做了的分析必写的公式 {need} 组；问题 {len(problems)} 处")
        return 0 if not problems else 1
    out, js = ws / args.out, ws / args.json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown(entries), encoding="utf-8")
    js.write_text(json.dumps({"schema": "paperkit.survey.formulas/v1", "entries": entries}, ensure_ascii=False, indent=2),
                  encoding="utf-8")
    need = [e for e in entries if e["required"]]
    print(f"✅ 公式清单：{len(entries)} 组（必写 {len(need)} 组），共 {sum(len(e['latex']) for e in entries)} 个公式 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
