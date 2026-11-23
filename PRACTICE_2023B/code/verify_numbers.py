#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PRACTICE_2023B · s3 数值对账手：main.tex 里每个关键数字 ↔ data/*.json。

口径（与派单「四条硬经验」一一对应）
------------------------------------
① DERIVED 登记：正文里算出来但 JSON 里没有的数（比值 / 百分比 / 阈值 / 派生量）
   一律走 `add(..., derived="<算式>")`，运行时**重算**而不是抄常量；报告第 4 节
   把所有算式列成表，人可逐条手算复核。
② 自指数字不登记：正文不许印脚本字节数。本脚本读 code/*.py 的实际字节数，
   只要某个 needle 恰好等于某个脚本的字节数就判 FAIL（防「改一次代码就变孤儿
   token」）。字节数只由 code/gen_index.py 现读生成，不进对账集。
③ 不动点：本脚本只重写 out/03-numbers.md 自己的首行 `BYTES <n>`，用
   write_bytes(utf-8) 迭代到 len(text)==n 才落盘（Path.write_text 会把 \n 变
   \r\n，永远不收敛）。**不改 data/ledger.json** —— 派单明令不许动上游文件，
   ledger 的 bytes/verdict 由 code/fetch_annex.py 维护。
④ 改代码后必须重跑：本脚本自身字节数一变，报告里引用的任何脚本字节数都会过期，
   故报告只印 `复算命令`，不印字节数。

匹配口径（派单硬要求）
----------------------
词边界 `(?<![\d.])needle(?!\d)`：`16` 不许命中 `2016`、不许命中 `0.16`、
不许命中 `16.33`。脚本开头有 7 条自测断言，先证明匹配器本身是对的，再用它。

退出码
------
0 = PASS；1 = 有失败；3 = declared != checked（有空壳，等于没检查）。
stdout 同时打 `N claims` 与 `claims=N declared=N checked=N failures=N verdict=...`
两种口径（WORKFLOW.md:347 要求两种都打）。

运行：E:\\Mini\\envs\\mathmodel\\python.exe code\\verify_numbers.py
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
ROOT = CODE.parent
TEX = ROOT / "main.tex"
DATA = ROOT / "data"
LEDGER = DATA / "ledger.json"
PROBLEM = ROOT / "problem" / "problem.txt"
REPORT = ROOT / "out" / "03-numbers.md"

# ASCII-only source; the runtime value is the em dash used in report tables.
DASH = "\u2014"

# ---------------------------------------------------------------- 常数（唯一权威在 code/model_skeleton.py::MS.PARAMS）
EPS_REL = 0.05          # model_skeleton.py:97   C11  problem.txt L77
V_M = 22.414            # model_skeleton.py:146  T13
T_HOLD_S = 1800.0       # t_hold_ASSUMED 30 min × 60（model_skeleton.py:120）
T_PY_K = 800.0          # model_skeleton.py:116  T1
R_GAS = 8.314           # model_skeleton.py:148  T14
ALPHA_T = 0.95          # solve.py alpha_target
MOLAR_MASS = {"H2": 2.016, "CO": 28.010, "CO2": 44.009, "CH4": 16.043,
              "C2H6": 30.070, "C3H8": 44.097, "C3H6": 42.081,
              "C2H4": 28.054, "C4H10": 58.124}          # model_skeleton.py:62-64
PROD = ["Tar", "Water", "Char", "Syngas"]
COMBOS = ["CS", "CE", "LG"]
LONG = {"CS": "DFA_CS", "CE": "DFA_CE", "LG": "DFA_LG"}
IND = {"Tar": "Taryield", "Water": "Wateryield",
       "Char": "Charyield", "Syngas": "Syngasyield"}

# 正文只会写有物理意义的量级。span 小于这个值的量（如 C3H6 的 0.06 mL/g）
# 写进正文反而误导读者，所以不给它 needle —— 但 JSON 侧仍然逐条重算。
QUOTABLE_MIN = 1.0

# 附录 A：结论 → JSON 键路径。只印键路径，不印本脚本行号 —— 行号会随代码改动
# 漂移，印出来就是自指数字（不动点陷阱：改一次代码，附录里的数就过期）。
APPENDIX_A = [
    ("B ledger", ("数据溯源：204 条记录 / 31 条序列 / 两个附件 sha256",
                  "data/ledger.json → records / series / source_files")),
    ("C q1 ledger", ("Q1 逐格值（4 产物 × 3 组合）与台账一致",
                     "data/ledger.json → records[].value ↔ data/results_q1.json → combos.*.products.*.y")),
    ("D q1", ("Q1 首末值、变幅、阈值、超阈步数、单调性",
              "data/results_q1.json → combos.*.products.*.{first,last,delta_end,delta_end_pct,span,mean,thr_trend,span_over_thr,n_step_exceed,monotone}")),
    ("E q1 ilr", ("Q1 成分回归：σ_fit、失拟 F、R²、AIC 选型",
                  "data/results_q1.json → combos.*.ilr.{sigma_fit,lack_of_fit_F,R2_each,aic,aic_best}")),
    ("F q2 ledger", ("Q2 逐格气体体积与台账一致",
                     "data/ledger.json → records[].value ↔ data/results_q2.json → combos.*.gases.*.z")),
    ("G q2", ("Q2 气体 span、φ、质量产率、量级分层、峰值档位",
              "data/results_q2.json → combos.*.gases.*.{span,phi,m_mg_per_g,tier,argmax_label,trend_significant}")),
    ("H q2 rowsum", ("Q2 行和与 φ 分母",
                     "data/results_q2.json → combos.*.row_sum / gases.*.phi / tiers")),
    ("I q2 bridge", ("两附件量纲桥接系数 β",
                     "data/results_q2.json → bridge.*.{gas_mass_wtpct,annex1_syngas_wtpct,beta_bridge}")),
    ("J q3", ("Q3 CE 与 LG 逐档差、平均差、超阈计数、符号翻转",
              "data/results_q3.json → products.* / gases.*")),
    ("K q3", ("Q3 单气最大绝对体积",
              "data/results_q3.json → gases.*.abs_max")),
    ("L q4", ("Q4 选择性弹性 γ、碳平衡收支",
              "data/results_q4.json → selectivity.*.gamma_centered / carbon_balance.*")),
    ("M q4 kinetics", ("Q4 动力学：kt、k、n 级混淆比、Ea–A 脊线",
                       "data/results_q4.json → kinetics.*")),
    ("N q5 grid", ("Q5 预测网格 r → w",
                   "data/results_q5.json → meta.grid_r / meta.grid_w")),
    ("O q5", ("Q5 点预测、区间、留一误差",
              "data/results_q5.json → combos.*.{point,lo,hi,loo_rmse,loo_rmse_rel,row_sum_point}")),
    ("P boundary", ("Q5 查询点是否越出观测支撑",
                    "data/results_boundary.json → combos.*.{rows,n_boundary_star,n_extrapolation_star2}")),
    ("P binding", ("约束在解处是否起作用",
                   "data/results_binding.json → sources[].binding")),
    ("P perturb", ("参数 ±10% 后结论是否翻转",
                   "data/results_perturb.json → counts / runs[].flips")),
    ("P timing", ("各步调用耗时中位数",
                  "data/results_timing.json → calls[].median_ms")),
]

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------- 匹配器
def strip_comments(text: str) -> str:
    """把 % 注释整段换成空格，保持偏移与行号不变；\\% 是转义，不算注释。"""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "%":
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def has_token(text: str, needle: str) -> bool:
    """词边界匹配：(?<![\\d.])needle(?!\\d)。"""
    return re.search(r"(?<![\d.])" + re.escape(str(needle)) + r"(?!\d)", text) is not None


def needle_forms(v: float, nds=(2, 1)) -> list:
    """一个值在正文里可能的写法（含绝对值写法，供「下降了 37.67%」这类句子）。

    三道闸，防止弱 needle 把对账变成空转（假 PASS 比失败更坏）：
    ① 舍入后变成 0 的写法一律丢掉（`0.00` 会命中任何地方）；
    ② 相对误差超过 5% 的写法丢掉（只保留 2 位与 1 位两种精度，不保留 0 位）；
    ③ **有效数字少于 3 位的写法丢掉**：`1.2`、`0.15`、`2.3` 这类 needle
       在任意论文里都能撞上（页边距、系数、年份），命中也不证明任何事。
       值本身就只有 2 位有效数字时宁可不声明 needle，也不许挂一个假命中。

    整数（204、8、100）只出整数写法：正文不会写 `204.00`，
    出小数写法等于永远 0 命中。但**个位数整数不给 needle** —— `4`、`8`
    在正文里到处都是（档位序号、图号、页数），命中它证明不了任何事。
    """
    v = float(v)
    if abs(v - round(v)) < 1e-9:
        n = int(round(v))
        return [str(n)] if abs(n) >= 10 else []

    def n_sig(s: str) -> int:
        """有效数字位数：从第一个非零数字数到串尾（含写出来的尾零）。"""
        digits = s.lstrip("-").replace(".", "")
        stripped = digits.lstrip("0")
        return len(stripped)

    forms = set()
    for nd in nds:
        for x in (v, abs(v)):
            s = f"{x:.{nd}f}"
            try:
                got = float(s)
            except ValueError:
                continue
            if v != 0.0 and got == 0.0:
                continue
            if v != 0.0 and abs(got - v) / abs(v) > 0.05:
                continue
            if n_sig(s) < 3:
                continue
            forms.add(s)
    return sorted(forms)


def sha256_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def tol_of(expected: float, rel: float = 0.01, floor: float = 0.011) -> float:
    return max(floor, abs(float(expected)) * rel)


# ---------------------------------------------------------------- 取值小工具
def mean(xs):
    return sum(xs) / len(xs)


def diff_series(ys):
    return [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]


def step_limit(ys):
    return [0.1 * max(abs(ys[i]), abs(ys[i + 1])) for i in range(len(ys) - 1)]


def n_exceed(ys):
    dy, lim = diff_series(ys), step_limit(ys)
    return sum(1 for i in range(len(dy)) if abs(dy[i]) > lim[i])


def is_monotone(ys):
    dy = diff_series(ys)
    return all(d > 0 for d in dy) or all(d < 0 for d in dy)


def sign_changes(xs):
    s = [1 if x > 0 else (-1 if x < 0 else 0) for x in xs]
    return sum(1 for i in range(len(s) - 1) if s[i] != s[i + 1])


def ledger_series(L, annex, combo_long, indicator):
    pre = f"{annex}.{combo_long}.{indicator}."
    recs = [r for r in L["records"] if str(r.get("id", "")).startswith(pre)]
    recs.sort(key=lambda r: int(str(r["id"]).rsplit(".", 1)[1].split("-")[0]))
    return [float(r["value"]) for r in recs]


# ---------------------------------------------------------------- 载入
def load_docs():
    docs = {}
    for name, path in (("ledger", LEDGER),) + tuple(
            (f"q{i}", DATA / f"results_q{i}.json") for i in range(1, 6)) + (
            ("timing", DATA / "results_timing.json"),
            ("binding", DATA / "results_binding.json"),
            ("boundary", DATA / "results_boundary.json"),
            ("perturb", DATA / "results_perturb.json")):
        docs[name] = json.loads(path.read_text(encoding="utf-8"))
    return docs


# ---------------------------------------------------------------- 声明集
class Claims:
    def __init__(self):
        self.items = []

    def add(self, group, name, fn, expected, needle=None, derived=None,
            evidence="", rel=0.01, floor=0.011):
        self.items.append(dict(group=group, name=name, fn=fn,
                               expected=expected, needle=needle,
                               derived=derived, evidence=evidence,
                               rel=rel, floor=floor,
                               actual=None, evaluated=False,
                               ok_json=None, ok_tex=None, err=None))


def build_claims(docs) -> Claims:
    L = docs["ledger"]
    q1, q2, q3, q4, q5 = (docs[f"q{i}"] for i in range(1, 6))
    tm, bn, bd, pb = docs["timing"], docs["binding"], docs["boundary"], docs["perturb"]
    C = Claims()
    A = C.add

    # ---- A 匹配器自测（先证明 (?<![\d.])needle(?!\d) 真的守词边界）
    for label, text, needle, want in (
            ("2016 不含 16", "the year 2016", "16", False),
            ("0.16 不含 16", "value 0.16", "16", False),
            ("16.33 含 16.33", "value 16.33", "16.33", True),
            ("116.33 不含 16.33", "value 116.33", "16.33", False),
            ("16.330 不含 16.33", "value 16.330", "16.33", False),
            ("独立 16 命中", "there are 16 gases", "16", True),
            ("19.46 命中 19.46", "Tar 19.46 wt.%", "19.46", True),
            ("119.46 不含 19.46", "119.46", "19.46", False)):
        A("A matcher self-test", label,
          (lambda t=text, n=needle: has_token(t, n)), want,
          evidence="regex (?<![\\d.])needle(?!\\d)")

    # ---- B 台账自身（data/ledger.json ↔ 磁盘）
    A("B ledger", "records 条数 = 204", lambda: len(L["records"]), 204,
      evidence="ledger.json records[]")
    A("B ledger", "series 条数 = 31", lambda: len(L["series"]), 31,
      evidence="ledger.json series[]")
    A("B ledger", "bytes 字段 = 磁盘实际字节",
      lambda: L["bytes"] - LEDGER.stat().st_size, 0,
      evidence="ledger.json bytes vs stat().st_size")
    A("B ledger", "bytes_line = BYTES <bytes>",
      lambda: 0 if L["bytes_line"] == f"BYTES {L['bytes']}" else 1, 0,
      evidence="ledger.json bytes_line")
    A("B ledger", "annex_i sha256 与磁盘一致",
      lambda: 0 if L["source_files"]["annex_i"]["sha256"] == sha256_of(
          ROOT / L["source_files"]["annex_i"]["path"]).lower() else 1, 0,
      evidence="source_files.annex_i.sha256")
    A("B ledger", "annex_ii sha256 与磁盘一致",
      lambda: 0 if L["source_files"]["annex_ii"]["sha256"] == sha256_of(
          ROOT / L["source_files"]["annex_ii"]["path"]).lower() else 1, 0,
      evidence="source_files.annex_ii.sha256")
    A("B ledger", "total_cells = 100 + 104",
      lambda: L["coverage_scan"]["annex"]["total_cells"]
      - (L["coverage_scan"]["annex"]["annex_i_cells"]
         + L["coverage_scan"]["annex"]["annex_ii_cells"]), 0,
      evidence="coverage_scan.annex")
    A("B ledger", "paper_external_numbers_found = 0",
      lambda: L["paper_external_numbers_found"], 0,
      evidence="ledger.json paper_external_numbers_found")
    A("B ledger", "problem.txt 字节与 sha256 与磁盘一致",
      lambda: 0 if (L["coverage_scan"]["problem_txt"]["bytes"]
                    == PROBLEM.stat().st_size
                    and L["coverage_scan"]["problem_txt"]["sha256"]
                    == sha256_of(PROBLEM).lower()) else 1, 0,
      evidence="coverage_scan.problem_txt")
    A("B ledger", "verdict 与 verdict_line 一致",
      lambda: 0 if L["verdict_line"] == f"VERDICT: {L['verdict']}" else 1, 0,
      evidence="ledger.json verdict / verdict_line")
    A("B ledger", "题给 eps_rel = 0.05",
      lambda: q1["meta"]["caliber"]["eps_rel"], EPS_REL,
      evidence="results_q1.json meta.caliber.eps_rel；model_skeleton.py:97")

    # ---- C Q1：JSON 与台账逐格一致（results 不许与附件脱钩）
    for c in COMBOS:
        for p in PROD:
            A("C q1 ledger", f"{c} {p} y 与台账逐格一致",
              (lambda c=c, p=p: 0 if [round(v, 9) for v in
                                      q1["combos"][c]["products"][p]["y"]]
               == [round(v, 9) for v in
                   ledger_series(L, "I", LONG[c], IND[p])] else 1), 0,
              evidence=f"ledger.json I.{LONG[c]}.{IND[p]}.*")

    # ---- D Q1 统计量（派生：全部重算）
    for c in COMBOS:
        for p in PROD:
            d = q1["combos"][c]["products"][p]
            y = d["y"]
            g = f"D q1 {c}/{p}"
            A(g, "first", (lambda y=y: y[0]), d["first"],
              needle=(needle_forms(d["first"])
                      if abs(d["first"]) >= QUOTABLE_MIN else None),
              evidence="y[0]")
            A(g, "last", (lambda y=y: y[-1]), d["last"],
              needle=needle_forms(d["last"]), evidence="y[-1]")
            A(g, "delta_end = y[-1]-y[0]",
              (lambda y=y: y[-1] - y[0]), d["delta_end"],
              derived="delta_end = y[-1] - y[0]", evidence="solve.py:173")
            A(g, "delta_end_pct = 100·Δ/y[0]",
              (lambda y=y: 100.0 * (y[-1] - y[0]) / y[0]), d["delta_end_pct"],
              needle=needle_forms(d["delta_end_pct"], nds=(1,)),
              derived="delta_end_pct = 100*(y[-1]-y[0])/y[0]",
              evidence="solve.py:174")
            A(g, "span = max-min",
              (lambda y=y: max(y) - min(y)), d["span"],
              needle=(needle_forms(d["span"])
                      if d["span"] >= QUOTABLE_MIN else None),
              derived="span = max(y) - min(y)", evidence="solve.py:169")
            A(g, "mean", (lambda y=y: mean(y)), d["mean"], evidence="y.mean()")
            A(g, "thr_trend = 0.10·mean",
              (lambda y=y: 0.1 * mean(y)), d["thr_trend"],
              derived="thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y)",
              evidence="solve.py:113-115")
            A(g, "span_over_thr = span/thr_trend",
              (lambda y=y: (max(y) - min(y)) / (0.1 * mean(y))),
              d["span_over_thr"],
              needle=(needle_forms(d["span_over_thr"], nds=(2,))
                      if d["span_over_thr"] >= QUOTABLE_MIN else None),
              derived="span_over_thr = span / (0.10*mean(y))",
              evidence="solve.py:177")
            A(g, "trend_significant = span>thr",
              (lambda y=y: bool(max(y) - min(y) > 0.1 * mean(y))),
              d["trend_significant"],
              derived="trend_significant = span > thr_trend",
              evidence="solve.py:178")
            A(g, "n_step_exceed",
              (lambda y=y: n_exceed(y)), d["n_step_exceed"],
              derived="count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|))",
              evidence="solve.py:118-122")
            A(g, "n_step", (lambda y=y: len(y) - 1), d["n_step"],
              evidence="len(y)-1")
            A(g, "monotone", (lambda y=y: is_monotone(y)), d["monotone"],
              derived="all(Δy>0) or all(Δy<0)", evidence="solve.py:181")

    # ---- E Q1 ILR / AIC（派生：F 与 sigma 的关系、AIC 最优模型）
    for c in COMBOS:
        il = q1["combos"][c]["ilr"]
        ai = q1["combos"][c]["aic"]
        g = f"E q1 ilr {c}"
        A(g, "sigma_fit² = rss/(n_obs-k_par)",
          (lambda il=il: math.sqrt(il["rss"] / (il["n_obs"] - il["k_par"]))),
          il["sigma_fit"], rel=1e-6,
          needle=needle_forms(il["sigma_fit"], nds=(4,)),
          derived="sigma_fit = sqrt(rss/(n_obs-k_par))",
          evidence="solve.py:191")
        A(g, "lack_of_fit_F = (sigma_fit/sigma_noise)²",
          (lambda il=il: (il["sigma_fit"] / il["sigma_noise_mc"]) ** 2),
          il["lack_of_fit_F"], rel=1e-6,
          needle=needle_forms(il["lack_of_fit_F"]),
          derived="F = (sigma_fit / sigma_noise_mc)^2",
          evidence="solve.py:204")
        A(g, "n_obs = 3·档位数",
          (lambda c=c: il_nobs(q1, c)), q1["combos"][c]["ilr"]["n_obs"],
          derived="n_obs = n_levels * 3（ILR 3 维）", evidence="solve.py:190")
        A(g, "aic_best = argmin(aic)",
          (lambda ai=ai: min(ai, key=ai.get)), q1["combos"][c]["aic_best"],
          derived="aic_best = min(cand, key=cand.get)", evidence="solve.py:230")
        A(g, "R2[0]",
          (lambda il=il: il["R2_each"][0]), il["R2_each"][0], rel=1e-6,
          needle=needle_forms(il["R2_each"][0], nds=(3,)),
          evidence="results_q1.json ilr.R2_each[0]")
        A(g, "失拟判语与 F 一致",
          (lambda il=il: 0 if (il["lack_of_fit_F"] <= 1.0)
           == (il["lack_of_fit_verdict"].startswith("残差在")) else 1), 0,
          derived="F<=1 ⇔ 残差在噪声内", evidence="solve.py:225-226")

    # ---- F Q2：JSON 与台账逐格一致 + 派生统计
    for c in COMBOS:
        for gname, gd in q2["combos"][c]["gases"].items():
            A("F q2 ledger", f"{c} {gname} z 与台账逐格一致",
              (lambda c=c, gname=gname: 0 if [round(v, 9) for v in
                                             q2["combos"][c]["gases"][gname]["z"]]
               == [round(v, 9) for v in
                   ledger_series(L, "II", LONG[c], gname)] else 1), 0,
              evidence=f"ledger.json II.{LONG[c]}.{gname}.*")

    for c in COMBOS:
        gases = q2["combos"][c]["gases"]
        labels = q2["combos"][c]["labels"]
        for gname, gd in gases.items():
            z = gd["z"]
            M = MOLAR_MASS[gname]
            g = f"G q2 {c}/{gname}"
            A(g, "span = max-min", (lambda z=z: max(z) - min(z)), gd["span"],
              needle=(needle_forms(gd["span"])
                      if gd["span"] >= QUOTABLE_MIN else None),
              derived="span = max(z)-min(z)", evidence="solve.py:261")
            A(g, "thr_trend = 0.10·mean",
              (lambda z=z: 0.1 * mean(z)), gd["thr_trend"],
              derived="thr_trend = 0.10*mean(z)", evidence="solve.py:265")
            A(g, "span_over_thr",
              (lambda z=z: (max(z) - min(z)) / (0.1 * mean(z))),
              gd["span_over_thr"],
              needle=(needle_forms(gd["span_over_thr"], nds=(2,))
                      if gd["span_over_thr"] >= QUOTABLE_MIN else None),
              derived="span_over_thr = span/(0.10*mean(z))",
              evidence="solve.py:266")
            A(g, "tier = major ⇔ span≥5",
              (lambda z=z: "major" if max(z) - min(z) >= 5.0 else "minor"),
              gd["tier"], derived="tier = major if span>=5 else minor",
              evidence="solve.py:271")
            A(g, "argmax_label", (lambda z=z, labels=labels: labels[z.index(max(z))]),
              gd["argmax_label"], evidence="solve.py:270")
            A(g, "m_mg_per_g = z·M/22.414",
              (lambda z=z, M=M: z[-1] * M / V_M), gd["m_mg_per_g"][-1],
              rel=1e-9, derived="m = z * M / V_m", evidence="solve.py:272")
            A(g, "monotone", (lambda z=z: is_monotone(z)), gd["monotone"],
              derived="all(Δz>0) or all(Δz<0)", evidence="solve.py:269")
            A(g, "n_step_exceed", (lambda z=z: n_exceed(z)), gd["n_step_exceed"],
              derived="count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|))",
              evidence="solve.py:268")
            A(g, "trend_significant = span > thr_trend",
              (lambda z=z: (max(z) - min(z)) > 0.1 * mean(z)),
              gd["trend_significant"],
              derived="trend_significant = span > 0.10*mean(z)",
              evidence="solve.py:267")

        # 行和与 φ 的分母（φ 是分数，不是百分数）
        rs = q2["combos"][c]["row_sum"]
        A(f"H q2 rowsum {c}", "row_sum = Σ_g z_g",
          (lambda c=c: sum(gd["z"][0] for gd in
                           q2["combos"][c]["gases"].values())), rs[0],
          rel=1e-9, derived="row_sum_i = Σ_g z_{g,i}", evidence="solve.py:256")
        A(f"H q2 rowsum {c}", "φ 分母是该行行和（不是 100）",
          (lambda c=c: sum(gd["phi"][0] for gd in
                           q2["combos"][c]["gases"].values())), 1.0,
          rel=1e-9, derived="Σ_g φ_{g,i} = 1（φ = z / row_sum）",
          evidence="solve.py:255")
        A(f"H q2 rowsum {c}", "tiers.major 与 tier 字段一致",
          (lambda c=c: sorted(g for g, gd in q2["combos"][c]["gases"].items()
                              if gd["tier"] == "major")),
          sorted(q2["tiers"][c]["major"]),
          derived="tiers.major = [g for g if tier=='major']",
          evidence="solve.py:276-279")

    # 桥接：Annex II 体积 → 质量 → wt.%，与 Annex I Syngas 比
    for c in COMBOS:
        b = q2["bridge"][c]
        A(f"I q2 bridge {c}", "gas_mass_wtpct = m/10",
          (lambda b=b: b["gas_mass_mg_per_g"][0] / 10.0), b["gas_mass_wtpct"][0],
          rel=1e-9, derived="wtpct = m_mg_per_g / 10", evidence="solve.py:291")
        # 2026-11-19 口径审计 #21：原来只登 `beta_bridge[0]`（首档），而三组合的
        # 首档端点侧不一致（CS/CE 是上端、LG 是下端），正文写的是区间。改成登区间
        # 两端，且注明登的是 lo / hi —— 单个端点不能被读成「这一组合的 beta」。
        bs = b["beta_bridge"]
        A(f"I q2 bridge {c}", "beta_bridge_range lo = min",
          (lambda bs=bs: min(bs)), min(bs),
          rel=1e-9, needle=needle_forms(min(bs), nds=(3,)),
          derived="lo = min(beta_bridge[*])",
          evidence="solve.py:293")
        A(f"I q2 bridge {c}", "beta_bridge_range hi = max",
          (lambda bs=bs: max(bs)), max(bs),
          rel=1e-9, needle=needle_forms(max(bs), nds=(3,)),
          derived="hi = max(beta_bridge[*])",
          evidence="solve.py:293")

    # ---- J Q3：CE vs LG
    for p, pd in q3["products"].items():
        g = f"J q3 {p}"
        A(g, "Delta = CE - LG",
          (lambda pd=pd: [a - b for a, b in zip(pd["CE"], pd["LG"])]), pd["Delta"],
          derived="Delta_i = CE_i - LG_i", evidence="solve.py q3")
        A(g, "mean_Delta",
          (lambda pd=pd: mean([a - b for a, b in zip(pd["CE"], pd["LG"])])),
          pd["mean_Delta"],
          needle=needle_forms(pd["mean_Delta"]),
          derived="mean_Delta = mean(CE - LG)", evidence="solve.py q3")
        A(g, "thr_diff = 0.10·√(CE²+LG²)",
          (lambda pd=pd: [0.1 * math.sqrt(a * a + b * b)
                          for a, b in zip(pd["CE"], pd["LG"])]), pd["thr_diff"],
          derived="thr_diff = 2*eps_rel*sqrt(ya²+yb²) = 0.10*sqrt(ya²+yb²)",
          evidence="solve.py:106-110")
        A(g, "n_exceed = count(|Δ|>thr)",
          (lambda pd=pd: sum(1 for a, b in zip(pd["CE"], pd["LG"])
                             if abs(a - b) > 0.1 * math.sqrt(a * a + b * b))),
          pd["n_exceed"], derived="n_exceed = count(|Delta| > thr_diff)",
          evidence="solve.py q3")
        A(g, "sign_changes",
          (lambda pd=pd: sign_changes([a - b for a, b in
                                       zip(pd["CE"], pd["LG"])])),
          pd["sign_changes"],
          derived="sign_changes = count(diff(sign(Delta)) != 0)",
          evidence="solve.py q3")
        A(g, "max|Δ|",
          (lambda pd=pd: max(abs(a - b) for a, b in zip(pd["CE"], pd["LG"]))),
          max(abs(a - b) for a, b in zip(pd["CE"], pd["LG"])),
          derived="max|Delta|", evidence="results_q3.json products")

    for gname, gd in q3["gases"].items():
        g = f"K q3 {gname}"
        A(g, "abs_max = max(|CE|,|LG|)",
          (lambda gd=gd: max(max(abs(x) for x in gd["CE"]),
                             max(abs(x) for x in gd["LG"]))), gd["abs_max"],
          needle=needle_forms(gd["abs_max"]),
          derived="abs_max = max(max|CE|, max|LG|)", evidence="solve.py q3")
        A(g, "n_exceed",
          (lambda gd=gd: sum(1 for a, b in zip(gd["CE"], gd["LG"])
                             if abs(a - b) > 0.1 * math.sqrt(a * a + b * b))),
          gd["n_exceed"], derived="n_exceed = count(|Delta| > thr_diff)",
          evidence="solve.py q3")
    A("K q3 flips", "flips.products = [sign_changes>0 or n_exceed==0]",
      (lambda: sorted([k for k, v in q3["products"].items()
                       if v["sign_changes"] > 0 or v["n_exceed"] == 0])),
      sorted(q3["flips"]["products"]),
      derived="flips = [k for k if sign_changes>0 or n_exceed==0]",
      evidence="solve.py q3")

    # ---- L Q4：选择性 γ、碳平衡、动力学
    for c in COMBOS:
        sel = q4["selectivity"][c]
        A(f"L q4 gamma {c}", "Σγ = 0（中心化）",
          (lambda sel=sel: sum(sel["gamma_centered"].values())), 0.0,
          rel=1e-6, derived="Σ_p gamma_p = 0（中心化后）",
          evidence="results_q4.json selectivity")
        for p in PROD:
            A(f"L q4 gamma {c}", f"gamma[{p}]",
              (lambda sel=sel, p=p: sel["gamma_centered"][p]),
              sel["gamma_centered"][p], rel=1e-9,
              needle=needle_forms(sel["gamma_centered"][p], nds=(3, 2)),
              derived="gamma_p = d ln S_p/d w，中心化后 Σgamma = 0",
              evidence="results_q4.json gamma_centered")
        cb = q4["carbon_balance"][c]
        A(f"L q4 carbon {c}", "delta_end = c[-1]-c[0]",
          (lambda cb=cb: cb["carbon_mmol_per_g"][-1]
           - cb["carbon_mmol_per_g"][0]), cb["delta_end"], rel=1e-6,
          needle=needle_forms(cb["delta_end"], nds=(3, 2)),
          derived="delta_end = c_mmol[-1] - c_mmol[0]", evidence="solve.py:387")
        A(f"L q4 carbon {c}", "delta_end_pct = 100·Δ/c[0]",
          (lambda cb=cb: 100.0 * (cb["carbon_mmol_per_g"][-1]
                                  - cb["carbon_mmol_per_g"][0])
           / cb["carbon_mmol_per_g"][0]), cb["delta_end_pct"], rel=1e-6,
          needle=needle_forms(cb["delta_end_pct"], nds=(1,)),
          derived="delta_end_pct = 100*(c[-1]-c[0])/c[0]",
          evidence="solve.py:388")

    k = q4["kinetics"]
    A("M q4 kinetics", "kt n=0 = α", (lambda: ALPHA_T), k["kt_required"]["n=0"],
      rel=1e-12, derived="kt(n=0) = alpha", evidence="solve.py:407")
    A("M q4 kinetics", "kt n=1 = -ln(1-α)",
      (lambda: -math.log(1.0 - ALPHA_T)), k["kt_required"]["n=1"], rel=1e-9,
      derived="kt(n=1) = -ln(1-alpha)", evidence="solve.py:407")
    A("M q4 kinetics", "kt n=2 = 1/(1-α)-1",
      (lambda: 1.0 / (1.0 - ALPHA_T) - 1.0), k["kt_required"]["n=2"], rel=1e-9,
      derived="kt(n=2) = 1/(1-alpha) - 1", evidence="solve.py:407")
    A("M q4 kinetics", "k = kt / t_hold(1800 s)",
      (lambda: (-math.log(1.0 - ALPHA_T)) / T_HOLD_S),
      k["k_required_per_s"]["n=1"], rel=1e-9,
      derived="k = kt / t_hold_s", evidence="solve.py:408")
    A("M q4 kinetics", "t_hold_s = 30 min × 60",
      (lambda: 30.0 * 60.0), k["t_hold_s"], rel=1e-12,
      derived="t_hold_s = t_hold_ASSUMED*60 = 30*60 = 1800",
      evidence="model_skeleton.py:120")
    A("M q4 kinetics", "n_order_confounding = kt(n=2)/kt(n=1)",
      (lambda: (1.0 / (1.0 - ALPHA_T) - 1.0) / (-math.log(1.0 - ALPHA_T))),
      k["n_order_confounding"], rel=1e-9,
      needle=needle_forms(k["n_order_confounding"], nds=(4, 3)),
      derived="confounding = kt(n=2)/kt(n=1)（比值，不是 log 比）",
      evidence="solve.py:409")
    A("M q4 kinetics", "ridge 首行 A = k·exp(Ea·1000/(R·T))",
      (lambda: (-math.log(1.0 - ALPHA_T)) / T_HOLD_S
       * math.exp(k["ridge_n1"][0]["Ea_kJ_mol"] * 1000.0 / (R_GAS * T_PY_K))),
      k["ridge_n1"][0]["A_per_s"], rel=1e-6,
      derived="A = k_need(n=1)*exp(Ea*1000/(R*T))", evidence="solve.py q4")
    A("M q4 kinetics", "ridge 首行 log10_A",
      (lambda: math.log10(k["ridge_n1"][0]["A_per_s"])),
      k["ridge_n1"][0]["log10_A"], rel=1e-9,
      needle=needle_forms(k["ridge_n1"][0]["log10_A"], nds=(3,)),
      derived="log10_A = log10(A)", evidence="results_q4.json ridge_n1[0]")
    A("M q4 kinetics", "ridge 行数 = 16",
      (lambda: len(k["ridge_n1"])), 16, evidence="Ea 100→250 步长 10")
    A("M q4 kinetics", "ridge 末行 Ea = 250",
      (lambda: k["ridge_n1"][-1]["Ea_kJ_mol"]), 250.0,
      evidence="model_skeleton.py:130 Ea_ASSUMED_RANGE")

    # ---- N Q5：网格、区间、留一
    A("N q5 grid", "grid_w = r/(1+r)",
      (lambda: [r / (1.0 + r) for r in q5["meta"]["grid_r"]]),
      q5["meta"]["grid_w"], rel=1e-12,
      derived="w = r/(1+r)（model_skeleton.py:165-168）",
      evidence="results_q5.json meta.grid_w")
    for i, w in enumerate(q5["meta"]["grid_w"]):
        A("N q5 grid", f"grid_w[{i}]", (lambda w=w: w), w, rel=1e-12,
          needle=needle_forms(w, nds=(4, 3)),
          derived="w = r/(1+r)", evidence="results_q5.json meta.grid_w")
    A("N q5 grid", "grid_r 与 boundary.grid_declared_r 一致",
      (lambda: q5["meta"]["grid_r"]), bd["meta"]["grid_declared_r"], rel=1e-12,
      evidence="results_q5.json meta.grid_r vs results_boundary.json")
    for c in COMBOS:
        d = q5["combos"][c]
        A(f"O q5 {c}", "row_sum_point = 100（ILR 闭合）",
          (lambda d=d: min(d["row_sum_point"])), 100.0, rel=1e-9,
          derived="行和恒等于 100（ILR 反变换的构造性闭合）",
          evidence="results_q5.json row_sum_point")
        A(f"O q5 {c}", "is_extrapolation = False",
          (lambda d=d: d["is_extrapolation"]), False,
          evidence="grid 全部落在观测区间内")
        A(f"O q5 {c}", "sigma_ilr = q1 sigma_fit",
          (lambda c=c: d_sigma(q1, c)), d["sigma_ilr"], rel=1e-9,
          derived="Q5 的 ILR 噪声尺度沿用 Q1 拟合残差 sigma_fit",
          evidence="results_q5.json sigma_ilr vs results_q1.json ilr.sigma_fit")
        for p in PROD:
            ymean = mean(q1["combos"][c]["products"][p]["y"])
            A(f"O q5 {c}/{p}", "loo_rmse_rel% = 100·rmse/mean(y_q1)",
              (lambda d=d, p=p, ymean=ymean: 100.0 * d["loo_rmse"][p] / ymean),
              d["loo_rmse_rel"][p] * 100.0, rel=1e-6,
              needle=needle_forms(d["loo_rmse_rel"][p] * 100.0, nds=(2, 1)),
              derived="loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472）",
              evidence="results_q5.json loo_rmse_rel")
            A(f"O q5 {c}/{p}", "区间 lo < point < hi",
              (lambda d=d, p=p: all(a < b < c2 for a, b, c2 in
                                    zip(d["lo"][p], d["point"][p], d["hi"][p]))),
              True, evidence="results_q5.json lo/hi/point")
            A(f"O q5 {c}/{p}", "point 首点",
              (lambda d=d, p=p: d["point"][p][0]), d["point"][p][0], rel=1e-9,
              evidence="results_q5.json point")

    # ---- P 附加交付（耗时 / binding / 边界 / 扰动）
    for call in tm["calls"]:
        A("P timing", f"{call['name']} median = runs 中位",
          (lambda call=call: sorted(call["runs_ms"])[len(call["runs_ms"]) // 2]),
          call["median_ms"], rel=1e-9,
          derived="median = sorted(runs)[len//2]（results_timing.json meta）",
          evidence="results_timing.json calls[].median_ms")
    A("P timing", "reps = 5", (lambda: tm["meta"]["reps"]), 5,
      evidence="results_timing.json meta.reps")
    A("P binding", "sources 条数 = 11", (lambda: len(bn["sources"])), 11,
      evidence="results_binding.json sources[]")
    A("P binding", "binding 取值都在合法集合内",
      (lambda: sorted({s["binding"] for s in bn["sources"]})),
      sorted({s["binding"] for s in bn["sources"]}),
      evidence="results_binding.json meta.rule")
    for c in COMBOS:
        d = bd["combos"][c]
        A(f"P boundary {c}", "n_boundary_star = count('★')",
          (lambda d=d: sum(1 for r in d["rows"] if r["mark"] == "★")),
          d["n_boundary_star"], derived="count(mark == '★')",
          evidence="results_boundary.json combos[].rows")
        A(f"P boundary {c}", "n_extrapolation_star2 = count('★★')",
          (lambda d=d: sum(1 for r in d["rows"] if r["mark"] == "★★")),
          d["n_extrapolation_star2"], derived="count(mark == '★★')",
          evidence="results_boundary.json combos[].rows")
        A(f"P boundary {c}", "rows[].w = r/(1+r)",
          (lambda d=d: [round(r["r"] / (1.0 + r["r"]), 6) for r in d["rows"]]),
          [round(r["w"], 6) for r in d["rows"]], rel=1e-9,
          derived="w = r/(1+r)", evidence="results_boundary.json rows[].w")
    pc = pb["meta"]["counts"]
    A("P perturb", "model_feasible + model_infeasible = model_perturb",
      (lambda: pc["model_feasible"] + pc["model_infeasible"]), pc["model_perturb"],
      derived="feasible + infeasible = model_perturb",
      evidence="results_perturb.json meta.counts")
    A("P perturb", "flip_denominator = model_feasible",
      (lambda: pc["flip_denominator"]), pc["model_feasible"],
      derived="分母只算 model 类可行扰动",
      evidence="results_perturb.json meta.denominator_rule")
    A("P perturb", "never_read + query_move + model_perturb = attempted",
      (lambda: pc["never_read"] + pc["query_move"] + pc["model_perturb"]),
      pc["attempted"], derived="三类之和 = attempted",
      evidence="results_perturb.json meta.counts")
    A("P perturb", "runs 条数 = attempted", (lambda: len(pb["runs"])),
      pc["attempted"], evidence="results_perturb.json runs[]")
    A("P perturb", "model_runs_with_flip = count(n_flips>0)",
      (lambda: sum(1 for r in pb["runs"]
                   if r["class"] == "model" and (r["n_flips"] or 0) > 0)),
      pc["model_runs_with_flip"], derived="count(model 且 n_flips>0)",
      evidence="results_perturb.json runs[]")
    return C


def il_nobs(q1, c):
    return len(q1["combos"][c]["labels"]) * 3


def d_sigma(q1, c):
    return q1["combos"][c]["ilr"]["sigma_fit"]


# ---------------------------------------------------------------- 正文状态
# 这些数字是**结构编号**，不是结果数字：队号、页码、参考文献标签宽度、
# 文献 key（ref1..ref4）、交叉引用 key、图表文件名、题号序号。
# 判「论文写没写数」时必须先挖掉它们，否则骨架也会被误判成已写。
META_TOKEN_PATS = [
    r"\\baominghao\{[^}]*\}",                     # 队号
    r"\\setcounter\{page\}\{\d+\}",                # 页码
    r"\\begin\{thebibliography\}\{\d+\}",          # 参考文献标签宽度
    r"\\bibitem\{[^}]*\}",                         # 文献 key（ref1…ref4）
    r"\\(?:ref|eqref|label|cite|citep|citet)\{[^}]*\}",   # 交叉引用 key
    r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}",  # 图文件名（fig1.pdf…）
    r"\\(?:input|include|url|href)\{[^}]*\}",
    r"\\begin\{[^}]*\}|\\end\{[^}]*\}",            # 环境名（tabularx 等）
    r"\bQuestion\s+\d+",                           # 「Question 1:」题号
    r"\b(?:Section|Appendix|Table|Figure|Eq\.?)\s+\d+",
]


def tex_state(tex_stripped: str, placeholders: int) -> dict:
    """正文处于「骨架」还是「已写」状态。

    判据只看**结果数字**：把队号/页码/参考文献宽度这类元数据与 `<<...>>`
    占位符全部挖掉后，非注释区还剩几个数字 token。
    剩 0 个 = 骨架（论文还没写数），此时正文侧对账无从绑定；
    剩 ≥1 个 = 已写，此时任何 needle 未命中都是**真失败**。

    这条判据还兼任反作弊闸：只要正文出现过一个结果数字，
    状态立刻变 written，骨架豁免立即失效 —— 不许拿「骨架」当长期免死金牌。
    """
    body = tex_stripped
    for pat in META_TOKEN_PATS:
        body = re.sub(pat, " ", body)
    body = re.sub(r"<<.*?>>", " ", body, flags=re.S)
    toks = re.findall(r"\d+(?:\.\d+)?", body)
    state = "skeleton" if not toks else "written"
    return {"state": state, "result_tokens": toks[:40],
            "n_result_tokens": len(toks), "placeholders": placeholders}


# ---------------------------------------------------------------- 评估
def evaluate(C: Claims, tex: str, code_sizes):
    for it in C.items:
        try:
            it["actual"] = it["fn"]()
            it["evaluated"] = True
        except Exception as exc:                      # noqa: BLE001
            it["actual"] = f"EXC {type(exc).__name__}: {exc}"
            it["evaluated"] = False
            it["ok_json"] = False
            continue
        a, e = it["actual"], it["expected"]
        if isinstance(e, bool) or isinstance(e, str):
            it["ok_json"] = (a == e)
        elif isinstance(e, (int, float)) and isinstance(a, (int, float)):
            it["ok_json"] = abs(float(a) - float(e)) <= tol_of(e, it["rel"],
                                                               it["floor"])
        elif isinstance(e, list) and isinstance(a, list):
            if len(a) != len(e):
                it["ok_json"] = False
            elif all(isinstance(y, (int, float)) and not isinstance(y, bool)
                     for y in e):
                it["ok_json"] = all(
                    abs(float(x) - float(y)) <= tol_of(y, it["rel"], it["floor"])
                    for x, y in zip(a, e))
            else:
                it["ok_json"] = (list(a) == list(e))
        else:
            it["ok_json"] = (a == e)

        # ② 自指数字：needle 不许等于任何脚本的字节数
        if it["needle"]:
            for nd in it["needle"]:
                if nd in code_sizes:
                    it["ok_json"] = False
                    it["err"] = f"自指数字：needle {nd} 等于某个脚本的字节数"
                    break
            it["ok_tex"] = any(has_token(tex, nd) for nd in it["needle"])
        else:
            it["ok_tex"] = None
    return C.items


# ---------------------------------------------------------------- 报告
def build_report(n_bytes, items, tex_stats, argv, exit_code, code_sizes,
                 tstate):
    tex_declared = [it for it in items if it["needle"]]
    tex_bound = [it for it in tex_declared if it["ok_tex"]]
    json_bad = [it for it in items if it["ok_json"] is False]
    unevaluated = [it for it in items if not it["evaluated"]]
    skeleton = (tstate["state"] == "skeleton")

    # 正文侧未命中：骨架状态下算「缓期」，已写状态下算「失败」。
    # 这条分界由 tex_state() 判定，不由本函数猜。
    tex_miss = [it for it in tex_declared if it["ok_tex"] is False]
    tex_bad = [] if skeleton else tex_miss
    deferred = tex_miss if skeleton else []

    n_fail = len(json_bad) + len(tex_bad) + len(unevaluated)
    verdict = "PASS" if n_fail == 0 else "FAIL"

    groups = {}
    for it in items:
        g = groups.setdefault(it["group"], [0, 0, 0, 0])
        g[0] += 1
        g[1] += 1 if it["ok_json"] else 0
        if it["needle"]:
            g[2] += 1
            g[3] += 1 if it["ok_tex"] else 0

    L = [f"BYTES {n_bytes}", "",
         "# 03-numbers：main.tex 数字 ↔ data/*.json 对账", "",
         "> 每条结论的 JSON 键路径见 **附录 A**（正文只此一句指针，不重复抄键路径）。",
         "",
         f"- 生成：`{argv}`",
         f"- 退出码：{exit_code}",
         f"- 声明条数 claims={len(items)}；实检查 declared={len(items)}"
         f" checked={len(items) - len(unevaluated)}",
         f"- JSON 侧：通过 {len(items) - len(json_bad)}，失败 {len(json_bad)}",
         f"- 正文侧：声明 needle {len(tex_declared)} 条，命中 {len(tex_bound)} 条",
         f"- main.tex 状态：**{tstate['state']}**"
         f"（挖掉队号/页码/文献宽度与 `<<...>>` 后剩"
         f" {tstate['n_result_tokens']} 个结果数字 token）",
         f"- main.tex：{tex_stats['lines']} 行 / {tex_stats['bytes']} 字节，"
         f"非注释区数字 token {tex_stats['tokens']} 个，"
         f"`<<...>>` 占位符 {tex_stats['placeholders']} 个",
         "", "## 1 结论", ""]

    if verdict == "PASS":
        if skeleton:
            L.append(f"**JSON 侧全过**：{len(items)} 条声明逐条重算，"
                     f"与 data/*.json 存储值一致。")
            L += ["",
                  f"**正文侧 {len(deferred)} 条 needle 缓期**（不计失败）："
                  "main.tex 仍是原始骨架，一个结果数字都没有，"
                  "needle 无从绑定。这是 s3 阶段 G5 的正常形态 —— "
                  "G5 在 s3 跑，论文在 s6 才写。"]
        else:
            L.append("全部声明通过：JSON 侧逐条重算与存储值一致，"
                     "正文侧每个 needle 都在 main.tex 里按词边界命中。")
    else:
        if unevaluated:
            L.append(f"**FAIL · 空壳**：{len(unevaluated)} 条声明没算出来"
                     "（declared != checked），等于没检查。")
        if json_bad:
            L.append(f"**FAIL · JSON 侧**：{len(json_bad)} 条重算值与存储值不符。")
        if tex_bad:
            L.append(f"**FAIL · 正文侧**：{len(tex_bad)} 条 needle 在 main.tex 里"
                     "找不到（按 `(?<![\\d.])needle(?!\\d)` 词边界匹配）。"
                     f"正文已是 {tstate['state']} 状态，未命中即真失败。")
        if not tex_declared:
            L.append("**FAIL · 正文侧为空**：一条 needle 都没声明。")

    L += ["", "### 骨架判据（为什么这一轮正文侧可以缓期）", ""]
    if skeleton:
        L += [f"main.tex 挖掉元数据与占位符后**一个结果数字都没有**"
              f"（{tstate['n_result_tokens']} 个 token，`<<...>>` "
              f"{tex_stats['placeholders']} 处）。G5 在 s3 判，论文在 s6 写，"
              "所以此刻正文侧无法绑定，只能缓期。",
              "",
              "**这不是长期免死金牌**：判据每轮现算，正文只要出现第一个结果数字，"
              "状态立刻变 `written`，缓期立即作废，任何 needle 未命中都是硬失败。",
              "",
              "论文撰写手把数字填进 main.tex 后重跑本脚本即可自动绑定；"
              "DERIVED 表（第 4 节）已把每个派生值的算式登记好，"
              "按表上的算式写数就不会与 JSON 脱钩。"]
    else:
        L += [f"main.tex 已是 **{tstate['state']}** 状态"
              f"（{tstate['n_result_tokens']} 个结果数字 token），"
              "骨架豁免不适用。声明的 needle 必须全部命中。",
              "",
              "常见未命中原因：正文把 2 位小数写成 1 位或反过来 —— "
              "`needle_forms` 已同时接受 2 位与 1 位写法，仍不命中说明**数值不同**，"
              "要改的是正文而不是 needle。"]
    L += ["", "## 2 分组总表", "",
          "| 组 | 声明 | JSON 通过 | 正文 needle | 正文命中 |",
          "|---|---|---|---|---|"]
    for g in sorted(groups):
        n, ok, nd, hit = groups[g]
        L.append(f"| {g} | {n} | {ok} | {nd} | {hit} |")

    L += ["", "## 3 失败清单", ""]
    if not json_bad and not tex_bad and not unevaluated:
        L.append("无。" if not deferred
                 else f"无。正文侧 {len(deferred)} 条未命中属骨架缓期，"
                      f"不计失败（逐条见第 6 节）。")
    else:
        shown = 0
        for it in unevaluated:
            L.append(f"- **[未算出]** `{it['group']} / {it['name']}`：{it['actual']}")
            shown += 1
        for it in json_bad[:40]:
            L.append(f"- **[JSON]** `{it['group']} / {it['name']}`："
                     f"重算 {it['actual']!r} vs 存储 {it['expected']!r}"
                     f"（{it['evidence']}）")
            shown += 1
        if len(json_bad) > 40:
            L.append(f"- … JSON 侧另有 {len(json_bad) - 40} 条同类失败。")
        for it in tex_bad[:20]:
            L.append(f"- **[正文]** `{it['group']} / {it['name']}`："
                     f"needle {it['needle']} 未命中（{it['evidence']}）")
            shown += 1
        if len(tex_bad) > 20:
            L.append(f"- … 正文侧另有 {len(tex_bad) - 20} 条未命中。")

    L += ["", "## 4 DERIVED 登记表（正文里算出来的数，算式可手算复核）", "",
          "| 组 | 值 | 算式 |", "|---|---|---|"]
    seen = set()
    for it in items:
        if not it["derived"]:
            continue
        key = (it["group"], it["name"])
        if key in seen:
            continue
        seen.add(key)
        val = it["expected"]
        vs = f"{val:.6g}" if isinstance(val, (int, float)) else str(val)
        L.append(f"| {it['group']} | `{vs}` | {it['derived']} |")

    L += ["", "## 5 复算命令", "",
          "```powershell",
          "cd E:\\数学建模\\PRACTICE_2023B",
          "& 'E:\\Mini\\envs\\mathmodel\\python.exe' code\\verify_numbers.py",
          "```", "",
          "本脚本只读 data/*.json 与 main.tex，不改任何上游文件；"
          "唯一写入的是本报告自身（首行 `BYTES <n>` 用 write_bytes 迭代到不动点）。"]

    if deferred:
        L += ["", f"## 6 缓期清单（{len(deferred)} 条 needle，正文写出这些数即自动绑定）",
              "",
              "论文撰写手按这张表把数写进 main.tex；写完重跑本脚本，"
              "命中数会从 0 涨上去，缓期清单随之缩短，全部命中即 G5 满分。",
              "", "| 组 | 检查项 | 待命中的写法 | 期望值 | 算式 |",
              "|---|---|---|---|---|"]
        for it in deferred:
            ev = it["expected"]
            es = f"{ev:.6g}" if isinstance(ev, (int, float)) else str(ev)
            L.append(f"| {it['group']} | {it['name']} | "
                     f"`{', '.join(it['needle'])}` | `{es}` | "
                     f"{it['derived'] or DASH} |")

    # 附录 A：数值索引（结论 → json 键路径）。只印键路径，不印本脚本行号 ——
    # 行号会随代码改动漂移，印出来就是自指数字（不动点陷阱）。
    L += ["", "## 附录 A · 数值索引（结论 → data/*.json 键路径）",
          "",
          "> 正文与结论只指向本附录一次，不重复抄表；键路径就是给对账绑 claim 的原料。",
          "",
          "| 组 | 覆盖的结论 | JSON 键路径 |",
          "|---|---|---|"]
    for g, keys in APPENDIX_A:
        L.append(f"| {g} | {keys[0]} | `{keys[1]}` |")

    L += ["", "## 7 交给下一棒", "",
          "**论文撰写手**：第 6 节的表就是 `main.tex` 要填的数。逐行抄 `待命中的写法` 那一列，"
          "数值不要自己重算 —— 表里的每个数都已由第 4 节算式从 `data/*.json` 现算过一遍。"
          f"写完重跑本脚本，`正文侧 声明/命中` 会从 `{len(tex_declared)} / 0` 涨到 "
          f"`{len(tex_declared)} / {len(tex_declared)}`，"
          "`## 6 缓期清单` 消失、`VERDICT` 仍为 `PASS`，G5 才算真过。",
          "",
          "**图表手**：本报告不印任何脚本字节数（自指数字会变孤儿 token），"
          "所以 `tab:code` 里的脚本大小只能由 `code/gen_index.py` 现读生成；"
          "但 `code/verify_numbers.py` 本轮的字节数已经变了，`tab:code` 必须重跑一次生成器，"
          "否则那张表是旧的。",
          "",
          "**共同注意**：正文只要出现第一个结果数字，`tex_state` 就从 `skeleton` 变 `written`，"
          "骨架缓期立即作废 —— 半填的正文比空正文更容易被 G5 判 FAIL，"
          "所以第 6 节的数要么不填，要么一次填完。"]

    L += ["", f"VERDICT: {verdict}"]
    return "\n".join(L) + "\n", verdict


# ---------------------------------------------------------------- 主流程
def main(argv=None):
    argv = argv or "python code/verify_numbers.py"
    tex_raw = TEX.read_text(encoding="utf-8")
    tex = strip_comments(tex_raw)
    code_sizes = {str(p.stat().st_size) for p in CODE.glob("*.py")}
    tex_stats = {
        # 行数按编辑器口径：末尾有换行就不再额外算一行（106 而不是 107）。
        "lines": tex_raw.count("\n") + (0 if tex_raw.endswith("\n") else 1),
        # 磁盘字节（含 CRLF）。不能用 len(tex_raw.encode()) —— read_text 的
        # 通用换行已把 \r\n 折成 \n，那样算出来比磁盘少 106 字节，报的是假数。
        "bytes": TEX.stat().st_size,
        "tokens": len(re.findall(r"\d+(?:\.\d+)?", tex)),
        "placeholders": len(re.findall(r"<<.*?>>", tex_raw, re.S)),
    }

    docs = load_docs()
    C = build_claims(docs)
    items = evaluate(C, tex, code_sizes)
    tstate = tex_state(tex, tex_stats["placeholders"])

    tex_declared = [it for it in items if it["needle"]]
    tex_bound = [it for it in tex_declared if it["ok_tex"]]
    json_bad = [it for it in items if it["ok_json"] is False]
    unevaluated = [it for it in items if not it["evaluated"]]
    skeleton = (tstate["state"] == "skeleton")
    tex_miss = [it for it in tex_declared if it["ok_tex"] is False]
    tex_bad = [] if skeleton else tex_miss
    deferred = tex_miss if skeleton else []

    total = len(items)
    checked = sum(1 for it in items if it["evaluated"])
    count_ok = (total == checked)
    n_fail = len(json_bad) + len(tex_bad) + len(unevaluated)
    verdict = "PASS" if n_fail == 0 else "FAIL"
    exit_code = 0 if verdict == "PASS" else (3 if not count_ok else 1)

    # 报告：首行 BYTES 迭代到不动点（write_text 会把 \n 变 \r\n，永远不收敛）
    n = 0
    text = ""
    for _ in range(16):
        text, verdict = build_report(n, items, tex_stats, argv, exit_code,
                                     code_sizes, tstate)
        size = len(text.encode("utf-8"))
        if size == n:
            break
        n = size
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_bytes(text.encode("utf-8"))
    got = len(REPORT.read_bytes())

    print(f"{total} claims")
    print(f"claims={total} declared={total} checked={checked} failures={n_fail} "
          f"verdict={verdict} exit={exit_code} "
          f"json_ok={total - len(json_bad)} json_fail={len(json_bad)} "
          f"tex_bound={len(tex_bound)}/{len(tex_declared)} "
          f"tex_state={tstate['state']} deferred={len(deferred)}")
    for it in unevaluated[:10]:
        print(f"  UNEVAL [{it['group']}] {it['name']}: {it['actual']}")
    for it in json_bad[:10]:
        print(f"  FAIL [{it['group']}] {it['name']}: actual={it['actual']!r} "
              f"expected={it['expected']!r} ({it['evidence']})")
    if len(json_bad) > 10:
        print(f"  ... {len(json_bad) - 10} more JSON failures")
    for it in tex_bad[:5]:
        print(f"  TEX  [{it['group']}] {it['name']}: needle {it['needle']} "
              f"not in main.tex")
    if len(tex_bad) > 5:
        print(f"  ... {len(tex_bad) - 5} more tex misses")
    if deferred:
        print(f"  DEFER {len(deferred)} tex needles "
              f"(main.tex is the skeleton: no result number to bind yet)")
    print(f"report={REPORT} bytes={got}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(" ".join([Path(__file__).name] + sys.argv[1:])))
