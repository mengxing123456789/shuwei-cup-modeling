# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 final: multi-seed stability of the quantile predictor + preregistered verdict
+ decision-layer re-optimisation of the re-observation interval.

Protocol inherited unchanged from code/up_p2_quantile.py:
  * windows identical to p2_predict.windows (asserted at L=30, max|diff| < 1e-5);
    CTX=10, L in {6,18,30} frames = 0.2/0.6/1.0 s, train cap 150, val/test cap 400.
  * ridge_replica: Ridge(alpha=10) on p2_predict.feats + [(h+1)/L, L/30],
    StandardScaler, fitted on train windows only. Deterministic across seeds.
  * quantile: GRU(80->96, 2 layers) + shared horizon head, K=11 pinball quantiles,
    point prediction = tau=0.50. 40 epochs, model selection on validation only.
  * conformal: split conformal, absolute 3-D radius, q = np.quantile(val_err, .90).
  * units: rmse_3d_cm = 100*sqrt(mean(||e||^2)); rmse_coord_cm over all (window,horizon,axis).
Only the seed changes. The shrink arm and L=60 are dropped (shrink already rejected at
L=18/30; L=60 never beat ridge).

PREREGISTERED BAR (declared in this file before the new seeds were run;
no threshold may be edited after seeing results):
    at L=30 (1.0 s), over the MEAN of the three seeds
        rmse_3d_cm <= 5.80  AND  q90_cm <= 9.50  AND  coverage_test in [0.88, 0.93]

DECISION LAYER: J(T) = RMSE(T)[cm] + lambda*(C0/T + C1), exactly as recorded in
data/p2_prediction.json (C0=0.5, C1=0.2, lambda=1.0), on the same 0.05 s grid as
code/p2_predict.py, restricted to the measured domain [0.2, 1.0] s (no extrapolation).
The quantile RMSE(T) curve is filled between the measured points by linear interpolation
(and a monotone envelope if the three points are not increasing); flagged `interpolated`.

Outputs (new files only, no npz, nothing overwritten outside data/up_p2_final.*):
  data/up_p2_final.json   (rewritten after every finished seed)
  data/up_p2_final.txt    (3-line human summary, rewritten after every finished seed)
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))

CTX = 10
TAUS = np.array([0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 0.80, 0.90, 0.95, 0.98])
I50 = int(list(TAUS).index(0.50))
WRIST_L, WRIST_R = slice(0, 3), slice(32, 35)

SEEDS = [20261121, 20261122, 20261123]
LENS = [6, 18, 30]
EPOCHS = 40

BAR = dict(
    at="L30", statistic="mean over the 3 seeds", seeds=list(SEEDS),
    rmse_3d_max_cm=5.80, q90_max_cm=9.50,
    coverage_min=0.88, coverage_max=0.93,
    source="preregistered in code/up_p2_final.py before running seeds 20261122/20261123",
)

FORMULA_NOTE = (
    "The authoritative objective in data/p2_prediction.json is "
    "J(T)=RMSE(T)[cm]+lambda*(C0/T+C1) with C0=0.5, C1=0.2, lambda=1.0; that is the "
    "form used for the primary decision layer. The paraphrase 'C0 + C1*T + lambda*rmse(T)' "
    "does not match the stored artifact and is reported separately as alt_paraphrase."
)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
class Panel:
    def __init__(self):
        st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
        self.recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
        self.rec = st["rec"].astype(np.int64)
        self.dom = st["dom"].astype(np.int64)
        self.badL, self.badR = st["badL"], st["badR"]
        self.rich = np.concatenate([st["fl"], st["fr"], st["gl"], st["gr"]], axis=1).astype(np.float32)
        self.slices = {}
        for r in np.unique(self.rec):
            ii = np.flatnonzero(self.rec == r)
            self.slices[int(r)] = (int(ii[0]), int(ii[-1]) + 1)
        self.env = self.recs.set_index("rec").env.to_dict()
        self.dataset = self.recs.set_index("rec").dataset.to_dict()

    def windows(self, split, L, cap, ctx=CTX):
        """Same start selection as p2_predict.windows, plus rich context + ids."""
        out = {"ctx": [], "rich": [], "tgt": [], "rec": [], "start": []}
        for r in self.recs[self.recs.split == split].rec.astype(int):
            lo, hi = self.slices[r]
            d = int(self.dom[r])
            bad = (self.badL[lo:hi] if d == 0 else self.badR[lo:hi]).astype(bool)
            wrist = self.rich[lo:hi, WRIST_L if d == 0 else WRIST_R]
            ok = ~bad
            run, starts = 0, []
            for k in range(hi - lo):
                run = run + 1 if ok[k] else 0
                if run >= ctx + L:
                    starts.append(k - ctx - L + 1)
            if not starts:
                continue
            starts = np.asarray(starts)[:: max(1, L // 2)]
            if len(starts) > cap:
                starts = starts[np.linspace(0, len(starts) - 1, cap).astype(int)]
            if len(starts) == 0:
                continue
            anchor = wrist[starts + ctx - 1]
            seg = np.lib.stride_tricks.sliding_window_view(self.rich[lo:hi], ctx, axis=0)
            seg = np.transpose(seg, (0, 2, 1))[starts].copy()
            seg[:, :, 0:3] -= anchor[:, None, :]
            seg[:, :, 32:35] -= anchor[:, None, :]
            tgt = wrist[starts[:, None] + ctx + np.arange(L)[None, :]] - anchor[:, None, :]
            c3 = wrist[starts[:, None] + np.arange(ctx)[None, :]]
            out["ctx"].append(c3.astype(np.float32))
            out["rich"].append(np.nan_to_num(seg, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32))
            out["tgt"].append(np.nan_to_num(tgt, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32))
            out["rec"].append(np.full(len(starts), r, dtype=np.int64))
            out["start"].append(starts.astype(np.int64))
        if not out["ctx"]:
            return None
        return {k: np.concatenate(v) for k, v in out.items()}


# --------------------------------------------------------------------------
# ridge replica (identical maths to p2_predict.py / up_p2_quantile.py)
# --------------------------------------------------------------------------
def feats(ctx):
    rel = ctx - ctx[:, -1:, :]
    vel = np.diff(ctx, axis=1)
    acc = np.diff(ctx, n=2, axis=1)
    return np.concatenate([rel.reshape(len(ctx), -1), vel[:, -1], acc[:, -1]], axis=1)


def ridge_design(ctx, L):
    f = feats(ctx)
    n = len(ctx)
    h = np.tile(np.arange(1, L + 1) / L, n)
    lf = np.full(n * L, L / 30.0)
    return np.concatenate([np.repeat(f, L, axis=0), h[:, None], lf[:, None]], axis=1)


def ridge_fit(W, L, alpha=10.0):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    X = ridge_design(W["ctx"], L)
    Y = W["tgt"].reshape(-1, 3)
    sc = StandardScaler().fit(X)
    mdl = Ridge(alpha=alpha).fit(sc.transform(X), Y)
    return sc, mdl


def ridge_predict(sc, mdl, ctx, L):
    X = ridge_design(ctx, L)
    return mdl.predict(sc.transform(X)).reshape(len(ctx), L, 3)


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------
def metric_block(pred, W):
    e = pred - W["tgt"]
    n3 = np.linalg.norm(e, axis=2)
    return dict(
        n_windows=int(len(e)), n_frames=int(e.shape[0] * e.shape[1]),
        rmse_3d_cm=float(100 * np.sqrt(np.mean(n3 ** 2))),
        rmse_coord_cm=float(100 * np.sqrt(np.mean(e ** 2))),
        end_rmse_3d_cm=float(100 * np.sqrt(np.mean(n3[:, -1] ** 2))),
        end_rmse_coord_cm=float(100 * np.sqrt(np.mean(e[:, -1] ** 2))),
        median_err_cm=float(100 * np.median(n3)),
        mae_3d_cm=float(100 * np.mean(n3)),
        within_2cm=float(np.mean(n3 <= 0.02)), within_5cm=float(np.mean(n3 <= 0.05)))


def conformal(ev, et, alpha=0.10):
    q = float(np.quantile(ev, 1 - alpha))
    return dict(q90_cm=float(100 * q), coverage_test=float(np.mean(et <= q)),
                n_val=int(len(ev)), n_test=int(len(et)))


def per_record(pred, W):
    e = np.linalg.norm(pred - W["tgt"], axis=2)
    out = {}
    for r in np.unique(W["rec"]):
        m = W["rec"] == r
        out[str(int(r))] = dict(n_windows=int(m.sum()),
                                rmse_3d_cm=float(100 * np.sqrt(np.mean(e[m] ** 2))))
    return out


def paired(a, b):
    """a,b: {rec: rmse_3d_cm}; positive delta = a worse than b (b improves)."""
    keys = sorted(set(a) & set(b), key=int)
    va = np.array([a[k] for k in keys])
    vb = np.array([b[k] for k in keys])
    d = va - vb
    n = len(d)
    ci = float(1.96 * d.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    return dict(n_records=n, mean_delta_cm=float(d.mean()), ci95=ci,
                lower=float(d.mean() - ci), upper=float(d.mean() + ci),
                improved=int((d > 0).sum()), worsened=int((d < 0).sum()),
                per_record={k: float(x) for k, x in zip(keys, d)})


# --------------------------------------------------------------------------
# quantile model
# --------------------------------------------------------------------------
def train_quantile(Wtr, Wva, L, epochs, seed, batch=256, horizons=8, lr=2e-3, dev="cuda", log=print):
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    np.random.seed(seed)
    nq = len(TAUS)

    class QG(nn.Module):
        def __init__(self, fdim, h=96):
            super().__init__()
            self.gru = nn.GRU(fdim, h, num_layers=2, batch_first=True, dropout=0.10)
            self.head = nn.Sequential(nn.Linear(h + 2, 256), nn.GELU(), nn.Dropout(0.10),
                                      nn.Linear(256, 256), nn.GELU(), nn.Linear(256, 3 * nq))

        def forward(self, x, hf):
            _, hn = self.gru(x)
            z = hn[-1]
            B, S, _ = hf.shape
            zz = z[:, None, :].expand(B, S, z.shape[-1])
            out = self.head(torch.cat([zz, hf], dim=-1))
            return out.view(B, S, 3, nq)

    def hfeat(h, L):
        return np.stack([(h + 1) / L, np.full_like(h, L / 30.0, dtype=float)], axis=-1).astype(np.float32)

    m = QG(Wtr["rich"].shape[2]).to(dev)
    npar = int(sum(p.numel() for p in m.parameters()))
    X = torch.from_numpy(Wtr["rich"]).to(dev)
    Y = torch.from_numpy(Wtr["tgt"] * 100.0).to(dev)
    YV = Wva["tgt"]
    N = len(X)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-4)
    steps = (N + batch - 1) // batch
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * steps)
    taus = torch.tensor(TAUS, device=dev, dtype=torch.float32).view(1, 1, 1, -1)

    def predict(Wx, bs=512):
        m.eval()
        outs = []
        with torch.no_grad():
            for i in range(0, len(Wx["rich"]), bs):
                xb = torch.from_numpy(Wx["rich"][i:i + bs]).to(dev)
                B = len(xb)
                hf = torch.from_numpy(hfeat(np.tile(np.arange(L), B), L)).view(B, L, 2).to(dev)
                q = m(xb, hf).cpu().numpy() / 100.0
                outs.append(np.sort(q, axis=-1))
        return np.concatenate(outs)

    best = (1e18, -1, None)
    t0 = time.time()
    for ep in range(1, epochs + 1):
        m.train()
        perm = torch.randperm(N, device=dev)
        tot, cnt = 0.0, 0
        for i in range(steps):
            sel = perm[i * batch:(i + 1) * batch]
            B = len(sel)
            hs = torch.randint(0, L, (B, horizons), device=dev)
            hf = torch.stack([(hs + 1).float() / L, torch.full_like(hs, L / 30.0, dtype=torch.float32)], -1)
            yb = torch.gather(Y[sel], 1, hs[..., None].expand(-1, -1, 3))
            opt.zero_grad(set_to_none=True)
            pred = m(X[sel], hf)
            d = yb.unsqueeze(-1) - pred
            loss = torch.maximum(taus * d, (taus - 1) * d).mean()
            loss.backward()
            nn.utils.clip_grad_norm_(m.parameters(), 2.0)
            opt.step(); sch.step()
            tot += float(loss.detach()) * B; cnt += B
        qv = predict(Wva)
        med = qv[..., I50]
        vrmse = float(100 * np.sqrt(np.mean((med - YV) ** 2)))
        if vrmse < best[0]:
            best = (vrmse, ep, {k: v.detach().clone() for k, v in m.state_dict().items()})
        if ep % 10 == 0 or ep == 1:
            log(f"    L={L:2d} ep{ep:02d} pinball={tot/max(cnt,1):.4f} val_q50_coordRMSE={vrmse:.3f} cm")
    m.load_state_dict(best[2])
    return m, predict, dict(params=npar, best_epoch=int(best[1]), val_q50_coord_cm=float(best[0]),
                            train_seconds=round(time.time() - t0, 1))


# --------------------------------------------------------------------------
# per-seed run
# --------------------------------------------------------------------------
def run_seed(P, Wc, ridge, seed, lens, epochs, dev, log=print):
    import torch
    out, gpu = {}, 0.0
    for L in lens:
        Wtr, Wva, Wte = Wc[L]["train"], Wc[L]["validation"], Wc[L]["test"]
        log(f"  [seed {seed}] L={L} ({L/30:.2f} s) training ...")
        m, predict, info = train_quantile(Wtr, Wva, L, epochs, seed, dev=dev, log=log)
        gpu += info["train_seconds"]
        qv, qt = predict(Wva), predict(Wte)
        pv, pt = qv[..., I50], qt[..., I50]
        ev = np.linalg.norm(pv - Wva["tgt"], axis=2).ravel()
        et = np.linalg.norm(pt - Wte["tgt"], axis=2).ravel()
        blk = dict(**info, **metric_block(pt, Wte), **conformal(ev, et),
                   val_rmse_coord_cm=float(100 * np.sqrt(np.mean((pv - Wva["tgt"]) ** 2))),
                   per_record=per_record(pt, Wte))
        g = {k: v["rmse_3d_cm"] for k, v in blk["per_record"].items()}
        r = {k: v["rmse_3d_cm"] for k, v in ridge[L]["per_record"].items()}
        blk["paired"] = {"ridge_replica__to__quantile": paired(r, g)}
        out[f"L{L}"] = blk
        log(f"  [seed {seed}] L={L} rmse_3d={blk['rmse_3d_cm']:.4f} cm "
            f"q90={blk['q90_cm']:.4f} cov={blk['coverage_test']:.4f} "
            f"pair d={blk['paired']['ridge_replica__to__quantile']['mean_delta_cm']:+.4f} "
            f"({blk['paired']['ridge_replica__to__quantile']['improved']}/7 better)")
    return out, gpu


def extract_old_seed(path, seed, lens):
    """Reuse the already-finished seed from data/up_p2_quantile.json (same protocol)."""
    d = json.load(open(path, encoding="utf-8"))
    if int(d["_meta"]["seed"]) != int(seed) or int(d["_meta"].get("epochs", -1)) != EPOCHS:
        return None, 0.0
    q = d["arms"]["quantile"]
    out, gpu = {}, 0.0
    for L in lens:
        x = q.get(str(L))
        if x is None:
            return None, 0.0
        keep = ("n_windows", "n_frames", "params", "best_epoch", "val_q50_coord_cm", "train_seconds",
                "rmse_3d_cm", "rmse_coord_cm", "end_rmse_3d_cm", "end_rmse_coord_cm",
                "median_err_cm", "mae_3d_cm", "within_2cm", "within_5cm", "q90_cm",
                "coverage_test", "n_val", "n_test", "val_rmse_coord_cm", "adaptive_conformal")
        blk = {k: x[k] for k in keep if k in x}
        p = x.get("paired", {}).get("ridge_replica__to__quantile")
        if p is None:
            return None, 0.0
        blk["paired"] = {"ridge_replica__to__quantile": {
            k: p[k] for k in ("n_records", "mean_delta_cm", "ci95", "lower", "upper",
                              "improved", "worsened", "per_record") if k in p}}
        blk["source"] = "reused from data/up_p2_quantile.json (seed 20261121, epochs 40)"
        out[f"L{L}"] = blk
        gpu += float(x.get("train_seconds", 0.0))
    return out, round(gpu, 1)


# --------------------------------------------------------------------------
# aggregate + verdict
# --------------------------------------------------------------------------
def aggregate(per_seed, lens):
    agg = {}
    for L in lens:
        vals = [per_seed[s][f"L{L}"] for s in per_seed if f"L{L}" in per_seed[s]]
        if not vals:
            continue
        def stat(key):
            v = np.array([x[key] for x in vals], dtype=float)
            return dict(mean=float(v.mean()),
                        sd=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                        min=float(v.min()), max=float(v.max()), values=[float(x) for x in v])
        pd_ = [x["paired"]["ridge_replica__to__quantile"] for x in vals]
        agg[f"L{L}"] = dict(
            n_seeds=len(vals), seeds=sorted(int(s) for s in per_seed if f"L{L}" in per_seed[s]),
            rmse_3d_cm=stat("rmse_3d_cm"), rmse_coord_cm=stat("rmse_coord_cm"),
            q90_cm=stat("q90_cm"), coverage_test=stat("coverage_test"),
            paired=dict(mean_delta_cm_mean=float(np.mean([p["mean_delta_cm"] for p in pd_])),
                        mean_delta_cm_sd=float(np.std([p["mean_delta_cm"] for p in pd_], ddof=1))
                        if len(pd_) > 1 else 0.0,
                        ci95_mean=float(np.mean([p["ci95"] for p in pd_])),
                        min_improved=int(min(p["improved"] for p in pd_)),
                        n_records=int(pd_[0]["n_records"]),
                        all_seeds_all_7_better=bool(all(p["improved"] == pd_[0]["n_records"] and
                                                        p["worsened"] == 0 for p in pd_))))
    return agg


def decide(agg, seeds_done, expected_seeds, lens):
    if not all(f"L{L}" in agg for L in lens):
        return dict(passes_bar=False, status="pending",
                    reason="not all lengths finished yet: " +
                           ", ".join(f"L{L}={'yes' if f'L{L}' in agg else 'no'}" for L in lens))
    missing = [s for s in expected_seeds if s not in seeds_done]
    if missing:
        return dict(passes_bar=False, status="pending",
                    reason=f"{len(seeds_done)}/{len(expected_seeds)} seeds done; missing {missing}. "
                           f"Bar is defined on the mean of {len(expected_seeds)} seeds.")
    a = agg["L30"]
    m_rmse, m_q90, m_cov = a["rmse_3d_cm"]["mean"], a["q90_cm"]["mean"], a["coverage_test"]["mean"]
    c1 = m_rmse <= BAR["rmse_3d_max_cm"]
    c2 = m_q90 <= BAR["q90_max_cm"]
    c3 = BAR["coverage_min"] <= m_cov <= BAR["coverage_max"]
    reasons = [
        f"L30 mean rmse_3d={m_rmse:.4f} cm vs <= {BAR['rmse_3d_max_cm']:.2f} ({'PASS' if c1 else 'FAIL'}, "
        f"margin {BAR['rmse_3d_max_cm'] - m_rmse:+.4f})",
        f"mean q90={m_q90:.4f} cm vs <= {BAR['q90_max_cm']:.2f} ({'PASS' if c2 else 'FAIL'}, "
        f"margin {BAR['q90_max_cm'] - m_q90:+.4f})",
        f"mean coverage={m_cov:.4f} vs [{BAR['coverage_min']}, {BAR['coverage_max']}] "
        f"({'PASS' if c3 else 'FAIL'})",
    ]
    n_fail = int((not c1) + (not c2) + (not c3))
    return dict(passes_bar=bool(c1 and c2 and c3), status="decided",
                criteria=dict(rmse_3d=bool(c1), q90=bool(c2), coverage=bool(c3),
                              n_failed=n_fail),
                all_seeds_in_coverage_band=bool(
                    all(BAR["coverage_min"] <= v <= BAR["coverage_max"]
                        for v in a["coverage_test"]["values"])),
                reason=f"{n_fail}/3 criteria failed. " + "; ".join(reasons) + ".")


# --------------------------------------------------------------------------
# decision layer
# --------------------------------------------------------------------------
def _optimise(curve_T, curve_rmse, grid, C0, C1, lam):
    rm = np.interp(grid, curve_T, curve_rmse)
    J = rm + lam * (C0 / grid + C1)
    i = int(np.argmin(J))
    return dict(T_s=float(grid[i]), rmse_cm=float(rm[i]),
                cost_per_s=float(C0 / grid[i] + C1), objective=float(J[i]),
                boundary=bool(i == 0 or i == len(grid) - 1))


def decision_layer(agg, per_seed, lens):
    p2 = json.load(open(os.path.join(DATA, "p2_prediction.json"), encoding="utf-8"))
    opt = p2["economics"]["optimum"]
    C0, C1 = float(opt["C0"]), float(opt["C1"])
    LAM = float(opt.get("lambda_per_cm", 1.0))
    rows = sorted([r for r in p2["by_length"] if r["method"] == "ridge"], key=lambda r: r["L_s"])
    rT = np.array([r["L_s"] for r in rows], dtype=float)
    rR = np.array([r["rmse"] for r in rows], dtype=float) * 100.0

    grid_full = np.round(np.arange(0.1, 2.51, 0.05), 10)
    J_full = np.interp(grid_full, rT, rR) + LAM * (C0 / grid_full + C1)
    i_full = int(np.argmin(J_full))
    pub_check = dict(T_s=float(grid_full[i_full]), objective=float(J_full[i_full]),
                     matches_published=bool(abs(grid_full[i_full] - float(opt["T_s"])) < 1e-9 and
                                            abs(J_full[i_full] - float(opt["objective"])) < 1e-9),
                     published_T_s=float(opt["T_s"]), published_objective=float(opt["objective"]),
                     published_rmse_cm=float(opt["rmse_cm"]))

    Ts = np.array(sorted(L / 30.0 for L in lens), dtype=float)
    Rq = np.array([agg[f"L{L}"]["rmse_3d_cm"]["mean"] for L in sorted(lens, key=lambda x: x / 30.0)],
                  dtype=float)
    monotone = bool(np.all(np.diff(Rq) > 0))
    if not monotone:
        Rq = np.maximum.accumulate(Rq)

    lo, hi = float(Ts.min()), float(Ts.max())
    grid = grid_full[(grid_full >= lo - 1e-9) & (grid_full <= hi + 1e-9)]
    q = _optimise(Ts, Rq, grid, C0, C1, LAM)
    r = _optimise(rT, rR, grid, C0, C1, LAM)

    gain_pct = float(100.0 * (r["objective"] - q["objective"]) / r["objective"])

    per_seed_T = {}
    for s in sorted(per_seed):
        Rs = np.array([per_seed[s][f"L{L}"]["rmse_3d_cm"] for L in sorted(lens, key=lambda x: x / 30.0)],
                      dtype=float)
        if not np.all(np.diff(Rs) > 0):
            Rs = np.maximum.accumulate(Rs)
        per_seed_T[s] = _optimise(Ts, Rs, grid, C0, C1, LAM)

    # literal paraphrase the requester wrote: J2 = C0 + C1*T + lambda*rmse(T)
    def J2(T, curve_T, curve_rmse):
        rm = np.interp(T, curve_T, curve_rmse)
        return rm + LAM * (C0 + C1 * T)
    j2q = J2(grid, Ts, Rq)
    j2r = J2(grid, rT, rR)
    iq, ir = int(np.argmin(j2q)), int(np.argmin(j2r))
    alt = dict(formula="J2(T)=C0 + C1*T + lambda*RMSE(T)[cm]  (literal paraphrase; NOT the stored artifact)",
               T_ridge_s=float(grid[ir]), objective_ridge=float(j2r[ir]),
               T_quantile_s=float(grid[iq]), objective_quantile=float(j2q[iq]),
               gain_pct=float(100.0 * (j2r[ir] - j2q[iq]) / j2r[ir]),
               ridge_boundary=bool(ir == 0 or ir == len(grid) - 1),
               quantile_boundary=bool(iq == 0 or iq == len(grid) - 1),
               note="under this literal form the optimum sits at the lower edge of the measured "
                    "domain for both models, so the T comparison is degenerate; only the gain is informing.")

    return dict(
        formula=opt["formula"], C0=C0, C1=C1, lambda_per_cm=LAM,
        grid_step_s=0.05, grid=("0.10..2.50 step 0.05 exactly as code/p2_predict.py, "
                                "then restricted to the measured domain"),
        domain_s=[lo, hi],
        T_ridge_s=r["T_s"], objective_ridge=r["objective"], rmse_ridge_cm=r["rmse_cm"],
        T_quantile_s=q["T_s"], objective_quantile=q["objective"], rmse_quantile_cm=q["rmse_cm"],
        gain_pct=gain_pct, gain_cm_equivalent=float(r["objective"] - q["objective"]),
        interpolated=True,
        interpolation=("linear (np.interp) between the measured mean-RMSE points "
                       f"{[round(float(t), 3) for t in Ts]} s; nothing outside [{lo}, {hi}] s; "
                       + ("monotone as measured" if monotone else "monotone envelope applied")),
        curve_quantile=[dict(T_s=float(t), rmse_cm=float(v), measured=True,
                             n_seeds=agg[f"L{L}"]["n_seeds"])
                        for t, v, L in zip(Ts, Rq, sorted(lens, key=lambda x: x / 30.0))],
        curve_ridge_published=[dict(T_s=float(t), rmse_cm=float(v)) for t, v in zip(rT, rR)],
        ridge_curve_source="data/p2_prediction.json by_length (method=ridge, train cap 400)",
        ridge_published_check=pub_check,
        ridge_domain_restricted=dict(T_s=r["T_s"], objective=r["objective"],
                                     matches_published=bool(abs(r["T_s"] - float(opt["T_s"])) < 1e-9)),
        T_quantile_s_by_seed={str(k): v["T_s"] for k, v in per_seed_T.items()},
        objective_quantile_by_seed={str(k): v["objective"] for k, v in per_seed_T.items()},
        alt_paraphrase=alt,
        formula_note=FORMULA_NOTE,
    )


# --------------------------------------------------------------------------
# persistence
# --------------------------------------------------------------------------
def write_state(state, path_json, path_txt, per_seed, agg, verdict, lens):
    with open(path_json, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    dl = state.get("decision_layer") or {}
    l30 = agg.get("L30", {})
    seeds = sorted(per_seed)
    if dl:
        line2 = (f"L30 mean over {l30.get('n_seeds', 0)} seeds: rmse_3d={l30['rmse_3d_cm']['mean']:.3f}"
                 f" +-{l30['rmse_3d_cm']['sd']:.3f} cm | q90={l30['q90_cm']['mean']:.3f}"
                 f" +-{l30['q90_cm']['sd']:.3f} cm | coverage={l30['coverage_test']['mean']:.4f}"
                 f" | paired d={l30['paired']['mean_delta_cm_mean']:+.3f} cm "
                 f"({l30['paired']['min_improved']}/7 better in the worst seed)"
                 f" | T* ridge={dl['T_ridge_s']:.2f}s vs quantile={dl['T_quantile_s']:.2f}s"
                 f" | gain={dl['gain_pct']:+.1f}%")
        line1 = (f"P2 final seeds={','.join(str(s) for s in seeds)} lens={lens} epochs={EPOCHS} "
                 f"bar: L30 mean rmse_3d<={BAR['rmse_3d_max_cm']:.2f} cm, q90<={BAR['q90_max_cm']:.2f} cm, "
                 f"coverage in [{BAR['coverage_min']},{BAR['coverage_max']}]")
        line3 = (f"P2FINAL {verdict['passes_bar']} L30_rmse={l30['rmse_3d_cm']['mean']:.3f} "
                 f"L30_q90={l30['q90_cm']['mean']:.3f} gain_pct={dl['gain_pct']:.1f} "
                 f"| verdict={verdict.get('status')} {verdict['reason']}")
    else:
        line1 = f"P2 final seeds={','.join(str(s) for s in seeds)} lens={lens} epochs={EPOCHS} (partial)"
        line2 = "incomplete: " + ", ".join(f"L{L}: {'ok' if f'L{L}' in agg else 'missing'}" for L in lens)
        line3 = "P2FINAL False L30_rmse=nan L30_q90=nan gain_pct=nan | pending"
    with open(path_txt, "w", encoding="utf-8", newline="\n") as f:
        f.write(line1 + "\n" + line2 + "\n" + line3 + "\n")
    return line3


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    ap.add_argument("--lens", default=",".join(str(x) for x in LENS))
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--out", default="up_p2_final.json")
    ap.add_argument("--txt", default="up_p2_final.txt")
    ap.add_argument("--reuse-from", default="up_p2_quantile.json",
                    help="already-finished seed JSON to reuse when --reuse-seed matches")
    ap.add_argument("--reuse-seed", type=int, default=20261121)
    ap.add_argument("--fresh", action="store_true", help="ignore an existing data/up_p2_final.json")
    args = ap.parse_args()

    seeds = [int(x) for x in args.seeds.split(",")]
    lens = [int(x) for x in args.lens.split(",")]
    t_start = time.time()
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    path_json = os.path.join(DATA, args.out)
    path_txt = os.path.join(DATA, args.txt)

    state = dict(
        _meta=dict(script="code/up_p2_final.py", seeds=list(SEEDS), seeds_requested=seeds,
                   lens=lens, bar=BAR,
                   device=dev, gpu_train_seconds=0.0, epochs=args.epochs,
                   protocol=dict(ctx=CTX, caps=dict(train=150, validation=400, test=400),
                                 windows="identical to p2_predict.windows (asserted max|diff|<1e-5 at L=30)",
                                 conformal="split conformal, absolute 3-D radius, np.quantile(.90)",
                                 selection="epochs on validation records only; test evaluated once",
                                 dice="GRU(80->96,2 layers)+shared head(96+2->256->256->33), "
                                      "K=11 pinball, point=tau=0.50, horizons 8/step, AdamW lr 2e-3, "
                                      "OneCycle, 40 epochs, best val q50"),
                   dropped=["quantile_plus_shrink (rejected: 7/7 worse at L18 and L30)",
                            "L=60 (never beat ridge; skipped to save time)"],
                   decision=FORMULA_NOTE),
        per_seed={}, aggregate={}, verdict={}, decision_layer={})

    # resume: keep seeds already in the file when the signature matches
    if os.path.exists(path_json) and not args.fresh:
        try:
            old = json.load(open(path_json, encoding="utf-8"))
            om = old.get("_meta", {})
            if (om.get("seeds") == list(SEEDS) and om.get("lens") == lens and
                    int(om.get("epochs", -1)) == args.epochs and old.get("per_seed")):
                state["per_seed"] = old["per_seed"]
                print(f"resume: reusing seeds {sorted(state['per_seed'])} from {path_json}", flush=True)
        except Exception as e:
            print(f"resume ignored ({e})", flush=True)

    print(f"device={dev} seeds={seeds} lens={lens} epochs={args.epochs} bar={BAR}", flush=True)

    P = Panel()
    Wc = {}
    for L in lens:
        Wc[L] = {s: P.windows(s, L, cap) for s, cap in
                 (("train", 150), ("validation", 400), ("test", 400))}
        print(f"L={L}: " + str({s: (len(v['rec']) if v else 0) for s, v in Wc[L].items()}), flush=True)

    import p2_predict as PP
    if 30 in lens:
        ref = PP.windows("test", 30, cap=400)
        mine = Wc[30]["test"]
        assert len(ref) == len(mine["rec"]), (len(ref), len(mine["rec"]))
        dmax = 0.0
        for i, (ctx, tgt, post, r) in enumerate(ref):
            dmax = max(dmax, float(np.abs(ctx - mine["ctx"][i]).max()),
                       float(np.abs((tgt - ctx[-1]) - mine["tgt"][i]).max()))
            assert int(r) == int(mine["rec"][i])
        print(f"window identity vs p2_predict.windows: max|diff|={dmax:.3e} over {len(ref)} windows", flush=True)
        assert dmax < 1e-5

    ridge = {}
    for L in lens:
        sc, mdl = ridge_fit(Wc[L]["train"], L)
        pr = ridge_predict(sc, mdl, Wc[L]["test"]["ctx"], L)
        ev = np.linalg.norm(ridge_predict(sc, mdl, Wc[L]["validation"]["ctx"], L)
                            - Wc[L]["validation"]["tgt"], axis=2).ravel()
        et = np.linalg.norm(pr - Wc[L]["test"]["tgt"], axis=2).ravel()
        ridge[L] = dict(**metric_block(pr, Wc[L]["test"]), **conformal(ev, et),
                        per_record=per_record(pr, Wc[L]["test"]))
        print(f"ridge_replica L={L}: rmse_3d={ridge[L]['rmse_3d_cm']:.4f} "
              f"q90={ridge[L]['q90_cm']:.4f} cov={ridge[L]['coverage_test']:.4f}", flush=True)

    old_path = os.path.join(DATA, args.reuse_from)
    gpu_total = float(state["_meta"].get("gpu_train_seconds") or 0.0)
    gpu_this_run = 0.0
    for s in seeds:
        if s in state["per_seed"]:
            print(f"seed {s}: already in {path_json}, skipped", flush=True)
            continue
        reused = None
        if s == args.reuse_seed and os.path.exists(old_path):
            reused, g = extract_old_seed(old_path, s, lens)
        if reused is not None:
            state["per_seed"][str(s)] = {k: v for k, v in reused.items()}
            state["per_seed"][str(s)]["_meta"] = dict(
                seed=s, gpu_train_seconds=g, source=f"reused from data/{args.reuse_from}")
            gpu_total += g
            print(f"seed {s}: reused from {old_path} (gpu {g:.1f}s)", flush=True)
        else:
            t_seed = time.time()
            blk, g = run_seed(P, Wc, ridge, s, lens, args.epochs, dev)
            state["per_seed"][str(s)] = dict(**blk)
            state["per_seed"][str(s)]["_meta"] = dict(seed=s, gpu_train_seconds=g,
                                                      seconds=round(time.time() - t_seed, 1),
                                                      source="trained here")
            gpu_total += g
            gpu_this_run += g
            print(f"seed {s}: trained in {time.time()-t_seed:.1f}s (gpu {g:.1f}s)", flush=True)

        agg = aggregate(state["per_seed"], lens)
        verdict = decide(agg, [int(k) for k in state["per_seed"]], BAR["seeds"], lens)
        dl = decision_layer(agg, state["per_seed"], lens) if all(f"L{L}" in agg for L in lens) else {}
        state["aggregate"] = agg
        state["verdict"] = verdict
        state["decision_layer"] = dl
        state["_meta"]["gpu_train_seconds"] = round(gpu_total, 1)
        state["_meta"]["gpu_train_seconds_this_run"] = round(gpu_this_run, 1)
        state["_meta"]["gpu_train_seconds_note"] = (
            "total over the 3 seeds; the reused seed 20261121 contributes the "
            "train_seconds recorded in data/up_p2_quantile.json (same protocol)")
        state["_meta"]["gpu_train_seconds_by_seed"] = {
            k: round(float(v["_meta"]["gpu_train_seconds"]), 1) for k, v in state["per_seed"].items()}
        state["_meta"]["wall_seconds"] = round(time.time() - t_start, 1)
        state["_meta"]["seeds_done"] = sorted(int(k) for k in state["per_seed"])
        state["ridge_replica"] = {f"L{L}": {k: v[k] for k in ("rmse_3d_cm", "rmse_coord_cm",
                                                              "q90_cm", "coverage_test")}
                                  for L, v in ridge.items()}
        last = write_state(state, path_json, path_txt, state["per_seed"], agg, verdict, lens)
        print(f"[checkpoint] seeds done={sorted(state['per_seed'])} -> {path_json}", flush=True)

    final = state["decision_layer"]
    l30 = state["aggregate"]["L30"]
    print("")
    print(last, flush=True)
    print(f"P2FINAL {state['verdict']['passes_bar']} L30_rmse={l30['rmse_3d_cm']['mean']:.3f} "
          f"L30_q90={l30['q90_cm']['mean']:.3f} gain_pct={final['gain_pct']:.1f}", flush=True)
    print(f"saved -> {path_json} ; {path_txt}  ({state['_meta']['wall_seconds']}s wall, "
          f"{state['_meta']['gpu_train_seconds']}s gpu)", flush=True)


if __name__ == "__main__":
    main()