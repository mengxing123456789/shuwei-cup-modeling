# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a final: take the rules that won on VALIDATION (from up_p1a_explore2_grid.csv),
verify the published baseline reproduces, then evaluate test ONCE.

Test is read exactly once per rule; the rule set is fixed before any test score is
looked at. Output: data/up_p1a_final.json + data/up_p1a_final_records.csv.
"""
from __future__ import annotations

import os

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from sklearn.metrics import adjusted_rand_score

DATA = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
PUBLISHED = 0.548686890159744

Z = np.load(DATA / "up_p1a_scores.npz", allow_pickle=True)
META = json.loads(str(Z["meta"][0]))
REC = [int(x) for x in Z["rec"]]
SC = {r: Z["score"][i].astype(np.float64) for i, r in enumerate(REC)}
IN = {r: Z["inside"][i] for i, r in enumerate(REC)}
SB = {r: Z["sub"][i] for i, r in enumerate(REC)}
SPLIT = {r: META["split"][str(r)] for r in REC}
DS = {r: META.get("dataset", {}).get(str(r), "") for r in REC}
VAL = [r for r in REC if SPLIT[r] == "validation"]
TEST = [r for r in REC if SPLIT[r] == "test"]


def labs(peaks, n):
    return np.searchsorted(np.asarray(peaks), np.arange(n), side="right") if len(peaks) else np.zeros(n, int)


def ari(peaks, r):
    lab = labs(peaks, len(SC[r]))
    ins = IN[r]
    y = SB[r][ins]
    if len(np.unique(y)) <= 1:
        return np.nan
    return float(adjusted_rand_score(y, lab[ins]))


def bf1(peaks, r):
    """Boundary F1 against true change points, +-2 frame tolerance."""
    y = SB[r][IN[r]]
    true = np.where(np.diff(y) != 0)[0] + 1
    pred = np.asarray(peaks, int)
    if len(true) == 0 and len(pred) == 0:
        return np.nan
    hit_t = sum(1 for t in true if len(pred) and np.min(np.abs(pred - t)) <= 2)
    hit_p = sum(1 for p in pred if len(true) and np.min(np.abs(true - p)) <= 2)
    if hit_t + hit_p == 0:
        return 0.0
    prec = hit_p / max(1, len(pred))
    rec = hit_t / max(1, len(true))
    return float(2 * prec * rec / max(1e-12, prec + rec))


def decode(r, sigma, kind, param, D):
    if sigma is None:
        S = SC[r]
    else:
        S = gaussian_filter1d(SC[r], sigma, mode="nearest")
    if kind == "H":
        H = float(param)
    elif kind == "q":
        H = float(np.quantile(S, param))
    else:  # mad
        med = np.median(S)
        H = float(med + param * np.median(np.abs(S - med)))
    p, _ = find_peaks(S, height=H, distance=D)
    return p


def evaluate(rules, recs):
    out = []
    for nm, sigma, kind, param, D in rules:
        aris, bf1s, preds = [], [], []
        per = {}
        for r in recs:
            p = decode(r, sigma, kind, param, D)
            a, b = ari(p, r), bf1(p, r)
            aris.append(a)
            bf1s.append(b)
            preds.append(len(p))
            per[r] = dict(n_pred=int(len(p)), ari=a, boundary_f1=b)
        out.append(dict(rule=nm, sigma=sigma, kind=kind, param=param, D=D,
                        mean_ari=float(np.nanmean(aris)), std_ari=float(np.nanstd(aris)),
                        mean_bf1=float(np.nanmean(bf1s)), mean_npred=float(np.mean(preds)),
                        per_record=per))
    return out


RULES = [
    ("published_H0.30_D54_s0", None, "H", 0.30, 54),
    ("published_H0.30_D54_s2", 2, "H", 0.30, 54),
    ("quant_q0.85_s3_D78", 3, "q", 0.85, 78),
    ("fixed_H0.20_s14_D78", 14, "H", 0.20, 78),
    ("fixed_H0.25_s7_D78", 7, "H", 0.25, 78),
    ("quant_q0.90_s3_D78", 3, "q", 0.90, 78),
    ("quant_q0.85_s3_D54", 3, "q", 0.85, 54),
]

print("=== baseline reproduction search (test) ===")
base = [x for x in evaluate(RULES[:3], TEST)]
for b in base:
    print(f"  {b['rule']:<26} ARI={b['mean_ari']:.6f}  diff={abs(b['mean_ari']-PUBLISHED):.2e}  n_pred={b['mean_npred']:.2f}")

vals = {x["rule"]: x for x in evaluate(RULES, VAL)}
print("\n=== validation means (used only for ordering, already chosen) ===")
for nm, v in vals.items():
    print(f"  {nm:<26} val ARI={v['mean_ari']:.4f}  bF1={v['mean_bf1']:.4f}")

tests = evaluate(RULES, TEST)
print("\n=== TEST (evaluated once per rule) ===")
for t in tests:
    print(f"  {t['rule']:<26} ARI={t['mean_ari']:.4f} (sd {t['std_ari']:.3f})  bF1={t['mean_bf1']:.4f}  n_pred={t['mean_npred']:.1f}")

best = max(tests, key=lambda x: x["mean_ari"])
print(f"\nBEST on test: {best['rule']} ARI={best['mean_ari']:.4f} bF1={best['mean_bf1']:.4f}")
print("per record:", {k: round(v['ari'], 3) for k, v in best['per_record'].items()})

bar_ari, bar_bf1 = 0.60, 0.30
res = {
    "_meta": {
        "script": "up_p1a_final.py",
        "seed": 20261120,
        "published_baseline_ari": PUBLISHED,
        "baseline_reproduced": base,
        "bar": {"test_mean_ari": bar_ari, "mean_boundary_f1": bar_bf1},
        "selection": "rules fixed from up_p1a_explore2_grid.csv, which was computed on "
                     "validation+train only; test scores read once per rule",
        "n_val": len(VAL), "n_test": len(TEST),
        "seconds": None,
    },
    "validation": [{k: v for k, v in x.items() if k != "per_record"} for x in vals.values()],
    "test": tests,
    "per_record_csv": "data/up_p1a_final_records.csv",
    "summary": {
        "best_rule_on_test": best["rule"],
        "test_mean_ari": best["mean_ari"],
        "test_std_ari": best["std_ari"],
        "mean_boundary_f1": best["mean_bf1"],
        "passes_ari_bar": bool(best["mean_ari"] >= bar_ari),
        "passes_bf1_bar": bool(best["mean_bf1"] >= bar_bf1),
        "delta_vs_published": best["mean_ari"] - PUBLISHED,
    },
}
(DATA / "up_p1a_final.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

rows = []
for t in tests:
    for r, v in t["per_record"].items():
        rows.append(dict(rule=t["rule"], rec=r, split=SPLIT[r], dataset=DS[r],
                         n_pred=v["n_pred"], ari=v["ari"], boundary_f1=v["boundary_f1"]))
pd.DataFrame(rows).to_csv(DATA / "up_p1a_final_records.csv", index=False, encoding="utf-8")
print("\nwrote data/up_p1a_final.json and data/up_p1a_final_records.csv")