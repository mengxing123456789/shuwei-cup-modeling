# -*- coding: utf-8 -*-
"""s3 \u6c42\u89e3\u4ea4\u4ed8\u9a71\u52a8\uff1a\u8ba1\u65f6 / \u7ea6\u675f\u7ed1\u5b9a / \u8fb9\u754c\u89e3 / \u00b110% \u6270\u52a8\u3002

\u672c\u6587\u4ef6\u662f s3 \u68d2\u6b21\u65b0\u589e\u7684**\u53ea\u8bfb\u9a71\u52a8**\uff1a\u4e0d\u4fee\u6539 solve.py / model_skeleton.py / numlib.py\uff0c
\u53ea\u8c03\u7528\u5b83\u4eec\u5e76\u628a\u56db\u7c7b\u8bc1\u636e\u843d\u76d8\u5230 data/results_*.json\u3002

\u590d\u7b97\uff1a  python code\\s3_deliver.py
\u7ea6\u675f\uff1a  \u5168\u7a0b\u7981\u7528 BLAS\uff08A@B / np.dot / np.linalg.*\uff09\uff0c\u7ebf\u6027\u4ee3\u6570\u53ea\u8d70 numlib\u3002
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

REPS = 5                            # \u8ba1\u65f6\u91cd\u590d\u6b21\u6570\uff08\u53d6\u4e2d\u4f4d\uff09
SIGNS = (+1, -1)
DELTA = 0.10                        # \u00b110%
# \u653e\u5bbd\u540e\u7684\u67e5\u8be2\u7f51\u683c\uff1a\u542b\u8bbe\u8ba1\u8fb9\u754c r=0.10 / 1.00 \u4e0e\u4e09\u6863\u5916\u63a8
GRID_WIDE = [0.10, 0.15, 0.25, 0.35, 0.45, 0.55, 0.70, 0.90,
             1.00, 1.20, 1.50, 2.00, 3.00]
COMBO3 = ("CS", "CE", "LG")
SOLVE_SRC = (CODE / "solve.py").read_text(encoding="utf-8")


# ------------------------------------------------------------------ \u57fa\u7840\u8bbe\u65bd
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
    r4 = S.q4(ai, aii, None)          # q4 \u7b7e\u540d\u7b2c\u4e09\u53c2 r1 \u672a\u88ab\u8bfb\u53d6
    r5 = S.q5(ai)
    return r1, r2, r3, r4, r5


# ------------------------------------------------------------------ \u5934\u6761\u7ed3\u8bba
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


# ------------------------------------------------------------------ 1 \u8ba1\u65f6
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
        fn()                                      # \u6bcf\u4e2a call \u5404\u4e00\u6b21 warmup
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
            "warmup": "\u6bcf\u4e2a call \u5148\u8dd1 1 \u6b21\u4e0d\u8ba1\u5165",
            "unit": "ms",
            "median_rule": "\u6392\u5e8f\u540e\u53d6 runs[len//2]\uff08\u5947\u6570\u6837\u672c\u771f\u4e2d\u4f4d\uff09",
            "serial": True,
            "note": ("BLAS \u88ab\u7981\uff08\u89c1 numlib\uff09\uff0c\u6545 numpy \u4e0d\u5e76\u884c\uff1b\u5355\u6b21\u6d4b\u91cf\u566a\u58f0\u672c\u673a\u5b9e\u6d4b\u53ef\u5230 \u00b156%\uff0c"
                     "\u6545\u62a5\u4e2d\u4f4d\u4e0d\u62a5\u5355\u6b21"),
            "interpreter": sys.version.split()[0],
            "numpy": np.__version__,
        },
        "calls": calls,
    }


# ------------------------------------------------------------------ 2 \u7ea6\u675f\u7ed1\u5b9a
def leverage(w):
    w = np.asarray(w, dtype=float)
    n = len(w)
    wb = float(w.mean())
    sxx = float(((w - wb) ** 2).sum())
    return [float(1.0 / n + (wi - wb) ** 2 / sxx) for wi in w], n, wb, sxx


def part_binding(ai, aii, r1, r2, r3, r4):
    src = []

    # B1 C1 \u56db\u4ea7\u7269\u95ed\u5408\uff08Annex I\uff09
    st = M.selftest(verbose=False)
    src.append({
        "id": "C1", "from": "Annex I \u6bcf\u5217\u56db\u4ea7\u7269\u4e4b\u548c",
        "statement": "\u03a3_p S_p = 1\uff08\u56db\u4ea7\u7269\u95ed\u5408\uff09",
        "binding": "active",
        "measure": {"max_abs_sum_minus_100": float(st["max_abs_sum_minus_100"]),
                    "n_columns": int(st["n_cols_annex_i"]),
                    "dof_before": 4, "dof_after": 3},
        "effect": "\u7b49\u5f0f\u5728\u673a\u5668\u7cbe\u5ea6\u5185\u6210\u7acb\uff081.42e-14\uff09\uff0c\u628a\u56db\u4ea7\u7269\u4ece 4 \u7ef4\u538b\u5230 3 \u7ef4\uff1b"
                  "\u4efb\u4f55\u5355\u4ea7\u7269 R\u00b2 \u90fd\u4e0d\u80fd\u5355\u72ec\u4f5c\u4e3a\u8bc1\u636e\u3002",
    })

    # B2 C2 ILR \u53c2\u6570\u5316
    src.append({
        "id": "C2", "from": "\u81ea\u8bbe\uff08\u6210\u5206\u6570\u636e\u6807\u51c6\u53c2\u6570\u5316\uff09",
        "statement": "\u62df\u5408\u5728 v = ilr(S) \u2208 R^3 \u8fdb\u884c\uff0c\u4e0d\u76f4\u63a5\u62df\u5408 S",
        "binding": "active",
        "measure": {cs: {"n_obs": int(r1["combos"][cs]["ilr"]["n_obs"]),
                         "k_par": int(r1["combos"][cs]["ilr"]["k_par"]),
                         "df": int(r1["combos"][cs]["ilr"]["n_obs"])
                               - int(r1["combos"][cs]["ilr"]["k_par"])}
                    for cs in COMBO3},
        "effect": "\u81ea\u7531\u5ea6 3\u00d7n \u800c\u975e 4\u00d7n\uff1bdf = 21/18/18 \u662f\u540e\u9762 F \u68c0\u9a8c\u4e0e\u5931\u62df\u5224\u5b9a\u7684\u5206\u6bcd\u3002",
    })

    # B3 C3 \u63ba\u6bd4\u7f51\u683c\uff1a\u7aef\u70b9\u6760\u6746
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
        "id": "C3", "from": "\u9898\u9762 L74\u2013L75\uff08\u516b\u6863\u63ba\u6bd4\uff0c\u4e0d\u7b49\u8ddd\uff09",
        "statement": "r \u53ea\u80fd\u53d6 0.1\u20261.0 \u516b\u4e2a\u89c2\u6d4b\u6863\uff08CS \u53e6\u6709 r=0\uff09",
        "binding": "active-at-endpoints",
        "measure": lev,
        "effect": ("\u4e24\u7aef\u70b9\u6760\u6746\u6700\u9ad8\uff1aCS \u9996\u70b9 h=%.4f\u3001\u672b\u70b9 h=%.4f\uff0c\u4e2d\u70b9\u6700\u4f4e h=%.4f\u3002"
                   "\u89e3\u5bf9 w=0 \u4e0e w=0.5 \u4e24\u7aef\u7684\u89c2\u6d4b\u6700\u654f\u611f\uff0c\u4e2d\u95f4\u6863\u51e0\u4e4e\u4e0d\u7ea6\u675f\u659c\u7387\u3002"
                   % (lev["CS"]["h_at_first"], lev["CS"]["h_at_last"], lev["CS"]["h_min"])),
    })

    # B4 C4 \u53cd\u4f8b\u6863\u7981\u7528
    labs = set()
    for d in list(ai.values()) + list(aii.values()):
        labs |= set(d["labels"])
    bad = [l for l in ("5/100", "7/100") if l in labs]
    src.append({
        "id": "C4", "from": "\u9898\u9762 L78\uff085/100\u30017/100 \u4e3a\u53cd\u4f8b\uff09",
        "statement": "r=0.05 \u4e0e r=0.07 \u4e0d\u5f97\u4f5c\u5b9e\u9a8c\u70b9",
        "binding": "vacuous",
        "measure": {"forbidden_labels_present_in_annex": bad,
                    "n_rows_removed": 0, "all_labels": sorted(labs)},
        "effect": "\u9644\u4ef6\u91cc\u6839\u672c\u4e0d\u5b58\u5728\u8fd9\u4e24\u6863 \u2192 \u8be5\u7ea6\u675f\u6ca1\u6709\u5220\u6389\u4efb\u4f55\u4e00\u884c\u89c2\u6d4b\uff0c\u5c5e\u7a7a\u7ea6\u675f\uff1b"
                  "\u5b83\u53ea\u7981\u6b62\u628a r=0.05/0.07 \u5199\u8fdb Q5 \u7f51\u683c\u3002",
    })

    # B5 C5 \u8de8\u9644\u4ef6\u53ea\u5bf9\u9f50\u4ea4\u96c6
    bridge = {cs: {"n_levels_used": len(r2["bridge"][cs]["labels"]),
                   "labels": r2["bridge"][cs]["labels"],
                   "n_levels_annex1": len(ai[{"CS": "DFA/CS", "CE": "DFA/CE",
                                              "LG": "DFA/LG"}[cs]]["labels"]),
                   "n_levels_annex2": len(aii[{"CS": "DFA/CS", "CE": "DFA/CE",
                                               "LG": "DFA/LG"}[cs]]["labels"])}
              for cs in COMBO3}
    src.append({
        "id": "C5", "from": "Annex I \u4e0e Annex II \u6863\u4f4d\u4e0d\u540c",
        "statement": "\u8de8\u9644\u4ef6\u53ea\u5bf9\u9f50 {20,40,50,80,100}\uff08CS \u53e6\u6709 0/100\uff09",
        "binding": "active",
        "measure": bridge,
        "effect": ("CS \u4e22\u6389 10/100\u300130/100\u300160/100 \u4e09\u6863\u624d\u4e0e Annex II \u5bf9\u9f50\uff1bCE/LG \u516b\u6863\u5168\u4e22\u4e09\u6863\u3002"
                   "beta_bridge \u53ea\u5728\u4ea4\u96c6\u4e0a\u5b9a\u4e49\uff0c\u4e0d\u80fd\u5f53\u5168\u57df\u8d28\u91cf\u95ed\u5408\u3002"),
    })

    # B6 C6 CE/LG \u65e0\u96f6\u57fa\u7ebf
    cs_d = r1["combos"]["CS"]["products"]["Tar"]
    y0 = cs_d["y"][0]
    y1 = cs_d["y"][1]
    src.append({
        "id": "C6", "from": "Annex I\uff08CE/LG \u65e0 0/100 \u884c\uff09",
        "statement": "CE/LG \u6ca1\u6709\u7eaf\u751f\u7269\u8d28\u57fa\u7ebf\uff0c\u767e\u5206\u6bd4\u53ea\u80fd\u76f8\u5bf9 10/100 \u6863",
        "binding": "active-on-interpretation",
        "measure": {"CS_Tar_pct_vs_0/100": float(cs_d["delta_end_pct"]),
                    "CS_Tar_pct_vs_10/100": float(100.0 * (cs_d["y"][-1] - y1) / y1),
                    "CE_Tar_pct_vs_10/100": float(r1["combos"]["CE"]["products"]["Tar"]["delta_end_pct"]),
                    "LG_Tar_pct_vs_10/100": float(r1["combos"]["LG"]["products"]["Tar"]["delta_end_pct"])},
        "effect": ("CS \u7684 Tar \u53d8\u5316\u53ef\u62a5\u4e24\u4e2a\u57fa\u51c6\uff08\u221237.7%% \u5bf9\u7eaf\u68c9\u79c6 / %.1f%% \u5bf9 10/100\uff09\uff0c"
                   "CE \u7684 +31.6%% \u4e0e LG \u7684 \u221254.7%% \u53ea\u6709 10/100 \u8fd9\u4e00\u4e2a\u57fa\u51c6\u3002"
                   "\u4e09\u7ec4\u5408\u7684\u767e\u5206\u6570\u56e0\u6b64\u4e0d\u53ef\u6a2a\u5411\u6bd4\u8f83\u3002"
                   % float(100.0 * (cs_d["y"][-1] - y1) / y1)),
    })

    # B7 A7 \u91cf\u7ea7\u9608\u503c 5.0\uff1a\u53ef\u884c\u5e26
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
        "id": "A7", "from": "\u81ea\u8bbe\uff0801-model.md L112\u2013L121 C3/A7\uff09",
        "statement": "span \u2265 5 mL/g(daf) \u5224\u4e3b\u91cf\u7ea7",
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
        "effect": ("\u5168\u90e8\u5206\u680f\u4e0d\u53d8\u7684\u9608\u503c\u533a\u95f4\u662f (%.2f, %.2f]\uff1b\u58f0\u660e\u503c 5.0 \u8ddd\u4e0a\u8fb9\u754c\u53ea\u5269 %.1f%%\uff0c"
                   "\u6240\u4ee5 CS \u7684 CO\uff085.40\uff09\u4e0e LG \u7684 CO\uff085.71\uff09\u662f\u8d34\u7ebf\u89e3\uff1a\u9608\u503c\u62ac\u5230 5.5 \u5c31\u628a CS CO \u6253\u56de\u6b21\u91cf\u7ea7\u3002"
                   "\u53e6\u6709 %d \u4e2a\u683c\u5b50\u5728\u6b21\u91cf\u7ea7\u91cc\u5374\u6709 span_over_thr>5\uff08\u5982 CE \u7684 CH4\uff0c2.50 \u5224\u6b21\u91cf\u7ea7\u4f46\u6bd4\u503c 14.88\uff09\uff0c"
                   "\u8bf4\u660e\u300c\u5206\u680f\u300d\u4e0e\u300c\u662f\u5426\u8c08\u8d8b\u52bf\u300d\u662f\u4e24\u5957\u5224\u636e\uff0c\u4e0d\u80fd\u4e92\u76f8\u4ee3\u8bc1\u3002"
                   % (lo, hi, 100.0 * (hi - 5.0) / 5.0,
                      len([s for s in spans if s[3] == "minor" and s[4] > 5.0]))),
    })

    # B8 T_py \u81ea\u8bbe\uff1a\u53ea\u7ed1 A\uff0c\u4e0d\u7ed1 k
    kin = r4["kinetics"]
    T = kin["T_py_K"]
    Rg = kin["R"]
    shifts = []
    for Ea in (100.0, 250.0):
        d = (Ea * 1000.0 / (Rg * math.log(10.0))) * (1.0 / (0.9 * T) - 1.0 / T)
        shifts.append({"Ea_kJ_mol": Ea, "dlog10A_for_T_minus10pct": round(d, 4)})
    src.append({
        "id": "T_py", "from": "\u81ea\u8bbe\uff08\u9898\u9762 L145\u2013L146 \u53ea\u8bf4\u540c\u4e00\u6e29\u5ea6\uff0c\u672a\u7ed9\u6570\u503c\uff09",
        "statement": "T_py = 800 K",
        "binding": "active-on-A-only",
        "measure": {"k_required_per_s": kin["k_required_per_s"],
                    "k_required_independent_of_T": True,
                    "dlog10A_when_T_10pct_lower": shifts},
        "effect": ("k(T)\u00b7t \u53ea\u7531 \u03b1 \u4e0e t \u5b9a\uff08k_need = kt/t_s\uff0c\u516c\u5f0f\u91cc\u6ca1\u6709 T\uff09\uff0c"
                   "T \u53ea\u8fdb\u5165\u810a\u7ebf\u7684 A\u3002\u6545 T_py \u7684\u81ea\u8bbe\u8bef\u5dee\u4e0d\u6c61\u67d3 k\uff0c\u53ea\u5e73\u79fb log10A\uff1a"
                   "T \u964d 10%% \u65f6 Ea=100 \u7684 log10A \u6389 %.3f\u3002"
                   % abs(shifts[0]["dlog10A_for_T_minus10pct"])),
    })

    # B9 eps_rel \u5224\u636e\uff1a\u53ef\u884c\u5e26
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
        "id": "eps_rel", "from": "\u9898\u9762 L77\uff08\u5e73\u884c\u5b9e\u9a8c\u76f8\u5bf9\u8bef\u5dee \u22485%\uff09",
        "statement": "\u4e09\u6761\u9608\u503c\u8def\u5f84\u5171\u7528 eps_rel = 0.05",
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
        "effect": ("\u6bd4\u503c\u4e0e eps_rel \u6210\u53cd\u6bd4\uff0c\u6545\u6bcf\u4e2a\u683c\u5b50\u6709\u4e00\u4e2a\u7ffb\u8f6c\u70b9 eps* = 0.05\u00b7ratio\u3002"
                   "\u5168\u90e8\u663e\u8457\u6027\u5224\u5b9a\u4e0d\u53d8\u7684\u533a\u95f4\u662f (%.4f, %.4f)\uff0c\u5bbd\u5ea6\u53ea\u5360\u58f0\u660e\u503c\u7684 %.1f%%\u3002"
                   "\u5224\u636e\u5728 5%% \u5904\u4e0d\u662f\u300c\u5bbd\u677e\u300d\u800c\u662f\u300c\u521a\u597d\u300d\u3002" % (band_lo, band_hi,
                                                              100.0 * (band_hi - band_lo) / eps0)),
    })

    # B10 Annex II \u884c\u548c
    rs = {cs: [float(min(r2["combos"][cs]["row_sum"])),
               float(max(r2["combos"][cs]["row_sum"]))] for cs in COMBO3}
    bb = {cs: [float(min(r2["bridge"][cs]["beta_bridge"])),
               float(max(r2["bridge"][cs]["beta_bridge"]))] for cs in COMBO3}
    src.append({
        "id": "AnnexII", "from": "Annex II\uff08\u4f53\u79ef mL/g(daf)\uff0c\u884c\u548c \u2260 100\uff09",
        "statement": "Annex II \u53ea\u4f5c\u76f8\u5bf9\u7ec4\u6210 \u03c6\uff0c\u4e0d\u505a\u7edd\u5bf9\u8d28\u91cf\u95ed\u5408",
        "binding": "active",
        "measure": {"row_sum_range": rs, "beta_bridge_range": bb},
        "effect": ("\u884c\u548c\u843d\u5728 68.00\u2013153.25\uff0c\u65e2\u4e0d\u7b49\u4e8e 100 \u4e5f\u4e0d\u7b49\u4e8e Annex I \u7684 Syngas\uff1b"
                   "beta_bridge \u53ea\u6709 0.570\u20130.713\uff0c\u8bf4\u660e\u4e24\u9644\u4ef6\u91cf\u7eb2\u4e0d\u540c\u3002"
                   "\u628a Annex II \u5f53\u7edd\u5bf9\u4ea7\u7387\u4f1a\u7cfb\u7edf\u6027\u9ad8\u4f30\u6c14\u76f8\u3002"),
    })

    # B11 C8 \u65e0\u91cd\u590d\u5b9e\u9a8c \u2192 \u7981\u89e3\u6790\u5f0f\u654f\u611f\u6027
    src.append({
        "id": "C8", "from": "\u9644\u4ef6\uff08\u6bcf\u6863\u5355\u6b21\uff0c\u65e0\u5e73\u884c\u6837\uff09",
        "statement": "\u65e0\u91cd\u590d\u5b9e\u9a8c \u2192 \u4e0d\u5141\u8bb8\u300c\u00b110% \u6270\u52a8\u91cd\u89e3\u300d\u5192\u5145\u7edf\u8ba1\u654f\u611f\u6027",
        "binding": "active-as-prohibition",
        "measure": {"replicates_in_annex": 0,
                    "substitute": "5% \u8f93\u5165\u566a\u58f0 MC(4000) + \u7559\u4e00\u4ea4\u53c9\u9a8c\u8bc1 + \u53c2\u6570 \u00b110% \u771f\u8dd1"},
        "effect": ("\u672c\u68d2\u6309\u6b64\u7ea6\u675f\u628a\u654f\u611f\u6027\u62c6\u6210\u4e24\u4ef6\u72ec\u7acb\u7684\u4e8b\uff1a\u7edf\u8ba1\u4e0d\u786e\u5b9a\u6027\u8d70 MC \u4e0e LOO\uff08results_q5.json\uff09\uff0c"
                   "\u53c2\u6570\u9c81\u68d2\u6027\u8d70\u771f\u8dd1\u6270\u52a8\uff08results_perturb.json\uff09\uff0c\u4e24\u8005\u5206\u6bcd\u4e0d\u540c\u3001\u4e0d\u5408\u5e76\u3002"),
    })

    return {
        "meta": {
            "question": "\u7ea6\u675f\u5728\u89e3\u5904\u662f\u5426\u8d77\u4f5c\u7528\uff08\u9010\u6765\u6e90\uff09",
            "rule": "active=\u89e3\u843d\u5728\u8be5\u7ea6\u675f\u7684\u8fb9\u754c\u6216\u7b49\u5f0f\u4e0a\uff1bactive-at-endpoints=\u53ea\u5728\u8bbe\u8ba1\u7aef\u70b9\u8d77\u4f5c\u7528\uff1b"
                    "active-near-edge=\u58f0\u660e\u503c\u79bb\u7ffb\u8f6c\u70b9\u4e0d\u8db3 20%\uff1bvacuous=\u6ca1\u6709\u5220\u6389\u4efb\u4f55\u89c2\u6d4b",
            "note": "\u672c\u9898\u65e0\u4e0d\u7b49\u5f0f\u7ea6\u675f\u7ec4\uff0c\u6545\u4e0d\u5b58\u5728\u300c\u4e00\u4e2a True \u6982\u62ec\u5168\u90e8\u300d\u7684 binding \u6807\u91cf",
        },
        "sources": src,
    }


# ------------------------------------------------------------------ 3 \u8fb9\u754c\u89e3
def part_boundary(ai, r5_base):
    wmap = {cs: ai[{"CS": "DFA/CS", "CE": "DFA/CE", "LG": "DFA/LG"}[cs]]["w"]
            for cs in COMBO3}
    setp("grid_pred_ASSUMED", list(GRID_WIDE))
    try:
        r5w = S.q5(ai)
    finally:
        restore()
    out = {"meta": {
        "question": "\u89e3\u662f\u5426\u5728\u641c\u7d22\u7f51\u683c\u8fb9\u754c",
        "grid_declared_r": BASE["grid_pred_ASSUMED"],
        "grid_widened_r": GRID_WIDE,
        "star_rule": "\u2605 = \u67e5\u8be2\u70b9\u6070\u597d\u843d\u5728\u8be5\u7ec4\u5408\u89c2\u6d4b\u652f\u6491\u7684\u7aef\u70b9\uff08w=w_min \u6216 w=w_max\uff09\uff1b"
                     "\u2605\u2605 = \u67e5\u8be2\u70b9\u79bb\u5f00\u652f\u6491\uff0c\u5c5e\u5916\u63a8\uff0c\u503c\u4ec5\u4f9b\u53c2\u8003",
        "w_map": {cs: "w = r/(1+r)\uff0cr=1.00 \u2192 w=0.5 \u53ea\u662f 50 wt% \u63ba\u7070\uff0c\u4e0d\u662f\u7eaf\u8131\u786b\u7070"
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
                mark = "\u2605\u2605"
            elif abs(wq - wmax) < 1e-12 or abs(wq - wmin) < 1e-12:
                mark = "\u2605"
            else:
                mark = ""
            rows.append({"r": r, "w": round(wq, 6), "mark": mark,
                         "point": {p: round(float(q["point"][p][i]), 4)
                                   for p in q["point"]},
                         "lo": {p: round(float(q["lo"][p][i]), 4) for p in q["lo"]},
                         "hi": {p: round(float(q["hi"][p][i]), 4) for p in q["hi"]}})
        # \u4e0e\u58f0\u660e\u7f51\u683c\u91cd\u53e0\u5904\u5fc5\u987b\u9010\u4f4d\u4e00\u81f4
        cross = []
        for i, r in enumerate(BASE["grid_pred_ASSUMED"]):
            j = GRID_WIDE.index(r)
            for p in q["point"]:
                cross.append(abs(float(q["point"][p][j])
                                 - float(r5_base["combos"][cs]["point"][p][i])))
        out["combos"][cs] = {
            "w_min": round(wmin, 6), "w_max": round(wmax, 6),
            "n_boundary_star": sum(1 for x in rows if x["mark"] == "\u2605"),
            "n_extrapolation_star2": sum(1 for x in rows if x["mark"] == "\u2605\u2605"),
            "max_abs_diff_on_overlap": max(cross),
            "rows": rows,
        }
    return out


# ------------------------------------------------------------------ 4 \u00b110% \u6270\u52a8
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
    """\u6309 solve.py L392\u2013L404 \u7684\u540c\u4e00\u7b97\u5f0f\u91cd\u7b97\uff0c\u4ec5\u628a alpha \u6362\u6389\uff08q4 \u91cc alpha \u662f\u5b57\u9762\u91cf\uff09\u3002"""
    t_s = kin["t_hold_s"]
    R = kin["R"]
    T = kin["T_py_K"]
    if alpha >= 1.0:
        return {"ok": False, "why": "alpha>=1\uff1an=1 \u9700 ln(1-\u03b1)\u3001n=2 \u9700 1/(1-\u03b1)-1\uff0c\u5747\u65e0\u5b9a\u4e49"}
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
                    rec["mode"] = "recompute(q4 \u91cc alpha \u662f\u5b57\u9762\u91cf)"
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
                    rec["mode"] = "run(\u5206\u680f\u7531 span \u91cd\u5224)"
                elif name.startswith("grid_r"):
                    g = list(BASE["grid_pred_ASSUMED"])
                    i = int(name[-1])
                    g[i] = g[i] * f
                    setp("grid_pred_ASSUMED", g)
                    r1, r2, r3, r4, r5 = run_all(ai, aii)
                    rec["mode"] = "run(\u53ea\u79fb\u52a8\u67e5\u8be2\u70b9)"
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
                    reasons.append(f"{cs} \u9884\u6d4b\u70b9\u79bb\u5f00\u89c2\u6d4b\u652f\u6491\uff08\u5916\u63a8\uff09")
                if max(abs(x - 100.0) for x in r5["combos"][cs]["row_sum_point"]) > 1e-6:
                    reasons.append(f"{cs} \u9884\u6d4b\u884c\u548c\u504f\u79bb 100")
                for p, vals in r5["combos"][cs]["point"].items():
                    if any((not math.isfinite(v)) or v <= 0.0 for v in vals):
                        reasons.append(f"{cs}.{p} \u51fa\u73b0\u975e\u6b63\u6216\u975e\u6709\u9650\u7ec4\u6210")
            rec["feasible"] = (len(reasons) == 0)
            rec["infeasible_reason"] = "\uff1b".join(reasons) if reasons else None

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
            "question": "\u53c2\u6570 \u00b110% \u540e\u7ed3\u8bba\u662f\u5426\u7ffb\u8f6c",
            "n_attempted": n_all,
            "n_sources": len(SOURCES),
            "delta": DELTA,
            "signs": list(SIGNS),
            "denominator_rule": ("\u4e09\u7c7b\u5206\u5f00\u8bb0\uff1anever-read \u53c2\u6570\u4ece\u672a\u88ab solve.py \u8bfb\u53d6 \u2192 \u5206\u6bcd\u5254\u9664\uff1b"
                                 "query \u7c7b\u53ea\u79fb\u52a8\u67e5\u8be2\u70b9\u3001\u6a21\u578b\u4e0d\u53d8 \u2192 \u4e0d\u53c2\u4e0e\u300c\u7ed3\u8bba\u7ffb\u8f6c\u300d\u5206\u6bcd\uff1b"
                                 "model \u7c7b\u624d\u662f\u771f\u6270\u52a8\u3002\u4e0d\u53ef\u884c\u7684\u5355\u6b21\u5355\u5217\uff0c\u4e0d\u8fdb\u4efb\u4f55\u5206\u6bcd\u3002"),
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

    print("=== \u8ba1\u65f6\uff08median_ms\uff09")
    for c in t["calls"]:
        print(f"  {c['name']:<20} {c['median_ms']:>9.3f}  (min {c['min_ms']:.3f} "
              f"max {c['max_ms']:.3f} stdev {c['stdev_ms']:.3f})")
    print("=== \u7ea6\u675f\u7ed1\u5b9a\uff08\u9010\u6765\u6e90\uff09")
    for s in b["sources"]:
        print(f"  {s['id']:<10} {s['binding']}")
    print("=== \u8fb9\u754c\u89e3")
    for cs in COMBO3:
        c = bd["combos"][cs]
        print(f"  {cs} w\u2208[{c['w_min']},{c['w_max']}] \u2605{c['n_boundary_star']} "
              f"\u2605\u2605{c['n_extrapolation_star2']} \u91cd\u53e0\u5904\u6700\u5927\u5dee {c['max_abs_diff_on_overlap']:.3e}")
    print("=== \u6270\u52a8")
    cc = pt["meta"]["counts"]
    print(f"  \u5c1d\u8bd5 {cc['attempted']} \u6b21\uff1anever-read {cc['never_read']} / "
          f"query {cc['query_move']} / model {cc['model_perturb']}")
    print(f"  model \u4e0d\u53ef\u884c {cc['model_infeasible']}\uff0c\u53ef\u884c {cc['model_feasible']}\uff0c"
          f"\u5176\u4e2d\u7ffb\u8f6c {cc['model_runs_with_flip']}")
    for r in pt["infeasible"]:
        print(f"    \u4e0d\u53ef\u884c: {r['source']}{r['sign']} \u2014\u2014 {r['reason']}")
    print("=== \u843d\u76d8")
    for p in (p_t, p_b, p_bd, p_pt):
        print(f"  {p.name}  {p.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
