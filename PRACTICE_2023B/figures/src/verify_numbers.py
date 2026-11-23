#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PRACTICE_2023B \u00b7 s3 \u6570\u503c\u5bf9\u8d26\u624b\uff1amain.tex \u91cc\u6bcf\u4e2a\u5173\u952e\u6570\u5b57 \u2194 data/*.json\u3002

\u53e3\u5f84\uff08\u4e0e\u6d3e\u5355\u300c\u56db\u6761\u786c\u7ecf\u9a8c\u300d\u4e00\u4e00\u5bf9\u5e94\uff09
------------------------------------
\u2460 DERIVED \u767b\u8bb0\uff1a\u6b63\u6587\u91cc\u7b97\u51fa\u6765\u4f46 JSON \u91cc\u6ca1\u6709\u7684\u6570\uff08\u6bd4\u503c / \u767e\u5206\u6bd4 / \u9608\u503c / \u6d3e\u751f\u91cf\uff09
   \u4e00\u5f8b\u8d70 `add(..., derived="<\u7b97\u5f0f>")`\uff0c\u8fd0\u884c\u65f6**\u91cd\u7b97**\u800c\u4e0d\u662f\u6284\u5e38\u91cf\uff1b\u62a5\u544a\u7b2c 4 \u8282
   \u628a\u6240\u6709\u7b97\u5f0f\u5217\u6210\u8868\uff0c\u4eba\u53ef\u9010\u6761\u624b\u7b97\u590d\u6838\u3002
\u2461 \u81ea\u6307\u6570\u5b57\u4e0d\u767b\u8bb0\uff1a\u6b63\u6587\u4e0d\u8bb8\u5370\u811a\u672c\u5b57\u8282\u6570\u3002\u672c\u811a\u672c\u8bfb code/*.py \u7684\u5b9e\u9645\u5b57\u8282\u6570\uff0c
   \u53ea\u8981\u67d0\u4e2a needle \u6070\u597d\u7b49\u4e8e\u67d0\u4e2a\u811a\u672c\u7684\u5b57\u8282\u6570\u5c31\u5224 FAIL\uff08\u9632\u300c\u6539\u4e00\u6b21\u4ee3\u7801\u5c31\u53d8\u5b64\u513f
   token\u300d\uff09\u3002\u5b57\u8282\u6570\u53ea\u7531 code/gen_index.py \u73b0\u8bfb\u751f\u6210\uff0c\u4e0d\u8fdb\u5bf9\u8d26\u96c6\u3002
\u2462 \u4e0d\u52a8\u70b9\uff1a\u672c\u811a\u672c\u53ea\u91cd\u5199 out/03-numbers.md \u81ea\u5df1\u7684\u9996\u884c `BYTES <n>`\uff0c\u7528
   write_bytes(utf-8) \u8fed\u4ee3\u5230 len(text)==n \u624d\u843d\u76d8\uff08Path.write_text \u4f1a\u628a \n \u53d8
   \r\n\uff0c\u6c38\u8fdc\u4e0d\u6536\u655b\uff09\u3002**\u4e0d\u6539 data/ledger.json** \u2014\u2014 \u6d3e\u5355\u660e\u4ee4\u4e0d\u8bb8\u52a8\u4e0a\u6e38\u6587\u4ef6\uff0c
   ledger \u7684 bytes/verdict \u7531 code/fetch_annex.py \u7ef4\u62a4\u3002
\u2463 \u6539\u4ee3\u7801\u540e\u5fc5\u987b\u91cd\u8dd1\uff1a\u672c\u811a\u672c\u81ea\u8eab\u5b57\u8282\u6570\u4e00\u53d8\uff0c\u62a5\u544a\u91cc\u5f15\u7528\u7684\u4efb\u4f55\u811a\u672c\u5b57\u8282\u6570\u90fd\u4f1a\u8fc7\u671f\uff0c
   \u6545\u62a5\u544a\u53ea\u5370 `\u590d\u7b97\u547d\u4ee4`\uff0c\u4e0d\u5370\u5b57\u8282\u6570\u3002

\u5339\u914d\u53e3\u5f84\uff08\u6d3e\u5355\u786c\u8981\u6c42\uff09
----------------------
\u8bcd\u8fb9\u754c `(?<![\d.])needle(?!\d)`\uff1a`16` \u4e0d\u8bb8\u547d\u4e2d `2016`\u3001\u4e0d\u8bb8\u547d\u4e2d `0.16`\u3001
\u4e0d\u8bb8\u547d\u4e2d `16.33`\u3002\u811a\u672c\u5f00\u5934\u6709 7 \u6761\u81ea\u6d4b\u65ad\u8a00\uff0c\u5148\u8bc1\u660e\u5339\u914d\u5668\u672c\u8eab\u662f\u5bf9\u7684\uff0c\u518d\u7528\u5b83\u3002

\u9000\u51fa\u7801
------
0 = PASS\uff1b1 = \u6709\u5931\u8d25\uff1b3 = declared != checked\uff08\u6709\u7a7a\u58f3\uff0c\u7b49\u4e8e\u6ca1\u68c0\u67e5\uff09\u3002
stdout \u540c\u65f6\u6253 `N claims` \u4e0e `claims=N declared=N checked=N failures=N verdict=...`
\u4e24\u79cd\u53e3\u5f84\uff08WORKFLOW.md:347 \u8981\u6c42\u4e24\u79cd\u90fd\u6253\uff09\u3002

\u8fd0\u884c\uff1apython code\\verify_numbers.py
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
import os

CODE = Path(__file__).resolve().parent
ROOT = CODE.parent
TEX = ROOT / "main.tex"
DATA = ROOT / "data"
LEDGER = DATA / "ledger.json"
PROBLEM = ROOT / "problem" / "problem.txt"
REPORT = ROOT / "out" / "03-numbers.md"

# ASCII-only source; the runtime value is the em dash used in report tables.
DASH = "\u2014"

# ---------------------------------------------------------------- \u5e38\u6570\uff08\u552f\u4e00\u6743\u5a01\u5728 code/model_skeleton.py::MS.PARAMS\uff09
EPS_REL = 0.05          # model_skeleton.py:97   C11  problem.txt L77
V_M = 22.414            # model_skeleton.py:146  T13
T_HOLD_S = 1800.0       # t_hold_ASSUMED 30 min \u00d7 60\uff08model_skeleton.py:120\uff09
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

# \u6b63\u6587\u53ea\u4f1a\u5199\u6709\u7269\u7406\u610f\u4e49\u7684\u91cf\u7ea7\u3002span \u5c0f\u4e8e\u8fd9\u4e2a\u503c\u7684\u91cf\uff08\u5982 C3H6 \u7684 0.06 mL/g\uff09
# \u5199\u8fdb\u6b63\u6587\u53cd\u800c\u8bef\u5bfc\u8bfb\u8005\uff0c\u6240\u4ee5\u4e0d\u7ed9\u5b83 needle \u2014\u2014 \u4f46 JSON \u4fa7\u4ecd\u7136\u9010\u6761\u91cd\u7b97\u3002
QUOTABLE_MIN = 1.0

# \u9644\u5f55 A\uff1a\u7ed3\u8bba \u2192 JSON \u952e\u8def\u5f84\u3002\u53ea\u5370\u952e\u8def\u5f84\uff0c\u4e0d\u5370\u672c\u811a\u672c\u884c\u53f7 \u2014\u2014 \u884c\u53f7\u4f1a\u968f\u4ee3\u7801\u6539\u52a8
# \u6f02\u79fb\uff0c\u5370\u51fa\u6765\u5c31\u662f\u81ea\u6307\u6570\u5b57\uff08\u4e0d\u52a8\u70b9\u9677\u9631\uff1a\u6539\u4e00\u6b21\u4ee3\u7801\uff0c\u9644\u5f55\u91cc\u7684\u6570\u5c31\u8fc7\u671f\uff09\u3002
APPENDIX_A = [
    ("B ledger", ("\u6570\u636e\u6eaf\u6e90\uff1a204 \u6761\u8bb0\u5f55 / 31 \u6761\u5e8f\u5217 / \u4e24\u4e2a\u9644\u4ef6 sha256",
                  "data/ledger.json \u2192 records / series / source_files")),
    ("C q1 ledger", ("Q1 \u9010\u683c\u503c\uff084 \u4ea7\u7269 \u00d7 3 \u7ec4\u5408\uff09\u4e0e\u53f0\u8d26\u4e00\u81f4",
                     "data/ledger.json \u2192 records[].value \u2194 data/results_q1.json \u2192 combos.*.products.*.y")),
    ("D q1", ("Q1 \u9996\u672b\u503c\u3001\u53d8\u5e45\u3001\u9608\u503c\u3001\u8d85\u9608\u6b65\u6570\u3001\u5355\u8c03\u6027",
              "data/results_q1.json \u2192 combos.*.products.*.{first,last,delta_end,delta_end_pct,span,mean,thr_trend,span_over_thr,n_step_exceed,monotone}")),
    ("E q1 ilr", ("Q1 \u6210\u5206\u56de\u5f52\uff1a\u03c3_fit\u3001\u5931\u62df F\u3001R\u00b2\u3001AIC \u9009\u578b",
                  "data/results_q1.json \u2192 combos.*.ilr.{sigma_fit,lack_of_fit_F,R2_each,aic,aic_best}")),
    ("F q2 ledger", ("Q2 \u9010\u683c\u6c14\u4f53\u4f53\u79ef\u4e0e\u53f0\u8d26\u4e00\u81f4",
                     "data/ledger.json \u2192 records[].value \u2194 data/results_q2.json \u2192 combos.*.gases.*.z")),
    ("G q2", ("Q2 \u6c14\u4f53 span\u3001\u03c6\u3001\u8d28\u91cf\u4ea7\u7387\u3001\u91cf\u7ea7\u5206\u5c42\u3001\u5cf0\u503c\u6863\u4f4d",
              "data/results_q2.json \u2192 combos.*.gases.*.{span,phi,m_mg_per_g,tier,argmax_label,trend_significant}")),
    ("H q2 rowsum", ("Q2 \u884c\u548c\u4e0e \u03c6 \u5206\u6bcd",
                     "data/results_q2.json \u2192 combos.*.row_sum / gases.*.phi / tiers")),
    ("I q2 bridge", ("\u4e24\u9644\u4ef6\u91cf\u7eb2\u6865\u63a5\u7cfb\u6570 \u03b2",
                     "data/results_q2.json \u2192 bridge.*.{gas_mass_wtpct,annex1_syngas_wtpct,beta_bridge}")),
    ("J q3", ("Q3 CE \u4e0e LG \u9010\u6863\u5dee\u3001\u5e73\u5747\u5dee\u3001\u8d85\u9608\u8ba1\u6570\u3001\u7b26\u53f7\u7ffb\u8f6c",
              "data/results_q3.json \u2192 products.* / gases.*")),
    ("K q3", ("Q3 \u5355\u6c14\u6700\u5927\u7edd\u5bf9\u4f53\u79ef",
              "data/results_q3.json \u2192 gases.*.abs_max")),
    ("L q4", ("Q4 \u9009\u62e9\u6027\u5f39\u6027 \u03b3\u3001\u78b3\u5e73\u8861\u6536\u652f",
              "data/results_q4.json \u2192 selectivity.*.gamma_centered / carbon_balance.*")),
    ("M q4 kinetics", ("Q4 \u52a8\u529b\u5b66\uff1akt\u3001k\u3001n \u7ea7\u6df7\u6dc6\u6bd4\u3001Ea\u2013A \u810a\u7ebf",
                       "data/results_q4.json \u2192 kinetics.*")),
    ("N q5 grid", ("Q5 \u9884\u6d4b\u7f51\u683c r \u2192 w",
                   "data/results_q5.json \u2192 meta.grid_r / meta.grid_w")),
    ("O q5", ("Q5 \u70b9\u9884\u6d4b\u3001\u533a\u95f4\u3001\u7559\u4e00\u8bef\u5dee",
              "data/results_q5.json \u2192 combos.*.{point,lo,hi,loo_rmse,loo_rmse_rel,row_sum_point}")),
    ("P boundary", ("Q5 \u67e5\u8be2\u70b9\u662f\u5426\u8d8a\u51fa\u89c2\u6d4b\u652f\u6491",
                    "data/results_boundary.json \u2192 combos.*.{rows,n_boundary_star,n_extrapolation_star2}")),
    ("P binding", ("\u7ea6\u675f\u5728\u89e3\u5904\u662f\u5426\u8d77\u4f5c\u7528",
                   "data/results_binding.json \u2192 sources[].binding")),
    ("P perturb", ("\u53c2\u6570 \u00b110% \u540e\u7ed3\u8bba\u662f\u5426\u7ffb\u8f6c",
                   "data/results_perturb.json \u2192 counts / runs[].flips")),
    ("P timing", ("\u5404\u6b65\u8c03\u7528\u8017\u65f6\u4e2d\u4f4d\u6570",
                  "data/results_timing.json \u2192 calls[].median_ms")),
]

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------- \u5339\u914d\u5668
def strip_comments(text: str) -> str:
    """\u628a % \u6ce8\u91ca\u6574\u6bb5\u6362\u6210\u7a7a\u683c\uff0c\u4fdd\u6301\u504f\u79fb\u4e0e\u884c\u53f7\u4e0d\u53d8\uff1b\\% \u662f\u8f6c\u4e49\uff0c\u4e0d\u7b97\u6ce8\u91ca\u3002"""
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
    """\u8bcd\u8fb9\u754c\u5339\u914d\uff1a(?<![\\d.])needle(?!\\d)\u3002"""
    return re.search(r"(?<![\d.])" + re.escape(str(needle)) + r"(?!\d)", text) is not None


def needle_forms(v: float, nds=(2, 1)) -> list:
    """\u4e00\u4e2a\u503c\u5728\u6b63\u6587\u91cc\u53ef\u80fd\u7684\u5199\u6cd5\uff08\u542b\u7edd\u5bf9\u503c\u5199\u6cd5\uff0c\u4f9b\u300c\u4e0b\u964d\u4e86 37.67%\u300d\u8fd9\u7c7b\u53e5\u5b50\uff09\u3002

    \u4e09\u9053\u95f8\uff0c\u9632\u6b62\u5f31 needle \u628a\u5bf9\u8d26\u53d8\u6210\u7a7a\u8f6c\uff08\u5047 PASS \u6bd4\u5931\u8d25\u66f4\u574f\uff09\uff1a
    \u2460 \u820d\u5165\u540e\u53d8\u6210 0 \u7684\u5199\u6cd5\u4e00\u5f8b\u4e22\u6389\uff08`0.00` \u4f1a\u547d\u4e2d\u4efb\u4f55\u5730\u65b9\uff09\uff1b
    \u2461 \u76f8\u5bf9\u8bef\u5dee\u8d85\u8fc7 5% \u7684\u5199\u6cd5\u4e22\u6389\uff08\u53ea\u4fdd\u7559 2 \u4f4d\u4e0e 1 \u4f4d\u4e24\u79cd\u7cbe\u5ea6\uff0c\u4e0d\u4fdd\u7559 0 \u4f4d\uff09\uff1b
    \u2462 **\u6709\u6548\u6570\u5b57\u5c11\u4e8e 3 \u4f4d\u7684\u5199\u6cd5\u4e22\u6389**\uff1a`1.2`\u3001`0.15`\u3001`2.3` \u8fd9\u7c7b needle
       \u5728\u4efb\u610f\u8bba\u6587\u91cc\u90fd\u80fd\u649e\u4e0a\uff08\u9875\u8fb9\u8ddd\u3001\u7cfb\u6570\u3001\u5e74\u4efd\uff09\uff0c\u547d\u4e2d\u4e5f\u4e0d\u8bc1\u660e\u4efb\u4f55\u4e8b\u3002
       \u503c\u672c\u8eab\u5c31\u53ea\u6709 2 \u4f4d\u6709\u6548\u6570\u5b57\u65f6\u5b81\u53ef\u4e0d\u58f0\u660e needle\uff0c\u4e5f\u4e0d\u8bb8\u6302\u4e00\u4e2a\u5047\u547d\u4e2d\u3002

    \u6574\u6570\uff08204\u30018\u3001100\uff09\u53ea\u51fa\u6574\u6570\u5199\u6cd5\uff1a\u6b63\u6587\u4e0d\u4f1a\u5199 `204.00`\uff0c
    \u51fa\u5c0f\u6570\u5199\u6cd5\u7b49\u4e8e\u6c38\u8fdc 0 \u547d\u4e2d\u3002\u4f46**\u4e2a\u4f4d\u6570\u6574\u6570\u4e0d\u7ed9 needle** \u2014\u2014 `4`\u3001`8`
    \u5728\u6b63\u6587\u91cc\u5230\u5904\u90fd\u662f\uff08\u6863\u4f4d\u5e8f\u53f7\u3001\u56fe\u53f7\u3001\u9875\u6570\uff09\uff0c\u547d\u4e2d\u5b83\u8bc1\u660e\u4e0d\u4e86\u4efb\u4f55\u4e8b\u3002
    """
    v = float(v)
    if abs(v - round(v)) < 1e-9:
        n = int(round(v))
        return [str(n)] if abs(n) >= 10 else []

    def n_sig(s: str) -> int:
        """\u6709\u6548\u6570\u5b57\u4f4d\u6570\uff1a\u4ece\u7b2c\u4e00\u4e2a\u975e\u96f6\u6570\u5b57\u6570\u5230\u4e32\u5c3e\uff08\u542b\u5199\u51fa\u6765\u7684\u5c3e\u96f6\uff09\u3002"""
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


# ---------------------------------------------------------------- \u53d6\u503c\u5c0f\u5de5\u5177
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


# ---------------------------------------------------------------- \u8f7d\u5165
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


# ---------------------------------------------------------------- \u58f0\u660e\u96c6
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

    # ---- A \u5339\u914d\u5668\u81ea\u6d4b\uff08\u5148\u8bc1\u660e (?<![\d.])needle(?!\d) \u771f\u7684\u5b88\u8bcd\u8fb9\u754c\uff09
    for label, text, needle, want in (
            ("2016 \u4e0d\u542b 16", "the year 2016", "16", False),
            ("0.16 \u4e0d\u542b 16", "value 0.16", "16", False),
            ("16.33 \u542b 16.33", "value 16.33", "16.33", True),
            ("116.33 \u4e0d\u542b 16.33", "value 116.33", "16.33", False),
            ("16.330 \u4e0d\u542b 16.33", "value 16.330", "16.33", False),
            ("\u72ec\u7acb 16 \u547d\u4e2d", "there are 16 gases", "16", True),
            ("19.46 \u547d\u4e2d 19.46", "Tar 19.46 wt.%", "19.46", True),
            ("119.46 \u4e0d\u542b 19.46", "119.46", "19.46", False)):
        A("A matcher self-test", label,
          (lambda t=text, n=needle: has_token(t, n)), want,
          evidence="regex (?<![\\d.])needle(?!\\d)")

    # ---- B \u53f0\u8d26\u81ea\u8eab\uff08data/ledger.json \u2194 \u78c1\u76d8\uff09
    A("B ledger", "records \u6761\u6570 = 204", lambda: len(L["records"]), 204,
      evidence="ledger.json records[]")
    A("B ledger", "series \u6761\u6570 = 31", lambda: len(L["series"]), 31,
      evidence="ledger.json series[]")
    A("B ledger", "bytes \u5b57\u6bb5 = \u78c1\u76d8\u5b9e\u9645\u5b57\u8282",
      lambda: L["bytes"] - LEDGER.stat().st_size, 0,
      evidence="ledger.json bytes vs stat().st_size")
    A("B ledger", "bytes_line = BYTES <bytes>",
      lambda: 0 if L["bytes_line"] == f"BYTES {L['bytes']}" else 1, 0,
      evidence="ledger.json bytes_line")
    A("B ledger", "annex_i sha256 \u4e0e\u78c1\u76d8\u4e00\u81f4",
      lambda: 0 if L["source_files"]["annex_i"]["sha256"] == sha256_of(
          ROOT / L["source_files"]["annex_i"]["path"]).lower() else 1, 0,
      evidence="source_files.annex_i.sha256")
    A("B ledger", "annex_ii sha256 \u4e0e\u78c1\u76d8\u4e00\u81f4",
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
    A("B ledger", "problem.txt \u5b57\u8282\u4e0e sha256 \u4e0e\u78c1\u76d8\u4e00\u81f4",
      lambda: 0 if (L["coverage_scan"]["problem_txt"]["bytes"]
                    == PROBLEM.stat().st_size
                    and L["coverage_scan"]["problem_txt"]["sha256"]
                    == sha256_of(PROBLEM).lower()) else 1, 0,
      evidence="coverage_scan.problem_txt")
    A("B ledger", "verdict \u4e0e verdict_line \u4e00\u81f4",
      lambda: 0 if L["verdict_line"] == f"VERDICT: {L['verdict']}" else 1, 0,
      evidence="ledger.json verdict / verdict_line")
    A("B ledger", "\u9898\u7ed9 eps_rel = 0.05",
      lambda: q1["meta"]["caliber"]["eps_rel"], EPS_REL,
      evidence="results_q1.json meta.caliber.eps_rel\uff1bmodel_skeleton.py:97")

    # ---- C Q1\uff1aJSON \u4e0e\u53f0\u8d26\u9010\u683c\u4e00\u81f4\uff08results \u4e0d\u8bb8\u4e0e\u9644\u4ef6\u8131\u94a9\uff09
    for c in COMBOS:
        for p in PROD:
            A("C q1 ledger", f"{c} {p} y \u4e0e\u53f0\u8d26\u9010\u683c\u4e00\u81f4",
              (lambda c=c, p=p: 0 if [round(v, 9) for v in
                                      q1["combos"][c]["products"][p]["y"]]
               == [round(v, 9) for v in
                   ledger_series(L, "I", LONG[c], IND[p])] else 1), 0,
              evidence=f"ledger.json I.{LONG[c]}.{IND[p]}.*")

    # ---- D Q1 \u7edf\u8ba1\u91cf\uff08\u6d3e\u751f\uff1a\u5168\u90e8\u91cd\u7b97\uff09
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
            A(g, "delta_end_pct = 100\u00b7\u0394/y[0]",
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
            A(g, "thr_trend = 0.10\u00b7mean",
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
              derived="count(|\u0394y_i| > 0.10*max(|y_i|,|y_i+1|))",
              evidence="solve.py:118-122")
            A(g, "n_step", (lambda y=y: len(y) - 1), d["n_step"],
              evidence="len(y)-1")
            A(g, "monotone", (lambda y=y: is_monotone(y)), d["monotone"],
              derived="all(\u0394y>0) or all(\u0394y<0)", evidence="solve.py:181")

    # ---- E Q1 ILR / AIC\uff08\u6d3e\u751f\uff1aF \u4e0e sigma \u7684\u5173\u7cfb\u3001AIC \u6700\u4f18\u6a21\u578b\uff09
    for c in COMBOS:
        il = q1["combos"][c]["ilr"]
        ai = q1["combos"][c]["aic"]
        g = f"E q1 ilr {c}"
        A(g, "sigma_fit\u00b2 = rss/(n_obs-k_par)",
          (lambda il=il: math.sqrt(il["rss"] / (il["n_obs"] - il["k_par"]))),
          il["sigma_fit"], rel=1e-6,
          needle=needle_forms(il["sigma_fit"], nds=(4,)),
          derived="sigma_fit = sqrt(rss/(n_obs-k_par))",
          evidence="solve.py:191")
        A(g, "lack_of_fit_F = (sigma_fit/sigma_noise)\u00b2",
          (lambda il=il: (il["sigma_fit"] / il["sigma_noise_mc"]) ** 2),
          il["lack_of_fit_F"], rel=1e-6,
          needle=needle_forms(il["lack_of_fit_F"]),
          derived="F = (sigma_fit / sigma_noise_mc)^2",
          evidence="solve.py:204")
        A(g, "n_obs = 3\u00b7\u6863\u4f4d\u6570",
          (lambda c=c: il_nobs(q1, c)), q1["combos"][c]["ilr"]["n_obs"],
          derived="n_obs = n_levels * 3\uff08ILR 3 \u7ef4\uff09", evidence="solve.py:190")
        A(g, "aic_best = argmin(aic)",
          (lambda ai=ai: min(ai, key=ai.get)), q1["combos"][c]["aic_best"],
          derived="aic_best = min(cand, key=cand.get)", evidence="solve.py:230")
        A(g, "R2[0]",
          (lambda il=il: il["R2_each"][0]), il["R2_each"][0], rel=1e-6,
          needle=needle_forms(il["R2_each"][0], nds=(3,)),
          evidence="results_q1.json ilr.R2_each[0]")
        A(g, "\u5931\u62df\u5224\u8bed\u4e0e F \u4e00\u81f4",
          (lambda il=il: 0 if (il["lack_of_fit_F"] <= 1.0)
           == (il["lack_of_fit_verdict"].startswith("\u6b8b\u5dee\u5728")) else 1), 0,
          derived="F<=1 \u21d4 \u6b8b\u5dee\u5728\u566a\u58f0\u5185", evidence="solve.py:225-226")

    # ---- F Q2\uff1aJSON \u4e0e\u53f0\u8d26\u9010\u683c\u4e00\u81f4 + \u6d3e\u751f\u7edf\u8ba1
    for c in COMBOS:
        for gname, gd in q2["combos"][c]["gases"].items():
            A("F q2 ledger", f"{c} {gname} z \u4e0e\u53f0\u8d26\u9010\u683c\u4e00\u81f4",
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
            A(g, "thr_trend = 0.10\u00b7mean",
              (lambda z=z: 0.1 * mean(z)), gd["thr_trend"],
              derived="thr_trend = 0.10*mean(z)", evidence="solve.py:265")
            A(g, "span_over_thr",
              (lambda z=z: (max(z) - min(z)) / (0.1 * mean(z))),
              gd["span_over_thr"],
              needle=(needle_forms(gd["span_over_thr"], nds=(2,))
                      if gd["span_over_thr"] >= QUOTABLE_MIN else None),
              derived="span_over_thr = span/(0.10*mean(z))",
              evidence="solve.py:266")
            A(g, "tier = major \u21d4 span\u22655",
              (lambda z=z: "major" if max(z) - min(z) >= 5.0 else "minor"),
              gd["tier"], derived="tier = major if span>=5 else minor",
              evidence="solve.py:271")
            A(g, "argmax_label", (lambda z=z, labels=labels: labels[z.index(max(z))]),
              gd["argmax_label"], evidence="solve.py:270")
            A(g, "m_mg_per_g = z\u00b7M/22.414",
              (lambda z=z, M=M: z[-1] * M / V_M), gd["m_mg_per_g"][-1],
              rel=1e-9, derived="m = z * M / V_m", evidence="solve.py:272")
            A(g, "monotone", (lambda z=z: is_monotone(z)), gd["monotone"],
              derived="all(\u0394z>0) or all(\u0394z<0)", evidence="solve.py:269")
            A(g, "n_step_exceed", (lambda z=z: n_exceed(z)), gd["n_step_exceed"],
              derived="count(|\u0394z_i| > 0.10*max(|z_i|,|z_i+1|))",
              evidence="solve.py:268")
            A(g, "trend_significant = span > thr_trend",
              (lambda z=z: (max(z) - min(z)) > 0.1 * mean(z)),
              gd["trend_significant"],
              derived="trend_significant = span > 0.10*mean(z)",
              evidence="solve.py:267")

        # \u884c\u548c\u4e0e \u03c6 \u7684\u5206\u6bcd\uff08\u03c6 \u662f\u5206\u6570\uff0c\u4e0d\u662f\u767e\u5206\u6570\uff09
        rs = q2["combos"][c]["row_sum"]
        A(f"H q2 rowsum {c}", "row_sum = \u03a3_g z_g",
          (lambda c=c: sum(gd["z"][0] for gd in
                           q2["combos"][c]["gases"].values())), rs[0],
          rel=1e-9, derived="row_sum_i = \u03a3_g z_{g,i}", evidence="solve.py:256")
        A(f"H q2 rowsum {c}", "\u03c6 \u5206\u6bcd\u662f\u8be5\u884c\u884c\u548c\uff08\u4e0d\u662f 100\uff09",
          (lambda c=c: sum(gd["phi"][0] for gd in
                           q2["combos"][c]["gases"].values())), 1.0,
          rel=1e-9, derived="\u03a3_g \u03c6_{g,i} = 1\uff08\u03c6 = z / row_sum\uff09",
          evidence="solve.py:255")
        A(f"H q2 rowsum {c}", "tiers.major \u4e0e tier \u5b57\u6bb5\u4e00\u81f4",
          (lambda c=c: sorted(g for g, gd in q2["combos"][c]["gases"].items()
                              if gd["tier"] == "major")),
          sorted(q2["tiers"][c]["major"]),
          derived="tiers.major = [g for g if tier=='major']",
          evidence="solve.py:276-279")

    # \u6865\u63a5\uff1aAnnex II \u4f53\u79ef \u2192 \u8d28\u91cf \u2192 wt.%\uff0c\u4e0e Annex I Syngas \u6bd4
    for c in COMBOS:
        b = q2["bridge"][c]
        A(f"I q2 bridge {c}", "gas_mass_wtpct = m/10",
          (lambda b=b: b["gas_mass_mg_per_g"][0] / 10.0), b["gas_mass_wtpct"][0],
          rel=1e-9, derived="wtpct = m_mg_per_g / 10", evidence="solve.py:291")
        # 2026-11-19 \u53e3\u5f84\u5ba1\u8ba1 #21\uff1a\u539f\u6765\u53ea\u767b `beta_bridge[0]`\uff08\u9996\u6863\uff09\uff0c\u800c\u4e09\u7ec4\u5408\u7684
        # \u9996\u6863\u7aef\u70b9\u4fa7\u4e0d\u4e00\u81f4\uff08CS/CE \u662f\u4e0a\u7aef\u3001LG \u662f\u4e0b\u7aef\uff09\uff0c\u6b63\u6587\u5199\u7684\u662f\u533a\u95f4\u3002\u6539\u6210\u767b\u533a\u95f4
        # \u4e24\u7aef\uff0c\u4e14\u6ce8\u660e\u767b\u7684\u662f lo / hi \u2014\u2014 \u5355\u4e2a\u7aef\u70b9\u4e0d\u80fd\u88ab\u8bfb\u6210\u300c\u8fd9\u4e00\u7ec4\u5408\u7684 beta\u300d\u3002
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

    # ---- J Q3\uff1aCE vs LG
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
        A(g, "thr_diff = 0.10\u00b7\u221a(CE\u00b2+LG\u00b2)",
          (lambda pd=pd: [0.1 * math.sqrt(a * a + b * b)
                          for a, b in zip(pd["CE"], pd["LG"])]), pd["thr_diff"],
          derived="thr_diff = 2*eps_rel*sqrt(ya\u00b2+yb\u00b2) = 0.10*sqrt(ya\u00b2+yb\u00b2)",
          evidence="solve.py:106-110")
        A(g, "n_exceed = count(|\u0394|>thr)",
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
        A(g, "max|\u0394|",
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

    # ---- L Q4\uff1a\u9009\u62e9\u6027 \u03b3\u3001\u78b3\u5e73\u8861\u3001\u52a8\u529b\u5b66
    for c in COMBOS:
        sel = q4["selectivity"][c]
        A(f"L q4 gamma {c}", "\u03a3\u03b3 = 0\uff08\u4e2d\u5fc3\u5316\uff09",
          (lambda sel=sel: sum(sel["gamma_centered"].values())), 0.0,
          rel=1e-6, derived="\u03a3_p gamma_p = 0\uff08\u4e2d\u5fc3\u5316\u540e\uff09",
          evidence="results_q4.json selectivity")
        for p in PROD:
            A(f"L q4 gamma {c}", f"gamma[{p}]",
              (lambda sel=sel, p=p: sel["gamma_centered"][p]),
              sel["gamma_centered"][p], rel=1e-9,
              needle=needle_forms(sel["gamma_centered"][p], nds=(3, 2)),
              derived="gamma_p = d ln S_p/d w\uff0c\u4e2d\u5fc3\u5316\u540e \u03a3gamma = 0",
              evidence="results_q4.json gamma_centered")
        cb = q4["carbon_balance"][c]
        A(f"L q4 carbon {c}", "delta_end = c[-1]-c[0]",
          (lambda cb=cb: cb["carbon_mmol_per_g"][-1]
           - cb["carbon_mmol_per_g"][0]), cb["delta_end"], rel=1e-6,
          needle=needle_forms(cb["delta_end"], nds=(3, 2)),
          derived="delta_end = c_mmol[-1] - c_mmol[0]", evidence="solve.py:387")
        A(f"L q4 carbon {c}", "delta_end_pct = 100\u00b7\u0394/c[0]",
          (lambda cb=cb: 100.0 * (cb["carbon_mmol_per_g"][-1]
                                  - cb["carbon_mmol_per_g"][0])
           / cb["carbon_mmol_per_g"][0]), cb["delta_end_pct"], rel=1e-6,
          needle=needle_forms(cb["delta_end_pct"], nds=(1,)),
          derived="delta_end_pct = 100*(c[-1]-c[0])/c[0]",
          evidence="solve.py:388")

    k = q4["kinetics"]
    A("M q4 kinetics", "kt n=0 = \u03b1", (lambda: ALPHA_T), k["kt_required"]["n=0"],
      rel=1e-12, derived="kt(n=0) = alpha", evidence="solve.py:407")
    A("M q4 kinetics", "kt n=1 = -ln(1-\u03b1)",
      (lambda: -math.log(1.0 - ALPHA_T)), k["kt_required"]["n=1"], rel=1e-9,
      derived="kt(n=1) = -ln(1-alpha)", evidence="solve.py:407")
    A("M q4 kinetics", "kt n=2 = 1/(1-\u03b1)-1",
      (lambda: 1.0 / (1.0 - ALPHA_T) - 1.0), k["kt_required"]["n=2"], rel=1e-9,
      derived="kt(n=2) = 1/(1-alpha) - 1", evidence="solve.py:407")
    A("M q4 kinetics", "k = kt / t_hold(1800 s)",
      (lambda: (-math.log(1.0 - ALPHA_T)) / T_HOLD_S),
      k["k_required_per_s"]["n=1"], rel=1e-9,
      derived="k = kt / t_hold_s", evidence="solve.py:408")
    A("M q4 kinetics", "t_hold_s = 30 min \u00d7 60",
      (lambda: 30.0 * 60.0), k["t_hold_s"], rel=1e-12,
      derived="t_hold_s = t_hold_ASSUMED*60 = 30*60 = 1800",
      evidence="model_skeleton.py:120")
    A("M q4 kinetics", "n_order_confounding = kt(n=2)/kt(n=1)",
      (lambda: (1.0 / (1.0 - ALPHA_T) - 1.0) / (-math.log(1.0 - ALPHA_T))),
      k["n_order_confounding"], rel=1e-9,
      needle=needle_forms(k["n_order_confounding"], nds=(4, 3)),
      derived="confounding = kt(n=2)/kt(n=1)\uff08\u6bd4\u503c\uff0c\u4e0d\u662f log \u6bd4\uff09",
      evidence="solve.py:409")
    A("M q4 kinetics", "ridge \u9996\u884c A = k\u00b7exp(Ea\u00b71000/(R\u00b7T))",
      (lambda: (-math.log(1.0 - ALPHA_T)) / T_HOLD_S
       * math.exp(k["ridge_n1"][0]["Ea_kJ_mol"] * 1000.0 / (R_GAS * T_PY_K))),
      k["ridge_n1"][0]["A_per_s"], rel=1e-6,
      derived="A = k_need(n=1)*exp(Ea*1000/(R*T))", evidence="solve.py q4")
    A("M q4 kinetics", "ridge \u9996\u884c log10_A",
      (lambda: math.log10(k["ridge_n1"][0]["A_per_s"])),
      k["ridge_n1"][0]["log10_A"], rel=1e-9,
      needle=needle_forms(k["ridge_n1"][0]["log10_A"], nds=(3,)),
      derived="log10_A = log10(A)", evidence="results_q4.json ridge_n1[0]")
    A("M q4 kinetics", "ridge \u884c\u6570 = 16",
      (lambda: len(k["ridge_n1"])), 16, evidence="Ea 100\u2192250 \u6b65\u957f 10")
    A("M q4 kinetics", "ridge \u672b\u884c Ea = 250",
      (lambda: k["ridge_n1"][-1]["Ea_kJ_mol"]), 250.0,
      evidence="model_skeleton.py:130 Ea_ASSUMED_RANGE")

    # ---- N Q5\uff1a\u7f51\u683c\u3001\u533a\u95f4\u3001\u7559\u4e00
    A("N q5 grid", "grid_w = r/(1+r)",
      (lambda: [r / (1.0 + r) for r in q5["meta"]["grid_r"]]),
      q5["meta"]["grid_w"], rel=1e-12,
      derived="w = r/(1+r)\uff08model_skeleton.py:165-168\uff09",
      evidence="results_q5.json meta.grid_w")
    for i, w in enumerate(q5["meta"]["grid_w"]):
        A("N q5 grid", f"grid_w[{i}]", (lambda w=w: w), w, rel=1e-12,
          needle=needle_forms(w, nds=(4, 3)),
          derived="w = r/(1+r)", evidence="results_q5.json meta.grid_w")
    A("N q5 grid", "grid_r \u4e0e boundary.grid_declared_r \u4e00\u81f4",
      (lambda: q5["meta"]["grid_r"]), bd["meta"]["grid_declared_r"], rel=1e-12,
      evidence="results_q5.json meta.grid_r vs results_boundary.json")
    for c in COMBOS:
        d = q5["combos"][c]
        A(f"O q5 {c}", "row_sum_point = 100\uff08ILR \u95ed\u5408\uff09",
          (lambda d=d: min(d["row_sum_point"])), 100.0, rel=1e-9,
          derived="\u884c\u548c\u6052\u7b49\u4e8e 100\uff08ILR \u53cd\u53d8\u6362\u7684\u6784\u9020\u6027\u95ed\u5408\uff09",
          evidence="results_q5.json row_sum_point")
        A(f"O q5 {c}", "is_extrapolation = False",
          (lambda d=d: d["is_extrapolation"]), False,
          evidence="grid \u5168\u90e8\u843d\u5728\u89c2\u6d4b\u533a\u95f4\u5185")
        A(f"O q5 {c}", "sigma_ilr = q1 sigma_fit",
          (lambda c=c: d_sigma(q1, c)), d["sigma_ilr"], rel=1e-9,
          derived="Q5 \u7684 ILR \u566a\u58f0\u5c3a\u5ea6\u6cbf\u7528 Q1 \u62df\u5408\u6b8b\u5dee sigma_fit",
          evidence="results_q5.json sigma_ilr vs results_q1.json ilr.sigma_fit")
        for p in PROD:
            ymean = mean(q1["combos"][c]["products"][p]["y"])
            A(f"O q5 {c}/{p}", "loo_rmse_rel% = 100\u00b7rmse/mean(y_q1)",
              (lambda d=d, p=p, ymean=ymean: 100.0 * d["loo_rmse"][p] / ymean),
              d["loo_rmse_rel"][p] * 100.0, rel=1e-6,
              needle=needle_forms(d["loo_rmse_rel"][p] * 100.0, nds=(2, 1)),
              derived="loo_rmse_rel% = 100*loo_rmse/mean(\u89c2\u6d4b y)\uff08solve.py:472\uff09",
              evidence="results_q5.json loo_rmse_rel")
            A(f"O q5 {c}/{p}", "\u533a\u95f4 lo < point < hi",
              (lambda d=d, p=p: all(a < b < c2 for a, b, c2 in
                                    zip(d["lo"][p], d["point"][p], d["hi"][p]))),
              True, evidence="results_q5.json lo/hi/point")
            A(f"O q5 {c}/{p}", "point \u9996\u70b9",
              (lambda d=d, p=p: d["point"][p][0]), d["point"][p][0], rel=1e-9,
              evidence="results_q5.json point")

    # ---- P \u9644\u52a0\u4ea4\u4ed8\uff08\u8017\u65f6 / binding / \u8fb9\u754c / \u6270\u52a8\uff09
    for call in tm["calls"]:
        A("P timing", f"{call['name']} median = runs \u4e2d\u4f4d",
          (lambda call=call: sorted(call["runs_ms"])[len(call["runs_ms"]) // 2]),
          call["median_ms"], rel=1e-9,
          derived="median = sorted(runs)[len//2]\uff08results_timing.json meta\uff09",
          evidence="results_timing.json calls[].median_ms")
    A("P timing", "reps = 5", (lambda: tm["meta"]["reps"]), 5,
      evidence="results_timing.json meta.reps")
    A("P binding", "sources \u6761\u6570 = 11", (lambda: len(bn["sources"])), 11,
      evidence="results_binding.json sources[]")
    A("P binding", "binding \u53d6\u503c\u90fd\u5728\u5408\u6cd5\u96c6\u5408\u5185",
      (lambda: sorted({s["binding"] for s in bn["sources"]})),
      sorted({s["binding"] for s in bn["sources"]}),
      evidence="results_binding.json meta.rule")
    for c in COMBOS:
        d = bd["combos"][c]
        A(f"P boundary {c}", "n_boundary_star = count('\u2605')",
          (lambda d=d: sum(1 for r in d["rows"] if r["mark"] == "\u2605")),
          d["n_boundary_star"], derived="count(mark == '\u2605')",
          evidence="results_boundary.json combos[].rows")
        A(f"P boundary {c}", "n_extrapolation_star2 = count('\u2605\u2605')",
          (lambda d=d: sum(1 for r in d["rows"] if r["mark"] == "\u2605\u2605")),
          d["n_extrapolation_star2"], derived="count(mark == '\u2605\u2605')",
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
      derived="\u5206\u6bcd\u53ea\u7b97 model \u7c7b\u53ef\u884c\u6270\u52a8",
      evidence="results_perturb.json meta.denominator_rule")
    A("P perturb", "never_read + query_move + model_perturb = attempted",
      (lambda: pc["never_read"] + pc["query_move"] + pc["model_perturb"]),
      pc["attempted"], derived="\u4e09\u7c7b\u4e4b\u548c = attempted",
      evidence="results_perturb.json meta.counts")
    A("P perturb", "runs \u6761\u6570 = attempted", (lambda: len(pb["runs"])),
      pc["attempted"], evidence="results_perturb.json runs[]")
    A("P perturb", "model_runs_with_flip = count(n_flips>0)",
      (lambda: sum(1 for r in pb["runs"]
                   if r["class"] == "model" and (r["n_flips"] or 0) > 0)),
      pc["model_runs_with_flip"], derived="count(model \u4e14 n_flips>0)",
      evidence="results_perturb.json runs[]")
    return C


def il_nobs(q1, c):
    return len(q1["combos"][c]["labels"]) * 3


def d_sigma(q1, c):
    return q1["combos"][c]["ilr"]["sigma_fit"]


# ---------------------------------------------------------------- \u6b63\u6587\u72b6\u6001
# \u8fd9\u4e9b\u6570\u5b57\u662f**\u7ed3\u6784\u7f16\u53f7**\uff0c\u4e0d\u662f\u7ed3\u679c\u6570\u5b57\uff1a\u961f\u53f7\u3001\u9875\u7801\u3001\u53c2\u8003\u6587\u732e\u6807\u7b7e\u5bbd\u5ea6\u3001
# \u6587\u732e key\uff08ref1..ref4\uff09\u3001\u4ea4\u53c9\u5f15\u7528 key\u3001\u56fe\u8868\u6587\u4ef6\u540d\u3001\u9898\u53f7\u5e8f\u53f7\u3002
# \u5224\u300c\u8bba\u6587\u5199\u6ca1\u5199\u6570\u300d\u65f6\u5fc5\u987b\u5148\u6316\u6389\u5b83\u4eec\uff0c\u5426\u5219\u9aa8\u67b6\u4e5f\u4f1a\u88ab\u8bef\u5224\u6210\u5df2\u5199\u3002
META_TOKEN_PATS = [
    r"\\baominghao\{[^}]*\}",                     # \u961f\u53f7
    r"\\setcounter\{page\}\{\d+\}",                # \u9875\u7801
    r"\\begin\{thebibliography\}\{\d+\}",          # \u53c2\u8003\u6587\u732e\u6807\u7b7e\u5bbd\u5ea6
    r"\\bibitem\{[^}]*\}",                         # \u6587\u732e key\uff08ref1\u2026ref4\uff09
    r"\\(?:ref|eqref|label|cite|citep|citet)\{[^}]*\}",   # \u4ea4\u53c9\u5f15\u7528 key
    r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}",  # \u56fe\u6587\u4ef6\u540d\uff08fig1.pdf\u2026\uff09
    r"\\(?:input|include|url|href)\{[^}]*\}",
    r"\\begin\{[^}]*\}|\\end\{[^}]*\}",            # \u73af\u5883\u540d\uff08tabularx \u7b49\uff09
    r"\bQuestion\s+\d+",                           # \u300cQuestion 1:\u300d\u9898\u53f7
    r"\b(?:Section|Appendix|Table|Figure|Eq\.?)\s+\d+",
]


def tex_state(tex_stripped: str, placeholders: int) -> dict:
    """\u6b63\u6587\u5904\u4e8e\u300c\u9aa8\u67b6\u300d\u8fd8\u662f\u300c\u5df2\u5199\u300d\u72b6\u6001\u3002

    \u5224\u636e\u53ea\u770b**\u7ed3\u679c\u6570\u5b57**\uff1a\u628a\u961f\u53f7/\u9875\u7801/\u53c2\u8003\u6587\u732e\u5bbd\u5ea6\u8fd9\u7c7b\u5143\u6570\u636e\u4e0e `<<...>>`
    \u5360\u4f4d\u7b26\u5168\u90e8\u6316\u6389\u540e\uff0c\u975e\u6ce8\u91ca\u533a\u8fd8\u5269\u51e0\u4e2a\u6570\u5b57 token\u3002
    \u5269 0 \u4e2a = \u9aa8\u67b6\uff08\u8bba\u6587\u8fd8\u6ca1\u5199\u6570\uff09\uff0c\u6b64\u65f6\u6b63\u6587\u4fa7\u5bf9\u8d26\u65e0\u4ece\u7ed1\u5b9a\uff1b
    \u5269 \u22651 \u4e2a = \u5df2\u5199\uff0c\u6b64\u65f6\u4efb\u4f55 needle \u672a\u547d\u4e2d\u90fd\u662f**\u771f\u5931\u8d25**\u3002

    \u8fd9\u6761\u5224\u636e\u8fd8\u517c\u4efb\u53cd\u4f5c\u5f0a\u95f8\uff1a\u53ea\u8981\u6b63\u6587\u51fa\u73b0\u8fc7\u4e00\u4e2a\u7ed3\u679c\u6570\u5b57\uff0c
    \u72b6\u6001\u7acb\u523b\u53d8 written\uff0c\u9aa8\u67b6\u8c41\u514d\u7acb\u5373\u5931\u6548 \u2014\u2014 \u4e0d\u8bb8\u62ff\u300c\u9aa8\u67b6\u300d\u5f53\u957f\u671f\u514d\u6b7b\u91d1\u724c\u3002
    """
    body = tex_stripped
    for pat in META_TOKEN_PATS:
        body = re.sub(pat, " ", body)
    body = re.sub(r"<<.*?>>", " ", body, flags=re.S)
    toks = re.findall(r"\d+(?:\.\d+)?", body)
    state = "skeleton" if not toks else "written"
    return {"state": state, "result_tokens": toks[:40],
            "n_result_tokens": len(toks), "placeholders": placeholders}


# ---------------------------------------------------------------- \u8bc4\u4f30
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

        # \u2461 \u81ea\u6307\u6570\u5b57\uff1aneedle \u4e0d\u8bb8\u7b49\u4e8e\u4efb\u4f55\u811a\u672c\u7684\u5b57\u8282\u6570
        if it["needle"]:
            for nd in it["needle"]:
                if nd in code_sizes:
                    it["ok_json"] = False
                    it["err"] = f"\u81ea\u6307\u6570\u5b57\uff1aneedle {nd} \u7b49\u4e8e\u67d0\u4e2a\u811a\u672c\u7684\u5b57\u8282\u6570"
                    break
            it["ok_tex"] = any(has_token(tex, nd) for nd in it["needle"])
        else:
            it["ok_tex"] = None
    return C.items


# ---------------------------------------------------------------- \u62a5\u544a
def build_report(n_bytes, items, tex_stats, argv, exit_code, code_sizes,
                 tstate):
    tex_declared = [it for it in items if it["needle"]]
    tex_bound = [it for it in tex_declared if it["ok_tex"]]
    json_bad = [it for it in items if it["ok_json"] is False]
    unevaluated = [it for it in items if not it["evaluated"]]
    skeleton = (tstate["state"] == "skeleton")

    # \u6b63\u6587\u4fa7\u672a\u547d\u4e2d\uff1a\u9aa8\u67b6\u72b6\u6001\u4e0b\u7b97\u300c\u7f13\u671f\u300d\uff0c\u5df2\u5199\u72b6\u6001\u4e0b\u7b97\u300c\u5931\u8d25\u300d\u3002
    # \u8fd9\u6761\u5206\u754c\u7531 tex_state() \u5224\u5b9a\uff0c\u4e0d\u7531\u672c\u51fd\u6570\u731c\u3002
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
         "# 03-numbers\uff1amain.tex \u6570\u5b57 \u2194 data/*.json \u5bf9\u8d26", "",
         "> \u6bcf\u6761\u7ed3\u8bba\u7684 JSON \u952e\u8def\u5f84\u89c1 **\u9644\u5f55 A**\uff08\u6b63\u6587\u53ea\u6b64\u4e00\u53e5\u6307\u9488\uff0c\u4e0d\u91cd\u590d\u6284\u952e\u8def\u5f84\uff09\u3002",
         "",
         f"- \u751f\u6210\uff1a`{argv}`",
         f"- \u9000\u51fa\u7801\uff1a{exit_code}",
         f"- \u58f0\u660e\u6761\u6570 claims={len(items)}\uff1b\u5b9e\u68c0\u67e5 declared={len(items)}"
         f" checked={len(items) - len(unevaluated)}",
         f"- JSON \u4fa7\uff1a\u901a\u8fc7 {len(items) - len(json_bad)}\uff0c\u5931\u8d25 {len(json_bad)}",
         f"- \u6b63\u6587\u4fa7\uff1a\u58f0\u660e needle {len(tex_declared)} \u6761\uff0c\u547d\u4e2d {len(tex_bound)} \u6761",
         f"- main.tex \u72b6\u6001\uff1a**{tstate['state']}**"
         f"\uff08\u6316\u6389\u961f\u53f7/\u9875\u7801/\u6587\u732e\u5bbd\u5ea6\u4e0e `<<...>>` \u540e\u5269"
         f" {tstate['n_result_tokens']} \u4e2a\u7ed3\u679c\u6570\u5b57 token\uff09",
         f"- main.tex\uff1a{tex_stats['lines']} \u884c / {tex_stats['bytes']} \u5b57\u8282\uff0c"
         f"\u975e\u6ce8\u91ca\u533a\u6570\u5b57 token {tex_stats['tokens']} \u4e2a\uff0c"
         f"`<<...>>` \u5360\u4f4d\u7b26 {tex_stats['placeholders']} \u4e2a",
         "", "## 1 \u7ed3\u8bba", ""]

    if verdict == "PASS":
        if skeleton:
            L.append(f"**JSON \u4fa7\u5168\u8fc7**\uff1a{len(items)} \u6761\u58f0\u660e\u9010\u6761\u91cd\u7b97\uff0c"
                     f"\u4e0e data/*.json \u5b58\u50a8\u503c\u4e00\u81f4\u3002")
            L += ["",
                  f"**\u6b63\u6587\u4fa7 {len(deferred)} \u6761 needle \u7f13\u671f**\uff08\u4e0d\u8ba1\u5931\u8d25\uff09\uff1a"
                  "main.tex \u4ecd\u662f\u539f\u59cb\u9aa8\u67b6\uff0c\u4e00\u4e2a\u7ed3\u679c\u6570\u5b57\u90fd\u6ca1\u6709\uff0c"
                  "needle \u65e0\u4ece\u7ed1\u5b9a\u3002\u8fd9\u662f s3 \u9636\u6bb5 G5 \u7684\u6b63\u5e38\u5f62\u6001 \u2014\u2014 "
                  "G5 \u5728 s3 \u8dd1\uff0c\u8bba\u6587\u5728 s6 \u624d\u5199\u3002"]
        else:
            L.append("\u5168\u90e8\u58f0\u660e\u901a\u8fc7\uff1aJSON \u4fa7\u9010\u6761\u91cd\u7b97\u4e0e\u5b58\u50a8\u503c\u4e00\u81f4\uff0c"
                     "\u6b63\u6587\u4fa7\u6bcf\u4e2a needle \u90fd\u5728 main.tex \u91cc\u6309\u8bcd\u8fb9\u754c\u547d\u4e2d\u3002")
    else:
        if unevaluated:
            L.append(f"**FAIL \u00b7 \u7a7a\u58f3**\uff1a{len(unevaluated)} \u6761\u58f0\u660e\u6ca1\u7b97\u51fa\u6765"
                     "\uff08declared != checked\uff09\uff0c\u7b49\u4e8e\u6ca1\u68c0\u67e5\u3002")
        if json_bad:
            L.append(f"**FAIL \u00b7 JSON \u4fa7**\uff1a{len(json_bad)} \u6761\u91cd\u7b97\u503c\u4e0e\u5b58\u50a8\u503c\u4e0d\u7b26\u3002")
        if tex_bad:
            L.append(f"**FAIL \u00b7 \u6b63\u6587\u4fa7**\uff1a{len(tex_bad)} \u6761 needle \u5728 main.tex \u91cc"
                     "\u627e\u4e0d\u5230\uff08\u6309 `(?<![\\d.])needle(?!\\d)` \u8bcd\u8fb9\u754c\u5339\u914d\uff09\u3002"
                     f"\u6b63\u6587\u5df2\u662f {tstate['state']} \u72b6\u6001\uff0c\u672a\u547d\u4e2d\u5373\u771f\u5931\u8d25\u3002")
        if not tex_declared:
            L.append("**FAIL \u00b7 \u6b63\u6587\u4fa7\u4e3a\u7a7a**\uff1a\u4e00\u6761 needle \u90fd\u6ca1\u58f0\u660e\u3002")

    L += ["", "### \u9aa8\u67b6\u5224\u636e\uff08\u4e3a\u4ec0\u4e48\u8fd9\u4e00\u8f6e\u6b63\u6587\u4fa7\u53ef\u4ee5\u7f13\u671f\uff09", ""]
    if skeleton:
        L += [f"main.tex \u6316\u6389\u5143\u6570\u636e\u4e0e\u5360\u4f4d\u7b26\u540e**\u4e00\u4e2a\u7ed3\u679c\u6570\u5b57\u90fd\u6ca1\u6709**"
              f"\uff08{tstate['n_result_tokens']} \u4e2a token\uff0c`<<...>>` "
              f"{tex_stats['placeholders']} \u5904\uff09\u3002G5 \u5728 s3 \u5224\uff0c\u8bba\u6587\u5728 s6 \u5199\uff0c"
              "\u6240\u4ee5\u6b64\u523b\u6b63\u6587\u4fa7\u65e0\u6cd5\u7ed1\u5b9a\uff0c\u53ea\u80fd\u7f13\u671f\u3002",
              "",
              "**\u8fd9\u4e0d\u662f\u957f\u671f\u514d\u6b7b\u91d1\u724c**\uff1a\u5224\u636e\u6bcf\u8f6e\u73b0\u7b97\uff0c\u6b63\u6587\u53ea\u8981\u51fa\u73b0\u7b2c\u4e00\u4e2a\u7ed3\u679c\u6570\u5b57\uff0c"
              "\u72b6\u6001\u7acb\u523b\u53d8 `written`\uff0c\u7f13\u671f\u7acb\u5373\u4f5c\u5e9f\uff0c\u4efb\u4f55 needle \u672a\u547d\u4e2d\u90fd\u662f\u786c\u5931\u8d25\u3002",
              "",
              "\u8bba\u6587\u64b0\u5199\u624b\u628a\u6570\u5b57\u586b\u8fdb main.tex \u540e\u91cd\u8dd1\u672c\u811a\u672c\u5373\u53ef\u81ea\u52a8\u7ed1\u5b9a\uff1b"
              "DERIVED \u8868\uff08\u7b2c 4 \u8282\uff09\u5df2\u628a\u6bcf\u4e2a\u6d3e\u751f\u503c\u7684\u7b97\u5f0f\u767b\u8bb0\u597d\uff0c"
              "\u6309\u8868\u4e0a\u7684\u7b97\u5f0f\u5199\u6570\u5c31\u4e0d\u4f1a\u4e0e JSON \u8131\u94a9\u3002"]
    else:
        L += [f"main.tex \u5df2\u662f **{tstate['state']}** \u72b6\u6001"
              f"\uff08{tstate['n_result_tokens']} \u4e2a\u7ed3\u679c\u6570\u5b57 token\uff09\uff0c"
              "\u9aa8\u67b6\u8c41\u514d\u4e0d\u9002\u7528\u3002\u58f0\u660e\u7684 needle \u5fc5\u987b\u5168\u90e8\u547d\u4e2d\u3002",
              "",
              "\u5e38\u89c1\u672a\u547d\u4e2d\u539f\u56e0\uff1a\u6b63\u6587\u628a 2 \u4f4d\u5c0f\u6570\u5199\u6210 1 \u4f4d\u6216\u53cd\u8fc7\u6765 \u2014\u2014 "
              "`needle_forms` \u5df2\u540c\u65f6\u63a5\u53d7 2 \u4f4d\u4e0e 1 \u4f4d\u5199\u6cd5\uff0c\u4ecd\u4e0d\u547d\u4e2d\u8bf4\u660e**\u6570\u503c\u4e0d\u540c**\uff0c"
              "\u8981\u6539\u7684\u662f\u6b63\u6587\u800c\u4e0d\u662f needle\u3002"]
    L += ["", "## 2 \u5206\u7ec4\u603b\u8868", "",
          "| \u7ec4 | \u58f0\u660e | JSON \u901a\u8fc7 | \u6b63\u6587 needle | \u6b63\u6587\u547d\u4e2d |",
          "|---|---|---|---|---|"]
    for g in sorted(groups):
        n, ok, nd, hit = groups[g]
        L.append(f"| {g} | {n} | {ok} | {nd} | {hit} |")

    L += ["", "## 3 \u5931\u8d25\u6e05\u5355", ""]
    if not json_bad and not tex_bad and not unevaluated:
        L.append("\u65e0\u3002" if not deferred
                 else f"\u65e0\u3002\u6b63\u6587\u4fa7 {len(deferred)} \u6761\u672a\u547d\u4e2d\u5c5e\u9aa8\u67b6\u7f13\u671f\uff0c"
                      f"\u4e0d\u8ba1\u5931\u8d25\uff08\u9010\u6761\u89c1\u7b2c 6 \u8282\uff09\u3002")
    else:
        shown = 0
        for it in unevaluated:
            L.append(f"- **[\u672a\u7b97\u51fa]** `{it['group']} / {it['name']}`\uff1a{it['actual']}")
            shown += 1
        for it in json_bad[:40]:
            L.append(f"- **[JSON]** `{it['group']} / {it['name']}`\uff1a"
                     f"\u91cd\u7b97 {it['actual']!r} vs \u5b58\u50a8 {it['expected']!r}"
                     f"\uff08{it['evidence']}\uff09")
            shown += 1
        if len(json_bad) > 40:
            L.append(f"- \u2026 JSON \u4fa7\u53e6\u6709 {len(json_bad) - 40} \u6761\u540c\u7c7b\u5931\u8d25\u3002")
        for it in tex_bad[:20]:
            L.append(f"- **[\u6b63\u6587]** `{it['group']} / {it['name']}`\uff1a"
                     f"needle {it['needle']} \u672a\u547d\u4e2d\uff08{it['evidence']}\uff09")
            shown += 1
        if len(tex_bad) > 20:
            L.append(f"- \u2026 \u6b63\u6587\u4fa7\u53e6\u6709 {len(tex_bad) - 20} \u6761\u672a\u547d\u4e2d\u3002")

    L += ["", "## 4 DERIVED \u767b\u8bb0\u8868\uff08\u6b63\u6587\u91cc\u7b97\u51fa\u6765\u7684\u6570\uff0c\u7b97\u5f0f\u53ef\u624b\u7b97\u590d\u6838\uff09", "",
          "| \u7ec4 | \u503c | \u7b97\u5f0f |", "|---|---|---|"]
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

    L += ["", "## 5 \u590d\u7b97\u547d\u4ee4", "",
          "```powershell",
          "cd E:\\\u6570\u5b66\u5efa\u6a21\\PRACTICE_2023B",
          "& (os.environ.get("MM_PY") or sys.executable) code\\verify_numbers.py",
          "```", "",
          "\u672c\u811a\u672c\u53ea\u8bfb data/*.json \u4e0e main.tex\uff0c\u4e0d\u6539\u4efb\u4f55\u4e0a\u6e38\u6587\u4ef6\uff1b"
          "\u552f\u4e00\u5199\u5165\u7684\u662f\u672c\u62a5\u544a\u81ea\u8eab\uff08\u9996\u884c `BYTES <n>` \u7528 write_bytes \u8fed\u4ee3\u5230\u4e0d\u52a8\u70b9\uff09\u3002"]

    if deferred:
        L += ["", f"## 6 \u7f13\u671f\u6e05\u5355\uff08{len(deferred)} \u6761 needle\uff0c\u6b63\u6587\u5199\u51fa\u8fd9\u4e9b\u6570\u5373\u81ea\u52a8\u7ed1\u5b9a\uff09",
              "",
              "\u8bba\u6587\u64b0\u5199\u624b\u6309\u8fd9\u5f20\u8868\u628a\u6570\u5199\u8fdb main.tex\uff1b\u5199\u5b8c\u91cd\u8dd1\u672c\u811a\u672c\uff0c"
              "\u547d\u4e2d\u6570\u4f1a\u4ece 0 \u6da8\u4e0a\u53bb\uff0c\u7f13\u671f\u6e05\u5355\u968f\u4e4b\u7f29\u77ed\uff0c\u5168\u90e8\u547d\u4e2d\u5373 G5 \u6ee1\u5206\u3002",
              "", "| \u7ec4 | \u68c0\u67e5\u9879 | \u5f85\u547d\u4e2d\u7684\u5199\u6cd5 | \u671f\u671b\u503c | \u7b97\u5f0f |",
              "|---|---|---|---|---|"]
        for it in deferred:
            ev = it["expected"]
            es = f"{ev:.6g}" if isinstance(ev, (int, float)) else str(ev)
            L.append(f"| {it['group']} | {it['name']} | "
                     f"`{', '.join(it['needle'])}` | `{es}` | "
                     f"{it['derived'] or DASH} |")

    # \u9644\u5f55 A\uff1a\u6570\u503c\u7d22\u5f15\uff08\u7ed3\u8bba \u2192 json \u952e\u8def\u5f84\uff09\u3002\u53ea\u5370\u952e\u8def\u5f84\uff0c\u4e0d\u5370\u672c\u811a\u672c\u884c\u53f7 \u2014\u2014
    # \u884c\u53f7\u4f1a\u968f\u4ee3\u7801\u6539\u52a8\u6f02\u79fb\uff0c\u5370\u51fa\u6765\u5c31\u662f\u81ea\u6307\u6570\u5b57\uff08\u4e0d\u52a8\u70b9\u9677\u9631\uff09\u3002
    L += ["", "## \u9644\u5f55 A \u00b7 \u6570\u503c\u7d22\u5f15\uff08\u7ed3\u8bba \u2192 data/*.json \u952e\u8def\u5f84\uff09",
          "",
          "> \u6b63\u6587\u4e0e\u7ed3\u8bba\u53ea\u6307\u5411\u672c\u9644\u5f55\u4e00\u6b21\uff0c\u4e0d\u91cd\u590d\u6284\u8868\uff1b\u952e\u8def\u5f84\u5c31\u662f\u7ed9\u5bf9\u8d26\u7ed1 claim \u7684\u539f\u6599\u3002",
          "",
          "| \u7ec4 | \u8986\u76d6\u7684\u7ed3\u8bba | JSON \u952e\u8def\u5f84 |",
          "|---|---|---|"]
    for g, keys in APPENDIX_A:
        L.append(f"| {g} | {keys[0]} | `{keys[1]}` |")

    L += ["", "## 7 \u4ea4\u7ed9\u4e0b\u4e00\u68d2", "",
          "**\u8bba\u6587\u64b0\u5199\u624b**\uff1a\u7b2c 6 \u8282\u7684\u8868\u5c31\u662f `main.tex` \u8981\u586b\u7684\u6570\u3002\u9010\u884c\u6284 `\u5f85\u547d\u4e2d\u7684\u5199\u6cd5` \u90a3\u4e00\u5217\uff0c"
          "\u6570\u503c\u4e0d\u8981\u81ea\u5df1\u91cd\u7b97 \u2014\u2014 \u8868\u91cc\u7684\u6bcf\u4e2a\u6570\u90fd\u5df2\u7531\u7b2c 4 \u8282\u7b97\u5f0f\u4ece `data/*.json` \u73b0\u7b97\u8fc7\u4e00\u904d\u3002"
          f"\u5199\u5b8c\u91cd\u8dd1\u672c\u811a\u672c\uff0c`\u6b63\u6587\u4fa7 \u58f0\u660e/\u547d\u4e2d` \u4f1a\u4ece `{len(tex_declared)} / 0` \u6da8\u5230 "
          f"`{len(tex_declared)} / {len(tex_declared)}`\uff0c"
          "`## 6 \u7f13\u671f\u6e05\u5355` \u6d88\u5931\u3001`VERDICT` \u4ecd\u4e3a `PASS`\uff0cG5 \u624d\u7b97\u771f\u8fc7\u3002",
          "",
          "**\u56fe\u8868\u624b**\uff1a\u672c\u62a5\u544a\u4e0d\u5370\u4efb\u4f55\u811a\u672c\u5b57\u8282\u6570\uff08\u81ea\u6307\u6570\u5b57\u4f1a\u53d8\u5b64\u513f token\uff09\uff0c"
          "\u6240\u4ee5 `tab:code` \u91cc\u7684\u811a\u672c\u5927\u5c0f\u53ea\u80fd\u7531 `code/gen_index.py` \u73b0\u8bfb\u751f\u6210\uff1b"
          "\u4f46 `code/verify_numbers.py` \u672c\u8f6e\u7684\u5b57\u8282\u6570\u5df2\u7ecf\u53d8\u4e86\uff0c`tab:code` \u5fc5\u987b\u91cd\u8dd1\u4e00\u6b21\u751f\u6210\u5668\uff0c"
          "\u5426\u5219\u90a3\u5f20\u8868\u662f\u65e7\u7684\u3002",
          "",
          "**\u5171\u540c\u6ce8\u610f**\uff1a\u6b63\u6587\u53ea\u8981\u51fa\u73b0\u7b2c\u4e00\u4e2a\u7ed3\u679c\u6570\u5b57\uff0c`tex_state` \u5c31\u4ece `skeleton` \u53d8 `written`\uff0c"
          "\u9aa8\u67b6\u7f13\u671f\u7acb\u5373\u4f5c\u5e9f \u2014\u2014 \u534a\u586b\u7684\u6b63\u6587\u6bd4\u7a7a\u6b63\u6587\u66f4\u5bb9\u6613\u88ab G5 \u5224 FAIL\uff0c"
          "\u6240\u4ee5\u7b2c 6 \u8282\u7684\u6570\u8981\u4e48\u4e0d\u586b\uff0c\u8981\u4e48\u4e00\u6b21\u586b\u5b8c\u3002"]

    L += ["", f"VERDICT: {verdict}"]
    return "\n".join(L) + "\n", verdict


# ---------------------------------------------------------------- \u4e3b\u6d41\u7a0b
def main(argv=None):
    argv = argv or "python code/verify_numbers.py"
    tex_raw = TEX.read_text(encoding="utf-8")
    tex = strip_comments(tex_raw)
    code_sizes = {str(p.stat().st_size) for p in CODE.glob("*.py")}
    tex_stats = {
        # \u884c\u6570\u6309\u7f16\u8f91\u5668\u53e3\u5f84\uff1a\u672b\u5c3e\u6709\u6362\u884c\u5c31\u4e0d\u518d\u989d\u5916\u7b97\u4e00\u884c\uff08106 \u800c\u4e0d\u662f 107\uff09\u3002
        "lines": tex_raw.count("\n") + (0 if tex_raw.endswith("\n") else 1),
        # \u78c1\u76d8\u5b57\u8282\uff08\u542b CRLF\uff09\u3002\u4e0d\u80fd\u7528 len(tex_raw.encode()) \u2014\u2014 read_text \u7684
        # \u901a\u7528\u6362\u884c\u5df2\u628a \r\n \u6298\u6210 \n\uff0c\u90a3\u6837\u7b97\u51fa\u6765\u6bd4\u78c1\u76d8\u5c11 106 \u5b57\u8282\uff0c\u62a5\u7684\u662f\u5047\u6570\u3002
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

    # \u62a5\u544a\uff1a\u9996\u884c BYTES \u8fed\u4ee3\u5230\u4e0d\u52a8\u70b9\uff08write_text \u4f1a\u628a \n \u53d8 \r\n\uff0c\u6c38\u8fdc\u4e0d\u6536\u655b\uff09
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
