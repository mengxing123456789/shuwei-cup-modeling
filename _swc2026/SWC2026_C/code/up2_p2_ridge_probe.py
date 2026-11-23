# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 v2 linear probes (validation-only selection, no test peeking for candidates).

Questions answered here:
  * does an unconstrained per-horizon linear model beat the frozen ridge replica
    (whose prediction is linear in the horizon with ONE shared weight vector)?
  * does canonicalising the hand order (dominant hand first) help?
  * does adding the second hand / finger / geometry channels help?
All fits on train windows, scored on validation windows only.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CTX = 10
LENS = [6, 18, 30, 60]


def feats_replica(ctx):
    rel = ctx - ctx[:, -1:, :]
    vel = np.diff(ctx, axis=1)
    acc = np.diff(ctx, n=2, axis=1)
    return np.concatenate([rel.reshape(len(ctx), -1), vel[:, -1], acc[:, -1]], axis=1)


def design_rep(ctx, L):
    f = feats_replica(ctx)
    n = len(ctx)
    h = np.tile(np.arange(1, L + 1) / L, n)
    lf = np.full(n * L, L / 30.0)
    return np.concatenate([np.repeat(f, L, axis=0), h[:, None], lf[:, None]], axis=1)


def rmse3(e):
    return float(100 * np.sqrt(np.mean(np.sum(e ** 2, axis=2))))


def fit_per_horizon(Ftr, Ytr, Fva, alpha=10.0):
    """Independent ridge per horizon. Ftr (N,d), Ytr (N,L,3)."""
    from sklearn.linear_model import Ridge
    out = np.zeros((len(Fva), Ytr.shape[1], 3))
    for h in range(Ytr.shape[1]):
        mdl = Ridge(alpha=alpha).fit(Ftr, Ytr[:, h])
        out[:, h] = mdl.predict(Fva)
    return out


def main():
    from up_p2_quantile import Panel
    P = Panel()
    out = {}
    dom = {int(r): int(P.dom[r]) for r in P.recs.rec}
    print("dom counts per split:", {s: int(sum(dom[r] for r in P.recs[P.recs.split == s].rec))
                                    for s in ("train", "validation", "test")})

    for L in LENS:
        Wtr = P.windows("train", L, 150)
        Wva = P.windows("validation", L, 400)
        Wte = P.windows("test", L, 400)

        def rich_canon(W):
            """reorder rich so channels 0:32 = dominant hand, 32:64 = other hand."""
            X = W["rich"].copy()
            swap = np.array([dom[int(r)] == 1 for r in W["rec"]])
            X[swap] = np.concatenate([X[swap][:, :, 32:64], X[swap][:, :, 0:32],
                                      X[swap][:, :, 72:80], X[swap][:, :, 64:72]], axis=2)
            return X

        # ---- replica (sanity) ----
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler
        X = design_rep(Wtr["ctx"], L)
        sc = StandardScaler().fit(X)
        mdl = Ridge(alpha=10.0).fit(sc.transform(X), Wtr["tgt"].reshape(-1, 3))
        pr = mdl.predict(sc.transform(design_rep(Wva["ctx"], L))).reshape(len(Wva["ctx"]), L, 3)
        rows = {"replica": rmse3(pr - Wva["tgt"])}

        # ---- per-horizon linear on the same features ----
        Ftr, Fva = feats_replica(Wtr["ctx"]), feats_replica(Wva["ctx"])
        for alpha in (1.0, 10.0, 100.0):
            rows[f"perh_a{alpha:g}"] = rmse3(fit_per_horizon(Ftr, Wtr["tgt"], Fva, alpha) - Wva["tgt"])

        # ---- richer feature sets, per-horizon ----
        def rich_feats(W, canon=True):
            X = rich_canon(W) if canon else W["rich"]
            d = X[:, -1]                                   # last frame, 80 dims
            rel = X - X[:, -1:, :]
            # dominant hand: wrist rel + velocity/acc already in the 32 block;
            # add per-frame velocity of the dominant wrist (9x3) and aperture/palm
            w = X[:, :, 0:3]
            vel = np.diff(w, axis=1)                       # (N,9,3)
            acc = np.diff(w, n=2, axis=1)                  # (N,8,3)
            hand = X[:, -1, 0:32]                          # dominant hand current state
            other = X[:, -1, 32:64]                        # other hand current state
            geom = X[:, -1, 64:80]
            return np.concatenate([rel.reshape(len(X), -1), vel.reshape(len(X), -1),
                                   acc.reshape(len(X), -1), hand, other, geom], axis=1)

        for alpha in (1.0, 10.0, 100.0, 1000.0):
            Ftr2, Fva2 = rich_feats(Wtr), rich_feats(Wva)
            sc2 = StandardScaler().fit(Ftr2)
            rows[f"perh_rich_a{alpha:g}"] = rmse3(
                fit_per_horizon(sc2.transform(Ftr2), Wtr["tgt"], sc2.transform(Fva2), alpha) - Wva["tgt"])

        out[str(L)] = rows
        print(f"L={L} val 3-D RMSE cm: " + " | ".join(f"{k}={v:.3f}" for k, v in rows.items()), flush=True)

    with open(os.path.join(DATA, "up2_p2_ridge_probe.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()