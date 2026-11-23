#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PRACTICE_2023B · s2 模型骨架：常量、符号、数据契约（唯一权威源）。

四条纪律（对应派单「四条硬经验」）
--------------------------------
① 一个数字只属于一个读法。本题有三个**外形相似、含义不同**的坐标，绝不许互换：
     r  = 掺比读数 a/100          （题面写法 10/100 … 100/100，无量纲，0.1–1.0）
     w  = DFA 质量分数 a/(a+100)  （0–0.5；100/100 → w=0.5，不是 1.0）
     φ  = 气体体积分数 z_g/Σz_g   （分母是该行气体之和，不是 100）
   以及两条**阈值路径**：τ_single=0.10·y（单测量 vs 已知真值）、
   τ_diff=0.10·√(y_a²+y_b²)（两个独立测量的差）。凡写「显著」必须标路径。
② 本文件不写任何「本文 X 个」「脚本 Y 字节」式自指数字；字节数由 code/gen_index.py 现读。
③ 数据契约（CONTRACT）只在这里定义一次。solve.py 与 make_figures.py 一律 import，
   不许各自硬编码 —— 改一处不改三处，图里柱子会全变 0（硬经验③）。
④ 常数三分类：GIVEN 题给 / ASSUMED 自设 / DERIVED 中间量。题面没有的一律 ASSUMED，
   键名后缀 `_ASSUMED`，值旁注「自设」。派生的量由 derive() 现算，不写死。

数据解析不重写：直接复用 code/fetch_annex.py 的 read_sheet / parse_annex_*，
保证与 data/ledger.json 是同一份解析（改解析只改一处）。
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

GIVEN = "题给"
ASSUMED = "自设"
DERIVED = "中间量"

# ---------------------------------------------------------------- 数据契约（唯一定义处）
CONTRACT = {
    "products": ["Tar", "Water", "Char", "Syngas"],
    "combos": ["DFA/CS", "DFA/CE", "DFA/LG"],
    "combo_short": {"DFA/CS": "CS", "DFA/CE": "CE", "DFA/LG": "LG"},
    "gases": {
        "DFA/CS": ["H2", "CO", "CO2", "CH4", "C2H6", "C3H8", "C3H6", "C2H4", "C4H10"],
        "DFA/CE": ["H2", "CO", "CO2", "CH4", "C2H6"],
        "DFA/LG": ["H2", "CO", "CO2", "CH4", "C2H6"],
    },
    # 图族顺序与配色：make_figures.py 的 FUNC_ORDER / FUNC_COLORS 必须等于这两项
    "figure_order": ["Tar", "Water", "Char", "Syngas"],
    "figure_colors": {"Tar": "#1f4e79", "Water": "#2e75b6",
                      "Char": "#7f7f7f", "Syngas": "#c55a11"},
    "gas_colors": {"H2": "#1f4e79", "CO": "#c55a11", "CO2": "#548235",
                   "CH4": "#7f6000", "C2H6": "#7030a0"},
    # 量级分层（Q2 分栏依据）：主量级 span ≥ 5 mL/g(daf)，次量级 < 5
    "tier_major": ["H2", "CO", "CO2", "CH4", "C2H6"],
}

# 摩尔质量 g/mol（文献常数，自设：题面未给）
MOLAR_MASS = {"H2": 2.016, "CO": 28.010, "CO2": 44.009, "CH4": 16.043,
              "C2H6": 30.070, "C3H8": 44.097, "C3H6": 42.081,
              "C2H4": 28.054, "C4H10": 58.124}


class MS:
    """模型骨架常量。`MS.PARAMS` 是全文常量的**唯一权威**（G1/G2 回查此处）。"""

    # ------------------------------------------------------------ 题给块（C01–C23）
    PARAMS = {
        # --- 掺比八档（L74–L75）。value 存 r=a/100；label 存题面写法
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
        # --- 反例档：题面点名但未采用，不得当实验点
        "r_neg1": dict(id="C09", sym="r_neg1", value=0.05, label="5/100",
                       unit="kg/kg", kind=GIVEN, src="problem.txt L78",
                       note="反例，未采用；不得作实验点"),
        "r_neg2": dict(id="C10", sym="r_neg2", value=0.07, label="7/100",
                       unit="kg/kg", kind=GIVEN, src="problem.txt L78",
                       note="反例，未采用"),
        # --- 噪声地板（L77）：判据的不等式右端，不是模型精度目标
        "eps_rel": dict(id="C11", sym="eps_rel", value=0.05, unit="1 (相对)",
                        kind=GIVEN, src="problem.txt L77",
                        note="平行实验相对误差 ≈5%；是数据不确定度，不是本文模型的精度指标"),
        "n_comb": dict(id="C14", sym="N_comb", value=3, unit="个",
                       kind=GIVEN, src="problem.txt L131-L137"),
        "n_prod": dict(id="C15", sym="N_prod", value=4, unit="种",
                       kind=GIVEN, src="problem.txt L138"),
        "n_gas_cs": dict(id="C16", sym="N_gas_CS", value=9, unit="种",
                         kind=GIVEN, src="problem.txt L139-L140"),
        "n_gas_ce": dict(id="C17", sym="N_gas_CE", value=5, unit="种",
                         kind=GIVEN, src="problem.txt L141-L142"),
        "n_gas_lg": dict(id="C18", sym="N_gas_LG", value=5, unit="种",
                         kind=GIVEN, src="problem.txt L143-L144"),
        "n_q": dict(id="C19", sym="N_Q", value=5, unit="问",
                    kind=GIVEN, src="problem.txt L90-L111"),
        "t_const": dict(id="C23", sym="T_const", value=None, unit="K",
                        kind=GIVEN, src="problem.txt L145-L146",
                        note="题面只声明「同一温度」，未给数值 —— 数值不得当题给"),
        # --- 自设块（T1–T12）：题面没有，全部后缀 _ASSUMED
        "T_py_ASSUMED": dict(id="T1", sym="T_py", value=800.0, unit="K", kind=ASSUMED,
                             note="自设：题面只说同一温度，未给数值"),
        "beta_heat_ASSUMED": dict(id="T2", sym="beta_heat", value=10.0, unit="K/min",
                                  kind=ASSUMED, note="自设：升温速率题面未提"),
        "t_hold_ASSUMED": dict(id="T3", sym="t_hold", value=30.0, unit="min",
                               kind=ASSUMED, note="自设：停留时间未给"),
        "Q_carrier_ASSUMED": dict(id="T4", sym="Q_carrier", value=100.0, unit="mL/min",
                                  kind=ASSUMED, note="自设：载气流速未给"),
        "d_p_ASSUMED": dict(id="T5", sym="d_p", value=0.2, unit="mm",
                            kind=ASSUMED, note="自设：粒径未给"),
        "m_sample_ASSUMED": dict(id="T6", sym="m_sample", value=5.0, unit="g",
                                 kind=ASSUMED, note="自设：单次进样量未给"),
        "A_pre_ASSUMED": dict(id="T7", sym="A_pre", value=None, unit="s^-1", kind=ASSUMED,
                              note="自设：待辨识，不得单独固定；与 Ea 联合成脊"),
        "Ea_ASSUMED_RANGE": dict(id="T8", sym="Ea", value=[100.0, 250.0], unit="kJ/mol",
                                 kind=ASSUMED, note="自设：先验区间，不是拟合值"),
        "n_order_ASSUMED": dict(id="T9", sym="n_order", value=1.0, unit="1",
                                kind=ASSUMED, note="自设：反应级数先验；须给 0/1/2 三档对比"),
        "f_alpha_ASSUMED": dict(id="T10", sym="f_alpha", value=["R2", "R3", "D1"],
                                unit="1", kind=ASSUMED,
                                note="自设：机理函数三档对比，不许只报一档"),
        "dfa_comp_ASSUMED": dict(id="T11", sym="dfa_comp",
                                 value={"CaO": 0.40, "CaSO4": 0.30, "SiO2": 0.15, "other": 0.15},
                                 unit="wt.%", kind=ASSUMED,
                                 note="自设/文献典型值：题面与附件均未给脱硫灰组成"),
        "grid_pred_ASSUMED": dict(id="T12", sym="grid_pred",
                                  value=[0.15, 0.25, 0.35, 0.45, 0.55, 0.70, 0.90],
                                  unit="1 (r)", kind=ASSUMED,
                                  note="自设：Q5 预测网格；全部落在观测区间内 = 内插，不是外推"),
        # --- 桥接用自设常数（Annex II 体积 → 质量）
        "V_m_ASSUMED": dict(id="T13", sym="V_m", value=22.414, unit="L/mol", kind=ASSUMED,
                            note="自设：STP(273.15 K, 101.325 kPa) 理想气体摩尔体积"),
        "R_gas": dict(id="T14", sym="R_gas", value=8.314, unit="J/(mol·K)", kind=GIVEN,
                      src="物理常数（非题面数据）", note="文献常数"),
    }

    # ------------------------------------------------------------ 派生块（现算）
    DERIVED: dict = {}

    @classmethod
    def p(cls, key: str) -> dict:
        return cls.PARAMS[key]

    @classmethod
    def v(cls, key: str) -> float:
        return cls.PARAMS[key]["value"]


# ---------------------------------------------------------------- 坐标换算
def w_of_r(r):
    """掺比读数 r=a/100 → DFA 质量分数 w=a/(a+100)=r/(1+r)。"""
    r = np.asarray(r, dtype=float)
    return r / (1.0 + r)


def r_of_w(w):
    w = np.asarray(w, dtype=float)
    return w / (1.0 - w)


def ratio_value(label: str) -> float:
    """'20/100' → 0.20。"""
    a, b = label.split("/")
    return float(a) / float(b)


# ---------------------------------------------------------------- 附件读取（复用 fetch_annex）
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
    """{combo: {labels, r, w, series{product: array}}}，产物名已去掉 ' yield'。"""
    return _pivot("I")


def load_annex_ii() -> dict:
    """{combo: {labels, r, w, series{gas: array}}}。"""
    return _pivot("II")


def formula_cells(which: str):
    """返回 [(cell, formula)]：附件里被 Excel 公式推出的单元格。

    这是本题最硬的一条建模约束：每张表**只有一个产物是公式推出来的**
    （CS→Syngas、CE→Char、LG→Tar），四产物只有三自由度。
    """
    try:
        import openpyxl
    except ImportError:  # 无 openpyxl 时返回 None，调用方须自行降级
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


# ---------------------------------------------------------------- 自检（solve.py 启动时调用）
def selftest(verbose: bool = True) -> dict:
    """三条结构断言：闭合性、公式派生列、两附件网格嵌套。失败直接抛。"""
    ai = load_annex_i()
    aii = load_annex_ii()
    prod = CONTRACT["products"]

    # 1) Annex I 闭合：Σ_p y_p = 100（逐列）
    sums = []
    for combo, d in ai.items():
        M = np.column_stack([d["series"][p] for p in prod])
        sums.extend(M.sum(axis=1).tolist())
    max_dev = float(np.max(np.abs(np.array(sums) - 100.0)))

    # 2) 公式派生列
    fc = formula_cells("I")
    n_formula = None if fc is None else len(fc)
    derived_col = {}
    if fc is not None:
        # 公式所在行 → 产物名；反查每表被推出的是哪个产物
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

    # 3) 网格嵌套：Annex II 的档位必须 ⊆ 同组合 Annex I 的档位
    nested = {}
    for combo in CONTRACT["combos"]:
        nested[combo] = set(aii[combo]["labels"]) <= set(ai[combo]["labels"])

    out = dict(max_abs_sum_minus_100=max_dev,
               n_formula_cells=n_formula,
               formula_rows=derived_col,
               nested=nested,
               n_cols_annex_i=int(sum(len(d["labels"]) for d in ai.values())),
               n_cols_annex_ii=int(sum(len(d["labels"]) for d in aii.values())))
    assert max_dev < 1e-6, f"Annex I 不闭合，最大偏差 {max_dev}"
    assert all(nested.values()), f"网格不嵌套：{nested}"
    if n_formula is not None:
        # 每张子表有**一整行**是公式：8 列 × 3 表 = 24 个单元格，每表各推出**不同**产物
        assert n_formula == 24, f"公式派生单元格应为 24 个，实测 {n_formula}"
        assert derived_col == {"Syngas": 8, "Char": 8, "Tar": 8}, \
            f"每表被推出的产物应为 Syngas/Char/Tar 各 8 列，实测 {derived_col}"
    MS.DERIVED.update(out)
    if verbose:
        print(f"[selftest] Annex I 闭合 max|Σ-100| = {max_dev:.2e} "
              f"（{out['n_cols_annex_i']} 列）")
        print(f"[selftest] 公式派生单元格 {n_formula} 个，行分布 {derived_col}")
        print(f"[selftest] 网格嵌套 {nested}；Annex II {out['n_cols_annex_ii']} 列")
    return out


# ---------------------------------------------------------------- 符号表（附录 A 用）
SYMBOLS = [
    # (符号, 含义, 单位, 类别, 量级, 用在)
    # 量级一律取 data/results_q*.json 的实测极值，不写先验猜测。
    ("c", "组合索引：棉秆 / 纤维素 / 木质素（CE 题面作 Cellooligosaccharide，附件脚注作 Cellulose，本文从脚注）",
     "—", GIVEN, "{CS, CE, LG}", "Q1–Q5"),
    ("p", "产物索引", "—", GIVEN, "{Tar, Water, Char, Syngas}", "Q1, Q3, Q4"),
    ("g", "气体组分索引", "—", GIVEN, "CS 9 种 / CE·LG 各 5 种", "Q2, Q3, Q4"),
    ("a", "掺比分子（DFA 质量 : 生物质质量 ×100）", "kg/kg", GIVEN, "0–100", "全"),
    ("r", "掺比读数 a/100", "1", GIVEN, "0–1.00（CS 九档含 0/100；CE/LG 八档自 0.10 起；步长不等距）", "全"),
    ("w", "DFA 质量分数 a/(a+100)", "1", DERIVED, "0–0.5000（CE/LG 无 0/100）", "全"),
    ("y_p", "产物产率", "wt.%(daf)", GIVEN, "8.19–58.17", "Q1, Q3, Q4"),
    ("z_g", "气体组分产率（绝对体积）", "mL/g(daf)", GIVEN, "0.05–65.80", "Q2, Q3, Q4"),
    ("φ_g", "气体体积分数 z_g/Σ_g z_g", "1", DERIVED, "5.3e-4–0.838", "Q2"),
    ("S_p", "归一化组成 y_p/100", "1", DERIVED, "0.0819–0.5817", "Q1, Q4"),
    ("u_p", "对数组成 ln S_p", "1", DERIVED, "-2.502–-0.542", "Q1, Q4"),
    ("v_1..v_3", "ILR 正交对数比坐标", "1", DERIVED, "-1.16–0.95", "Q1, Q4"),
    ("b_j0, b_j1", "ILR 坐标对 w 的线性回归系数", "1, 1", DERIVED, "b1 绝对值最大 1.79", "Q1"),
    ("γ_p", "选择性指数 d ln S_p/d w（中心化 Σγ=0）", "1", DERIVED, "-1.58–0.96", "Q4"),
    ("Δ_p", "同档位 CE-LG 的产物差", "wt.%(daf)", DERIVED, "-36.74–+37.09", "Q3"),
    ("Δ_g", "同档位 CE-LG 的气体差", "mL/g(daf)", DERIVED, "-41.56–+64.99", "Q3"),
    ("κ", "CE/LG 比值（同档位）", "1", DERIVED, "0.023–172.5", "Q3"),
    ("ε_rel", "平行实验相对误差（题面 L77）", "1", GIVEN, "0.05", "Q1–Q5"),
    ("τ_single", "单测量判据 2σ = 0.10·y", "同 y", DERIVED, "0.007–5.817（产物 0.819–5.817）", "Q1, Q2"),
    ("τ_diff", "两测量差判据 0.10·√(y_a²+y_b²)", "同 y", DERIVED, "0.320–6.580", "Q1–Q3"),
    ("τ_trend", "趋势判据 0.10·段内均值的绝对值（分母小会放大比值）", "同 y", DERIVED, "0.007–5.734", "Q1, Q2"),
    ("σ_fit", "ILR 残差标准差", "1", DERIVED, "0.0333–0.0941", "Q1, Q5"),
    ("σ_noise", "5% 噪声映射到 ILR 后的标准差（MC 4000 次）", "1", DERIVED, "0.0501–0.0502", "Q1"),
    ("F", "失拟统计量 (sigma_fit/sigma_noise)^2", "1", DERIVED, "0.44–3.52", "Q1"),
    ("df", "残差自由度 n_obs - k_par", "1", DERIVED, "21 / 18 / 18", "Q1"),
    ("k_p", "表观速率常数（alpha=0.95, t=1800 s, T=800 K）", "s^-1", DERIVED, "1.664e-3（n=1）", "Q4"),
    ("A_p", "指前因子（沿脊线，非点估计）", "s^-1", DERIVED, "5.63e3–3.51e13", "Q4"),
    ("Ea_p", "活化能（脊线自变量）", "kJ/mol", ASSUMED, "100–250", "Q4"),
    ("n", "反应级数", "1", ASSUMED, "0 / 1 / 2 三档", "Q4"),
    ("f(α)", "机理函数", "1", ASSUMED, "R2 / R3 / D1", "Q4"),
    ("α", "转化率（题面未给，自设）", "1", ASSUMED, "0.95", "Q4"),
    ("T_py", "热解温度（题面只说不随掺比变，无数值）", "K", ASSUMED, "800", "Q4"),
    ("R_gas", "气体常数", "J/(mol·K)", GIVEN, "8.314", "Q4"),
    ("t_hold", "停留时间（自设）", "min", ASSUMED, "30", "Q4"),
    ("m_g", "气体质量产率（体积折质量）", "mg/g(daf)", DERIVED, "0.060–118.6", "Q2, Q4"),
    ("M_g", "组分摩尔质量（文献值）", "g/mol", ASSUMED, "2.016–58.124", "Q2, Q4"),
    ("V_m", "STP 摩尔体积（自设）", "L/mol", ASSUMED, "22.414", "Q2"),
    ("β_bridge", "气体质量 / Annex I Syngas 质量比", "1", DERIVED, "0.570–0.713", "Q2, Q4"),
    ("ŷ", "模型拟合值", "同 y", DERIVED, "—", "Q1–Q5"),
    ("RMSE_loo", "留一交叉验证相对 RMSE", "1", DERIVED, "0.009–0.187", "Q5"),
    ("AIC", "赤池信息量", "1", DERIVED, "-187.9 – -80.2", "Q1"),
]


def symbols_by_kind() -> dict:
    out: dict = {}
    for sym, meaning, unit, kind, mag, used in SYMBOLS:
        out.setdefault(kind, []).append(sym)
    return out


if __name__ == "__main__":
    selftest()
    print(f"[MS] PARAMS {len(MS.PARAMS)} 条；SYMBOLS {len(SYMBOLS)} 条")
    for k, v in symbols_by_kind().items():
        print(f"  {k}: {len(v)} 个符号")
