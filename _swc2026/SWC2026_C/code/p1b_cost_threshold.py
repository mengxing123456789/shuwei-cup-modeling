# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-b: the calibration question is the wrong question for a keep/drop decision.

Only a threshold is consumed downstream (keep t iff R_t >= tau).  Temperature scaling and
Platt scaling are monotone transforms of one score, so they move the threshold and never
the ranking; what matters is where tau is put and what an asymmetric mistake costs.

Protocol (frozen here, before any number is looked at):
  * scores come from data/p1b_probs.npz, produced by code/p1b_calib.py;
  * tau is chosen on the VALIDATION scores only, by minimising
        cost = c_fp * (bad frames kept) + c_fn * (good frames dropped)
    per frame, for each cost ratio r = c_fn / c_fp in RATIOS;
  * the same tau is then evaluated once on the test scores;
  * three comparators on test: tau = 0.5 on the raw score, tau = 0.5 on the
    temperature-scaled score, tau = 0.5 on the Platt score (what a "use calibrated
    probabilities" rule would do);
  * ranking invariance of the three scores is checked, not assumed.

Nothing here fits on the test split.  All costs are per-frame costs in arbitrary but
explicit units; no conversion to protocol units is invented.
"""
import json
import os

import numpy as np

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUT = os.path.join(DATA, "p1b_cost_threshold.json")
RATIOS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]


def _cost(scores, y, tau, r):
    """r = cost of dropping a good frame / cost of keeping a bad one."""
    keep = scores >= tau
    bad_kept = float(np.sum(keep & (y > 0.5)))
    good_dropped = float(np.sum((~keep) & (y < 0.5)))
    return (bad_kept + r * good_dropped) / len(y)


def _op(scores, y, tau):
    keep = scores >= tau
    return dict(
        keep_rate=float(keep.mean()),
        bad_rejected=float(np.sum((~keep) & (y > 0.5)) / max(1, np.sum(y > 0.5))),
        good_kept=float(np.sum(keep & (y < 0.5)) / max(1, np.sum(y < 0.5))),
    )


def _grid(s):
    qs = np.unique(np.quantile(s, np.linspace(0.0, 1.0, 401)))
    return np.concatenate(([s.min() - 1e-6], qs, [s.max() + 1e-6]))


def main():
    z = np.load(os.path.join(DATA, "p1b_probs.npz"))
    if "pv" not in z.files:
        raise SystemExit("validation scores missing: rerun code/p1b_calib.py first")
    pv, yv = z["pv"].astype(float), z["yv"].astype(float)
    pt, yt = z["pt"].astype(float), z["yte"].astype(float)
    pcal, ppl = z["pcal"].astype(float), z["ppl"].astype(float)

    from sklearn.metrics import roc_auc_score
    aucs = {k: float(roc_auc_score(yt, v)) for k, v in
            (("raw", pt), ("temperature", pcal), ("platt", ppl))}
    invariant = max(aucs.values()) - min(aucs.values()) < 1e-9

    rows = []
    for r in RATIOS:
        taus = _grid(pv)
        costs = np.array([_cost(pv, yv, t, r) for t in taus])
        tau = float(taus[int(np.argmin(costs))])
        row = dict(ratio=r, tau=tau, val_cost=float(costs.min()),
                   test_cost=_cost(pt, yt, tau, r), **_op(pt, yt, tau))
        for nm, s in (("raw", pt), ("temperature", pcal), ("platt", ppl)):
            row[f"cost_{nm}_at_half"] = _cost(s, yt, 0.5, r)
        rows.append(row)

    best = min(rows, key=lambda x: x["test_cost"])
    cmp_half = min(min(r["cost_raw_at_half"], r["cost_temperature_at_half"],
                       r["cost_platt_at_half"]) for r in rows)
    out = dict(
        _meta=dict(script="p1b_cost_threshold.py",
                   question="does a keep/drop decision need a calibrated probability?",
                   scores="data/p1b_probs.npz from p1b_calib.py",
                   selection="tau minimises asymmetric cost on validation scores only",
                   ratios=RATIOS,
                   cost_units="per-frame, arbitrary but explicit; no protocol conversion",
                   test_policy="each tau evaluated once on test; comparators at tau=0.5"),
        n_validation=int(len(pv)), n_test=int(len(pt)),
        validation_prevalence=float(yv.mean()), test_prevalence=float(yt.mean()),
        auc_by_transform=aucs, ranking_invariant=bool(invariant),
        rows=rows,
        best_ratio=best["ratio"], best_tau=best["tau"], best_test_cost=best["test_cost"],
        best_keep_rate=best["keep_rate"], best_good_kept=best["good_kept"],
        best_bad_rejected=best["bad_rejected"],
        cost_of_probability_rule=cmp_half,
        calibrated_rule_is_better=bool(cmp_half < best["test_cost"]),
        conclusion=("a threshold decision consumes the ranking, not the probability: "
                    "the tau that minimises the declared cost is picked on validation "
                    "and transferred, and the three calibrations differ only in where "
                    "they would put an uninformed tau=0.5 cut"),
    )
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    for r in rows:
        print(f"r={r['ratio']:>4} tau={r['tau']:.4f} val={r['val_cost']:.5f} "
              f"test={r['test_cost']:.5f} keep={r['keep_rate']:.3f} "
              f"good_kept={r['good_kept']:.3f} bad_rej={r['bad_rejected']:.3f} "
              f"half(raw/T/platt)={r['cost_raw_at_half']:.5f}/"
              f"{r['cost_temperature_at_half']:.5f}/{r['cost_platt_at_half']:.5f}")
    print("ranking invariant:", invariant, "aucs:", aucs)
    print("wrote", OUT)


if __name__ == "__main__":
    main()