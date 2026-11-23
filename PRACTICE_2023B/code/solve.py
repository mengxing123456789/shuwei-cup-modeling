#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PRACTICE_2023B · s2 求解骨架：Q1–Q5 全部走通，落 data/results_q*.json。

设计原则（对应派单「四条硬经验」）
--------------------------------
① 每个数字标口径。凡「显著」「阈值」都带路径键，三条路径**不共用同一个词**：
     path="single" → 0.10·y            一次测量 vs 已知真值
     path="diff"   → 0.10·√(ya²+yb²)   两个独立测量之差
     path="trend"  → 0.10·mean(y)      整段跨度 vs 噪声地板
② 不写自指数字（「本文 N 个」）；只写从数据算出来的量。
③ 契约全部 import 自 model_skeleton.CONTRACT，不在此重复硬编码。
④ 常数只从 MS.PARAMS 取。

环境约束（硬）
--------------
本机 numpy 的 BLAS/LAPACK 一碰就整进程崩（0xc06d007f）。本文件**禁用**
`@` / `np.dot` / `np.linalg.*` / `np.polyfit`，线性代数一律走 code/numlib.py
（einsum 组正规方程 + 纯 Python 高斯消元）。复算：python code\\_probe_one.py matmul

关键建模判断（正文要引用的三条）
--------------------------------
(a) 四产物只有**三个自由度**：Annex I 每张子表有一整行是 `=100-...` 公式，
    且三表推的是**不同**产物（CS→Syngas、CE→Char、LG→Tar）。所以
    「四产物各自独立回归」是错的（派生列 R² 必然虚高），一律在 3 维 ILR
    正交对数比坐标里拟合，再反变换回成分。
(b) 等温终点数据只能辨识乘积 k(T)·t，不能分开辨识 A 与 Ea。
    Q4 报**脊线**（每个 Ea 对应的 A），不报点估计。
(c) 每组合只有 5–9 个档位且无重复实验 → 「±10% 扰动重算」等于凭空造数据。
    敏感性一律用 5% 噪声蒙特卡洛 + 留一交叉验证。

运行：E:\\Mini\\envs\\mathmodel\\python.exe code\\solve.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parent
ROOT = CODE.parent
DATA = ROOT / "data"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import model_skeleton as M  # noqa: E402
import numlib as NL  # noqa: E402
from model_skeleton import CONTRACT, MOLAR_MASS, MS  # noqa: E402

PROD = CONTRACT["products"]
COMBOS = CONTRACT["combos"]
SHORT = CONTRACT["combo_short"]
GASES = CONTRACT["gases"]

# Kept as a module-level constant so the source stays ASCII; at runtime this is
# the same two-character marker that the report tables use.
DERIVED_MARK = " [\u6d3e\u751f\u5217]"
RNG_SEED = 20231119
N_MC = 4000

# Windows 控制台默认 GBK，会把 σ / Δ / ² 打成异常并中断；统一改 UTF-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------- ILR 基（Helmert 型，行正交归一）
def _ilr_basis(k: int = 4) -> np.ndarray:
    V = np.zeros((k - 1, k))
    for i in range(k - 1):
        V[i, : i + 1] = 1.0
        V[i, i + 1] = -(i + 1)
        nrm = float(np.sqrt((V[i] * V[i]).sum()))
        V[i] = V[i] / nrm
    return V


V4 = _ilr_basis(4)


def ilr(S: np.ndarray) -> np.ndarray:
    """成分 (n,4) → ILR 坐标 (n,3)。用 einsum，不走 BLAS。"""
    S = np.atleast_2d(np.asarray(S, dtype=float))
    lg = np.log(S)
    u = lg - lg.mean(axis=1, keepdims=True)
    return np.einsum("nk,jk->nj", u, V4)


def ilr_inv(v: np.ndarray) -> np.ndarray:
    """ILR 坐标 (n,3) → 成分 (n,4)，行和 = 1。"""
    v = np.atleast_2d(np.asarray(v, dtype=float))
    u = np.einsum("nj,jk->nk", v, V4)
    e = np.exp(u)
    return e / e.sum(axis=1, keepdims=True)


def design(w) -> np.ndarray:
    return np.column_stack([np.ones_like(np.asarray(w, dtype=float)), w])


# ---------------------------------------------------------------- 判据（三条路径，互不替代）
def thr_single(y):
    y = np.abs(np.asarray(y, dtype=float))
    return 2.0 * MS.v("eps_rel") * y


def thr_diff(ya, yb):
    ya = np.abs(np.asarray(ya, dtype=float))
    yb = np.abs(np.asarray(yb, dtype=float))
    s = MS.v("eps_rel")
    return 2.0 * np.sqrt((s * ya) ** 2 + (s * yb) ** 2)


def thr_trend(y):
    y = np.asarray(y, dtype=float)
    return 2.0 * MS.v("eps_rel") * np.abs(y).mean()


def steps(y):
    y = np.asarray(y, dtype=float)
    d = np.diff(y)
    lim = 2.0 * MS.v("eps_rel") * np.maximum(np.abs(y[:-1]), np.abs(y[1:]))
    return d, lim, np.abs(d) > lim


def _f(x):
    if isinstance(x, np.ndarray):
        return [float(t) for t in x.ravel()]
    if isinstance(x, (np.floating, np.integer)):
        return float(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def dump(name: str, obj: dict) -> Path:
    path = DATA / name
    txt = json.dumps(obj, ensure_ascii=False, indent=1, default=_f)
    path.write_bytes((txt + "\n").encode("utf-8"))
    return path


# ---------------------------------------------------------------- Q1
def q1(ai: dict) -> dict:
    out = {"meta": {
        "question": "Q1 DFA 掺比对四产物产率的影响（幅度 / 方向 / 是否超噪）",
        "caliber": {
            "path_single": "0.10·y —— 一次测量与已知真值比",
            "path_trend": "0.10·mean(y) —— 整段跨度与噪声地板比",
            "eps_rel": MS.v("eps_rel"),
            "note_derived": "Annex I 每表有一整行是 =100-... 公式，该产物是派生量，其单独 R² 不可作证据",
        },
        "dof": "四产物 Σ=100 → 仅 3 个自由度；拟合在 3 维 ILR 空间进行",
        "linalg": "正规方程 + 纯 Python 高斯消元（BLAS 禁用，见 numlib）",
        "seed": RNG_SEED, "n_mc": N_MC,
    }, "combos": {}}

    rng = np.random.default_rng(RNG_SEED)
    for combo in COMBOS:
        d = ai[combo]
        w = d["w"]
        S = np.column_stack([d["series"][p] for p in PROD]) / 100.0
        V = ilr(S)
        rec = {"labels": d["labels"], "r": _f(d["r"]), "w": _f(w),
               "products": {}, "ilr": {}, "aic": {}}

        for p in PROD:
            y = d["series"][p]
            dy, lim, ex = steps(y)
            span = float(y.max() - y.min())
            rec["products"][p] = {
                "y": _f(y),
                "first": float(y[0]), "last": float(y[-1]),
                "delta_end": float(y[-1] - y[0]),
                "delta_end_pct": float(100.0 * (y[-1] - y[0]) / y[0]),
                "span": span, "mean": float(y.mean()),
                "thr_trend": float(thr_trend(y)),
                "span_over_thr": float(span / thr_trend(y)),
                "trend_significant": bool(span > thr_trend(y)),
                "steps": _f(dy), "step_lim": _f(lim),
                "n_step_exceed": int(ex.sum()), "n_step": int(len(dy)),
                "monotone": bool(np.all(dy > 0) or np.all(dy < 0)),
                "is_derived": bool((combo == "DFA/CS" and p == "Syngas")
                                   or (combo == "DFA/CE" and p == "Char")
                                   or (combo == "DFA/LG" and p == "Tar")),
            }

        X = design(w)
        B, rss = NL.lstsq(X, V)
        R = V - np.einsum("nk,km->nm", X, B)
        n_obs, k_par = int(V.size), int(B.size)
        sigma_fit = float(np.sqrt(rss / max(n_obs - k_par, 1)))
        r2_each = []
        for j in range(V.shape[1]):
            sst = float(((V[:, j] - V[:, j].mean()) ** 2).sum())
            r2_each.append(1.0 - float((R[:, j] ** 2).sum()) / sst if sst > 0 else 0.0)

        sims = np.zeros((N_MC, len(w), 3))
        for i in range(N_MC):
            noise = rng.normal(1.0, MS.v("eps_rel"), size=S.shape)
            Ss = S * noise
            Ss = Ss / Ss.sum(axis=1, keepdims=True)
            sims[i] = ilr(Ss)
        sigma_noise = float(sims.std(axis=0).mean())
        F = (sigma_fit / sigma_noise) ** 2 if sigma_noise > 0 else float("inf")

        def aic(rss_v, k):
            return float(n_obs * np.log(rss_v / n_obs) + 2 * k)

        cand = {"M1_linear_w": aic(rss, k_par)}
        for name, xf in (("M2_linear_logw", lambda t: np.log(t + 1e-3)),
                         ("M3_sqrt_w", lambda t: np.sqrt(t))):
            Xa = np.column_stack([np.ones_like(w), xf(w)])
            Ba, rss_a = NL.lstsq(Xa, V)
            cand[name] = aic(rss_a, int(Ba.size))
        cand["M0_null"] = aic(float(((V - V.mean(axis=0)) ** 2).sum()), V.shape[1])

        rec["ilr"] = {
            "basis": "Helmert 正交对比，行正交归一且行和为 0",
            "coef_table": {f"v{j+1}": {"b0": float(B[0, j]), "b1": float(B[1, j])}
                           for j in range(3)},
            "R2_each": _f(r2_each),
            "rss": rss, "n_obs": n_obs, "k_par": k_par,
            "sigma_fit": sigma_fit, "sigma_noise_mc": sigma_noise,
            "lack_of_fit_F": F,
            "lack_of_fit_verdict": ("残差在 5% 噪声可解释范围内" if F <= 1.0
                                    else "残差超出 5% 噪声，存在系统性失拟"),
            "n_mc": N_MC,
        }
        rec["aic"] = cand
        rec["aic_best"] = min(cand, key=cand.get)
        out["combos"][SHORT[combo]] = rec
    return out


# ---------------------------------------------------------------- Q2
def q2(aii: dict, ai: dict) -> dict:
    out = {"meta": {
        "question": "Q2 气体组分产率的图族方案与逐组分检验量",
        "caliber": {
            "path_single": "0.10·z —— 逐档与噪声地板比",
            "path_trend": "0.10·mean(z) —— 整段跨度",
            "phi_denominator": "该行 Σ_g z_g（不是 100）",
            "annex2_rowsum": "Annex II 行和 68.00–153.25，不等于 100，也不等于 Annex I Syngas",
            "note": "故 Annex II 只作相对组成 φ 使用，不做绝对质量闭合",
        },
        "tier_rule": "span ≥ 5 mL/g(daf) 为主量级，否则次量级（自设阈值，见 A7）",
        "V_m": MS.v("V_m_ASSUMED"),
    }, "combos": {}, "tiers": {}, "bridge": {}}

    for combo in COMBOS:
        d = aii[combo]
        rec = {"labels": d["labels"], "r": _f(d["r"]), "w": _f(d["w"]),
               "gases": {}}
        Z = np.column_stack([d["series"][g] for g in GASES[combo]])
        phi = Z / Z.sum(axis=1, keepdims=True)
        rec["row_sum"] = _f(Z.sum(axis=1))

        for gi, g in enumerate(GASES[combo]):
            z = d["series"][g]
            dz, lim, ex = steps(z)
            span = float(z.max() - z.min())
            rec["gases"][g] = {
                "z": _f(z), "phi": _f(phi[:, gi]),
                "span": span, "mean": float(z.mean()),
                "thr_trend": float(thr_trend(z)),
                "span_over_thr": float(span / thr_trend(z)),
                "trend_significant": bool(span > thr_trend(z)),
                "n_step_exceed": int(ex.sum()), "n_step": int(len(dz)),
                "monotone": bool(np.all(dz > 0) or np.all(dz < 0)),
                "argmax_label": d["labels"][int(np.argmax(z))],
                "tier": "major" if span >= 5.0 else "minor",
                "m_mg_per_g": _f(z * MOLAR_MASS[g] / MS.v("V_m_ASSUMED")),
                "M": MOLAR_MASS[g],
            }
        out["combos"][SHORT[combo]] = rec
        out["tiers"][SHORT[combo]] = {
            "major": [g for g in GASES[combo] if rec["gases"][g]["tier"] == "major"],
            "minor": [g for g in GASES[combo] if rec["gases"][g]["tier"] == "minor"],
        }

    for combo in COMBOS:
        d2, d1 = aii[combo], ai[combo]
        m = np.zeros(len(d2["labels"]))
        for g in GASES[combo]:
            m = m + d2["series"][g] * MOLAR_MASS[g] / MS.v("V_m_ASSUMED")
        y_syn = np.array([d1["series"]["Syngas"][d1["labels"].index(l)]
                          for l in d2["labels"]])
        out["bridge"][SHORT[combo]] = {
            "labels": d2["labels"],
            "gas_mass_mg_per_g": _f(m),
            "gas_mass_wtpct": _f(m / 10.0),
            "annex1_syngas_wtpct": _f(y_syn),
            "beta_bridge": _f((m / 10.0) / y_syn),
            "verdict": "两附件量纲体系不同（体积 vs 质量），比值不等于 1 属预期，不得当数据错误",
        }
    return out


# ---------------------------------------------------------------- Q3
def q3(ai: dict, aii: dict) -> dict:
    out = {"meta": {
        "question": "Q3 纤维素(CE) 与 木质素(LG) 在同一掺比下的差异",
        "caliber": {
            "path_diff": "0.10·√(y_CE²+y_LG²) —— 两个独立测量之差的判据",
            "levels_products": "Annex I 的 CE/LG 各有 8 档（10…100），逐档可配 8 对",
            "levels_gases": "Annex II 的 CE/LG 各有 5 档（20/40/50/80/100），只能配 5 对",
            "note": "两处档数不同，不得混用一个「公共档位」说法",
        },
    }, "products": {}, "gases": {}, "flips": {}}

    dCE, dLG = ai["DFA/CE"], ai["DFA/LG"]
    lev = [l for l in dCE["labels"] if l in set(dLG["labels"])]
    out["levels_products"] = lev
    for p in PROD:
        a = np.array([dCE["series"][p][dCE["labels"].index(l)] for l in lev])
        b = np.array([dLG["series"][p][dLG["labels"].index(l)] for l in lev])
        D = a - b
        lim = thr_diff(a, b)
        out["products"][p] = {
            "CE": _f(a), "LG": _f(b), "Delta": _f(D), "thr_diff": _f(lim),
            "n_exceed": int((np.abs(D) > lim).sum()), "n": int(len(lev)),
            "ratio_CE_over_LG": _f(a / b),
            "sign_changes": int((np.diff(np.sign(D)) != 0).sum()),
            "mean_Delta": float(D.mean()),
        }

    gCE, gLG = aii["DFA/CE"], aii["DFA/LG"]
    levg = [l for l in gCE["labels"] if l in set(gLG["labels"])]
    out["levels_gases"] = levg
    for g in GASES["DFA/CE"]:
        a = np.array([gCE["series"][g][gCE["labels"].index(l)] for l in levg])
        b = np.array([gLG["series"][g][gLG["labels"].index(l)] for l in levg])
        D = a - b
        lim = thr_diff(a, b)
        out["gases"][g] = {
            "CE": _f(a), "LG": _f(b), "Delta": _f(D), "thr_diff": _f(lim),
            "n_exceed": int((np.abs(D) > lim).sum()), "n": int(len(levg)),
            "ratio_CE_over_LG": _f(a / b),
            "abs_max": float(np.maximum(np.abs(a), np.abs(b)).max()),
        }

    # 气体块没有 sign_changes 键，统一按「方向翻转 / 全程不超噪」两条判据
    for group, tbl in (("products", out["products"]), ("gases", out["gases"])):
        out["flips"][group] = [k for k, v in tbl.items()
                               if v.get("sign_changes", 0) > 0 or v["n_exceed"] == 0]
    return out


# ---------------------------------------------------------------- Q4
def q4(ai: dict, aii: dict, r1: dict) -> dict:
    out = {"meta": {
        "question": "Q4 掺比改变产物分布的机制解释与动力学可辨识性",
        "caliber": {
            "gamma_definition": "gamma_p = d ln S_p / d w，S_p=y_p/100，中心化后 Σgamma=0",
            "identifiability": "等温终点数据只辨识 k(T)·t；A 与 Ea 不能分开辨识，报脊线不报点",
            "alpha_target": "自设：热解终点转化率取 0.95（题面未给转化率）",
        },
    }, "selectivity": {}, "carbon_balance": {}, "kinetics": {}}

    for combo in COMBOS:
        d = ai[combo]
        S = np.column_stack([d["series"][p] for p in PROD]) / 100.0
        u = np.log(S)
        w = d["w"]
        X = design(w)
        Bu, _ = NL.lstsq(X, u)
        b = Bu[1]
        gamma = b - b.mean()
        out["selectivity"][SHORT[combo]] = {
            "dlnS_dw_raw": _f(b),
            "gamma_centered": {p: float(gamma[i]) for i, p in enumerate(PROD)},
            "sum_gamma": float(gamma.sum()),
            "interpretation": ("gamma<0 表示该产物份额随掺灰按幂律下降，"
                               "gamma>0 表示份额上升；gamma≈0 表示几乎不参与"),
        }

    nC = {"H2": 0, "CO": 1, "CO2": 1, "CH4": 1, "C2H6": 2,
          "C3H8": 3, "C3H6": 3, "C2H4": 2, "C4H10": 4}
    for combo in COMBOS:
        d = aii[combo]
        c_mmol = np.zeros(len(d["labels"]))
        for g in GASES[combo]:
            c_mmol = c_mmol + nC[g] * d["series"][g] / MS.v("V_m_ASSUMED")
        out["carbon_balance"][SHORT[combo]] = {
            "labels": d["labels"],
            "carbon_mmol_per_g": _f(c_mmol),
            "delta_end": float(c_mmol[-1] - c_mmol[0]),
            "delta_end_pct": float(100.0 * (c_mmol[-1] - c_mmol[0]) / c_mmol[0]),
            "monotone": bool(np.all(np.diff(c_mmol) > 0) or np.all(np.diff(c_mmol) < 0)),
        }

    t_s = MS.v("t_hold_ASSUMED") * 60.0
    T = MS.v("T_py_ASSUMED")
    R = MS.v("R_gas")
    alpha = 0.95
    kt = {"n=0": alpha, "n=1": -np.log(1 - alpha), "n=2": 1.0 / (1 - alpha) - 1.0}
    k_need = {k: float(v / t_s) for k, v in kt.items()}
    Ea_grid = np.linspace(MS.v("Ea_ASSUMED_RANGE")[0],
                          MS.v("Ea_ASSUMED_RANGE")[1], 16)
    ridge = []
    for Ea in Ea_grid:
        A = k_need["n=1"] * np.exp(Ea * 1000.0 / (R * T))
        ridge.append({"Ea_kJ_mol": float(Ea), "A_per_s": float(A),
                      "log10_A": float(np.log10(A))})
    out["kinetics"] = {
        "t_hold_s": t_s, "T_py_K": T, "R": R, "alpha_target": alpha,
        "kt_required": {k: float(v) for k, v in kt.items()},
        "k_required_per_s": k_need,
        "n_order_confounding": float(kt["n=2"] / kt["n=1"]),
        "ridge_n1": ridge,
        "identifiable": "k(T)·t",
        "not_identifiable": ["A", "Ea"],
        "why": ("等温终点只有一组 (T,t)；任意 (A,Ea) 只要使 k(T)t 不变就同样拟合数据，"
                "故 A 与 Ea 沿脊线不可分。要分开须第二温度或非等温序列。"),
    }
    return out


# ---------------------------------------------------------------- Q5
def q5(ai: dict) -> dict:
    out = {"meta": {
        "question": "Q5 在指定掺比网格上预测四产物产率",
        "caliber": {
            "grid": "自设网格，全部落在观测区间内 → 内插，不是外推",
            "interval": "5% 输入噪声蒙特卡洛 + 拟合残差，取 5%/95% 分位",
            "closure": "预测经 ILR 反变换，四产物行和恒等于 100（构造性闭合）",
        },
        "grid_r": MS.v("grid_pred_ASSUMED"),
        "grid_w": _f(M.w_of_r(MS.v("grid_pred_ASSUMED"))),
        "n_mc": N_MC, "seed": RNG_SEED,
    }, "combos": {}}

    rng = np.random.default_rng(RNG_SEED + 1)
    for combo in COMBOS:
        d = ai[combo]
        w, S = d["w"], np.column_stack([d["series"][p] for p in PROD]) / 100.0
        V = ilr(S)
        X = design(w)
        B, rss = NL.lstsq(X, V)
        Rm = V - np.einsum("nk,km->nm", X, B)
        dof = max(V.size - int(B.size), 1)
        sig = float(np.sqrt(rss / dof))

        wg = M.w_of_r(np.array(MS.v("grid_pred_ASSUMED")))
        Xg = design(wg)
        Vg = np.einsum("nk,km->nm", Xg, B)
        point = ilr_inv(Vg) * 100.0

        extra = sig * np.sqrt(1.0 + 1.0 / len(w))
        draws = np.zeros((N_MC, len(wg), 3))
        for i in range(N_MC):
            draws[i] = Vg + rng.normal(0, sig, size=Vg.shape) \
                + rng.normal(0, extra, size=Vg.shape)
        Sg = ilr_inv(draws.reshape(-1, 3)).reshape(N_MC, len(wg), 4) * 100.0

        loo = np.zeros((len(w), 4))
        for i in range(len(w)):
            m = np.ones(len(w), bool)
            m[i] = False
            Bi, _ = NL.lstsq(X[m], V[m])
            loo[i] = ilr_inv(np.einsum("nk,km->nm", X[i:i + 1], Bi))[0] * 100.0
        obs = S * 100.0
        rmse = np.sqrt(((loo - obs) ** 2).mean(axis=0))

        out["combos"][SHORT[combo]] = {
            "labels": d["labels"], "w": _f(w),
            "point": {p: _f(point[:, i]) for i, p in enumerate(PROD)},
            "lo": {p: _f(np.percentile(Sg[:, :, i], 5, axis=0)) for i, p in enumerate(PROD)},
            "hi": {p: _f(np.percentile(Sg[:, :, i], 95, axis=0)) for i, p in enumerate(PROD)},
            "row_sum_point": _f(point.sum(axis=1)),
            "loo_rmse": {p: float(rmse[i]) for i, p in enumerate(PROD)},
            "loo_rmse_rel": {p: float(rmse[i] / obs[:, i].mean()) for i, p in enumerate(PROD)},
            "sigma_ilr": sig,
            "is_extrapolation": bool(np.any(wg > w.max() + 1e-12)
                                     or np.any(wg < w.min() - 1e-12)),
        }
    return out


# ---------------------------------------------------------------- main
def main() -> int:
    st = M.selftest(verbose=True)
    ai = M.load_annex_i()
    aii = M.load_annex_ii()

    r1, r2, r3 = q1(ai), q2(aii, ai), q3(ai, aii)
    r4, r5 = q4(ai, aii, r1), q5(ai)

    paths = [dump(f"results_q{i}.json", o)
             for i, o in enumerate((r1, r2, r3, r4, r5), 1)]

    print("\n=== 关键读数（口径逐条标注）")
    for cs in ("CS", "CE", "LG"):
        p = r1["combos"][cs]["products"]
        print(f"[Q1 {cs}] Tar {p['Tar']['first']:.2f}→{p['Tar']['last']:.2f} "
              f"Δ{p['Tar']['delta_end']:+.2f} ({p['Tar']['delta_end_pct']:+.1f}%) "
              f"span/thr={p['Tar']['span_over_thr']:.2f} 显著={p['Tar']['trend_significant']}")
        print(f"[Q1 {cs}] Char Δ{p['Char']['delta_end']:+.2f} "
              f"span/thr={p['Char']['span_over_thr']:.2f} 显著={p['Char']['trend_significant']}"
              f"{DERIVED_MARK if p['Char']['is_derived'] else ''}")
        il = r1["combos"][cs]["ilr"]
        print(f"[Q1 {cs}] ILR σ_fit={il['sigma_fit']:.4f} σ_noise={il['sigma_noise_mc']:.4f} "
              f"F={il['lack_of_fit_F']:.2f} R²={[round(v,3) for v in il['R2_each']]} "
              f"best={r1['combos'][cs]['aic_best']}")
    print(f"[Q2] CS 主量级 {r2['tiers']['CS']['major']}")
    print(f"[Q2] CS 次量级 {r2['tiers']['CS']['minor']}")
    print(f"[Q2] CS 行和 {min(r2['combos']['CS']['row_sum']):.2f}"
          f"–{max(r2['combos']['CS']['row_sum']):.2f}（≠100，只作相对组成）")
    print(f"[Q2] CS beta_bridge {[round(v,3) for v in r2['bridge']['CS']['beta_bridge']]}")
    print(f"[Q3] 产物 {len(r3['levels_products'])} 对 / 气体 {len(r3['levels_gases'])} 对")
    for k in ("Tar", "Char", "Water"):
        v = r3["products"][k]
        print(f"[Q3] {k} Δ={v['Delta'][0]:+.2f}…{v['Delta'][-1]:+.2f} "
              f"超噪 {v['n_exceed']}/{v['n']} 翻转 {v['sign_changes']}")
    print(f"[Q3] 翻转清单：产物 {r3['flips']['products']} 气体 {r3['flips']['gases']}")
    print(f"[Q4] 级数混淆 n=2/n=1 = {r4['kinetics']['n_order_confounding']:.2f}×")
    rg = r4["kinetics"]["ridge_n1"]
    print(f"[Q4] 脊线 Ea {rg[0]['Ea_kJ_mol']:.0f}→{rg[-1]['Ea_kJ_mol']:.0f} kJ/mol "
          f"⇒ log10A {rg[0]['log10_A']:.2f}→{rg[-1]['log10_A']:.2f}")
    for cs in ("CS", "CE", "LG"):
        g = r4["selectivity"][cs]["gamma_centered"]
        print(f"[Q4 {cs}] gamma {({k: round(v,3) for k, v in g.items()})} "
              f"Σ={r4['selectivity'][cs]['sum_gamma']:+.2e}")
        cb = r4["carbon_balance"][cs]
        print(f"[Q4 {cs}] 气相碳 {cb['carbon_mmol_per_g'][0]:.2f}→"
              f"{cb['carbon_mmol_per_g'][-1]:.2f} mmol/g ({cb['delta_end_pct']:+.1f}%)")
    for cs in ("CS", "CE", "LG"):
        q = r5["combos"][cs]
        print(f"[Q5 {cs}] 外推={q['is_extrapolation']} σ_ILR={q['sigma_ilr']:.4f} "
              f"LOO相对RMSE={ {k: round(v,4) for k, v in q['loo_rmse_rel'].items()} }")
        print(f"[Q5 {cs}] 行和 {min(q['row_sum_point']):.8f}–{max(q['row_sum_point']):.8f}")

    print("\n=== 落盘")
    for p in paths:
        print(f"  {p.name}  {p.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
