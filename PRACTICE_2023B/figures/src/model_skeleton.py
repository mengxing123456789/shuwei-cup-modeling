#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PRACTICE_2023B \u00b7 s2 \u6a21\u578b\u9aa8\u67b6\uff1a\u5e38\u91cf\u3001\u7b26\u53f7\u3001\u6570\u636e\u5951\u7ea6\uff08\u552f\u4e00\u6743\u5a01\u6e90\uff09\u3002

\u56db\u6761\u7eaa\u5f8b\uff08\u5bf9\u5e94\u6d3e\u5355\u300c\u56db\u6761\u786c\u7ecf\u9a8c\u300d\uff09
--------------------------------
\u2460 \u4e00\u4e2a\u6570\u5b57\u53ea\u5c5e\u4e8e\u4e00\u4e2a\u8bfb\u6cd5\u3002\u672c\u9898\u6709\u4e09\u4e2a**\u5916\u5f62\u76f8\u4f3c\u3001\u542b\u4e49\u4e0d\u540c**\u7684\u5750\u6807\uff0c\u7edd\u4e0d\u8bb8\u4e92\u6362\uff1a
     r  = \u63ba\u6bd4\u8bfb\u6570 a/100          \uff08\u9898\u9762\u5199\u6cd5 10/100 \u2026 100/100\uff0c\u65e0\u91cf\u7eb2\uff0c0.1\u20131.0\uff09
     w  = DFA \u8d28\u91cf\u5206\u6570 a/(a+100)  \uff080\u20130.5\uff1b100/100 \u2192 w=0.5\uff0c\u4e0d\u662f 1.0\uff09
     \u03c6  = \u6c14\u4f53\u4f53\u79ef\u5206\u6570 z_g/\u03a3z_g   \uff08\u5206\u6bcd\u662f\u8be5\u884c\u6c14\u4f53\u4e4b\u548c\uff0c\u4e0d\u662f 100\uff09
   \u4ee5\u53ca\u4e24\u6761**\u9608\u503c\u8def\u5f84**\uff1a\u03c4_single=0.10\u00b7y\uff08\u5355\u6d4b\u91cf vs \u5df2\u77e5\u771f\u503c\uff09\u3001
   \u03c4_diff=0.10\u00b7\u221a(y_a\u00b2+y_b\u00b2)\uff08\u4e24\u4e2a\u72ec\u7acb\u6d4b\u91cf\u7684\u5dee\uff09\u3002\u51e1\u5199\u300c\u663e\u8457\u300d\u5fc5\u987b\u6807\u8def\u5f84\u3002
\u2461 \u672c\u6587\u4ef6\u4e0d\u5199\u4efb\u4f55\u300c\u672c\u6587 X \u4e2a\u300d\u300c\u811a\u672c Y \u5b57\u8282\u300d\u5f0f\u81ea\u6307\u6570\u5b57\uff1b\u5b57\u8282\u6570\u7531 code/gen_index.py \u73b0\u8bfb\u3002
\u2462 \u6570\u636e\u5951\u7ea6\uff08CONTRACT\uff09\u53ea\u5728\u8fd9\u91cc\u5b9a\u4e49\u4e00\u6b21\u3002solve.py \u4e0e make_figures.py \u4e00\u5f8b import\uff0c
   \u4e0d\u8bb8\u5404\u81ea\u786c\u7f16\u7801 \u2014\u2014 \u6539\u4e00\u5904\u4e0d\u6539\u4e09\u5904\uff0c\u56fe\u91cc\u67f1\u5b50\u4f1a\u5168\u53d8 0\uff08\u786c\u7ecf\u9a8c\u2462\uff09\u3002
\u2463 \u5e38\u6570\u4e09\u5206\u7c7b\uff1aGIVEN \u9898\u7ed9 / ASSUMED \u81ea\u8bbe / DERIVED \u4e2d\u95f4\u91cf\u3002\u9898\u9762\u6ca1\u6709\u7684\u4e00\u5f8b ASSUMED\uff0c
   \u952e\u540d\u540e\u7f00 `_ASSUMED`\uff0c\u503c\u65c1\u6ce8\u300c\u81ea\u8bbe\u300d\u3002\u6d3e\u751f\u7684\u91cf\u7531 derive() \u73b0\u7b97\uff0c\u4e0d\u5199\u6b7b\u3002

\u6570\u636e\u89e3\u6790\u4e0d\u91cd\u5199\uff1a\u76f4\u63a5\u590d\u7528 code/fetch_annex.py \u7684 read_sheet / parse_annex_*\uff0c
\u4fdd\u8bc1\u4e0e data/ledger.json \u662f\u540c\u4e00\u4efd\u89e3\u6790\uff08\u6539\u89e3\u6790\u53ea\u6539\u4e00\u5904\uff09\u3002
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CODE = Path(__file__).resolve().parent
DATA = ROOT / "data"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import fetch_annex as FA  # noqa: E402

GIVEN = "\u9898\u7ed9"
ASSUMED = "\u81ea\u8bbe"
DERIVED = "\u4e2d\u95f4\u91cf"

# ---------------------------------------------------------------- \u6570\u636e\u5951\u7ea6\uff08\u552f\u4e00\u5b9a\u4e49\u5904\uff09
CONTRACT = {
    "products": ["Tar", "Water", "Char", "Syngas"],
    "combos": ["DFA/CS", "DFA/CE", "DFA/LG"],
    "combo_short": {"DFA/CS": "CS", "DFA/CE": "CE", "DFA/LG": "LG"},
    "gases": {
        "DFA/CS": ["H2", "CO", "CO2", "CH4", "C2H6", "C3H8", "C3H6", "C2H4", "C4H10"],
        "DFA/CE": ["H2", "CO", "CO2", "CH4", "C2H6"],
        "DFA/LG": ["H2", "CO", "CO2", "CH4", "C2H6"],
    },
    # \u56fe\u65cf\u987a\u5e8f\u4e0e\u914d\u8272\uff1amake_figures.py \u7684 FUNC_ORDER / FUNC_COLORS \u5fc5\u987b\u7b49\u4e8e\u8fd9\u4e24\u9879
    "figure_order": ["Tar", "Water", "Char", "Syngas"],
    "figure_colors": {"Tar": "#1f4e79", "Water": "#2e75b6",
                      "Char": "#7f7f7f", "Syngas": "#c55a11"},
    "gas_colors": {"H2": "#1f4e79", "CO": "#c55a11", "CO2": "#548235",
                   "CH4": "#7f6000", "C2H6": "#7030a0"},
    # \u91cf\u7ea7\u5206\u5c42\uff08Q2 \u5206\u680f\u4f9d\u636e\uff09\uff1a\u4e3b\u91cf\u7ea7 span \u2265 5 mL/g(daf)\uff0c\u6b21\u91cf\u7ea7 < 5
    "tier_major": ["H2", "CO", "CO2", "CH4", "C2H6"],
}

# \u6469\u5c14\u8d28\u91cf g/mol\uff08\u6587\u732e\u5e38\u6570\uff0c\u81ea\u8bbe\uff1a\u9898\u9762\u672a\u7ed9\uff09
MOLAR_MASS = {"H2": 2.016, "CO": 28.010, "CO2": 44.009, "CH4": 16.043,
              "C2H6": 30.070, "C3H8": 44.097, "C3H6": 42.081,
              "C2H4": 28.054, "C4H10": 58.124}


class MS:
    """\u6a21\u578b\u9aa8\u67b6\u5e38\u91cf\u3002`MS.PARAMS` \u662f\u5168\u6587\u5e38\u91cf\u7684**\u552f\u4e00\u6743\u5a01**\uff08G1/G2 \u56de\u67e5\u6b64\u5904\uff09\u3002"""

    # ------------------------------------------------------------ \u9898\u7ed9\u5757\uff08C01\u2013C23\uff09
    PARAMS = {
        # --- \u63ba\u6bd4\u516b\u6863\uff08L74\u2013L75\uff09\u3002value \u5b58 r=a/100\uff1blabel \u5b58\u9898\u9762\u5199\u6cd5
        "r_1": dict(id="C01", sym="r_1", value=0.10, label="10/100",
                    unit="kg/kg (DFA:biomass)", kind=GIVEN, src="problem.txt L74"),
        "r_2": dict(id="C02", sym="r_2", value=0.20, label="20/100",
                    unit="kg/kg", kind=GIVEN, src="problem.txt L74"),
        "r_3": dict(id="C03", sym="r_3", value=0.30, label="30/100",
                    unit="kg/kg", kind=GIVEN, src="problem.txt L75"),
        "r_4": dict(id="C04", sym="r_4", value=0.40, label="40/100",
                    unit="kg/kg", kind=GIVEN, src="problem.txt L75"),
        "r_5": dict(id="C05", sym="r_5", value=0.50, label="50/100",
                    unit="kg/kg", kind=GIVEN, src="problem.txt L75"),
        "r_6": dict(id="C06", sym="r_6", value=0.60, label="60/100",
                    unit="kg/kg", kind=GIVEN, src="problem.txt L75"),
        "r_7": dict(id="C07", sym="r_7", value=0.80, label="80/100",
                    unit="kg/kg", kind=GIVEN, src="problem.txt L75"),
        "r_8": dict(id="C08", sym="r_8", value=1.00, label="100/100",
                    unit="kg/kg", kind=GIVEN, src="problem.txt L75"),
        # --- \u53cd\u4f8b\u6863\uff1a\u9898\u9762\u70b9\u540d\u4f46\u672a\u91c7\u7528\uff0c\u4e0d\u5f97\u5f53\u5b9e\u9a8c\u70b9
        "r_neg1": dict(id="C09", sym="r_neg1", value=0.05, label="5/100",
                       unit="kg/kg", kind=GIVEN, src="problem.txt L78",
                       note="\u53cd\u4f8b\uff0c\u672a\u91c7\u7528\uff1b\u4e0d\u5f97\u4f5c\u5b9e\u9a8c\u70b9"),
        "r_neg2": dict(id="C10", sym="r_neg2", value=0.07, label="7/100",
                       unit="kg/kg", kind=GIVEN, src="problem.txt L78",
                       note="\u53cd\u4f8b\uff0c\u672a\u91c7\u7528"),
        # --- \u566a\u58f0\u5730\u677f\uff08L77\uff09\uff1a\u5224\u636e\u7684\u4e0d\u7b49\u5f0f\u53f3\u7aef\uff0c\u4e0d\u662f\u6a21\u578b\u7cbe\u5ea6\u76ee\u6807
        "eps_rel": dict(id="C11", sym="eps_rel", value=0.05, unit="1 (\u76f8\u5bf9)",
                        kind=GIVEN, src="problem.txt L77",
                        note="\u5e73\u884c\u5b9e\u9a8c\u76f8\u5bf9\u8bef\u5dee \u22485%\uff1b\u662f\u6570\u636e\u4e0d\u786e\u5b9a\u5ea6\uff0c\u4e0d\u662f\u672c\u6587\u6a21\u578b\u7684\u7cbe\u5ea6\u6307\u6807"),
        "n_comb": dict(id="C14", sym="N_comb", value=3, unit="\u4e2a",
                       kind=GIVEN, src="problem.txt L131-L137"),
        "n_prod": dict(id="C15", sym="N_prod", value=4, unit="\u79cd",
                       kind=GIVEN, src="problem.txt L138"),
        "n_gas_cs": dict(id="C16", sym="N_gas_CS", value=9, unit="\u79cd",
                         kind=GIVEN, src="problem.txt L139-L140"),
        "n_gas_ce": dict(id="C17", sym="N_gas_CE", value=5, unit="\u79cd",
                         kind=GIVEN, src="problem.txt L141-L142"),
        "n_gas_lg": dict(id="C18", sym="N_gas_LG", value=5, unit="\u79cd",
                         kind=GIVEN, src="problem.txt L143-L144"),
        "n_q": dict(id="C19", sym="N_Q", value=5, unit="\u95ee",
                    kind=GIVEN, src="problem.txt L90-L111"),
        "t_const": dict(id="C23", sym="T_const", value=None, unit="K",
                        kind=GIVEN, src="problem.txt L145-L146",
                        note="\u9898\u9762\u53ea\u58f0\u660e\u300c\u540c\u4e00\u6e29\u5ea6\u300d\uff0c\u672a\u7ed9\u6570\u503c \u2014\u2014 \u6570\u503c\u4e0d\u5f97\u5f53\u9898\u7ed9"),
        # --- \u81ea\u8bbe\u5757\uff08T1\u2013T12\uff09\uff1a\u9898\u9762\u6ca1\u6709\uff0c\u5168\u90e8\u540e\u7f00 _ASSUMED
        "T_py_ASSUMED": dict(id="T1", sym="T_py", value=800.0, unit="K", kind=ASSUMED,
                             note="\u81ea\u8bbe\uff1a\u9898\u9762\u53ea\u8bf4\u540c\u4e00\u6e29\u5ea6\uff0c\u672a\u7ed9\u6570\u503c"),
        "beta_heat_ASSUMED": dict(id="T2", sym="beta_heat", value=10.0, unit="K/min",
                                  kind=ASSUMED, note="\u81ea\u8bbe\uff1a\u5347\u6e29\u901f\u7387\u9898\u9762\u672a\u63d0"),
        "t_hold_ASSUMED": dict(id="T3", sym="t_hold", value=30.0, unit="min",
                               kind=ASSUMED, note="\u81ea\u8bbe\uff1a\u505c\u7559\u65f6\u95f4\u672a\u7ed9"),
        "Q_carrier_ASSUMED": dict(id="T4", sym="Q_carrier", value=100.0, unit="mL/min",
                                  kind=ASSUMED, note="\u81ea\u8bbe\uff1a\u8f7d\u6c14\u6d41\u901f\u672a\u7ed9"),
        "d_p_ASSUMED": dict(id="T5", sym="d_p", value=0.2, unit="mm",
                            kind=ASSUMED, note="\u81ea\u8bbe\uff1a\u7c92\u5f84\u672a\u7ed9"),
        "m_sample_ASSUMED": dict(id="T6", sym="m_sample", value=5.0, unit="g",
                                 kind=ASSUMED, note="\u81ea\u8bbe\uff1a\u5355\u6b21\u8fdb\u6837\u91cf\u672a\u7ed9"),
        "A_pre_ASSUMED": dict(id="T7", sym="A_pre", value=None, unit="s^-1", kind=ASSUMED,
                              note="\u81ea\u8bbe\uff1a\u5f85\u8fa8\u8bc6\uff0c\u4e0d\u5f97\u5355\u72ec\u56fa\u5b9a\uff1b\u4e0e Ea \u8054\u5408\u6210\u810a"),
        "Ea_ASSUMED_RANGE": dict(id="T8", sym="Ea", value=[100.0, 250.0], unit="kJ/mol",
                                 kind=ASSUMED, note="\u81ea\u8bbe\uff1a\u5148\u9a8c\u533a\u95f4\uff0c\u4e0d\u662f\u62df\u5408\u503c"),
        "n_order_ASSUMED": dict(id="T9", sym="n_order", value=1.0, unit="1",
                                kind=ASSUMED, note="\u81ea\u8bbe\uff1a\u53cd\u5e94\u7ea7\u6570\u5148\u9a8c\uff1b\u987b\u7ed9 0/1/2 \u4e09\u6863\u5bf9\u6bd4"),
        "f_alpha_ASSUMED": dict(id="T10", sym="f_alpha", value=["R2", "R3", "D1"],
                                unit="1", kind=ASSUMED,
                                note="\u81ea\u8bbe\uff1a\u673a\u7406\u51fd\u6570\u4e09\u6863\u5bf9\u6bd4\uff0c\u4e0d\u8bb8\u53ea\u62a5\u4e00\u6863"),
        "dfa_comp_ASSUMED": dict(id="T11", sym="dfa_comp",
                                 value={"CaO": 0.40, "CaSO4": 0.30, "SiO2": 0.15, "other": 0.15},
                                 unit="wt.%", kind=ASSUMED,
                                 note="\u81ea\u8bbe/\u6587\u732e\u5178\u578b\u503c\uff1a\u9898\u9762\u4e0e\u9644\u4ef6\u5747\u672a\u7ed9\u8131\u786b\u7070\u7ec4\u6210"),
        "grid_pred_ASSUMED": dict(id="T12", sym="grid_pred",
                                  value=[0.15, 0.25, 0.35, 0.45, 0.55, 0.70, 0.90],
                                  unit="1 (r)", kind=ASSUMED,
                                  note="\u81ea\u8bbe\uff1aQ5 \u9884\u6d4b\u7f51\u683c\uff1b\u5168\u90e8\u843d\u5728\u89c2\u6d4b\u533a\u95f4\u5185 = \u5185\u63d2\uff0c\u4e0d\u662f\u5916\u63a8"),
        # --- \u6865\u63a5\u7528\u81ea\u8bbe\u5e38\u6570\uff08Annex II \u4f53\u79ef \u2192 \u8d28\u91cf\uff09
        "V_m_ASSUMED": dict(id="T13", sym="V_m", value=22.414, unit="L/mol", kind=ASSUMED,
                            note="\u81ea\u8bbe\uff1aSTP(273.15 K, 101.325 kPa) \u7406\u60f3\u6c14\u4f53\u6469\u5c14\u4f53\u79ef"),
        "R_gas": dict(id="T14", sym="R_gas", value=8.314, unit="J/(mol\u00b7K)", kind=GIVEN,
                      src="\u7269\u7406\u5e38\u6570\uff08\u975e\u9898\u9762\u6570\u636e\uff09", note="\u6587\u732e\u5e38\u6570"),
    }

    # ------------------------------------------------------------ \u6d3e\u751f\u5757\uff08\u73b0\u7b97\uff09
    DERIVED: dict = {}

    @classmethod
    def p(cls, key: str) -> dict:
        return cls.PARAMS[key]

    @classmethod
    def v(cls, key: str) -> float:
        return cls.PARAMS[key]["value"]


# ---------------------------------------------------------------- \u5750\u6807\u6362\u7b97
def w_of_r(r):
    """\u63ba\u6bd4\u8bfb\u6570 r=a/100 \u2192 DFA \u8d28\u91cf\u5206\u6570 w=a/(a+100)=r/(1+r)\u3002"""
    r = np.asarray(r, dtype=float)
    return r / (1.0 + r)


def r_of_w(w):
    w = np.asarray(w, dtype=float)
    return w / (1.0 - w)


def ratio_value(label: str) -> float:
    """'20/100' \u2192 0.20\u3002"""
    a, b = label.split("/")
    return float(a) / float(b)


# ---------------------------------------------------------------- \u9644\u4ef6\u8bfb\u53d6\uff08\u590d\u7528 fetch_annex\uff09
def _pivot(which: str) -> dict:
    path = DATA / (FA.ANNEX_I if which == "I" else FA.ANNEX_II)
    recs = FA.parse_annex_i(path) if which == "I" else FA.parse_annex_ii(path)
    raw: dict = {}
    for rec in recs:
        combo = rec["combo"]
        ind = rec["indicator"]
        if which == "I":
            ind = ind.replace(" yield", "")
        raw.setdefault(combo, {}).setdefault(ind, {})[rec["ratio"]] = rec["value"]
    out = {}
    for combo, series in raw.items():
        labels = sorted({k for s in series.values() for k in s}, key=ratio_value)
        out[combo] = {
            "labels": labels,
            "r": np.array([ratio_value(x) for x in labels]),
            "w": w_of_r([ratio_value(x) for x in labels]),
            "series": {ind: np.array([s[x] for x in labels]) for ind, s in series.items()},
        }
    return out


def load_annex_i() -> dict:
    """{combo: {labels, r, w, series{product: array}}}\uff0c\u4ea7\u7269\u540d\u5df2\u53bb\u6389 ' yield'\u3002"""
    return _pivot("I")


def load_annex_ii() -> dict:
    """{combo: {labels, r, w, series{gas: array}}}\u3002"""
    return _pivot("II")


def formula_cells(which: str):
    """\u8fd4\u56de [(cell, formula)]\uff1a\u9644\u4ef6\u91cc\u88ab Excel \u516c\u5f0f\u63a8\u51fa\u7684\u5355\u5143\u683c\u3002

    \u8fd9\u662f\u672c\u9898\u6700\u786c\u7684\u4e00\u6761\u5efa\u6a21\u7ea6\u675f\uff1a\u6bcf\u5f20\u8868**\u53ea\u6709\u4e00\u4e2a\u4ea7\u7269\u662f\u516c\u5f0f\u63a8\u51fa\u6765\u7684**
    \uff08CS\u2192Syngas\u3001CE\u2192Char\u3001LG\u2192Tar\uff09\uff0c\u56db\u4ea7\u7269\u53ea\u6709\u4e09\u81ea\u7531\u5ea6\u3002
    """
    try:
        import openpyxl
    except ImportError:  # \u65e0 openpyxl \u65f6\u8fd4\u56de None\uff0c\u8c03\u7528\u65b9\u987b\u81ea\u884c\u964d\u7ea7
        return None
    path = DATA / (FA.ANNEX_I if which == "I" else FA.ANNEX_II)
    wb = openpyxl.load_workbook(path, data_only=False)
    ws = wb[wb.sheetnames[0]]
    hits = []
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                hits.append((cell.coordinate, cell.value))
    return hits


# ---------------------------------------------------------------- \u81ea\u68c0\uff08solve.py \u542f\u52a8\u65f6\u8c03\u7528\uff09
def selftest(verbose: bool = True) -> dict:
    """\u4e09\u6761\u7ed3\u6784\u65ad\u8a00\uff1a\u95ed\u5408\u6027\u3001\u516c\u5f0f\u6d3e\u751f\u5217\u3001\u4e24\u9644\u4ef6\u7f51\u683c\u5d4c\u5957\u3002\u5931\u8d25\u76f4\u63a5\u629b\u3002"""
    ai = load_annex_i()
    aii = load_annex_ii()
    prod = CONTRACT["products"]

    # 1) Annex I \u95ed\u5408\uff1a\u03a3_p y_p = 100\uff08\u9010\u5217\uff09
    sums = []
    for combo, d in ai.items():
        M = np.column_stack([d["series"][p] for p in prod])
        sums.extend(M.sum(axis=1).tolist())
    max_dev = float(np.max(np.abs(np.array(sums) - 100.0)))

    # 2) \u516c\u5f0f\u6d3e\u751f\u5217
    fc = formula_cells("I")
    n_formula = None if fc is None else len(fc)
    derived_col = {}
    if fc is not None:
        # \u516c\u5f0f\u6240\u5728\u884c \u2192 \u4ea7\u7269\u540d\uff1b\u53cd\u67e5\u6bcf\u8868\u88ab\u63a8\u51fa\u7684\u662f\u54ea\u4e2a\u4ea7\u7269
        grid = FA.read_sheet(DATA / FA.ANNEX_I)
        row2prod = {}
        for r, cells in grid.items():
            a = cells.get(0)
            if isinstance(a, str) and a.endswith("yield"):
                row2prod[r] = a.replace(" yield", "")
        for coord, _f in fc:
            row = int("".join(ch for ch in coord if ch.isdigit()))
            if row in row2prod:
                derived_col[row2prod[row]] = derived_col.get(row2prod[row], 0) + 1

    # 3) \u7f51\u683c\u5d4c\u5957\uff1aAnnex II \u7684\u6863\u4f4d\u5fc5\u987b \u2286 \u540c\u7ec4\u5408 Annex I \u7684\u6863\u4f4d
    nested = {}
    for combo in CONTRACT["combos"]:
        nested[combo] = set(aii[combo]["labels"]) <= set(ai[combo]["labels"])

    out = dict(max_abs_sum_minus_100=max_dev,
               n_formula_cells=n_formula,
               formula_rows=derived_col,
               nested=nested,
               n_cols_annex_i=int(sum(len(d["labels"]) for d in ai.values())),
               n_cols_annex_ii=int(sum(len(d["labels"]) for d in aii.values())))
    assert max_dev < 1e-6, f"Annex I \u4e0d\u95ed\u5408\uff0c\u6700\u5927\u504f\u5dee {max_dev}"
    assert all(nested.values()), f"\u7f51\u683c\u4e0d\u5d4c\u5957\uff1a{nested}"
    if n_formula is not None:
        # \u6bcf\u5f20\u5b50\u8868\u6709**\u4e00\u6574\u884c**\u662f\u516c\u5f0f\uff1a8 \u5217 \u00d7 3 \u8868 = 24 \u4e2a\u5355\u5143\u683c\uff0c\u6bcf\u8868\u5404\u63a8\u51fa**\u4e0d\u540c**\u4ea7\u7269
        assert n_formula == 24, f"\u516c\u5f0f\u6d3e\u751f\u5355\u5143\u683c\u5e94\u4e3a 24 \u4e2a\uff0c\u5b9e\u6d4b {n_formula}"
        assert derived_col == {"Syngas": 8, "Char": 8, "Tar": 8}, \
            f"\u6bcf\u8868\u88ab\u63a8\u51fa\u7684\u4ea7\u7269\u5e94\u4e3a Syngas/Char/Tar \u5404 8 \u5217\uff0c\u5b9e\u6d4b {derived_col}"
    MS.DERIVED.update(out)
    if verbose:
        print(f"[selftest] Annex I \u95ed\u5408 max|\u03a3-100| = {max_dev:.2e} "
              f"\uff08{out['n_cols_annex_i']} \u5217\uff09")
        print(f"[selftest] \u516c\u5f0f\u6d3e\u751f\u5355\u5143\u683c {n_formula} \u4e2a\uff0c\u884c\u5206\u5e03 {derived_col}")
        print(f"[selftest] \u7f51\u683c\u5d4c\u5957 {nested}\uff1bAnnex II {out['n_cols_annex_ii']} \u5217")
    return out


# ---------------------------------------------------------------- \u7b26\u53f7\u8868\uff08\u9644\u5f55 A \u7528\uff09
SYMBOLS = [
    # (\u7b26\u53f7, \u542b\u4e49, \u5355\u4f4d, \u7c7b\u522b, \u91cf\u7ea7, \u7528\u5728)
    # \u91cf\u7ea7\u4e00\u5f8b\u53d6 data/results_q*.json \u7684\u5b9e\u6d4b\u6781\u503c\uff0c\u4e0d\u5199\u5148\u9a8c\u731c\u6d4b\u3002
    ("c", "\u7ec4\u5408\u7d22\u5f15\uff1a\u68c9\u79c6 / \u7ea4\u7ef4\u7d20 / \u6728\u8d28\u7d20\uff08CE \u9898\u9762\u4f5c Cellooligosaccharide\uff0c\u9644\u4ef6\u811a\u6ce8\u4f5c Cellulose\uff0c\u672c\u6587\u4ece\u811a\u6ce8\uff09",
     "\u2014", GIVEN, "{CS, CE, LG}", "Q1\u2013Q5"),
    ("p", "\u4ea7\u7269\u7d22\u5f15", "\u2014", GIVEN, "{Tar, Water, Char, Syngas}", "Q1, Q3, Q4"),
    ("g", "\u6c14\u4f53\u7ec4\u5206\u7d22\u5f15", "\u2014", GIVEN, "CS 9 \u79cd / CE\u00b7LG \u5404 5 \u79cd", "Q2, Q3, Q4"),
    ("a", "\u63ba\u6bd4\u5206\u5b50\uff08DFA \u8d28\u91cf : \u751f\u7269\u8d28\u8d28\u91cf \u00d7100\uff09", "kg/kg", GIVEN, "0\u2013100", "\u5168"),
    ("r", "\u63ba\u6bd4\u8bfb\u6570 a/100", "1", GIVEN, "0\u20131.00\uff08CS \u4e5d\u6863\u542b 0/100\uff1bCE/LG \u516b\u6863\u81ea 0.10 \u8d77\uff1b\u6b65\u957f\u4e0d\u7b49\u8ddd\uff09", "\u5168"),
    ("w", "DFA \u8d28\u91cf\u5206\u6570 a/(a+100)", "1", DERIVED, "0\u20130.5000\uff08CE/LG \u65e0 0/100\uff09", "\u5168"),
    ("y_p", "\u4ea7\u7269\u4ea7\u7387", "wt.%(daf)", GIVEN, "8.19\u201358.17", "Q1, Q3, Q4"),
    ("z_g", "\u6c14\u4f53\u7ec4\u5206\u4ea7\u7387\uff08\u7edd\u5bf9\u4f53\u79ef\uff09", "mL/g(daf)", GIVEN, "0.05\u201365.80", "Q2, Q3, Q4"),
    ("\u03c6_g", "\u6c14\u4f53\u4f53\u79ef\u5206\u6570 z_g/\u03a3_g z_g", "1", DERIVED, "5.3e-4\u20130.838", "Q2"),
    ("S_p", "\u5f52\u4e00\u5316\u7ec4\u6210 y_p/100", "1", DERIVED, "0.0819\u20130.5817", "Q1, Q4"),
    ("u_p", "\u5bf9\u6570\u7ec4\u6210 ln S_p", "1", DERIVED, "-2.502\u2013-0.542", "Q1, Q4"),
    ("v_1..v_3", "ILR \u6b63\u4ea4\u5bf9\u6570\u6bd4\u5750\u6807", "1", DERIVED, "-1.16\u20130.95", "Q1, Q4"),
    ("b_j0, b_j1", "ILR \u5750\u6807\u5bf9 w \u7684\u7ebf\u6027\u56de\u5f52\u7cfb\u6570", "1, 1", DERIVED, "b1 \u7edd\u5bf9\u503c\u6700\u5927 1.79", "Q1"),
    ("\u03b3_p", "\u9009\u62e9\u6027\u6307\u6570 d ln S_p/d w\uff08\u4e2d\u5fc3\u5316 \u03a3\u03b3=0\uff09", "1", DERIVED, "-1.58\u20130.96", "Q4"),
    ("\u0394_p", "\u540c\u6863\u4f4d CE-LG \u7684\u4ea7\u7269\u5dee", "wt.%(daf)", DERIVED, "-36.74\u2013+37.09", "Q3"),
    ("\u0394_g", "\u540c\u6863\u4f4d CE-LG \u7684\u6c14\u4f53\u5dee", "mL/g(daf)", DERIVED, "-41.56\u2013+64.99", "Q3"),
    ("\u03ba", "CE/LG \u6bd4\u503c\uff08\u540c\u6863\u4f4d\uff09", "1", DERIVED, "0.023\u2013172.5", "Q3"),
    ("\u03b5_rel", "\u5e73\u884c\u5b9e\u9a8c\u76f8\u5bf9\u8bef\u5dee\uff08\u9898\u9762 L77\uff09", "1", GIVEN, "0.05", "Q1\u2013Q5"),
    ("\u03c4_single", "\u5355\u6d4b\u91cf\u5224\u636e 2\u03c3 = 0.10\u00b7y", "\u540c y", DERIVED, "0.007\u20135.817\uff08\u4ea7\u7269 0.819\u20135.817\uff09", "Q1, Q2"),
    ("\u03c4_diff", "\u4e24\u6d4b\u91cf\u5dee\u5224\u636e 0.10\u00b7\u221a(y_a\u00b2+y_b\u00b2)", "\u540c y", DERIVED, "0.320\u20136.580", "Q1\u2013Q3"),
    ("\u03c4_trend", "\u8d8b\u52bf\u5224\u636e 0.10\u00b7\u6bb5\u5185\u5747\u503c\u7684\u7edd\u5bf9\u503c\uff08\u5206\u6bcd\u5c0f\u4f1a\u653e\u5927\u6bd4\u503c\uff09", "\u540c y", DERIVED, "0.007\u20135.734", "Q1, Q2"),
    ("\u03c3_fit", "ILR \u6b8b\u5dee\u6807\u51c6\u5dee", "1", DERIVED, "0.0333\u20130.0941", "Q1, Q5"),
    ("\u03c3_noise", "5% \u566a\u58f0\u6620\u5c04\u5230 ILR \u540e\u7684\u6807\u51c6\u5dee\uff08MC 4000 \u6b21\uff09", "1", DERIVED, "0.0501\u20130.0502", "Q1"),
    ("F", "\u5931\u62df\u7edf\u8ba1\u91cf (sigma_fit/sigma_noise)^2", "1", DERIVED, "0.44\u20133.52", "Q1"),
    ("df", "\u6b8b\u5dee\u81ea\u7531\u5ea6 n_obs - k_par", "1", DERIVED, "21 / 18 / 18", "Q1"),
    ("k_p", "\u8868\u89c2\u901f\u7387\u5e38\u6570\uff08alpha=0.95, t=1800 s, T=800 K\uff09", "s^-1", DERIVED, "1.664e-3\uff08n=1\uff09", "Q4"),
    ("A_p", "\u6307\u524d\u56e0\u5b50\uff08\u6cbf\u810a\u7ebf\uff0c\u975e\u70b9\u4f30\u8ba1\uff09", "s^-1", DERIVED, "5.63e3\u20133.51e13", "Q4"),
    ("Ea_p", "\u6d3b\u5316\u80fd\uff08\u810a\u7ebf\u81ea\u53d8\u91cf\uff09", "kJ/mol", ASSUMED, "100\u2013250", "Q4"),
    ("n", "\u53cd\u5e94\u7ea7\u6570", "1", ASSUMED, "0 / 1 / 2 \u4e09\u6863", "Q4"),
    ("f(\u03b1)", "\u673a\u7406\u51fd\u6570", "1", ASSUMED, "R2 / R3 / D1", "Q4"),
    ("\u03b1", "\u8f6c\u5316\u7387\uff08\u9898\u9762\u672a\u7ed9\uff0c\u81ea\u8bbe\uff09", "1", ASSUMED, "0.95", "Q4"),
    ("T_py", "\u70ed\u89e3\u6e29\u5ea6\uff08\u9898\u9762\u53ea\u8bf4\u4e0d\u968f\u63ba\u6bd4\u53d8\uff0c\u65e0\u6570\u503c\uff09", "K", ASSUMED, "800", "Q4"),
    ("R_gas", "\u6c14\u4f53\u5e38\u6570", "J/(mol\u00b7K)", GIVEN, "8.314", "Q4"),
    ("t_hold", "\u505c\u7559\u65f6\u95f4\uff08\u81ea\u8bbe\uff09", "min", ASSUMED, "30", "Q4"),
    ("m_g", "\u6c14\u4f53\u8d28\u91cf\u4ea7\u7387\uff08\u4f53\u79ef\u6298\u8d28\u91cf\uff09", "mg/g(daf)", DERIVED, "0.060\u2013118.6", "Q2, Q4"),
    ("M_g", "\u7ec4\u5206\u6469\u5c14\u8d28\u91cf\uff08\u6587\u732e\u503c\uff09", "g/mol", ASSUMED, "2.016\u201358.124", "Q2, Q4"),
    ("V_m", "STP \u6469\u5c14\u4f53\u79ef\uff08\u81ea\u8bbe\uff09", "L/mol", ASSUMED, "22.414", "Q2"),
    ("\u03b2_bridge", "\u6c14\u4f53\u8d28\u91cf / Annex I Syngas \u8d28\u91cf\u6bd4", "1", DERIVED, "0.570\u20130.713", "Q2, Q4"),
    ("\u0177", "\u6a21\u578b\u62df\u5408\u503c", "\u540c y", DERIVED, "\u2014", "Q1\u2013Q5"),
    ("RMSE_loo", "\u7559\u4e00\u4ea4\u53c9\u9a8c\u8bc1\u76f8\u5bf9 RMSE", "1", DERIVED, "0.009\u20130.187", "Q5"),
    ("AIC", "\u8d64\u6c60\u4fe1\u606f\u91cf", "1", DERIVED, "-187.9 \u2013 -80.2", "Q1"),
]


def symbols_by_kind() -> dict:
    out: dict = {}
    for sym, meaning, unit, kind, mag, used in SYMBOLS:
        out.setdefault(kind, []).append(sym)
    return out


if __name__ == "__main__":
    selftest()
    print(f"[MS] PARAMS {len(MS.PARAMS)} \u6761\uff1bSYMBOLS {len(SYMBOLS)} \u6761")
    for k, v in symbols_by_kind().items():
        print(f"  {k}: {len(v)} \u4e2a\u7b26\u53f7")
