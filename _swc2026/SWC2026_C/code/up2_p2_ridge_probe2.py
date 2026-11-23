# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 v2: alpha / feature-ablation probe for the per-horizon linear model (validation only)."""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
LENS = [6, 18, 30, 60]


def rmse3(e):
    return float(100 * np.sqrt(np.mean(np.sum(e ** 2, axis=2))))


def main():
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from up_p2_quantile import Panel
    P = Panel()
    dom = {int(r): int(P.dom[r]) for r in P.recs.rec}
    out = {}

    for L in LENS:
        Wtr = P.windows("train", L, 150)
        Wva = P.windows("validation", L, 400)

        def canon(W):
            X = W["rich"].copy()
            swap = np.array([dom[int(r)] == 1 for r in W["rec"]])
            X[swap] = np.concatenate([X[swap][:, :, 32:64], X[swap][:, :, 0:32],
                                      X[swap][:, :, 72:80], X[swap][:, :, 64:72]], axis=2)
            return X

        def feats(W, mode):
            X = canon(W)
            w = X[:, :, 0:3]
            rel = (X - X[:, -1:, :]).reshape(len(X), -1)        # 800
            vel = np.diff(w, axis=1).reshape(len(X), -1)        # 27
            acc = np.diff(w, n=2, axis=1).reshape(len(X), -1)   # 24
            hand = X[:, -1, 0:32]                               # dom hand now
            other = X[:, -1, 32:64]
            geom = X[:, -1, 64:80]
            if mode == "rel+hand":
                return np.concatenate([rel, hand], axis=1)
            if mode == "rel+hand+velacc":
                return np.concatenate([rel, hand, vel, acc], axis=1)
            if mode == "hand+velacc":
                return np.concatenate([hand, vel, acc], axis=1)
            if mode == "core":
                return np.concatenate([w.reshape(len(X), -1), vel, acc, X[:, -1, 24:32]], axis=1)
            if mode == "core+other":
                return np.concatenate([w.reshape(len(X), -1), vel, acc, X[:, -1, 24:32],
                                       X[:, -1, 32:64]], axis=1)
            return np.concatenate([rel, hand, other, geom, vel, acc], axis=1)   # full

        def fit(Ftr, Ytr, Fva, alpha):
            sc = StandardScaler().fit(Ftr)
            A, B = sc.transform(Ftr), sc.transform(Fva)
            out_ = np.zeros((len(B), L, 3))
            for h in range(L):
                out_[:, h] = Ridge(alpha=alpha).fit(A, Ytr[:, h]).predict(B)
            return out_

        rows = {}
        for mode in ("full", "rel+hand+velacc", "rel+hand", "hand+velacc", "core", "core+other"):
            Ftr, Fva = feats(Wtr, mode), feats(Wva, mode)
            for alpha in (1000.0, 3000.0, 10000.0, 30000.0):
                rows[f"{mode}_a{alpha:g}"] = rmse3(fit(Ftr, Wtr["tgt"], Fva, alpha) - Wva["tgt"])
        out[str(L)] = rows
        best = sorted(rows.items(), key=lambda kv: kv[1])[:6]
        print(f"L={L} val: " + " | ".join(f"{k}={v:.3f}" for k, v in best), flush=True)

    with open(os.path.join(DATA, "up2_p2_ridge_probe2.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()