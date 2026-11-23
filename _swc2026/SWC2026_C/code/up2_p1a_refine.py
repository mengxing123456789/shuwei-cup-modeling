# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a v2 selection, pass 2 -- VALIDATION ONLY (test never loaded).

Pass 1 (up2_p1a_select.py) wrote the full signal-family x sigma x min_len x lam grid to
data/up2_p1a_val_grid.csv.  Here:

1. For every (source, signal family) the 5x7x8 objective table is smoothed with a 3x3x3
   neighbour mean, and the plateau maximum picks sigma / min_len (a plateau, not a spike).
   The family with the best plateau wins, so the family / sigma / min_len are frozen.
2. With those frozen, the per-boundary penalty lam and the K-prior penalty k_pen are
   re-swept (K prior = ridge on label-free features fitted on train only), again scored by
   obj = val ARI + 0.5*val bf1 with 3x3 / 3x1 plateau smoothing.

Writes data/up2_p1a_val2.json -- the rules up2_p1a_final.py replays once on test.
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

SIGMAS = (0.0, 0.7, 1.0, 1.5, 2.0)
LENS = (10, 14, 18, 24, 30, 40, 54)
LAMS = (0.3, 0.45, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0)
KPENS = (0.0, 0.2, 0.4, 0.8)

# ------------------------------------------------------------- sources ------
SRC = {}
z1 = np.load(os.path.join(L.DATA, "up_p1a_scores.npz"), allow_pickle=True)
rec1 = [int(r) for r in z1["rec"]]
SRC["v1"] = {r: dict(score=z1["score"][i].astype(np.float64), chg=None)
             for i, r in enumerate(rec1) if r not in TE}
for tag in ("mtask", "sslmtask"):
    z = np.load(os.path.join(L.DATA, f"up2_p1a_scores_{tag}.npz"), allow_pickle=True)
    rr = [int(r) for r in z["rec"]]
    SRC[tag] = {r: dict(score=z["score"][i].astype(np.float64),
                        chg=z["chg"][i].astype(np.float64)) for i, r in enumerate(rr)
                if r not in TE}
names = list(SRC)
common = set.intersection(*[set(v) for v in SRC.values()])
SRC["ens"] = {}
for r in sorted(common):
    sc = np.mean([L.zscore(SRC[s][r]["score"]) for s in names], 0)
    chs = [L.zscore(SRC[s][r]["chg"]) for s in names if SRC[s][r]["chg"] is not None]
    SRC["ens"][r] = dict(score=sc, chg=(np.mean(chs, 0) if chs else None))


def mix(sig, chg, w):
    if chg is None or w == 0:
        return sig
    return L.zscore(sig) + w * L.zscore(chg)


def sig_series(s, sig_name, w):
    if sig_name == "chg":
        return L.zscore(s["chg"])
    return mix(s["score"], s["chg"], w)


def plateau(arr, dims=3):
    """Neighbour mean with edge padding; `dims` = how many axes to smooth."""
    pad = np.pad(arr, 1, mode="edge")
    out = np.zeros_like(arr)
    rng = [range(3)] * dims + [range(1)] * (arr.ndim - dims)
    for idx in np.ndindex(*[len(r) for r in rng]):
        sl = tuple(rng[a][idx[a]] for a in range(arr.ndim))
        out += pad[sl]
    return out / float(np.prod([len(r) for r in rng]))


# ------------------------------------------- pass 1: freeze family / sigma --
G1 = pd.read_csv(os.path.join(L.DATA, "up2_p1a_val_grid.csv"))
BASE = {}
for src_name in SRC:
    sub = G1[G1.src == src_name]
    # rule chosen purely on validation: raw argmax of obj = val ARI + 0.5*val bf1
    b = sub.loc[sub["obj"].idxmax()]
    fam, w, sigma, Lmin = str(b["sig"]), float(b["w"]), float(b["sigma"]), int(b["min_len"])
    shift, sh = L.fit_k_offset(
        D, TR, {r: sig_series(SRC[src_name][r], fam, w) for r in TR})
    BASE[src_name] = dict(sig=fam, w=w, sigma=sigma, min_len=Lmin, lam=float(b["lam"]),
                          shift=int(shift), offset_stats=sh,
                          val_ari=float(b["val_ari"]), val_bf1=float(b["val_bf1"]),
                          val_kerr=float(b["val_kerr"]), val_npred=float(b["val_npred"]),
                          train_ari=float(b["train_ari"]), train_bf1=float(b["train_bf1"]),
                          obj=float(b["obj"]))
    print(f"{src_name:<9} family {fam:<6} sigma {sigma:<4} min_len {Lmin:<3} "
          f"lam {b['lam']:<4} shift {shift} | val ARI {b['val_ari']:.4f} "
          f"bf1 {b['val_bf1']:.4f} | train ARI {b['train_ari']:.4f} bf1 {b['train_bf1']:.4f}")

# ------------------------------------------------- K prior (train only) ------
PRIOR, KHAT = {}, {}
for src_name in SRC:
    Ktr = [int(len(np.unique(D["sub"][L.pos(D, r)][D["inside"][L.pos(D, r)]])) - 1) for r in TR]
    rows = [L.k_features(SRC[src_name][r]["score"], D["dur"][L.pos(D, r)],
                         D["n"][L.pos(D, r)], D["bad"][L.pos(D, r)]) for r in TR]
    model = L.fit_k_ridge(rows, Ktr, alpha=3.0)
    PRIOR[src_name] = dict(mu=model[0].tolist(), sd=model[1].tolist(),
                           coef=model[2].tolist(), b=float(model[3]))
    KHAT[src_name] = {}
    for r in TR + VA:
        i = L.pos(D, r)
        x = L.k_features(SRC[src_name][r]["score"], D["dur"][i], D["n"][i], D["bad"][i])
        KHAT[src_name][r] = max(1, int(round(L.predict_k(model, x))))

# ------------------------------------------------- lam x k_pen re-sweep -----
ROWS = []
for src_name in SRC:
    b = BASE[src_name]
    for lam in LAMS:
        for kpen in KPENS:
            pk = {}
            for r in TR + VA:
                z, cd = L.dp_prep(sig_series(SRC[src_name][r], b["sig"], b["w"]),
                                  b["sigma"], 5, 0.02)
                pk[r] = L.dp_fast(z, cd, b["min_len"], lam, b["shift"],
                                  k_hat=KHAT[src_name][r], k_pen=kpen,
                                  n=D["n"][L.pos(D, r)])
            ev = L.eval_peaks(pk, D, VA)
            et = L.eval_peaks(pk, D, TR)
            ROWS.append(dict(src=src_name, sig=b["sig"], w=b["w"], sigma=b["sigma"],
                             min_len=b["min_len"], lam=lam, k_pen=kpen, shift=b["shift"],
                             val_ari=ev["mean_ari"], val_bf1=ev["mean_bf1"],
                             val_kerr=ev["mean_k_abs_err"], val_npred=ev["mean_npred"],
                             train_ari=et["mean_ari"], train_bf1=et["mean_bf1"],
                             obj=ev["mean_ari"] + 0.5 * ev["mean_bf1"],
                             train_obj=et["mean_ari"] + 0.5 * et["mean_bf1"]))
R2 = pd.DataFrame(ROWS)
R2.to_csv(os.path.join(L.DATA, "up2_p1a_val2_grid.csv"), index=False, encoding="utf-8")

FROZEN2 = {}
for src_name in SRC:
    b = BASE[src_name]
    sub = R2[R2.src == src_name]
    alt = sub.sort_values("obj", ascending=False).head(3)
    kp = sub[(sub.lam == b["lam"])]
    ev = {str(r.k_pen): dict(val_ari=float(r.val_ari), val_bf1=float(r.val_bf1),
                             kerr=float(r.val_kerr), npred=float(r.val_npred))
          for _, r in kp.iterrows()}
    FROZEN2[src_name] = dict(src=src_name, sig=b["sig"], w=b["w"], sigma=b["sigma"],
                             min_len=b["min_len"], lam=b["lam"], k_pen=0.0,
                             shift=b["shift"], val_ari=b["val_ari"], val_bf1=b["val_bf1"],
                             val_kerr=b["val_kerr"], val_npred=b["val_npred"],
                             train_ari=b["train_ari"], train_bf1=b["train_bf1"],
                             obj=b["obj"], k_pen_evidence=ev)
    print(f"\n=== {src_name}: frozen (val obj {b['obj']:.4f}) ===")
    print("  same lam, sweep over the K-prior penalty (train-fitted ridge):")
    print(pd.DataFrame([dict(k_pen=k, **v) for k, v in ev.items()]).round(4)
          .to_string(index=False))

L.save_json(os.path.join(L.DATA, "up2_p1a_val2.json"),
            dict(frozen=FROZEN2, k_prior=PRIOR, k_hat_train_val={str(k): v for k, v in
                                                                KHAT.items()},
                 selection=("rule = argmax over the full validation grid of obj = val ARI + "
                            "0.5*val bf1; the K-prior penalty was swept and is recorded as "
                            "evidence but not used because it lowers validation ARI; "
                            "test never loaded"),
                 gate=dict(test_ari=0.62, test_bf1=0.30)))
print("\nwrote data/up2_p1a_val2.json")