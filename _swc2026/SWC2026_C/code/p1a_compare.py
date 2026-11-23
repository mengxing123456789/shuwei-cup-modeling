import os

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Paired comparison of the GPU boundary detector against the Ward baseline.

Both methods see the same 7 test records and the same annotated labels, so the
comparison is paired by record.  The p-value comes from an exact permutation test
on the mean paired difference (n=7 is too small for a normal approximation), and
the interval from a record-level bootstrap.  This is the only defensible way to
claim an improvement with seven test records.
"""
import json, os
import numpy as np
import pandas as pd
from itertools import product

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(PROJ, "data")
RNG = np.random.default_rng(20261120)


def exact_perm_p(d):
    """Two-sided sign-flip permutation test on the mean difference."""
    d = np.asarray(d, float)
    obs = abs(d.mean())
    signs = np.array(list(product([-1, 1], repeat=len(d))))
    perm = np.abs((signs * d).mean(1))
    return float((perm >= obs - 1e-12).mean())


def boot_ci(d, n=20000):
    d = np.asarray(d, float)
    idx = RNG.integers(0, len(d), size=(n, len(d)))
    m = d[idx].mean(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def main():
    base = pd.read_csv(os.path.join(DATA, "p1_segmentation_records.csv"))
    final = os.path.join(DATA, "p1a_gpu_segmentation_final_records.csv")
    tuned = os.path.join(DATA, "p1a_gpu_segmentation_tuned_records.csv")
    new = pd.read_csv(final if os.path.exists(final) else (tuned if os.path.exists(tuned) else os.path.join(DATA, "p1a_gpu_segmentation_records.csv")))
    ward = base[base.method == "ward"].copy()
    ward["b_f1"] = 2 * ward.b_precision * ward.b_recall / (ward.b_precision + ward.b_recall).replace(0, np.nan)
    ward = ward.set_index("rec")
    new = new.set_index("rec")
    recs = sorted(set(ward.index) & set(new.index))
    rows, out = [], {}
    for metric in ("ari", "f1", "boundary_f1"):
        if metric not in new.columns or metric not in ward.columns:
            continue
        a = new.loc[recs, metric].astype(float).values
        b = ward.loc[recs, metric].astype(float).values
        d = a - b
        rows.append(dict(metric=metric, ward=float(b.mean()), gpu=float(a.mean()),
                         diff=float(d.mean()), ci_low=boot_ci(d)[0], ci_high=boot_ci(d)[1],
                         perm_p=exact_perm_p(d), wins=int((d > 0).sum()), n=len(d)))
        out[metric] = dict(ward_mean=float(b.mean()), gpu_mean=float(a.mean()),
                           paired_diff=float(d.mean()), ci95=boot_ci(d),
                           perm_p=exact_perm_p(d), wins=int((d > 0).sum()), n=len(d),
                           per_record={int(r): float(v) for r, v in zip(recs, d)})
    tab = pd.DataFrame(rows)
    tab.to_csv(os.path.join(DATA, "p1a_segmentation_compare.csv"), index=False, encoding="utf-8")
    # per-dataset direction, so a single easy dataset cannot carry the claim
    j = new.join(ward[["dataset"]].rename(columns={"dataset": "dataset_base"}))
    out["by_dataset"] = {
        str(ds): dict(n=int(len(g)), ward_ari=float(g.ari_base.mean()) if "ari_base" in g else float(ward.loc[g.index, "ari"].mean()), gpu_ari=float(g.ari.mean()))
        for ds, g in j.groupby("dataset")}
    out["_meta"] = dict(test_records=len(recs),
                        baseline="Ward on head-normalised state, K from GMM BIC",
                        method="dilated bidirectional TCN boundary detector, seed ensemble",
                        test="exact two-sided sign-flip permutation on mean paired difference; "
                             "95% interval from 20,000 record-level bootstrap resamples")
    with open(os.path.join(DATA, "p1a_segmentation_compare.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(tab.round(4).to_string(index=False))
    print(json.dumps(out["by_dataset"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()