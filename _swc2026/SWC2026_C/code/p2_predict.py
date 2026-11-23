"""P2: prediction under artificial missing-observation windows + re-observation economics.

State kept from P1: dominant-hand wrist world position (3D).  Windows are replayed
on held-out (test-split) records; all comparators see the same windows.

Conventions fixed before looking at results:
  fps 30, context 10 frames (1/3 s), mask L in {0.2,0.5,1.0,2.0} s -> {6,15,30,60} frames
  up to 400 windows per L per split, stride L/2, no annotated-bad frame inside context+mask
  metrics: position RMSE / MAE (m), endpoint error (m), recovery jump (m)
  re-observation cost: c(T) = 0.5 + 0.2*T per request, error weight lambda = 1 per cm
"""

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from common import DATA, FIG, write_json

PANEL = np.load(os.path.join(DATA, "panel.npz"), allow_pickle=True)
STATE = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
fl, fr, dom = STATE["fl"], STATE["fr"], STATE["dom"]
badL, badR, rec, T = STATE["badL"], STATE["badR"], STATE["rec"], STATE["t"]
LENS = [6, 15, 30, 60]
CTX = 10
CAP = 400


def hand_of(r):
    return fl if dom[r] == 0 else fr


def windows(split, L, cap=CAP):
    out = []
    for r in recs[recs.split == split].rec:
        ii = np.where(rec == r)[0]
        F = hand_of(r)[ii, :3]
        bad = (badL[ii] if dom[r] == 0 else badR[ii]).astype(bool)
        ok = ~bad
        run = 0
        starts = []
        for k in range(len(ii)):
            run = run + 1 if ok[k] else 0
            if run >= CTX + L:
                starts.append(k - CTX - L + 1)
        if not starts:
            continue
        starts = np.array(starts)
        stride = max(1, L // 2)
        pick = starts[::stride]
        if len(pick) > cap:
            pick = pick[np.linspace(0, len(pick) - 1, cap).astype(int)]
        for s0 in pick:
            ctx = F[s0:s0 + CTX]
            tgt = F[s0 + CTX:s0 + CTX + L]
            post = F[s0 + CTX + L] if s0 + CTX + L < len(F) else None
            out.append((ctx, tgt, post, r))
    return out


def feats(ctx):
    rel = ctx - ctx[-1]
    vel = np.diff(ctx, axis=0)
    acc = np.diff(ctx, n=2, axis=0)
    return np.concatenate([rel.ravel(), vel[-1], acc[-1]])


def train_ridge(train, L):
    X, Y = [], []
    for ctx, tgt, _, _ in train[L]:
        f = feats(ctx)
        for h in range(L):
            X.append(np.concatenate([f, [(h + 1) / L, L / 30.0]]))
            Y.append(tgt[h] - ctx[-1])
    X, Y = np.array(X), np.array(Y)
    sc = StandardScaler().fit(X)
    mdl = Ridge(alpha=10.0).fit(sc.transform(X), Y)
    return sc, mdl


def predict(kind, ctx, L, mdl=None):
    p0 = ctx[-1]
    if kind == "hold":
        return np.repeat(p0[None], L, axis=0)
    v = ctx[-1] - ctx[-2]
    if kind == "cv":
        return p0[None] + v[None] * np.arange(1, L + 1)[:, None]
    a = (ctx[-1] - ctx[-2]) - (ctx[-2] - ctx[-3])
    h = np.arange(1, L + 1)[:, None]
    return p0[None] + v[None] * h + 0.5 * a[None] * h ** 2
    # ridge handled outside


def ridge_predict(sc, mdl, ctx, L):
    f = feats(ctx)
    X = np.array([np.concatenate([f, [(h + 1) / L, L / 30.0]]) for h in range(L)])
    return mdl.predict(sc.transform(X)) + ctx[-1]


def main():
    train = {L: windows("train", L) for L in LENS}
    test = {L: windows("test", L) for L in LENS}
    print({L: (len(train[L]), len(test[L])) for L in LENS})

    rows = []
    jumps = []
    for L in LENS:
        sc, mdl = train_ridge(train, L)
        for kind in ["hold", "cv", "ca", "ridge"]:
            errs, eps, jmp = [], [], []
            for ctx, tgt, post, r in test[L]:
                pred = ridge_predict(sc, mdl, ctx, L) if kind == "ridge" else predict(kind, ctx, L)
                e = np.linalg.norm(pred - tgt, axis=1)
                errs.append(e)
                eps.append(e[-1])
                if post is not None:
                    jmp.append(np.linalg.norm(pred[-1] - post))
            errs = np.concatenate(errs)
            rows.append(dict(L_s=L / 30.0, L_frames=L, method=kind, n_windows=len(test[L]),
                             rmse=float(np.sqrt((errs ** 2).mean())), mae=float(errs.mean()),
                             endpoint_rmse=float(np.sqrt(np.mean(np.square(eps)))),
                             jump_mean=float(np.mean(jmp)), jump_p95=float(np.percentile(jmp, 95)),
                             within_2cm=float((errs <= 0.02).mean()),
                             within_5cm=float((errs <= 0.05).mean())))
        jumps.append(dict(L_frames=L, n_windows=len(test[L])))

    pv = pd.DataFrame(rows)
    pv.to_csv(os.path.join(DATA, "p2_by_length.csv"), index=False)

    # ---- re-observation economics -------------------------------------------
    ridge = pv[pv.method == "ridge"].set_index("L_s")
    Ls = np.array(sorted(ridge.index))
    rm = ridge.loc[Ls, "rmse"].values * 100  # cm
    grid = np.arange(0.1, 2.51, 0.05)
    err_curve = np.interp(grid, Ls, rm)
    C0, C1, LAM = 0.5, 0.2, 1.0
    cost_curve = C0 / grid + C1
    J = err_curve + LAM * cost_curve
    ibest = int(np.argmin(J))
    opt = dict(T_s=float(grid[ibest]), rmse_cm=float(err_curve[ibest]), cost_per_s=float(cost_curve[ibest]),
               objective=float(J[ibest]), C0=C0, C1=C1, lambda_per_cm=LAM,
               formula="J(T)=RMSE(T)[cm] + lambda*(C0/T + C1)")
    base = {}
    for T in [0.5, 1.0]:
        e = float(np.interp(T, Ls, rm))
        base[f"fixed_{T}s"] = dict(T_s=T, rmse_cm=e, cost_per_s=C0 / T + C1, objective=e + LAM * (C0 / T + C1))
    # reactive: observe when predicted error exceeds 5 cm -> implied interval
    Treact = float(np.interp(5.0, rm, Ls)) if rm.min() <= 5 <= rm.max() else float(Ls[-1])
    e = float(np.interp(Treact, Ls, rm))
    base["reactive_5cm"] = dict(T_s=Treact, rmse_cm=e, cost_per_s=C0 / Treact + C1, objective=e + LAM * (C0 / Treact + C1))
    base["never_observe"] = dict(T_s=None, rmse_cm=float(rm[-1]), cost_per_s=0.0, objective=float(rm[-1]))

    # natural occlusion statistics from annotated bad runs
    occ = []
    for r in recs.rec:
        for flag in [badL, badR]:
            b = (flag[rec == r]).astype(int)
            d = np.diff(np.r_[0, b, 0])
            st, en = np.where(d == 1)[0], np.where(d == -1)[0]
            occ += list((en - st) / 30.0)
    occ = np.array(occ)

    out = dict(_meta=dict(convention="fixed before results: ctx=10 frames, L in {0.2,0.5,1,2}s, "
                          "up to 400 windows/L, no bad frames in window; test split only",
                          splits=dict(train_records=int((recs.split == 'train').sum()),
                                      test_records=int((recs.split == 'test').sum())),
                          windows={str(L): len(test[L]) for L in LENS}),
               by_length=rows, economics=dict(optimum=opt, baselines=base),
               occlusion=dict(n_runs=int(len(occ)), mean_s=float(occ.mean()), median_s=float(np.median(occ)),
                              p90_s=float(np.percentile(occ, 90)), max_s=float(occ.max()),
                              share_over_1s=float((occ > 1.0).mean())))
    write_json("p2_prediction.json", out)

    # ---- figures -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    for kind, g in pv.groupby("method"):
        ax.plot(g.L_s, g.rmse * 100, "o-", ms=3, label=kind)
    ax.set_xlabel("mask length L (s)"); ax.set_ylabel("position RMSE (cm)")
    ax.set_title("prediction error grows with missing duration"); ax.legend(fontsize=8); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig4_p2_error_vs_mask.png"), dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    ax.plot(grid, err_curve, label="prediction RMSE (cm)")
    ax.plot(grid, LAM * cost_curve, label="re-observation cost x lambda")
    ax.plot(grid, J, label="total objective")
    ax.axvline(grid[ibest], color="k", ls="--", lw=.8)
    ax.scatter([grid[ibest]], [J[ibest]], color="k", zorder=5)
    ax.set_xlabel("re-observation interval T (s)"); ax.set_ylabel("cm / cost units")
    ax.set_title(f"error-cost tradeoff, T*={grid[ibest]:.2f}s"); ax.legend(fontsize=8); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig5_p2_cost_tradeoff.png"), dpi=180); plt.close(fig)

    print(pv.pivot_table(index="L_s", columns="method", values="rmse").round(4))
    print("optimum", opt)
    print("bases", base)
    print("occlusion", out["occlusion"])

if __name__ == "__main__":
    main()
