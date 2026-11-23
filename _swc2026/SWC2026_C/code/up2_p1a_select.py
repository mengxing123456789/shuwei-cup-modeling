# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a v2 selection -- VALIDATION ONLY (test records are never loaded here).

Score sources
  v1        : v1 ensemble boundary score (data/up_p1a_scores.npz), train+val only
  mtask     : multi-task TCN (boundary + embedding change-point + bad-frame), 3-seed ensemble
  sslmtask  : same with trunk pre-trained by masked-keypoint modelling, 3-seed ensemble
  ens       : mean of the z-scored sources above (no extra training)

Signal families per source: boundary score, change-point 1-cos(emb_t, emb_t+1), and their
z-space mixes (w = 0.5, 1, 2).

Decoder: Gaussian smoothing sigma -> local maxima -> DP with minimum segment length
min_len and a per-boundary penalty lam on the IQR-normalised score (shift calibrated on
train). Selection uses the preregistered validation objective
    obj = mean ARI + 0.5 * mean boundary F1
with ties among the top five broken by the same objective on TRAIN.  up2_p1a_final.py
replays these frozen rules on test exactly once.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import up2_p1a_lib as L

D = L.load_cache()
TR, VA = L.ids(D, "train"), L.ids(D, "validation")
TE = set(L.ids(D, "test"))
assert not (set(TR + VA) & TE)

SRC = {}
z1 = np.load(os.path.join(L.DATA, "up_p1a_scores.npz"), allow_pickle=True)
rec1 = [int(r) for r in z1["rec"]]
SRC["v1"] = {r: dict(score=z1["score"][i].astype(np.float64), chg=None)
             for i, r in enumerate(rec1) if r not in TE}
for tag in ("mtask", "sslmtask"):
    p = os.path.join(L.DATA, f"up2_p1a_scores_{tag}.npz")
    if not os.path.exists(p):
        print(f"skip {tag}: no scores yet")
        continue
    z = np.load(p, allow_pickle=True)
    rr = [int(r) for r in z["rec"]]
    SRC[tag] = {r: dict(score=z["score"][i].astype(np.float64),
                        chg=z["chg"][i].astype(np.float64)) for i, r in enumerate(rr)
                if r not in TE}

if len(SRC) > 1:
    names = list(SRC)
    common = set.intersection(*[set(v) for v in SRC.values()])
    SRC["ens"] = {}
    for r in sorted(common):
        sc = np.mean([L.zscore(SRC[s][r]["score"]) for s in names], 0)
        chs = [L.zscore(SRC[s][r]["chg"]) for s in names if SRC[s][r]["chg"] is not None]
        SRC["ens"][r] = dict(score=sc, chg=(np.mean(chs, 0) if chs else None))

print("sources:", {k: len(v) for k, v in SRC.items()})

rng = np.random.default_rng(0)
for _ in range(6):
    x = rng.normal(size=400).cumsum() * 0.1 + rng.normal(size=400) * 0.3
    zs, cd = L.dp_prep(x, 0.7, 5, 0.02)
    for ml, lm in ((10, 0.6), (24, 1.0), (30, 0.3)):
        a = L.decode_dp(x, sigma=0.7, min_len=ml, lam=lm, cand_dist=5, prom_floor=0.02)
        b = L.dp_fast(zs, cd, ml, lm)
        assert np.array_equal(a, b), (ml, lm, a, b)
print("dp_fast == decode_dp on random signals")


def mix(sig, chg, w):
    if chg is None or w == 0:
        return sig
    return L.zscore(sig) + w * L.zscore(chg)


SIGMAS = (0.0, 0.7, 1.0, 1.5, 2.0)
LENS = (10, 14, 18, 24, 30, 40, 54)
LAMS = (0.3, 0.45, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0)
COLS = ("sig", "w", "sigma", "min_len", "lam", "shift", "val_ari", "val_bf1",
        "val_kerr", "val_npred", "train_ari", "train_bf1", "obj", "train_obj")

GRID = []
for src_name in list(SRC):
    shift, sh = L.fit_k_offset(D, TR, {r: SRC[src_name][r]["score"] for r in TR})
    print(f"\n{src_name}: train localisation offset {sh}")
    fams = [("score", 0.0)]
    if any(v["chg"] is not None for v in SRC[src_name].values()):
        fams += [("chg", 0.0), ("mix0.5", 0.5), ("mix1", 1.0), ("mix2", 2.0)]
    for sig_name, w in fams:
        first = len(GRID)
        for sigma in SIGMAS:
            cache = {}
            for r in TR + VA:
                if sig_name == "chg":
                    x = L.zscore(SRC[src_name][r]["chg"])
                else:
                    x = mix(SRC[src_name][r]["score"], SRC[src_name][r]["chg"], w)
                cache[r] = L.dp_prep(x, sigma, 5, 0.02)
            for Lmin in LENS:
                for lam in LAMS:
                    pk = {r: L.dp_fast(cache[r][0], cache[r][1], Lmin, lam, shift,
                                       n=D["n"][L.pos(D, r)]) for r in TR + VA}
                    ev = L.eval_peaks(pk, D, VA)
                    et = L.eval_peaks(pk, D, TR)
                    GRID.append(dict(src=src_name, sig=sig_name, w=float(w), sigma=sigma,
                                     min_len=Lmin, lam=lam, shift=shift,
                                     val_ari=ev["mean_ari"], val_bf1=ev["mean_bf1"],
                                     val_kerr=ev["mean_k_abs_err"],
                                     val_npred=ev["mean_npred"],
                                     train_ari=et["mean_ari"], train_bf1=et["mean_bf1"],
                                     obj=ev["mean_ari"] + 0.5 * ev["mean_bf1"],
                                     train_obj=et["mean_ari"] + 0.5 * et["mean_bf1"]))
        df = pd.DataFrame(GRID[first:]).sort_values("obj", ascending=False)
        print(f"  {sig_name:<6} best val obj {df.obj.iloc[0]:.4f} "
              f"(ARI {df.val_ari.iloc[0]:.4f} bf1 {df.val_bf1.iloc[0]:.4f} "
              f"kerr {df.val_kerr.iloc[0]:.2f}) train obj {df.train_obj.iloc[0]:.4f}")

G = pd.DataFrame(GRID)
G.to_csv(os.path.join(L.DATA, "up2_p1a_val_grid.csv"), index=False, encoding="utf-8")
print(f"\ngrid rows {len(G)}")

FROZEN = {}
for src_name in SRC:
    g = G[G.src == src_name].sort_values("obj", ascending=False).head(20)
    pick = g.head(5).sort_values("train_obj", ascending=False).iloc[0]
    d = {k: pick[k] for k in COLS}
    FROZEN[src_name] = dict(src=src_name, sig=str(d["sig"]), w=float(d["w"]),
                            sigma=float(d["sigma"]), min_len=int(d["min_len"]),
                            lam=float(d["lam"]), shift=int(d["shift"]),
                            val_ari=float(d["val_ari"]), val_bf1=float(d["val_bf1"]),
                            val_kerr=float(d["val_kerr"]), val_npred=float(d["val_npred"]),
                            train_ari=float(d["train_ari"]),
                            train_bf1=float(d["train_bf1"]), obj=float(d["obj"]))
    print(f"\n=== {src_name}: frozen rule (val obj {d['obj']:.4f}) ===")
    print(pd.DataFrame(g.head(8)).round(4).to_string(index=False))

PRIOR = {}
for src_name in SRC:
    Ktr = [int(len(np.unique(D["sub"][L.pos(D, r)][D["inside"][L.pos(D, r)]])) - 1) for r in TR]
    rows = [L.k_features(SRC[src_name][r]["score"], D["dur"][L.pos(D, r)],
                         D["n"][L.pos(D, r)], D["bad"][L.pos(D, r)]) for r in TR]
    model = L.fit_k_ridge(rows, Ktr, alpha=3.0)
    PRIOR[src_name] = dict(mu=model[0].tolist(), sd=model[1].tolist(),
                           coef=model[2].tolist(), b=float(model[3]))
    pick = FROZEN[src_name]
    pk = {}
    for r in VA:
        i = L.pos(D, r)
        x = L.k_features(SRC[src_name][r]["score"], D["dur"][i], D["n"][i], D["bad"][i])
        k = max(1, int(round(L.predict_k(model, x))))
        if pick["sig"] == "chg":
            sg = L.zscore(SRC[src_name][r]["chg"])
        else:
            sg = mix(SRC[src_name][r]["score"], SRC[src_name][r]["chg"], pick["w"])
        pk[r] = L.decode_topk(sg, k, sigma=pick["sigma"], min_len=pick["min_len"],
                              shift=pick["shift"], n=D["n"][i])
    ev = L.eval_peaks(pk, D, VA, "kprior_topk")
    print(f"{src_name}: K-prior top-k on val -> ARI {ev['mean_ari']:.4f} "
          f"bf1 {ev['mean_bf1']:.4f} kerr {ev['mean_k_abs_err']:.2f}")
    FROZEN[src_name]["kprior_topk_val"] = dict(ari=ev["mean_ari"], bf1=ev["mean_bf1"],
                                              kerr=ev["mean_k_abs_err"])

L.save_json(os.path.join(L.DATA, "up2_p1a_val.json"),
            dict(frozen=FROZEN, k_prior=PRIOR,
                 selection=("val-only grid; obj = val ARI + 0.5*val bf1; tie-break among the "
                            "top-5 rules by the same objective on train; test never loaded"),
                 gate=dict(test_ari=0.62, test_bf1=0.30),
                 n_val=len(VA), n_train=len(TR), grid_rows=int(len(G))))
print("\nwrote data/up2_p1a_val.json")