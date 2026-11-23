
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Secondary, family-level validation-selected challenger.

The primary global-max selection in p1a_improved_seg.py chose
`ward_bic_full32_s9_k8`; it failed on test.  The long-record hypothesis was
pre-specified as a separate family: coarse Ward(cap=8), then recursively split
runs whose internal SSE gain reaches a threshold.  All three hyperparameters
(feature set, smoothing, gain threshold) are chosen by validation ARI *within
that family*, not against the global ranking; no test quantity participates.

The single frozen challenger is `twostage_full32_s9_g0.5`, the best two-stage
configuration on validation (ARI 0.559996 > official baseline 0.548146).

This is one companion evaluation, not a second tuning pass.  It writes a
separate result file and never changes the primary selection.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import best_p1a_seg as B  # noqa: E402
import p1a_improved_seg as P  # noqa: E402

DATA = B.DATA
OUT = os.path.join(DATA, "p1a_improved_results_twostage.json")
FIXED_TAG = "twostage_full32_s9_g0.5"
METRICS = ["ari", "f1", "b_f1", "b_mae", "b_recall", "b_precision",
           "b_count_err", "n_seg", "k"]


def means(rows):
    return {k: float(np.mean([r[k] for r in rows if np.isfinite(r[k])])) for k in METRICS}


def main():
    sel = json.load(open(os.path.join(DATA, "p1a_improved_selection.json"), encoding="utf-8"))
    fam = [r for r in sel["ranking"] if r["cfg"]["tag"].startswith("twostage")]
    fam.sort(key=lambda r: (-r["agg"]["ari"], -r["agg"]["b_f1"]))
    assert fam, "two-stage family absent from selection"
    assert fam[0]["cfg"]["tag"] == FIXED_TAG, fam[0]["cfg"]["tag"]
    row = fam[0]
    assert row["agg"]["ari"] > sel["official_val_baseline"]
    cfg = P.Cfg(**row["cfg"])
    print(f"challenger {cfg.tag}: validation ARI={row['agg']['ari']:.6f} "
          f"bF1={row['agg']['b_f1']:.6f} (baseline {sel['official_val_baseline']:.6f})")

    test = P.build_records("test", cfg.fset, cfg.sw)
    rows = []
    for d in test:
        lab, K = P.apply_cfg(d, cfg)
        sc = P.score_full(lab, d["y"], d["t"])
        rows.append(dict(rec=d["rec"], ktrue=d["ktrue"], k=int(K), **sc))
    agg = means(rows)

    base_rows = []
    for d in P.build_records("test", "base18", 5):
        lab = P.ward_run(d["X"], P._k(d, 8))
        sc = P.score_full(lab, d["y"], d["t"])
        base_rows.append(dict(rec=d["rec"], ktrue=d["ktrue"], k=8, **sc))
    base_agg = means(base_rows)
    assert abs(base_agg["ari"] - 0.4138423666260523) < 5e-6, base_agg["ari"]

    delta = np.array([r["ari"] - b["ari"] for r, b in zip(rows, base_rows)])
    long_delta = np.array([r["ari"] - b["ari"] for r, b in zip(rows, base_rows)
                           if r["ktrue"] >= 9])
    out = dict(
        _meta=dict(
            phase="secondary_family_test",
            protocol="family-level validation selection (best two-stage config), one test evaluation; "
                     "does not change the primary global-max selection",
            selection_tag=cfg.tag,
            selection_val_ari=row["agg"]["ari"],
            selection_val_bf1=row["agg"]["b_f1"],
            official_val_baseline=sel["official_val_baseline"],
            baseline_test_ari=0.4138423666260523,
            family="coarse Ward cap8 then recursive SSE-gain splits",
        ),
        selected_cfg=cfg.__dict__,
        test_records=rows,
        test_mean=agg,
        baseline_records=base_rows,
        baseline_mean=base_agg,
        delta_ari=dict(mean=float(delta.mean()), median=float(np.median(delta)),
                       min=float(delta.min()), max=float(delta.max()),
                       wins=int((delta > 0).sum()), losses=int((delta < 0).sum()),
                       per_record=delta.tolist()),
        long_records=dict(recs=[r["rec"] for r in rows if r["ktrue"] >= 9],
                          mean_delta=float(long_delta.mean()) if len(long_delta) else None,
                          wins=int((long_delta > 0).sum()),
                          losses=int((long_delta < 0).sum()),
                          per_record=long_delta.tolist()),
        exceeds_baseline=bool(agg["ari"] > 0.4138423666260523),
        exceeds_by=float(agg["ari"] - 0.4138423666260523),
    )
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("test mean", {k: round(v, 4) for k, v in agg.items()})
    print("baseline  ", {k: round(v, 4) for k, v in base_agg.items()})
    print(f"delta ARI {delta.mean():+.6f}; wins {int((delta>0).sum())}/{len(delta)}; "
          f"long delta {long_delta.mean():+.6f}")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()