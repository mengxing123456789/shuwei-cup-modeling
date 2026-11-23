
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Calibrate the closed form  P(on time) = F_d((due - s - beta)/alpha).

The scheduler decides punctuality on line 189 as `C <= j.due` with `C = s + p` and
`p = alpha*d + beta`.  Solving for d gives an exact event,

    d <= (due - s - beta)/alpha,

so the probability is the predictive law evaluated at a single point.  Two
consequences follow, and both are testable against the per-job dump:

  * alpha enters only through the reciprocal inside the argument, so the whole
    mapping-sensitivity table must collapse onto one curve indexed by z.  If the
    realised rate at each (case, alpha) tracks F_d(z), the table is a corollary of
    the formula rather than a separate empirical finding.
  * the reservation b is absent.  b delays the next start, it does not make the
    current job punctual; that is why a slack policy helps through capacity and not
    through punctuality.

F_d is built from *train* durations of the same family, and the jobs are drawn from
the validation pool, so nothing here is evaluated on its own training data.

Output
    data/closedform_calib.json
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def cdf_at(sorted_vals, x):
    return float(np.searchsorted(sorted_vals, x, side="right")) / max(len(sorted_vals), 1)


def main():
    jobs = pd.read_csv(os.path.join(DATA, "p3_jobs.csv"))
    pred = pd.read_csv(os.path.join(DATA, "p3_duration_predictions.csv"))
    tr = pred[pred.split == "train"]

    law = {}
    for f in ("A", "L", "P"):
        v = np.sort(tr[tr.family == f].duration.values)
        if len(v) >= 8:
            law[f] = v
    glob = np.sort(tr.duration.values)

    def F(fam, x):
        return cdf_at(law.get(fam, glob), x)

    jobs["z"] = (jobs.due - jobs.s - jobs.beta) / jobs.alpha
    jobs["p_hat"] = [F(f, z) for f, z in zip(jobs.family, jobs.z)]
    y = jobs.on_time.astype(float).values
    p = np.clip(jobs.p_hat.values, 1e-6, 1 - 1e-6)

    base = float(y.mean())
    brier = float(np.mean((p - y) ** 2))
    brier_base = float(np.mean((base - y) ** 2))
    ll = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    ll_base = float(-np.mean(y * np.log(base) + (1 - y) * np.log(1 - base)))

    # reliability: ten bins on the predicted probability
    bins = np.linspace(0, 1, 11)
    idx = np.clip(np.digitize(p, bins) - 1, 0, 9)
    rel = []
    for b in range(10):
        m = idx == b
        if m.sum() >= 15:
            rel.append(dict(bin=b, lo=float(bins[b]), hi=float(bins[b + 1]),
                            n=int(m.sum()), mean_pred=float(p[m].mean()),
                            mean_real=float(y[m].mean())))
    ece = float(np.sum([abs(r["mean_real"] - r["mean_pred"]) * r["n"] for r in rel]) / max(sum(r["n"] for r in rel), 1))

    # calibration slope on the logit scale: 1.0 means perfectly calibrated
    lg = np.log(p / (1 - p))
    A = np.vstack([np.ones_like(lg), lg]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    slope = float(coef[1])

    # the alpha-collapse test: realised rate versus the formula, per (case, alpha)
    per = []
    for (case, al), g in jobs.groupby(["case", "alpha"]):
        per.append(dict(case=case, alpha=float(al), n=int(len(g)),
                        mean_p_hat=float(np.clip(g.p_hat, 0, 1).mean()),
                        realised=float(g.on_time.mean())))
    per = sorted(per, key=lambda r: (r["case"], r["alpha"]))
    err = [abs(r["mean_p_hat"] - r["realised"]) for r in per]

    # Why is the realised rate systematically above the prediction?  Either the
    # formula is biased or the train law sits above the validation draw.  Rebuilding
    # the law from every split separates the two: if the gap closes, the bias is the
    # train-to-validation shift in the duration pool, not the formula.
    law_all = {}
    for f in ("A", "L", "P"):
        v = np.sort(pred[pred.family == f].duration.values)
        if len(v) >= 8:
            law_all[f] = v
    glob_all = np.sort(pred.duration.values)
    p_hat_all = np.array([
        cdf_at(law_all.get(f, glob_all), z) for f, z in zip(jobs.family, jobs.z)])
    shift = dict(
        mean_p_hat_train_law=float(p.mean()), mean_p_hat_all_law=float(p_hat_all.mean()),
        realised=float(y.mean()),
        gap_train_law=float(y.mean() - p.mean()),
        gap_all_law=float(y.mean() - p_hat_all.mean()),
        n_train_law=int(sum(len(v) for v in law.values())),
        n_all_law=int(sum(len(v) for v in law_all.values())))

    out = dict(
        script="closedform_calib.py",
        shift_check=shift,
        formula="P(on time | s, due, alpha) = F_d((due - s - beta)/alpha)",
        n_jobs=int(len(jobs)), base_rate=base,
        brier=brier, brier_base=brier_base, brier_skill=float(1 - brier / brier_base),
        logloss=ll, logloss_base=ll_base, ece=ece, calibration_slope=slope,
        spearman_pred_vs_real=float(spearmanr(p, y).correlation),
        reliability=rel, alpha_collapse=per,
        alpha_collapse_max_abs_err=float(max(err)) if err else None,
        alpha_collapse_mean_abs_err=float(np.mean(err)) if err else None,
        note="F_d is the empirical law of train durations within the family; jobs are "
             "drawn from validation units, so the test is out-of-sample in duration.",
    )
    with open(os.path.join(DATA, "closedform_calib.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("jobs %d  base %.4f  brier %.4f (const %.4f)  skill %.3f  ece %.4f  slope %.3f"
          % (len(jobs), base, brier, brier_base, out["brier_skill"], ece, slope))
    print("%-6s%8s%8s%8s%6s" % ("case", "alpha", "p_hat", "real", "n"))
    for r in per:
        print("%-6s%8.2f%8.4f%8.4f%6d" % (r["case"], r["alpha"], r["mean_p_hat"],
                                          r["realised"], r["n"]))
    print("alpha-collapse |err| max %.4f mean %.4f"
          % (out["alpha_collapse_max_abs_err"], out["alpha_collapse_mean_abs_err"]))


if __name__ == "__main__":
    main()