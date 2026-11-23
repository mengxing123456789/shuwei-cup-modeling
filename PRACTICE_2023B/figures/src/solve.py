#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PRACTICE_2023B \u00b7 s2 \u6c42\u89e3\u9aa8\u67b6\uff1aQ1\u2013Q5 \u5168\u90e8\u8d70\u901a\uff0c\u843d data/results_q*.json\u3002

\u8bbe\u8ba1\u539f\u5219\uff08\u5bf9\u5e94\u6d3e\u5355\u300c\u56db\u6761\u786c\u7ecf\u9a8c\u300d\uff09
--------------------------------
\u2460 \u6bcf\u4e2a\u6570\u5b57\u6807\u53e3\u5f84\u3002\u51e1\u300c\u663e\u8457\u300d\u300c\u9608\u503c\u300d\u90fd\u5e26\u8def\u5f84\u952e\uff0c\u4e09\u6761\u8def\u5f84**\u4e0d\u5171\u7528\u540c\u4e00\u4e2a\u8bcd**\uff1a
     path="single" \u2192 0.10\u00b7y            \u4e00\u6b21\u6d4b\u91cf vs \u5df2\u77e5\u771f\u503c
     path="diff"   \u2192 0.10\u00b7\u221a(ya\u00b2+yb\u00b2)   \u4e24\u4e2a\u72ec\u7acb\u6d4b\u91cf\u4e4b\u5dee
     path="trend"  \u2192 0.10\u00b7mean(y)      \u6574\u6bb5\u8de8\u5ea6 vs \u566a\u58f0\u5730\u677f
\u2461 \u4e0d\u5199\u81ea\u6307\u6570\u5b57\uff08\u300c\u672c\u6587 N \u4e2a\u300d\uff09\uff1b\u53ea\u5199\u4ece\u6570\u636e\u7b97\u51fa\u6765\u7684\u91cf\u3002
\u2462 \u5951\u7ea6\u5168\u90e8 import \u81ea model_skeleton.CONTRACT\uff0c\u4e0d\u5728\u6b64\u91cd\u590d\u786c\u7f16\u7801\u3002
\u2463 \u5e38\u6570\u53ea\u4ece MS.PARAMS \u53d6\u3002

\u73af\u5883\u7ea6\u675f\uff08\u786c\uff09
--------------
\u672c\u673a numpy \u7684 BLAS/LAPACK \u4e00\u78b0\u5c31\u6574\u8fdb\u7a0b\u5d29\uff080xc06d007f\uff09\u3002\u672c\u6587\u4ef6**\u7981\u7528**
`@` / `np.dot` / `np.linalg.*` / `np.polyfit`\uff0c\u7ebf\u6027\u4ee3\u6570\u4e00\u5f8b\u8d70 code/numlib.py
\uff08einsum \u7ec4\u6b63\u89c4\u65b9\u7a0b + \u7eaf Python \u9ad8\u65af\u6d88\u5143\uff09\u3002\u590d\u7b97\uff1apython code\\_probe_one.py matmul

\u5173\u952e\u5efa\u6a21\u5224\u65ad\uff08\u6b63\u6587\u8981\u5f15\u7528\u7684\u4e09\u6761\uff09
--------------------------------
(a) \u56db\u4ea7\u7269\u53ea\u6709**\u4e09\u4e2a\u81ea\u7531\u5ea6**\uff1aAnnex I \u6bcf\u5f20\u5b50\u8868\u6709\u4e00\u6574\u884c\u662f `=100-...` \u516c\u5f0f\uff0c
    \u4e14\u4e09\u8868\u63a8\u7684\u662f**\u4e0d\u540c**\u4ea7\u7269\uff08CS\u2192Syngas\u3001CE\u2192Char\u3001LG\u2192Tar\uff09\u3002\u6240\u4ee5
    \u300c\u56db\u4ea7\u7269\u5404\u81ea\u72ec\u7acb\u56de\u5f52\u300d\u662f\u9519\u7684\uff08\u6d3e\u751f\u5217 R\u00b2 \u5fc5\u7136\u865a\u9ad8\uff09\uff0c\u4e00\u5f8b\u5728 3 \u7ef4 ILR
    \u6b63\u4ea4\u5bf9\u6570\u6bd4\u5750\u6807\u91cc\u62df\u5408\uff0c\u518d\u53cd\u53d8\u6362\u56de\u6210\u5206\u3002
(b) \u7b49\u6e29\u7ec8\u70b9\u6570\u636e\u53ea\u80fd\u8fa8\u8bc6\u4e58\u79ef k(T)\u00b7t\uff0c\u4e0d\u80fd\u5206\u5f00\u8fa8\u8bc6 A \u4e0e Ea\u3002
    Q4 \u62a5**\u810a\u7ebf**\uff08\u6bcf\u4e2a Ea \u5bf9\u5e94\u7684 A\uff09\uff0c\u4e0d\u62a5\u70b9\u4f30\u8ba1\u3002
(c) \u6bcf\u7ec4\u5408\u53ea\u6709 5\u20139 \u4e2a\u6863\u4f4d\u4e14\u65e0\u91cd\u590d\u5b9e\u9a8c \u2192 \u300c\u00b110% \u6270\u52a8\u91cd\u7b97\u300d\u7b49\u4e8e\u51ed\u7a7a\u9020\u6570\u636e\u3002
    \u654f\u611f\u6027\u4e00\u5f8b\u7528 5% \u566a\u58f0\u8499\u7279\u5361\u6d1b + \u7559\u4e00\u4ea4\u53c9\u9a8c\u8bc1\u3002

\u8fd0\u884c\uff1apython code\\solve.py
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

# Windows \u63a7\u5236\u53f0\u9ed8\u8ba4 GBK\uff0c\u4f1a\u628a \u03c3 / \u0394 / \u00b2 \u6253\u6210\u5f02\u5e38\u5e76\u4e2d\u65ad\uff1b\u7edf\u4e00\u6539 UTF-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------- ILR \u57fa\uff08Helmert \u578b\uff0c\u884c\u6b63\u4ea4\u5f52\u4e00\uff09
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
    """\u6210\u5206 (n,4) \u2192 ILR \u5750\u6807 (n,3)\u3002\u7528 einsum\uff0c\u4e0d\u8d70 BLAS\u3002"""
    S = np.atleast_2d(np.asarray(S, dtype=float))
    lg = np.log(S)
    u = lg - lg.mean(axis=1, keepdims=True)
    return np.einsum("nk,jk->nj", u, V4)


def ilr_inv(v: np.ndarray) -> np.ndarray:
    """ILR \u5750\u6807 (n,3) \u2192 \u6210\u5206 (n,4)\uff0c\u884c\u548c = 1\u3002"""
    v = np.atleast_2d(np.asarray(v, dtype=float))
    u = np.einsum("nj,jk->nk", v, V4)
    e = np.exp(u)
    return e / e.sum(axis=1, keepdims=True)


def design(w) -> np.ndarray:
    return np.column_stack([np.ones_like(np.asarray(w, dtype=float)), w])


# ---------------------------------------------------------------- \u5224\u636e\uff08\u4e09\u6761\u8def\u5f84\uff0c\u4e92\u4e0d\u66ff\u4ee3\uff09
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
        "question": "Q1 DFA \u63ba\u6bd4\u5bf9\u56db\u4ea7\u7269\u4ea7\u7387\u7684\u5f71\u54cd\uff08\u5e45\u5ea6 / \u65b9\u5411 / \u662f\u5426\u8d85\u566a\uff09",
        "caliber": {
            "path_single": "0.10\u00b7y \u2014\u2014 \u4e00\u6b21\u6d4b\u91cf\u4e0e\u5df2\u77e5\u771f\u503c\u6bd4",
            "path_trend": "0.10\u00b7mean(y) \u2014\u2014 \u6574\u6bb5\u8de8\u5ea6\u4e0e\u566a\u58f0\u5730\u677f\u6bd4",
            "eps_rel": MS.v("eps_rel"),
            "note_derived": "Annex I \u6bcf\u8868\u6709\u4e00\u6574\u884c\u662f =100-... \u516c\u5f0f\uff0c\u8be5\u4ea7\u7269\u662f\u6d3e\u751f\u91cf\uff0c\u5176\u5355\u72ec R\u00b2 \u4e0d\u53ef\u4f5c\u8bc1\u636e",
        },
        "dof": "\u56db\u4ea7\u7269 \u03a3=100 \u2192 \u4ec5 3 \u4e2a\u81ea\u7531\u5ea6\uff1b\u62df\u5408\u5728 3 \u7ef4 ILR \u7a7a\u95f4\u8fdb\u884c",
        "linalg": "\u6b63\u89c4\u65b9\u7a0b + \u7eaf Python \u9ad8\u65af\u6d88\u5143\uff08BLAS \u7981\u7528\uff0c\u89c1 numlib\uff09",
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
            "basis": "Helmert \u6b63\u4ea4\u5bf9\u6bd4\uff0c\u884c\u6b63\u4ea4\u5f52\u4e00\u4e14\u884c\u548c\u4e3a 0",
            "coef_table": {f"v{j+1}": {"b0": float(B[0, j]), "b1": float(B[1, j])}
                           for j in range(3)},
            "R2_each": _f(r2_each),
            "rss": rss, "n_obs": n_obs, "k_par": k_par,
            "sigma_fit": sigma_fit, "sigma_noise_mc": sigma_noise,
            "lack_of_fit_F": F,
            "lack_of_fit_verdict": ("\u6b8b\u5dee\u5728 5% \u566a\u58f0\u53ef\u89e3\u91ca\u8303\u56f4\u5185" if F <= 1.0
                                    else "\u6b8b\u5dee\u8d85\u51fa 5% \u566a\u58f0\uff0c\u5b58\u5728\u7cfb\u7edf\u6027\u5931\u62df"),
            "n_mc": N_MC,
        }
        rec["aic"] = cand
        rec["aic_best"] = min(cand, key=cand.get)
        out["combos"][SHORT[combo]] = rec
    return out


# ---------------------------------------------------------------- Q2
def q2(aii: dict, ai: dict) -> dict:
    out = {"meta": {
        "question": "Q2 \u6c14\u4f53\u7ec4\u5206\u4ea7\u7387\u7684\u56fe\u65cf\u65b9\u6848\u4e0e\u9010\u7ec4\u5206\u68c0\u9a8c\u91cf",
        "caliber": {
            "path_single": "0.10\u00b7z \u2014\u2014 \u9010\u6863\u4e0e\u566a\u58f0\u5730\u677f\u6bd4",
            "path_trend": "0.10\u00b7mean(z) \u2014\u2014 \u6574\u6bb5\u8de8\u5ea6",
            "phi_denominator": "\u8be5\u884c \u03a3_g z_g\uff08\u4e0d\u662f 100\uff09",
            "annex2_rowsum": "Annex II \u884c\u548c 68.00\u2013153.25\uff0c\u4e0d\u7b49\u4e8e 100\uff0c\u4e5f\u4e0d\u7b49\u4e8e Annex I Syngas",
            "note": "\u6545 Annex II \u53ea\u4f5c\u76f8\u5bf9\u7ec4\u6210 \u03c6 \u4f7f\u7528\uff0c\u4e0d\u505a\u7edd\u5bf9\u8d28\u91cf\u95ed\u5408",
        },
        "tier_rule": "span \u2265 5 mL/g(daf) \u4e3a\u4e3b\u91cf\u7ea7\uff0c\u5426\u5219\u6b21\u91cf\u7ea7\uff08\u81ea\u8bbe\u9608\u503c\uff0c\u89c1 A7\uff09",
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
            "verdict": "\u4e24\u9644\u4ef6\u91cf\u7eb2\u4f53\u7cfb\u4e0d\u540c\uff08\u4f53\u79ef vs \u8d28\u91cf\uff09\uff0c\u6bd4\u503c\u4e0d\u7b49\u4e8e 1 \u5c5e\u9884\u671f\uff0c\u4e0d\u5f97\u5f53\u6570\u636e\u9519\u8bef",
        }
    return out


# ---------------------------------------------------------------- Q3
def q3(ai: dict, aii: dict) -> dict:
    out = {"meta": {
        "question": "Q3 \u7ea4\u7ef4\u7d20(CE) \u4e0e \u6728\u8d28\u7d20(LG) \u5728\u540c\u4e00\u63ba\u6bd4\u4e0b\u7684\u5dee\u5f02",
        "caliber": {
            "path_diff": "0.10\u00b7\u221a(y_CE\u00b2+y_LG\u00b2) \u2014\u2014 \u4e24\u4e2a\u72ec\u7acb\u6d4b\u91cf\u4e4b\u5dee\u7684\u5224\u636e",
            "levels_products": "Annex I \u7684 CE/LG \u5404\u6709 8 \u6863\uff0810\u2026100\uff09\uff0c\u9010\u6863\u53ef\u914d 8 \u5bf9",
            "levels_gases": "Annex II \u7684 CE/LG \u5404\u6709 5 \u6863\uff0820/40/50/80/100\uff09\uff0c\u53ea\u80fd\u914d 5 \u5bf9",
            "note": "\u4e24\u5904\u6863\u6570\u4e0d\u540c\uff0c\u4e0d\u5f97\u6df7\u7528\u4e00\u4e2a\u300c\u516c\u5171\u6863\u4f4d\u300d\u8bf4\u6cd5",
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

    # \u6c14\u4f53\u5757\u6ca1\u6709 sign_changes \u952e\uff0c\u7edf\u4e00\u6309\u300c\u65b9\u5411\u7ffb\u8f6c / \u5168\u7a0b\u4e0d\u8d85\u566a\u300d\u4e24\u6761\u5224\u636e
    for group, tbl in (("products", out["products"]), ("gases", out["gases"])):
        out["flips"][group] = [k for k, v in tbl.items()
                               if v.get("sign_changes", 0) > 0 or v["n_exceed"] == 0]
    return out


# ---------------------------------------------------------------- Q4
def q4(ai: dict, aii: dict, r1: dict) -> dict:
    out = {"meta": {
        "question": "Q4 \u63ba\u6bd4\u6539\u53d8\u4ea7\u7269\u5206\u5e03\u7684\u673a\u5236\u89e3\u91ca\u4e0e\u52a8\u529b\u5b66\u53ef\u8fa8\u8bc6\u6027",
        "caliber": {
            "gamma_definition": "gamma_p = d ln S_p / d w\uff0cS_p=y_p/100\uff0c\u4e2d\u5fc3\u5316\u540e \u03a3gamma=0",
            "identifiability": "\u7b49\u6e29\u7ec8\u70b9\u6570\u636e\u53ea\u8fa8\u8bc6 k(T)\u00b7t\uff1bA \u4e0e Ea \u4e0d\u80fd\u5206\u5f00\u8fa8\u8bc6\uff0c\u62a5\u810a\u7ebf\u4e0d\u62a5\u70b9",
            "alpha_target": "\u81ea\u8bbe\uff1a\u70ed\u89e3\u7ec8\u70b9\u8f6c\u5316\u7387\u53d6 0.95\uff08\u9898\u9762\u672a\u7ed9\u8f6c\u5316\u7387\uff09",
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
            "interpretation": ("gamma<0 \u8868\u793a\u8be5\u4ea7\u7269\u4efd\u989d\u968f\u63ba\u7070\u6309\u5e42\u5f8b\u4e0b\u964d\uff0c"
                               "gamma>0 \u8868\u793a\u4efd\u989d\u4e0a\u5347\uff1bgamma\u22480 \u8868\u793a\u51e0\u4e4e\u4e0d\u53c2\u4e0e"),
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
        "identifiable": "k(T)\u00b7t",
        "not_identifiable": ["A", "Ea"],
        "why": ("\u7b49\u6e29\u7ec8\u70b9\u53ea\u6709\u4e00\u7ec4 (T,t)\uff1b\u4efb\u610f (A,Ea) \u53ea\u8981\u4f7f k(T)t \u4e0d\u53d8\u5c31\u540c\u6837\u62df\u5408\u6570\u636e\uff0c"
                "\u6545 A \u4e0e Ea \u6cbf\u810a\u7ebf\u4e0d\u53ef\u5206\u3002\u8981\u5206\u5f00\u987b\u7b2c\u4e8c\u6e29\u5ea6\u6216\u975e\u7b49\u6e29\u5e8f\u5217\u3002"),
    }
    return out


# ---------------------------------------------------------------- Q5
def q5(ai: dict) -> dict:
    out = {"meta": {
        "question": "Q5 \u5728\u6307\u5b9a\u63ba\u6bd4\u7f51\u683c\u4e0a\u9884\u6d4b\u56db\u4ea7\u7269\u4ea7\u7387",
        "caliber": {
            "grid": "\u81ea\u8bbe\u7f51\u683c\uff0c\u5168\u90e8\u843d\u5728\u89c2\u6d4b\u533a\u95f4\u5185 \u2192 \u5185\u63d2\uff0c\u4e0d\u662f\u5916\u63a8",
            "interval": "5% \u8f93\u5165\u566a\u58f0\u8499\u7279\u5361\u6d1b + \u62df\u5408\u6b8b\u5dee\uff0c\u53d6 5%/95% \u5206\u4f4d",
            "closure": "\u9884\u6d4b\u7ecf ILR \u53cd\u53d8\u6362\uff0c\u56db\u4ea7\u7269\u884c\u548c\u6052\u7b49\u4e8e 100\uff08\u6784\u9020\u6027\u95ed\u5408\uff09",
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

    print("\n=== \u5173\u952e\u8bfb\u6570\uff08\u53e3\u5f84\u9010\u6761\u6807\u6ce8\uff09")
    for cs in ("CS", "CE", "LG"):
        p = r1["combos"][cs]["products"]
        print(f"[Q1 {cs}] Tar {p['Tar']['first']:.2f}\u2192{p['Tar']['last']:.2f} "
              f"\u0394{p['Tar']['delta_end']:+.2f} ({p['Tar']['delta_end_pct']:+.1f}%) "
              f"span/thr={p['Tar']['span_over_thr']:.2f} \u663e\u8457={p['Tar']['trend_significant']}")
        print(f"[Q1 {cs}] Char \u0394{p['Char']['delta_end']:+.2f} "
              f"span/thr={p['Char']['span_over_thr']:.2f} \u663e\u8457={p['Char']['trend_significant']}"
              f"{DERIVED_MARK if p['Char']['is_derived'] else ''}")
        il = r1["combos"][cs]["ilr"]
        print(f"[Q1 {cs}] ILR \u03c3_fit={il['sigma_fit']:.4f} \u03c3_noise={il['sigma_noise_mc']:.4f} "
              f"F={il['lack_of_fit_F']:.2f} R\u00b2={[round(v,3) for v in il['R2_each']]} "
              f"best={r1['combos'][cs]['aic_best']}")
    print(f"[Q2] CS \u4e3b\u91cf\u7ea7 {r2['tiers']['CS']['major']}")
    print(f"[Q2] CS \u6b21\u91cf\u7ea7 {r2['tiers']['CS']['minor']}")
    print(f"[Q2] CS \u884c\u548c {min(r2['combos']['CS']['row_sum']):.2f}"
          f"\u2013{max(r2['combos']['CS']['row_sum']):.2f}\uff08\u2260100\uff0c\u53ea\u4f5c\u76f8\u5bf9\u7ec4\u6210\uff09")
    print(f"[Q2] CS beta_bridge {[round(v,3) for v in r2['bridge']['CS']['beta_bridge']]}")
    print(f"[Q3] \u4ea7\u7269 {len(r3['levels_products'])} \u5bf9 / \u6c14\u4f53 {len(r3['levels_gases'])} \u5bf9")
    for k in ("Tar", "Char", "Water"):
        v = r3["products"][k]
        print(f"[Q3] {k} \u0394={v['Delta'][0]:+.2f}\u2026{v['Delta'][-1]:+.2f} "
              f"\u8d85\u566a {v['n_exceed']}/{v['n']} \u7ffb\u8f6c {v['sign_changes']}")
    print(f"[Q3] \u7ffb\u8f6c\u6e05\u5355\uff1a\u4ea7\u7269 {r3['flips']['products']} \u6c14\u4f53 {r3['flips']['gases']}")
    print(f"[Q4] \u7ea7\u6570\u6df7\u6dc6 n=2/n=1 = {r4['kinetics']['n_order_confounding']:.2f}\u00d7")
    rg = r4["kinetics"]["ridge_n1"]
    print(f"[Q4] \u810a\u7ebf Ea {rg[0]['Ea_kJ_mol']:.0f}\u2192{rg[-1]['Ea_kJ_mol']:.0f} kJ/mol "
          f"\u21d2 log10A {rg[0]['log10_A']:.2f}\u2192{rg[-1]['log10_A']:.2f}")
    for cs in ("CS", "CE", "LG"):
        g = r4["selectivity"][cs]["gamma_centered"]
        print(f"[Q4 {cs}] gamma {({k: round(v,3) for k, v in g.items()})} "
              f"\u03a3={r4['selectivity'][cs]['sum_gamma']:+.2e}")
        cb = r4["carbon_balance"][cs]
        print(f"[Q4 {cs}] \u6c14\u76f8\u78b3 {cb['carbon_mmol_per_g'][0]:.2f}\u2192"
              f"{cb['carbon_mmol_per_g'][-1]:.2f} mmol/g ({cb['delta_end_pct']:+.1f}%)")
    for cs in ("CS", "CE", "LG"):
        q = r5["combos"][cs]
        print(f"[Q5 {cs}] \u5916\u63a8={q['is_extrapolation']} \u03c3_ILR={q['sigma_ilr']:.4f} "
              f"LOO\u76f8\u5bf9RMSE={ {k: round(v,4) for k, v in q['loo_rmse_rel'].items()} }")
        print(f"[Q5 {cs}] \u884c\u548c {min(q['row_sum_point']):.8f}\u2013{max(q['row_sum_point']):.8f}")

    print("\n=== \u843d\u76d8")
    for p in paths:
        print(f"  {p.name}  {p.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
