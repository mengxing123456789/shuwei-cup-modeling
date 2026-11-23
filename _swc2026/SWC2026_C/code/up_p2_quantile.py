# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 upgrade: quantile (pinball) prediction + hierarchical shrinkage + error decomposition.

Baselines / protocol (fixed BEFORE looking at any result of the new arms):
  * windows: exactly the selection rule of p2_predict.windows (clean ctx+L run,
    stride L//2, per-record cap), CTX=10, L in {6,18,30,60} frames = 0.2/0.6/1.0/2.0 s.
    train cap=150, validation cap=400, test cap=400  (== p2_interval.py).
  * ridge_replica: sklearn Ridge(alpha=10) on p2_predict.feats + [(h+1)/L, L/30],
    StandardScaler, fitted per L on train windows only. This is the predictor whose
    conformal q90 at L=30 is 10.127 cm in data/p2_interval.json.
  * conformal: split conformal, absolute 3-D error radius, q = quantile(val_err, .90),
    coverage measured on test. Same formula as p2_interval.py (np.quantile, linear).
  * units: rmse_3d_cm = 100*sqrt(mean(||e||_2^2)); rmse_coord_cm = rmse_3d_cm/sqrt(3)
    only when errors are isotropic -- here both are computed from the same residuals,
    rmse_coord_cm = 100*sqrt(mean(e^2)) over all (window,horizon,axis).
  * model selection (epochs, shrinkage kappa) on validation records only; the test
    split is evaluated once, after every choice is frozen.

Arms (one change at a time):
  ridge_replica        : the frozen ridge recipe above.
  quantile             : GRU(80->96,2 layers) encoder + shared horizon head,
                         K=11 pinball quantiles, point prediction = tau=0.50.
                         Same windows/targets as ridge_replica (paired per record).
  quantile_plus_shrink : quantile q50 + group residual offsets (dataset x env_group),
                         estimated on validation with leave-one-record-out, shrunk
                         toward the global offset by w=n/(n+kappa), kappa by LOO.

Outputs (new files, never overwrite existing JSON):
  data/up_p2_quantile.json, data/up_p2_decomp.json
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
SEED = 20261121
CTX = 10
LENS = [6, 18, 30, 60]
TAUS = np.array([0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 0.80, 0.90, 0.95, 0.98])
I50 = int(list(TAUS).index(0.50))
WRIST_L, WRIST_R = slice(0, 3), slice(32, 35)


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
        self.group = {int(r): f"{self.dataset[r]}|{self.env[r].split('_')[0]}" for r in self.recs.rec}
        self.env_group = {int(r): self.env[r].split("_")[0] for r in self.recs.rec}

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
            anchor = wrist[starts + ctx - 1]                       # (W,3)
            seg = np.lib.stride_tricks.sliding_window_view(self.rich[lo:hi], ctx, axis=0)
            seg = np.transpose(seg, (0, 2, 1))[starts].copy()      # (W,ctx,80)
            seg[:, :, 0:3] -= anchor[:, None, :]
            seg[:, :, 32:35] -= anchor[:, None, :]
            tgt = wrist[starts[:, None] + ctx + np.arange(L)[None, :]] - anchor[:, None, :]
            c3 = wrist[starts[:, None] + np.arange(ctx)[None, :]]  # raw wrist ctx (ridge feats)
            out["ctx"].append(c3.astype(np.float32))
            out["rich"].append(np.nan_to_num(seg, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32))
            out["tgt"].append(np.nan_to_num(tgt, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32))
            out["rec"].append(np.full(len(starts), r, dtype=np.int64))
            out["start"].append(starts.astype(np.int64))
        if not out["ctx"]:
            return None
        return {k: np.concatenate(v) for k, v in out.items()}


# --------------------------------------------------------------------------
# ridge replica (identical maths to p2_predict.py)
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
    e = pred - W["tgt"]                                # (N,L,3) metres
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
                                rmse_3d_cm=float(100 * np.sqrt(np.mean(e[m] ** 2))),
                                rmse_coord_cm=float(100 * np.sqrt(np.mean(e[m] ** 2) / 3)))
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
def train_quantile(Wtr, Wva, L, epochs, batch=256, horizons=8, lr=2e-3, dev="cuda", log=print):
    import torch
    import torch.nn as nn
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    nq = len(TAUS)

    class QG(nn.Module):
        def __init__(self, fdim, h=96):
            super().__init__()
            self.gru = nn.GRU(fdim, h, num_layers=2, batch_first=True, dropout=0.10)
            self.head = nn.Sequential(nn.Linear(h + 2, 256), nn.GELU(), nn.Dropout(0.10),
                                      nn.Linear(256, 256), nn.GELU(), nn.Linear(256, 3 * nq))

        def forward(self, x, hf):
            _, hn = self.gru(x)
            z = hn[-1]                                        # (B,h)
            B, S, _ = hf.shape
            zz = z[:, None, :].expand(B, S, z.shape[-1])
            out = self.head(torch.cat([zz, hf], dim=-1))
            return out.view(B, S, 3, nq)

    def hfeat(h, L):
        return np.stack([(h + 1) / L, np.full_like(h, L / 30.0, dtype=float)], axis=-1).astype(np.float32)

    m = QG(Wtr["rich"].shape[2]).to(dev)
    npar = int(sum(p.numel() for p in m.parameters()))
    X = torch.from_numpy(Wtr["rich"]).to(dev)
    Y = torch.from_numpy(Wtr["tgt"] * 100.0).to(dev)          # cm
    XV = torch.from_numpy(Wva["rich"]).to(dev)
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
        return np.concatenate(outs)                            # (N,L,3,nq) metres

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
        if ep % 5 == 0 or ep == 1:
            log(f"    L={L:2d} ep{ep:02d} pinball={tot/max(cnt,1):.4f} val_q50_coordRMSE={vrmse:.3f} cm")
    m.load_state_dict(best[2])
    return m, predict, dict(params=npar, best_epoch=int(best[1]), val_q50_coord_cm=float(best[0]),
                            train_seconds=round(time.time() - t0, 1))


# --------------------------------------------------------------------------
# hierarchical shrinkage of group residual offsets (validation LOO)
# --------------------------------------------------------------------------
def shrink_apply(pred, W, L, kappa, keyfn):
    """Offsets from validation residuals with leave-one-record-out; returns
    LOO-corrected validation predictions (honest recalibration)."""
    resid = W["tgt"] - pred                                    # (N,L,3)
    nb = 3
    bucket = np.minimum((np.arange(L) * nb) // L, nb - 1)
    groups = np.array([keyfn(r) for r in W["rec"]])
    recs = np.unique(W["rec"])

    def offsets(mask):
        g_all = groups[mask]
        r_all = resid[mask]
        glob = np.stack([r_all[:, bucket == b].reshape(-1, 3).mean(axis=0) for b in range(nb)])
        tab = {}
        for g in np.unique(g_all):
            sel = g_all == g
            n = int(sel.sum())
            w = n / (n + kappa)
            bg = np.stack([r_all[sel][:, bucket == b].reshape(-1, 3).mean(axis=0) for b in range(nb)])
            tab[str(g)] = w * bg + (1 - w) * glob
        return tab, glob

    corr = pred.copy()
    for r in recs:
        hold = W["rec"] == r
        tab, glob = offsets(~hold)
        off = tab.get(str(keyfn(int(r))), glob)
        corr[hold] = pred[hold] + off[bucket][None]
    return corr


def shrink_test_offsets(pred_val, Wva, L, kappa, keyfn, recs_te):
    resid = Wva["tgt"] - pred_val
    nb = 3
    bucket = np.minimum((np.arange(L) * nb) // L, nb - 1)
    groups = np.array([keyfn(r) for r in Wva["rec"]])
    glob = np.stack([resid[:, bucket == b].reshape(-1, 3).mean(axis=0) for b in range(nb)])
    tab = {}
    for g in np.unique(groups):
        sel = groups == g
        n = int(sel.sum())
        w = n / (n + kappa)
        bg = np.stack([resid[sel][:, bucket == b].reshape(-1, 3).mean(axis=0) for b in range(nb)])
        tab[str(g)] = dict(n_windows=n, weight=float(w), offset=(w * bg + (1 - w) * glob).tolist())
    keys_te = [str(keyfn(int(r))) for r in recs_te]
    off = np.stack([np.array(tab[k]["offset"]) if k in tab else glob for k in keys_te])
    return dict(groups=tab, global_offset=glob.tolist(),
                test_assign={k: sum(1 for x in keys_te if x == k) for k in sorted(set(keys_te))}), off, bucket


GROUP = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["all", "quantile", "decomp"])
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--lens", default="6,18,30,60")
    ap.add_argument("--out", default="up_p2_quantile.json")
    args = ap.parse_args()
    lens = [int(x) for x in args.lens.split(",")]
    t_start = time.time()
    dev = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    print(f"device={dev} seed={SEED} lens={lens} epochs={args.epochs}", flush=True)

    P = Panel()
    GROUP.update(P.group)
    W = {}
    for L in lens:
        W[L] = {s: P.windows(s, L, cap) for s, cap in
                (("train", 150), ("validation", 400), ("test", 400))}
        print(f"L={L}: " + str({s: (len(v['rec']) if v else 0) for s, v in W[L].items()}), flush=True)

    # ---- verify identity with p2_predict.windows ---------------------------
    import p2_predict as PP
    ref = PP.windows("test", 30, cap=400)
    mine = W[30]["test"] if 30 in W else None
    if mine is not None:
        assert len(ref) == len(mine["rec"]), (len(ref), len(mine["rec"]))
        dmax = 0.0
        for i, (ctx, tgt, post, r) in enumerate(ref):
            # p2_predict yields ABSOLUTE future positions; ours are displacements
            # from ctx[-1] (which is what train_ridge/predict also regress on).
            dmax = max(dmax, float(np.abs(ctx - mine["ctx"][i]).max()),
                       float(np.abs((tgt - ctx[-1]) - mine["tgt"][i]).max()))
            assert int(r) == int(mine["rec"][i])
        print(f"window identity vs p2_predict.windows: max|diff|={dmax:.3e} over {len(ref)} windows", flush=True)
        assert dmax < 1e-5

    arms = {}
    gpu_seconds = 0.0
    for L in lens:
        Wtr, Wva, Wte = W[L]["train"], W[L]["validation"], W[L]["test"]
        print(f"\n=== L={L} ({L/30:.2f} s) ===", flush=True)
        sc, mdl = ridge_fit(Wtr, L)
        pr_va, pr_te = ridge_predict(sc, mdl, Wva["ctx"], L), ridge_predict(sc, mdl, Wte["ctx"], L)
        np.savez_compressed(os.path.join(DATA, f"up_p2_ridge_pred_L{L}.npz"),
                            val=pr_va.astype(np.float32), test=pr_te.astype(np.float32),
                            val_rec=Wva["rec"], test_rec=Wte["rec"],
                            val_tgt=Wva["tgt"], test_tgt=Wte["tgt"])
        ev = np.linalg.norm(pr_va - Wva["tgt"], axis=2).ravel()
        et = np.linalg.norm(pr_te - Wte["tgt"], axis=2).ravel()
        arms.setdefault("ridge_replica", {})[str(L)] = dict(
            **metric_block(pr_te, Wte), **conformal(ev, et),
            val_rmse_coord_cm=float(100 * np.sqrt(np.mean((pr_va - Wva["tgt"]) ** 2))),
            per_record=per_record(pr_te, Wte))
        print("  ridge_replica", {k: round(v, 4) for k, v in arms["ridge_replica"][str(L)].items()
                                 if k in ("rmse_3d_cm", "rmse_coord_cm", "q90_cm", "coverage_test")}, flush=True)

        m, predict, info = train_quantile(Wtr, Wva, L, args.epochs, dev=dev)
        gpu_seconds += info["train_seconds"]
        qv, qt = predict(Wva), predict(Wte)
        np.savez_compressed(os.path.join(DATA, f"up_p2_quantile_pred_L{L}.npz"),
                            val=qv.astype(np.float32), test=qt.astype(np.float32),
                            val_rec=Wva["rec"], test_rec=Wte["rec"],
                            val_tgt=Wva["tgt"], test_tgt=Wte["tgt"])
        pv, pt = qv[..., I50], qt[..., I50]
        ev = np.linalg.norm(pv - Wva["tgt"], axis=2).ravel()
        et = np.linalg.norm(pt - Wte["tgt"], axis=2).ravel()
        arms.setdefault("quantile", {})[str(L)] = dict(
            **info, **metric_block(pt, Wte), **conformal(ev, et),
            val_rmse_coord_cm=float(100 * np.sqrt(np.mean((pv - Wva["tgt"]) ** 2))),
            per_record=per_record(pt, Wte))
        print("  quantile", {k: round(v, 4) for k, v in arms["quantile"][str(L)].items()
                            if k in ("rmse_3d_cm", "rmse_coord_cm", "q90_cm", "coverage_test")}, flush=True)

        # locally adaptive (normalized) conformal from the model's own quantiles
        sv = np.sqrt(np.mean((qv[..., 8] - qv[..., 2]) ** 2, axis=2)) + 1e-4   # tau .90-.10
        st = np.sqrt(np.mean((qt[..., 8] - qt[..., 2]) ** 2, axis=2)) + 1e-4
        zv = np.linalg.norm(pv - Wva["tgt"], axis=2) / sv
        zt = np.linalg.norm(pt - Wte["tgt"], axis=2) / st
        qz = float(np.quantile(zv.ravel(), 0.90))
        rad = qz * st
        arms["quantile"][str(L)]["adaptive_conformal"] = dict(
            q90_z=qz, coverage_test=float(np.mean(np.linalg.norm(pt - Wte["tgt"], axis=2) <= rad)),
            mean_radius_cm=float(100 * rad.mean()), q90_radius_cm=float(100 * np.quantile(rad, 0.9)))

        # ---- shrinkage (leave-one-record-out on validation) --------------
        levels = {"dataset": lambda r: P.dataset[r],
                  "dataset|env_group": lambda r: f"{P.dataset[r]}|{P.env_group[r]}"}
        grid = [0.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 1e9]
        scores, best = {}, (1e18, None, None)
        for lname in levels:
            keyfn = levels[lname]
            scores[lname] = {}
            for kap in grid:
                corr = shrink_apply(pv, Wva, L, kap, keyfn)
                scores[lname][str(kap)] = float(100 * np.sqrt(np.mean((corr - Wva["tgt"]) ** 2)))
                if scores[lname][str(kap)] < best[0]:
                    best = (scores[lname][str(kap)], lname, kap)
        _, lname, kap = best
        keyfn = levels[lname]
        corr_va = shrink_apply(pv, Wva, L, kap, keyfn)
        info_s, off, bucket = shrink_test_offsets(pv, Wva, L, kap, keyfn, Wte["rec"])
        pt_s = pt + off[:, bucket, :]
        ev = np.linalg.norm(corr_va - Wva["tgt"], axis=2).ravel()
        et = np.linalg.norm(pt_s - Wte["tgt"], axis=2).ravel()
        arms.setdefault("quantile_plus_shrink", {})[str(L)] = dict(
            level=lname, kappa=kap, loo_scores_coord_cm=scores, offsets=info_s,
            **metric_block(pt_s, Wte), **conformal(ev, et),
            val_rmse_coord_cm=float(100 * np.sqrt(np.mean((corr_va - Wva["tgt"]) ** 2))),
            per_record=per_record(pt_s, Wte))
        print(f"  quantile_plus_shrink level={lname} kappa={kap}",
              {k: round(v, 4) for k, v in arms["quantile_plus_shrink"][str(L)].items()
               if k in ("rmse_3d_cm", "rmse_coord_cm", "q90_cm", "coverage_test")}, flush=True)

        # ---- paired comparisons -----------------------------------------
        for a, b in (("ridge_replica", "quantile"), ("quantile", "quantile_plus_shrink"),
                     ("ridge_replica", "quantile_plus_shrink")):
            pa = {k: v["rmse_3d_cm"] for k, v in arms[a][str(L)]["per_record"].items()}
            pb = {k: v["rmse_3d_cm"] for k, v in arms[b][str(L)]["per_record"].items()}
            arms[b][str(L)].setdefault("paired", {})[f"{a}__to__{b}"] = paired(pa, pb)

    ref = {}
    pg = os.path.join(DATA, "p2_gpu.json")
    if os.path.exists(pg):
        rows = json.load(open(pg, encoding="utf-8"))["rows"]
        ref = {str(r["L_frames"]): dict(note="GRU v2 point model of train_gpu_p2.py; ALL clean starts "
                                             "(different window density), per-coordinate RMSE",
                                        rmse_coord_cm=round(100 * r["test_rmse_m"], 4),
                                        end_rmse_3d_cm=round(100 * r["test_endpoint_rmse_m"], 4))
               for r in rows if r["variant"] == "v2"}

    out = dict(
        _meta=dict(seed=SEED, seconds=round(time.time() - t_start, 1), gpu_train_seconds=round(gpu_seconds, 1),
                   script="code/up_p2_quantile.py", device=dev, epochs=args.epochs,
                   bar=dict(rmse_gate_cm=3.00, q90_gate_cm=9.0, coverage_min=0.88,
                            rmse_note="3-D gate needs -52% vs the ridge replica (6.30 cm); "
                                      "per-coordinate gate needs -17.5% (3.636 cm). Both units reported.",
                            secondary="if only one of RMSE/q90 passes, the other must not worsen >5%"),
                   baseline=dict(ridge_L30_rmse_3d_cm=6.298, ridge_L30_rmse_coord_cm=3.636,
                                 ridge_L30_q90_cm=10.127, ridge_L30_coverage=0.8926,
                                 gru_v2_L30_rmse_coord_cm=3.3077,
                                 unit_warning="the '3.31 cm @1 s' figure quoted upstream is the PER-COORDINATE "
                                              "RMSE of the GRU v2 in data/p2_gpu.json, not a ridge and not a "
                                              "3-D RMS; the ridge matching q90=10.13 cm is 6.298 cm 3-D / 3.636 cm per coordinate"),
                   protocol=dict(ctx=CTX, lens=lens, caps=dict(train=150, validation=400, test=400),
                                 windows="identical to p2_predict.windows (asserted max|diff|<1e-5 at L=30)",
                                 conformal="split conformal on validation, absolute 3-D radius, np.quantile(.90)",
                                 selection="epochs and kappa on validation records only; test evaluated once"),
                   quantile=dict(model="GRU(80->96,2 layers)+shared horizon head(96+2->256->256->33)",
                                 taus=TAUS.tolist(), loss="pinball in cm", point="tau=0.50",
                                 horizons_sampled_per_step=8),
                   shrink=dict(groups="dataset x env_group (A/L/P family exists only for P3 task units)",
                               estimator="validation leave-one-record-out residual offsets, 3 horizon buckets",
                               weight="w=n/(n+kappa) toward the global offset")),
        arms=arms, reference_gru_v2=ref)
    path = os.path.join(DATA, args.out)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\nsaved -> {path} ({out['_meta']['seconds']}s, gpu train {gpu_seconds:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
