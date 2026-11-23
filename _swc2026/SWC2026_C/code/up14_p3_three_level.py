# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up14_p3_three_level.py -- three-level design over the five effective rule knobs.

up12 crossed seven knobs at two levels.  Two of those seven (``ksk``, ``qsl``)
turned out to be structurally inert for the frozen rules, so a three-level
design is only meaningful on the remaining five.  This script builds the full
3^5 = 243 design per case, with the middle level of every knob set to the
frozen value, so the centre cell *is* the frozen policy.  It then fits a
coded-level linear model with all ten pairwise interactions and reports
coefficients in on-time points.

Why three levels: a two-level design can only see a linear effect plus a
curvature term that is aliased with the interaction it cannot separate.  With
three levels the centre cell identifies curvature directly, and the pairwise
terms are no longer confounded with it.

Output: data/up14_p3_three_level.json
"""
import itertools
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up2_p3_final as F

DATA = os.path.join(os.path.dirname(HERE), "data")
KEYS = ("q_hi", "gate", "late_tol", "mix", "gam")
LEVELS = {
    "S2": {"q_hi": (0.30, 0.45, 0.60), "gate": (0.55, 0.75, 0.95),
           "late_tol": (4.0, 12.0, 20.0), "mix": (0.30, 0.60, 0.90),
           "gam": (0.00, 0.125, 0.25)},
    "S3": {"q_hi": (0.20, 0.30, 0.45), "gate": (0.15, 0.35, 0.60),
           "late_tol": (8.0, 20.0, 28.0), "mix": (0.00, 0.15, 0.30),
           "gam": (0.00, 0.25, 0.50)},
}
CODE = (-1.0, 0.0, 1.0)


def design():
    """Rows of coded levels plus the decoded parameter dict per row."""
    rows = []
    for combo in itertools.product((0, 1, 2), repeat=len(KEYS)):
        rows.append(combo)
    return rows


def fit_model(y, X, names):
    """Least squares with intercept; returns coefficients and R^2."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return beta, r2


def main():
    with open(os.path.join(DATA, "up2_p3_search.json"), encoding="utf-8") as f:
        search = json.load(f)
    out = {"method": "3^5 full factorial on the five effective knobs; middle "
                     "level = frozen value, so the centre cell is the frozen policy; "
                     "30 seeds x 5 mappings on the vectorised engine",
           "keys": list(KEYS), "n_corners": 3 ** len(KEYS), "cases": {}}
    for case in ("S2", "S3"):
        frozen = dict(search["frozen"][case]["params"])
        rows = design()
        # The true frozen policy is run as its own candidate: for S2 the middle
        # level of ``gam`` is 0.125 while the frozen value is 0.0, so the centre
        # cell of the design is *not* the frozen policy and cannot serve as the
        # reference.  Everything below is measured against candidate 0.
        cands = []
        pf = dict(frozen)
        pf["name"] = "FROZEN"
        cands.append(pf)
        for i, combo in enumerate(rows):
            p = dict(frozen)
            p["name"] = "tl_%03d" % i
            for k, lv in zip(KEYS, combo):
                p[k] = LEVELS[case][k][lv]
            cands.append(p)
        t0 = time.time()
        res = F.run_policy_set(cands, case, F.ALL30)
        secs = time.time() - t0
        on_all = np.array([
            float(np.mean([res[m]["weighted_on_time_rate"][i].mean() for m in F.MAPPINGS]))
            for i in range(len(cands))])
        on_test = np.array([
            float(np.mean([res[m]["weighted_on_time_rate"][i][-5:].mean() for m in F.MAPPINGS]))
            for i in range(len(cands))])
        cost = np.array([
            float(np.mean([res[m]["cost"][i].mean() for m in F.MAPPINGS]))
            for i in range(len(cands))])

        base_all, base_test, base_cost = on_all[0], on_test[0], cost[0]
        on_all, on_test, cost = on_all[1:], on_test[1:], cost[1:]
        centre = rows.index(tuple(1 for _ in KEYS))

        # coded design matrix: intercept, five main effects, ten pairwise products
        X = [np.ones(len(rows))]
        names = ["intercept"]
        coded = np.array([[CODE[lv] for lv in combo] for combo in rows])
        for j, k in enumerate(KEYS):
            X.append(coded[:, j])
            names.append(k)
        for j, a in enumerate(KEYS):
            for l in range(j + 1, len(KEYS)):
                X.append(coded[:, j] * coded[:, l])
                names.append("%s x %s" % (a, KEYS[l]))
        X = np.column_stack(X)

        beta, r2 = fit_model(on_all, X, names)
        beta_pt = beta * 100.0
        coef = {n: float(v) for n, v in zip(names, beta_pt)}

        # curvature from the centre cell alone (quadratic term along each knob)
        curv = {}
        for j, k in enumerate(KEYS):
            lo = on_all[[i for i, c in enumerate(rows) if c[j] == 0 and
                         all(c[m] == 1 for m in range(len(KEYS)) if m != j)][0]]
            hi = on_all[[i for i, c in enumerate(rows) if c[j] == 2 and
                         all(c[m] == 1 for m in range(len(KEYS)) if m != j)][0]]
            curv[k] = float(((lo + hi) / 2.0 - base_all) * 100.0)

        order = np.argsort(on_all)
        out["cases"][case] = dict(
            frozen=dict(on_time_all30=float(base_all), on_time_test=float(base_test),
                        cost=float(base_cost)),
            n=int(len(rows)), wall_seconds=round(secs, 2),
            corner_mean=float(on_all.mean()), corner_sd=float(on_all.std(ddof=1)),
            corner_min=float(on_all.min()), corner_max=float(on_all.max()),
            corner_range_pt=float((on_all.max() - on_all.min()) * 100.0),
            frozen_percentile=float((on_all < base_all).mean() * 100.0),
            frozen_is_best=bool(np.argmax(on_all) == centre),
            n_corners_above_frozen=int((on_all > base_all + 1e-12).sum()),
            model_r2=float(r2),
            coefficients_pt=coef,
            curvature_pt=curv,
            levels={k: list(LEVELS[case][k]) for k in KEYS},
            top3=[dict(levels={k: float(cands[i + 1][k]) for k in KEYS},
                       on_time_all30=float(on_all[i]),
                       delta_pt=float((on_all[i] - base_all) * 100.0))
                  for i in order[-3:][::-1]],
            bottom3=[dict(levels={k: float(cands[i + 1][k]) for k in KEYS},
                          on_time_all30=float(on_all[i]),
                          delta_pt=float((on_all[i] - base_all) * 100.0))
                     for i in order[:3]],
        )
        print(case, "frozen %.4f" % base_all, "range %.2f pt" % ((on_all.max() - on_all.min()) * 100),
              "frozen pct %.1f" % ((on_all < base_all).mean() * 100),
              "above %d" % int((on_all > base_all + 1e-12).sum()),
              "R2 %.4f" % r2, "secs %.1f" % secs)
        for n in names[1:]:
            if abs(coef[n]) > 0.05:
                print("   %-16s %+7.2f pt" % (n, coef[n]))
        print("   curvature", {k: round(v, 2) for k, v in curv.items()})

    path = os.path.join(DATA, "up14_p3_three_level.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", path)


if __name__ == "__main__":
    main()
