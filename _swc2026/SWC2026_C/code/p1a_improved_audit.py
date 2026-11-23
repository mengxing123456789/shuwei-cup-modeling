
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Independent audit of the frozen P1-a improved-segmentation report.

Checks
------
1. The selection file contains validation records only; none of the seven test
   record ids appears in it.
2. `chosen` is the highest-ARI candidate among candidates above the official
   validation baseline, and its recorded validation scores match.
3. Recomputing the frozen candidate on test reproduces every stored ARI,
   Hungarian F1 and boundary metric to 1e-9.
4. The recomputed bic@8 baseline reproduces the published test ARI to 5e-6.
5. The stored delta array, means and `exceeds_baseline` flag are arithmetically
   consistent.

Writes data/p1a_improved_audit.json.
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
AUDIT_OUT = os.path.join(DATA, "p1a_improved_audit.json")
TEST_IDS = {17, 18, 37, 41, 56, 61, 68}
METRICS = ["ari", "f1", "b_f1", "b_mae", "b_recall", "b_precision", "b_count_err"]


def val_ids():
    return {int(r) for r in B.recs[B.recs.split == "validation"].rec
            if len(B.segs[B.segs.rec == r]) >= 2}


def main():
    sel = json.load(open(os.path.join(DATA, "p1a_improved_selection.json"), encoding="utf-8"))
    res = json.load(open(os.path.join(DATA, "p1a_improved_results.json"), encoding="utf-8"))
    checks = []

    allowed_val = val_ids()
    val_seen = set()
    for row in sel["ranking"]:
        for rr in row["val_records"]:
            val_seen.add(int(rr["rec"]))
    checks.append(dict(
        check="selection_contains_validation_only",
        passed=bool(val_seen <= allowed_val and not (val_seen & TEST_IDS)),
        observed=sorted(val_seen),
        expected_subset=sorted(allowed_val),
        test_ids_union=sorted(TEST_IDS),
    ))

    eligible = [r for r in sel["ranking"] if r["agg"]["ari"] > sel["official_val_baseline"]]
    best = max(eligible, key=lambda r: (r["agg"]["ari"], r["agg"]["b_f1"])) if eligible else None
    chosen = sel["chosen"]
    checks.append(dict(
        check="chosen_is_best_eligible_validation_candidate",
        passed=bool(chosen is not None and best is not None
                    and chosen["cfg"]["tag"] == best["cfg"]["tag"]
                    and abs(chosen["agg"]["ari"] - best["agg"]["ari"]) < 1e-12),
        chosen_tag=(chosen or {}).get("cfg", {}).get("tag"),
        best_eligible=(best or {}).get("cfg", {}).get("tag"),
        n_eligible=len(eligible),
        official_val_baseline=sel["official_val_baseline"],
    ))
    checks.append(dict(
        check="chosen_val_ari_beats_official_baseline",
        passed=bool(chosen and chosen["agg"]["ari"] > sel["official_val_baseline"]),
        val_ari=(chosen or {}).get("agg", {}).get("ari"),
        baseline=sel["official_val_baseline"],
        margin=(chosen["agg"]["ari"] - sel["official_val_baseline"]) if chosen else None,
    ))

    cfg = P.Cfg(**res["selected_cfg"])
    test = P.build_records("test", cfg.fset, cfg.sw)
    recomputed = []
    diffs = {}
    for d, stored in zip(test, res["test_records"]):
        lab, K = P.apply_cfg(d, cfg)
        sc = P.score_full(lab, d["y"], d["t"])
        recomputed.append(dict(rec=d["rec"], k=int(K), **sc))
        diffs[str(d["rec"])] = {m: abs(float(sc[m]) - float(stored[m])) for m in METRICS}
    worst = max((v, rec, m) for rec, dd in diffs.items() for m, v in dd.items())
    checks.append(dict(
        check="stored_test_metrics_reproduce",
        passed=bool(worst[0] < 1e-9),
        worst_abs_diff=worst[0], worst_record=int(worst[1]), worst_metric=worst[2],
    ))

    base_records = []
    test_base = P.build_records("test", "base18", 5)
    for d in test_base:
        lab = P.ward_run(d["X"], P._k(d, 8))
        base_records.append(dict(rec=d["rec"], ktrue=d["ktrue"], k=8,
                                 **P.score_full(lab, d["y"], d["t"])))
    base_ari = float(np.mean([r["ari"] for r in base_records]))
    published_base = res["_meta"]["baseline_test_ari"]
    checks.append(dict(
        check="published_test_baseline_reproduces",
        passed=bool(abs(base_ari - published_base) < 5e-6),
        observed=base_ari, published=published_base,
        abs_diff=abs(base_ari - published_base),
    ))

    ari_sel = float(np.mean([r["ari"] for r in recomputed]))
    delta = np.array([r["ari"] - b["ari"] for r, b in zip(recomputed, base_records)])
    checks.append(dict(
        check="means_and_delta_consistent",
        passed=bool(abs(ari_sel - res["test_mean"]["ari"]) < 1e-12
                    and abs(delta.mean() - res["delta_ari"]["mean"]) < 1e-12
                    and res["exceeds_baseline"] == (ari_sel > published_base)),
        selected_mean=ari_sel, stored_mean=res["test_mean"]["ari"],
        delta_mean=float(delta.mean()), stored_delta=res["delta_ari"]["mean"],
        exceeds_baseline=bool(ari_sel > published_base),
    ))

    # Secondary two-stage challenger: family-level selection, recomputed separately.
    ch_path = os.path.join(DATA, "p1a_improved_results_twostage.json")
    ch = json.load(open(ch_path, encoding="utf-8"))
    row = next(r for r in sel["ranking"] if r["cfg"]["tag"] == ch["selected_cfg"]["tag"])
    fam = [r for r in sel["ranking"] if r["cfg"]["tag"].startswith("twostage")]
    best_fam = max(fam, key=lambda r: (r["agg"]["ari"], r["agg"]["b_f1"]))
    checks.append(dict(
        check="challenger_is_best_two_stage_on_validation_and_eligible",
        passed=bool(best_fam["cfg"]["tag"] == row["cfg"]["tag"]
                    and row["agg"]["ari"] > sel["official_val_baseline"]
                    and ch["_meta"]["selection_val_ari"] == row["agg"]["ari"]),
        tag=row["cfg"]["tag"], val_ari=row["agg"]["ari"],
        baseline=sel["official_val_baseline"],
    ))
    cfg_ch = P.Cfg(**ch["selected_cfg"])
    test_ch = P.build_records("test", cfg_ch.fset, cfg_ch.sw)
    ch_diff = {}
    ch_rows = []
    for d, stored in zip(test_ch, ch["test_records"]):
        lab, K = P.apply_cfg(d, cfg_ch)
        sc = P.score_full(lab, d["y"], d["t"])
        ch_rows.append(dict(rec=d["rec"], k=int(K), **sc))
        ch_diff[str(d["rec"])] = {m: abs(float(sc[m]) - float(stored[m])) for m in METRICS}
    ch_worst = max((v, rec, m) for rec, dd in ch_diff.items() for m, v in dd.items())
    identical = all(abs(r["ari"] - q["ari"]) < 1e-12 for r, q in zip(recomputed, ch_rows))
    checks.append(dict(
        check="challenger_metrics_reproduce_and_degenerates_to_primary",
        passed=bool(ch_worst[0] < 1e-9 and identical),
        worst_abs_diff=ch_worst[0], worst_record=int(ch_worst[1]),
        worst_metric=ch_worst[2], identical_to_primary=bool(identical),
        challenger_ari=float(np.mean([r["ari"] for r in ch_rows])),
    ))

    out = dict(
        all_passed=bool(all(c["passed"] for c in checks)),
        n_checks=len(checks), checks=checks,
        selected_tag=cfg.tag,
        selected_test_ari=ari_sel,
        baseline_test_ari=base_ari,
        delta_ari=ari_sel - base_ari,
        per_record_diffs=diffs,
    )
    with open(AUDIT_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for c in checks:
        print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['check']}")
    print(f"all_passed={out['all_passed']}  selected ARI={ari_sel:.9f}  "
          f"baseline={base_ari:.9f}  delta={ari_sel-base_ari:+.9f}")
    print(f"saved {AUDIT_OUT}")
    if not out["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()