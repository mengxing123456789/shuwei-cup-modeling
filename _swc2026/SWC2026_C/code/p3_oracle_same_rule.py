# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# AI 辅助：DeepSeek Harness 助手生成的 oracle_same_rule 实现与配对检验。
# -*- coding: utf-8 -*-
"""P0-01 / 08 纲领 §6.5-1：把 "同一规则下的真值参考" 真正实现出来。

在此之前教科书里的 reference（`p3_stochastic_schedule` 的 oracle）是**另一条规则**
（`a = max(on, w/p*exp(-slack/10))`），所以 "adaptive 超过 reference" 不是受控对照。
这里给 `p3_improved_verify.simulate` 加一个 `oracle` 开关：规则、参数、动作集、
种子全部不变，只把 "规则读取时长的地方" 换成真值 ——

  * `onprob`：把残差情景分布换成退化分布（残差 0），即用真实的剩余时长算准时概率；
  * 预留 `b`：用真实时长而不是残差分位（知道 p 就不需要分位数缓冲）。

于是得到一个**同规则的上界**，可以直接与 headline 配对做差，CI 也有了对照意义。

输出 `data/p3_oracle_same_rule.json`（含 headline 复现闸、oracle、配对差与 CI）。
"""
from __future__ import annotations

import os

import json
from pathlib import Path

C = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = C / "code" / "p3_improved_verify.py"
OUT = C / "data" / "p3_oracle_same_rule.json"

t = F.read_text(encoding="utf-8")

# ---- patch 1: signature -------------------------------------------------
old_sig = 'def simulate(case, seed, policy, params=None):\n    """Direct replay. policy in {slack_old, risk_old}; params for risk_old."""'
new_sig = (
    'def simulate(case, seed, policy, params=None, oracle=False):\n'
    '    """Direct replay. policy in {slack_old, risk_old}; params for risk_old.\n'
    '\n'
    '    ``oracle=True`` keeps the rule, its parameters, the action set and the\n'
    '    seeds fixed and replaces only what the rule *knows*: the residual\n'
    '    scenarios become a point mass at the true remaining duration, so both the\n'
    '    on-time probability and the reservation are computed from true ``p``.\n'
    '    This is the same-rule reference the paper compares against.\n'
    '    """'
)
assert t.count(old_sig) == 1, "signature"
t = t.replace(old_sig, new_sig, 1)

# ---- patch 2: onprob uses the truth when oracle --------------------------
old_on = """    def onprob(a):
        ds = np.quantile(old.RES[0.2], SCEN_Q)
        phat = ALPHA * np.maximum(0.2, a["j"]["pred"] + ds) + BETA
        return float(np.mean(a["s"] + phat <= a["j"]["due"] + EPS))"""
new_on = """    def onprob(a):
        if oracle:
            phat_true = ALPHA * a["j"]["d"] + BETA
            return float(a["s"] + phat_true <= a["j"]["due"] + EPS)
        ds = np.quantile(old.RES[0.2], SCEN_Q)
        phat = ALPHA * np.maximum(0.2, a["j"]["pred"] + ds) + BETA
        return float(np.mean(a["s"] + phat <= a["j"]["due"] + EPS))"""
assert t.count(old_on) == 1, "onprob"
t = t.replace(old_on, new_on, 1)

# ---- patch 3: reservation uses the truth when oracle --------------------
old_b = """            elif policy == "risk_old":
                b = max(RESERVE_MIN, ALPHA * (j["pred"] + quantile(old.RES[0.2], qlevel)) + BETA)"""
new_b = """            elif policy == "risk_old":
                if oracle:
                    b = max(RESERVE_MIN, ALPHA * j["d"] + BETA)
                else:
                    b = max(RESERVE_MIN,
                            ALPHA * (j["pred"] + quantile(old.RES[0.2], qlevel)) + BETA)"""
assert t.count(old_b) == 1, "reservation"
t = t.replace(old_b, new_b, 1)

F.write_text(t, encoding="utf-8", newline="\n")
print("patched p3_improved_verify.simulate with oracle=...")

# ---- run ---------------------------------------------------------------
import sys

sys.path.insert(0, str(C / "code"))
import importlib

IV = importlib.import_module("p3_improved_verify")
import numpy as np

HEADLINE = {  # the 15-seed-selected parameters, frozen
    "S2": dict(Q_HI=0.5, GATE=0.6, LATE_TOL_RISK=12.0),
    "S3": dict(Q_HI=0.6, GATE=0.5, LATE_TOL_RISK=20.0),
}
SEEDS = list(range(2026111700, 2026111730))


def ci95(x):
    x = np.asarray(x, float)
    return float(1.96 * x.std(ddof=1) / np.sqrt(len(x)))


res = {"_meta": {
    "script": "p3_oracle_same_rule.py",
    "protocol": "same rule (risk_old) + same params + same seeds; only the duration knowledge changes",
    "oracle_definition": "on-time probability and reservation both use the true remaining duration",
    "seeds": SEEDS,
    "headline_params": HEADLINE,
}, "cases": {}}

for case in ("S2", "S3"):
    p = HEADLINE[case]
    rep, orc = [], []
    for s in SEEDS:
        rep.append(IV.simulate(case, s, "risk_old", p)["weighted_on_time_rate"])
        orc.append(IV.simulate(case, s, "risk_old", p, oracle=True)["weighted_on_time_rate"])
    rep = np.asarray(rep)
    orc = np.asarray(orc)
    d = orc - rep
    res["cases"][case] = {
        "n": len(SEEDS),
        "headline_mean": float(rep.mean()),
        "headline_ci95": ci95(rep),
        "same_rule_oracle_mean": float(orc.mean()),
        "same_rule_oracle_ci95": ci95(orc),
        "gap_oracle_minus_headline": float(d.mean()),
        "gap_ci95": ci95(d),
        "gap_lower": float(d.mean() - ci95(d)),
        "gap_upper": float(d.mean() + ci95(d)),
        "wins": int((d > 0).sum()),
        "ties": int((d == 0).sum()),
        "losses": int((d < 0).sum()),
        "per_seed": [float(x) for x in d],
        "check_gap_positive": bool(d.mean() > 0),
        "check_gap_ci_excludes_zero": bool(d.mean() - ci95(d) > 0),
    }
    print(f"{case}: headline {rep.mean():.4f}  same-rule oracle {orc.mean():.4f}  "
          f"gap {d.mean():+.4f} +/- {ci95(d):.4f}  W/T/L "
          f"{int((d>0).sum())}/{int((d==0).sum())}/{int((d<0).sum())}")

OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("written", OUT)