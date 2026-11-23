# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 v2 config D: validation-chosen combination of the two strongest families.

Selection rule (frozen before the test read):
  1. per-horizon ridge backbone: grid over train-window cap {150, 400} x alpha
     {3e3, 1e4, 3e4, 1e5}; pick the cell with the lowest VALIDATION 3-D RMSE;
  2. TCN arm-A point predictions (3 seeds, seed-mean) are blended with the chosen
     ridge: w in {0.00,0.05,...,1.00}; pick the w with the lowest VALIDATION RMSE;
  3. report the test metrics of the single chosen pair, once.
This is the "hierarchical shrinkage" step of direction 1 in its predictive form:
shrink the nonlinear predictor toward the stable linear backbone by a weight
estimated on held-out records, not on test.

Writes data/up2_p2_tune.json.
"""
import json
import os

import numpy as np

from up2_p2_models import (CTX, DATA, GATE, LENS, SEEDS, TAUS, Data, conformal,
                           feats_ridge, fit_ridge, metric_block, per_horizon,
                           pred_ridge, rmse3, torch_from, train_arm)

L = 30
CAPS = (150, 400)
ALPHAS = (3e3, 1e4, 3e4, 1e5)
WS = [round(x, 2) for x in np.arange(0, 1.0001, 0.05)]


def main():
    d = Data()
    P = d.P
    W = {cap: {s: P.windows(s, L, c) for s, c in
               (("train", cap), ("validation", 400), ("test", 400))}
         for cap in CAPS}
    for cap in CAPS:
        for s in ("train", "validation", "test"):
            W[cap][s]["x"] = d.canon(W[cap][s])
    print("windows:", {c: {s: len(W[c][s]["rec"]) for s in W[c]} for c in CAPS}, flush=True)

    # ---- 1) backbone grid, selected on validation ----
    grid = []
    best = None
    for cap in CAPS:
        Ftr = feats_ridge(W[cap]["train"]["x"], L)
        Fva = feats_ridge(W[cap]["validation"]["x"], L)
        Fte = feats_ridge(W[cap]["test"]["x"], L)
        ytr = W[cap]["train"]["tgt"]
        for a in ALPHAS:
            sc, ms = fit_ridge(Ftr, ytr, alpha=a)
            pv = pred_ridge(sc, ms, Fva, L)
            vr = rmse3(pv - W[cap]["validation"]["tgt"])
            grid.append(dict(cap=cap, alpha=a, val_rmse_3d_cm=vr))
            print(f"  ridge cap={cap} alpha={a:g} val_3d={vr:.4f}", flush=True)
            if best is None or vr < best["val"]:
                best = dict(cap=cap, alpha=a, val=vr, sc=sc, ms=ms,
                            pv=pv, pt=pred_ridge(sc, ms, Fte, L))
    print(f"chosen backbone: cap={best['cap']} alpha={best['alpha']:g} val={best['val']:.4f}", flush=True)

    Wv, Wt = W[best["cap"]]["validation"], W[best["cap"]]["test"]
    ridge_v, ridge_t = best["pv"], best["pt"]

    # ---- 2) TCN family at L30, 3 seeds ----
    Wtr = W[best["cap"]]["train"]
    preds_v, preds_t = [], []
    for seed in SEEDS:
        Wtr["y"] = Wtr["tgt"]; Wv["y"] = Wv["tgt"]
        m, predict, info = train_arm("A", Wtr, Wv, L, seed, 50, "cuda", log=print)
        _, mv = predict(torch_from(Wv["x"], "cuda"))
        _, mt = predict(torch_from(Wt["x"], "cuda"))
        preds_v.append(mv); preds_t.append(mt)
        print(f"  A seed {seed}: val={rmse3(mv-Wv['tgt']):.4f} test={rmse3(mt-Wt['tgt']):.4f}", flush=True)
    av, at = np.mean(preds_v, 0), np.mean(preds_t, 0)

    # ---- 3) blend weight on validation ----
    blend = []
    for w in WS:
        pv = w * ridge_v + (1 - w) * av
        vr = rmse3(pv - Wv["tgt"])
        blend.append(dict(w=w, val_rmse_3d_cm=vr))
    bw = min(blend, key=lambda r: r["val_rmse_3d_cm"])
    print(f"chosen blend w(ridge)={bw['w']} val={bw['val_rmse_3d_cm']:.4f}", flush=True)

    pv = bw["w"] * ridge_v + (1 - bw["w"]) * av
    pt = bw["w"] * ridge_t + (1 - bw["w"]) * at
    ev = np.linalg.norm(pv - Wv["tgt"], axis=2).ravel()
    et = np.linalg.norm(pt - Wt["tgt"], axis=2).ravel()
    res = dict(metric_block(pt, Wt["tgt"]), **conformal(ev, et),
               val_rmse_3d_cm=rmse3(pv - Wv["tgt"]),
               per_horizon_rmse_3d_cm=per_horizon(pt, Wt["tgt"]))
    print("D", {k: round(v, 4) if isinstance(v, float) else v for k, v in res.items()}, flush=True)

    c1 = res["rmse_3d_cm"] <= GATE["rmse_3d_max_cm"]
    c2 = res["q90_cm"] <= GATE["q90_max_cm"]
    c3 = GATE["coverage_min"] <= res["coverage_test"] <= GATE["coverage_max"]

    out = dict(_meta=dict(script="code/up2_p2_tune.py", L=L, caps=CAPS, alphas=list(ALPHAS),
                          ws=WS, seeds=SEEDS, epochs=50,
                          selection="cap/alpha and blend weight chosen on validation only; "
                                    "one test read of the chosen pair",
                          caveat="single run of the TCN family for this config (3 seeds), "
                                 "not a new architecture"),
               backbone_grid=grid, chosen_backbone=dict(cap=best["cap"], alpha=best["alpha"],
                                                        val_rmse_3d_cm=best["val"],
                                                        test_rmse_3d_cm=rmse3(ridge_t - Wt["tgt"]),
                                                        test_q90_cm=float(100*np.quantile(
                                                            np.linalg.norm(ridge_v - Wv["tgt"], axis=2), .9)),
                                                        test_coverage=float(np.mean(
                                                            np.linalg.norm(ridge_t - Wt["tgt"], axis=2)
                                                            <= np.quantile(np.linalg.norm(ridge_v - Wv["tgt"], axis=2), .9)))),
               blend_grid=blend, chosen_blend=dict(w_ridge=bw["w"], val_rmse_3d_cm=bw["val_rmse_3d_cm"]),
               config_D=res, gate=dict(criteria=dict(rmse_3d=bool(c1), q90=bool(c2), coverage=bool(c3)),
                                       detail=(f"L30 rmse_3d={res['rmse_3d_cm']:.4f} vs <=5.50 "
                                               f"({'PASS' if c1 else 'FAIL'}); q90={res['q90_cm']:.4f} "
                                               f"vs <=9.00 ({'PASS' if c2 else 'FAIL'}); "
                                               f"coverage={res['coverage_test']:.4f} vs [0.88,0.93] "
                                               f"({'PASS' if c3 else 'FAIL'})"),
                                       n_failed=int((not c1) + (not c2) + (not c3))),
               passes=bool(c1 and c2 and c3))
    p = os.path.join(DATA, "up2_p2_tune.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"saved -> {p}")


if __name__ == "__main__":
    main()