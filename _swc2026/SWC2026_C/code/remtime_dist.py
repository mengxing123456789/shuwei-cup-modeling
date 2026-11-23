
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Remaining time as a distribution, not a point.

Why the previous attempt failed
-------------------------------
Two designs were tried before this one, and both are wrong for the same reason:

1. Regressing total duration d on prefix features.  A prefix only bounds d from
   below, so this target throws the information away.  Reproduced here.
2. Regressing the remaining time d - s.  This *sounds* like the fix, but shifting
   the target by the same amount as the baseline leaves the comparison unchanged:
   measured MAE and the ratio to a constant predictor are almost identical in the
   two arms.  The run is kept in `data/residual_target.json` as the refutation.
3. A closed form R = s(1-phi)/phi with phi read off the *whole* trajectory reached
   2.05 s at a 1 s prefix, but phi is a hindsight quantity.  Predicting phi causally
   (`progress@*` in the same file) is worse than a constant: ratio 1.28-1.37.

What the decision actually consumes is not a point estimate but a distribution:
the scheduler reserves capacity from a quantile of the remaining time and the
observation decision trades the cost of a request against the reduction of that
quantile's uncertainty.  So this script predicts the quantile grid of r directly,
with a proper scoring rule, and measures calibration rather than only MAE.

Metrics
    pinball   mean pinball loss over the quantile grid (lower is better)
    crps      2 * pinball, the proper score for a distributional forecast
    cov50/80/90  empirical coverage of the corresponding central intervals
    mae       absolute error of the predicted median
    perm      CRPS after shuffling the geometry columns across test segments;
              if CRPS does not degrade, the prefix carries no information

Outputs
    data/remtime_dist.json
"""
import json
import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PREFIXES = (0.2, 0.6, 1.0)
QUANT = np.array([0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
SEED = 20261120
DEV = "cuda" if torch.cuda.is_available() else "cpu"
GEOM = ["f_L", "f_Lrate", "f_net", "f_curv", "f_vmean", "f_vmax", "f_vstd",
        "f_rev", "f_revrate", "f_pos0", "f_pos0y", "f_pos0z", "f_end", "f_endy", "f_endz"]


class QNet(nn.Module):
    """Monotone quantile head: a base level plus non-negative increments."""

    def __init__(self, n_in, k):
        super(QNet, self).__init__()
        self.body = nn.Sequential(nn.Linear(n_in, 64), nn.GELU(),
                                  nn.Linear(64, 32), nn.GELU())
        self.head = nn.Linear(32, k)

    def forward(self, x):
        h = self.body(x)
        raw = self.head(h)
        # softplus increments keep the grid monotone by construction
        inc = torch.nn.functional.softplus(raw)
        return torch.cumsum(inc, dim=1)


def pinball(pred, y, q):
    e = y[:, None] - pred
    return torch.where(e >= 0, q[None, :] * e, (q[None, :] - 1.0) * e).mean()


def fit(Xtr, ytr, Xva, yva, n_q, epochs=800, lr=3e-3):
    torch.manual_seed(SEED)
    m = QNet(Xtr.shape[1], n_q).to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-3)
    q = torch.tensor(QUANT, dtype=torch.float32, device=DEV)
    xt = torch.tensor(Xtr, dtype=torch.float32, device=DEV)
    yt = torch.tensor(ytr, dtype=torch.float32, device=DEV)
    xv = torch.tensor(Xva, dtype=torch.float32, device=DEV)
    yv = torch.tensor(yva, dtype=torch.float32, device=DEV)
    xe = torch.tensor(Xte_holder[0], dtype=torch.float32, device=DEV)
    best, best_state, best_ep = 1e9, None, -1
    for ep in range(epochs):
        m.train()
        perm = torch.randperm(len(xt), device=DEV)
        for i in range(0, len(xt), 32):
            idx = perm[i:i + 32]
            opt.zero_grad()
            loss = pinball(m(xt[idx]), yt[idx], q)
            loss.backward()
            opt.step()
        m.eval()
        with torch.no_grad():
            v = float(pinball(m(xv), yv, q))
        if v < best - 1e-6:
            best, best_ep = v, ep
            best_state = {k: t.detach().clone() for k, t in m.state_dict().items()}
    if best_state is not None:
        m.load_state_dict(best_state)
    m.eval()
    with torch.no_grad():
        pred = m(xe).cpu().numpy()
    return pred, best, best_ep


Xte_holder = [None]


def coverage(pred, y, level):
    """Empirical coverage of the central interval implied by the quantile grid."""
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    lo = np.array([np.interp(lo_q, QUANT, row) for row in pred])
    hi = np.array([np.interp(hi_q, QUANT, row) for row in pred])
    return float(np.mean((y >= lo) & (y <= hi)))


def main():
    df = pd.read_csv(os.path.join(DATA, "residual_target_records.csv"))
    d = pd.get_dummies(df, columns=["dataset"], prefix="ds")
    cols = ["f_prefix"] + GEOM + [c for c in d.columns if c.startswith("ds_")]
    out, seq = {}, {}
    for pre in PREFIXES:
        g = d[np.isclose(d.prefix, pre)]
        tr, va, te = g[g.split == "train"], g[g.split == "validation"], g[g.split == "test"]
        if len(te) < 10 or len(va) < 5:
            continue
        sc = StandardScaler().fit(tr[cols].values)
        Xtr, Xva, Xte = (sc.transform(tr[cols].values), sc.transform(va[cols].values),
                         sc.transform(te[cols].values))
        ytr, yva, yte = tr.r_true.values, va.r_true.values, te.r_true.values
        Xte_holder[0] = Xte
        pred, bestv, bestep = fit(Xtr, ytr, Xva, yva, len(QUANT))
        pred = np.sort(pred, axis=1)
        q = torch.tensor(QUANT, dtype=torch.float32)
        pb = float(pinball(torch.tensor(pred), torch.tensor(yte), q))
        med = np.array([np.interp(0.5, QUANT, row) for row in pred])
        # constant-quantile reference: empirical grid of the training residuals
        base_grid = np.quantile(ytr, QUANT)
        pb_base = float(pinball(torch.tensor(np.tile(base_grid, (len(yte), 1))),
                                torch.tensor(yte), q))
        med_base = float(np.median(ytr))
        # information test: shuffle the geometry columns across test segments
        rng = np.random.RandomState(SEED)
        Xsh = Xte.copy()
        gi = [cols.index(c) for c in GEOM]
        for j in gi:
            Xsh[:, j] = Xsh[rng.permutation(len(Xsh)), j]
        Xte_holder[0] = Xsh
        pred_sh = np.sort(fit(Xtr, ytr, Xva, yva, len(QUANT))[0], axis=1)
        pb_sh = float(pinball(torch.tensor(pred_sh), torch.tensor(yte), q))
        Xte_holder[0] = Xte
        key = "dist@%.1f" % pre
        out[key] = dict(
            n_train=int(len(tr)), n_val=int(len(va)), n_test=int(len(te)),
            pinball=pb, crps=2 * pb, pinball_constant=pb_base, crps_constant=2 * pb_base,
            crps_ratio=pb / max(pb_base, 1e-9),
            mae_median=float(np.mean(np.abs(med - yte))),
            mae_constant=float(np.mean(np.abs(med_base - yte))),
            cov50=coverage(pred, yte, 0.50), cov80=coverage(pred, yte, 0.80),
            cov90=coverage(pred, yte, 0.90),
            cov50_const=coverage(np.tile(base_grid, (len(yte), 1)), yte, 0.50),
            cov80_const=coverage(np.tile(base_grid, (len(yte), 1)), yte, 0.80),
            cov90_const=coverage(np.tile(base_grid, (len(yte), 1)), yte, 0.90),
            pinball_shuffled=pb_sh, crps_ratio_shuffled=pb_sh / max(pb_base, 1e-9),
            information_gain=float(pb_base - pb), best_epoch=int(bestep))
    crps = [out["dist@%.1f" % p]["crps"] for p in PREFIXES if "dist@%.1f" % p in out]
    if len(crps) == 3:
        seq["crps_by_prefix"] = crps
        seq["improves_with_prefix"] = bool(crps[0] > crps[1] > crps[2])
    audit = dict(
        script="remtime_dist.py", device=DEV, seed=SEED, torch=torch.__version__,
        quantiles=list(QUANT), prefixes=list(PREFIXES),
        target="remaining time r = d - s at the moment the prefix ends",
        monotone_by_construction="softplus increments, cumulative sum",
        results=out, sequences=seq,
        interpretation="crps_ratio < 1 means the learned distribution beats a constant "
                       "reference distribution; crps_ratio_shuffled close to crps_ratio "
                       "means the geometry columns carry no information about r")
    with open(os.path.join(DATA, "remtime_dist.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print("device %s  segments %d" % (DEV, int(len(d[d.prefix == PREFIXES[0]]))))
    print("%-10s%6s%9s%9s%7s%9s%7s%7s%7s%9s" % (
        "key", "n", "crps", "crps_c", "ratio", "mae", "c50", "c80", "c90", "shuf"))
    for k in sorted(out):
        o = out[k]
        print("%-10s%6d%9.3f%9.3f%7.3f%9.3f%7.3f%7.3f%7.3f%9.3f" % (
            k, o["n_test"], o["crps"], o["crps_constant"], o["crps_ratio"],
            o["mae_median"], o["cov50"], o["cov80"], o["cov90"],
            o["crps_ratio_shuffled"]))
    print("sequences:", seq)


if __name__ == "__main__":
    main()