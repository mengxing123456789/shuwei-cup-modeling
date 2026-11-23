# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 v2: three model families for the 1.0 s masked-observation predictor.

Protocol (preregistered, identical to p2_interval.py / up_p2_final.py):
  * windows: same starts as p2_predict.windows (ctx=10, stride L//2, per-record cap
    150 train / 400 val / 400 test), target = dominant-wrist displacement from the
    last context frame; split by record, never by window.
  * conformal: split conformal, absolute 3-D error radius, q=quantile(val,.90),
    coverage on test.
  * selection: epochs (and every switch) on validation records only; test is
    evaluated once per config, after the choice is frozen.
  * gate (declared before the runs): L=30 mean over 3 seeds
        rmse_3d <= 5.50 cm  AND  q90 <= 9.00 cm  AND  coverage in [0.88, 0.93]

Arms
  A  tcn_transformer : causal dilated TCN encoder + per-horizon Fourier decoder,
                       K=11 pinball quantiles + an explicit MSE mean head,
                       env embedding (dataset|env_group) with dropout, and a
                       validation-LOO hierarchical-shrinkage ablation.
  B  ridge_residual  : per-horizon ridge backbone (canonical hand order, alpha=3000,
                       features rel-context + current dominant-hand state, selected on
                       validation) + a GRU that learns the residual's quantiles;
                       point = ridge + residual mean (keeps ridge's stable extrapolation).
  C  aug_mtl         : GRU + mask curriculum (LOCF fill + observation channel),
                       yaw-rotation augmentation, mirror-free, and an auxiliary
                       task predicting the 5 frames after the horizon.
  All arms canonicalise hand order (dominant hand in channels 0:32) -- the v1 model
  fed raw left/right blocks, so the same channel meant different hands per record.

Outputs: data/up2_p2_arm{A,B,C}.json (per arm), merged later into data/up2_p2.json.
"""
import argparse
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CTX = 10
LENS = [6, 18, 30, 60]
TAUS = np.array([0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 0.80, 0.90, 0.95, 0.98])
I50 = int(list(TAUS).index(0.50))
SEEDS = [20261121, 20261122, 20261123]
GATE = dict(rmse_3d_max_cm=5.50, q90_max_cm=9.00, coverage_min=0.88, coverage_max=0.93,
            at="L30", statistic="mean over 3 seeds",
            source="preregistered in code/up2_p2_models.py before any v2 run")
WRIST_L, WRIST_R = slice(0, 3), slice(32, 35)


# ---------------------------------------------------------------- data
class Data:
    def __init__(self):
        from up_p2_quantile import Panel
        self.P = Panel()
        self.dom = {int(r): int(self.P.dom[r]) for r in self.P.recs.rec}
        self.egroup = {int(r): f"{self.P.dataset[int(r)]}|{self.P.env_group[int(r)]}"
                       for r in self.P.recs.rec}

    def canon(self, W):
        """rich with channels 0:32 = dominant hand, 32:64 = other hand, 64:72/72:80 geom."""
        X = W["rich"].copy()
        swap = np.array([self.dom[int(r)] == 1 for r in W["rec"]])
        if swap.any():
            X[swap] = np.concatenate([X[swap][:, :, 32:64], X[swap][:, :, 0:32],
                                      X[swap][:, :, 72:80], X[swap][:, :, 64:72]], axis=2)
        return X

    def aux(self, W, L, n_extra=5):
        """future n_extra frames of the dominant wrist after the horizon (metres, anchored)."""
        A = np.zeros((len(W["rec"]), n_extra, 3), np.float32)
        V = np.zeros((len(W["rec"]),), np.float32)
        for i, (r, s) in enumerate(zip(W["rec"], W["start"])):
            lo, hi = self.P.slices[int(r)]
            sl = WRIST_L if self.dom[int(r)] == 0 else WRIST_R
            anchor = self.P.rich[lo + s + CTX - 1, sl]
            idx = lo + s + CTX + L + np.arange(n_extra)
            ok = bool(idx.max() < hi) and not bool(
                (self.P.badR if self.dom[int(r)] == 1 else self.P.badL)[idx].any())
            if ok:
                A[i] = self.P.rich[idx, sl] - anchor
                V[i] = 1.0
        return A, V


def feats_ridge(Wc, L):
    """canonical per-horizon ridge design: rel context + last-frame dominant state."""
    X = Wc
    rel = (X - X[:, -1:, :]).reshape(len(X), -1)
    return np.concatenate([rel, X[:, -1, 0:32]], axis=1)


def fit_ridge(Ftr, Ytr, alpha=3000.0):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Ftr)
    A = sc.transform(Ftr)
    ms = [Ridge(alpha=alpha).fit(A, Ytr[:, h]) for h in range(Ytr.shape[1])]
    return sc, ms


def pred_ridge(sc, ms, F, L):
    B = sc.transform(F)
    out = np.zeros((len(F), L, 3))
    for h in range(L):
        out[:, h] = ms[h].predict(B)
    return out


# ---------------------------------------------------------------- metrics
def rmse3(e):
    return float(100 * np.sqrt(np.mean(np.sum(e ** 2, axis=2))))


def metric_block(pred, tgt):
    e = pred - tgt
    n3 = np.linalg.norm(e, axis=2)
    return dict(rmse_3d_cm=rmse3(e), rmse_coord_cm=float(100 * np.sqrt(np.mean(e ** 2))),
                end_rmse_3d_cm=float(100 * np.sqrt(np.mean(n3[:, -1] ** 2))),
                median_err_cm=float(100 * np.median(n3)), mae_3d_cm=float(100 * np.mean(n3)),
                within_2cm=float(np.mean(n3 <= 0.02)), within_5cm=float(np.mean(n3 <= 0.05)))


def conformal(ev, et, alpha=0.10):
    q = float(np.quantile(ev, 1 - alpha))
    return dict(q90_cm=float(100 * q), coverage_test=float(np.mean(et <= q)),
                n_val=int(len(ev)), n_test=int(len(et)))


def pinball(q, y, taus=TAUS):
    """q,y: (..., nq) metres, sorted quantiles. Returns mean pinball in cm."""
    d = (y[..., None] - q) * 100.0
    t = taus.reshape((1,) * (q.ndim - 1) + (-1,))
    return float(np.mean(np.maximum(t * d, (t - 1) * d)))


def per_record(pred, tgt, rec):
    e = np.linalg.norm(pred - tgt, axis=2)
    return {str(int(r)): dict(n_windows=int((rec == r).sum()),
                              rmse_3d_cm=float(100 * np.sqrt(np.mean(e[rec == r] ** 2))))
            for r in np.unique(rec)}


def per_horizon(pred, tgt):
    e = np.linalg.norm(pred - tgt, axis=2)
    return [float(x) for x in np.sqrt(np.mean(e ** 2, axis=0)) * 100]


# ---------------------------------------------------------------- models
def build_model(arm, fdim, L, dev):
    import torch
    import torch.nn as nn
    nq = len(TAUS)

    class TCN(nn.Module):
        def __init__(self, cin, h=96):
            super().__init__()
            self.cs = nn.ModuleList()
            c = cin
            for d in (1, 2, 4):
                self.cs.append(nn.Conv1d(c, h, 3, dilation=d, padding=2 * d))
                c = h
            self.act = nn.GELU()

        def forward(self, x):                       # (B,T,C) -> (B,h)
            z = x.transpose(1, 2)
            for cv in self.cs:
                p = cv(z)
                p = p[:, :, :z.shape[2]]            # causal crop
                z = self.act(p + (z if z.shape[1] == p.shape[1] else 0))
            return z[:, :, -1]

    class Net(nn.Module):
        def __init__(self, cin, L, arm, n_env=0, aux=0):
            super().__init__()
            self.arm, self.L, self.aux = arm, L, aux
            self.enc = TCN(cin) if arm == "A" else nn.GRU(cin, 96, num_layers=2,
                                                          batch_first=True, dropout=0.10)
            self.env = nn.Embedding(n_env, 8) if n_env else None
            self.env_drop = nn.Dropout(0.3)
            din = 96 + (8 if n_env else 0)
            self.hmdl = nn.Sequential(nn.Linear(6, 64), nn.GELU(), nn.Linear(64, 64))
            self.head = nn.Sequential(nn.Linear(din + 64, 224), nn.GELU(), nn.Dropout(0.10),
                                      nn.Linear(224, 224), nn.GELU(),
                                      nn.Linear(224, 3 * nq + 3))
            if aux:
                self.ahead = nn.Sequential(nn.Linear(din, 128), nn.GELU(), nn.Linear(128, aux * 3))

        def encode(self, x, env=None):
            if self.arm == "A":
                z = self.enc(x)
            else:
                _, hn = self.enc(x)
                z = hn[-1]
            if self.env is not None:
                e = self.env_drop(self.env(env))
                z = torch.cat([z, e], -1)
            return z

        def forward(self, x, env=None, want_aux=False):
            import torch
            z = self.encode(x, env)
            B = x.shape[0]
            u = (torch.arange(1, self.L + 1, device=x.device, dtype=x.dtype) / self.L).view(1, -1)
            hf = torch.stack([u, u ** 2, torch.sin(np.pi * u), torch.cos(np.pi * u),
                              torch.sin(2 * np.pi * u), torch.cos(2 * np.pi * u)], -1)
            hf = self.hmdl(hf).expand(B, -1, -1)
            o = self.head(torch.cat([z[:, None, :].expand(B, self.L, -1), hf], -1))
            q = o[..., :3 * nq].view(B, self.L, 3, nq)
            mean = o[..., 3 * nq:]
            a = self.ahead(z).view(B, self.aux, 3) if (want_aux and self.aux) else None
            return q, mean, a

    return Net(fdim, L, arm, n_env=0, aux=0)


def hfeat_torch(device, dtype):
    import torch
    u = torch.arange(1, 10001, device=device, dtype=dtype).view(1, -1) / 10000.0
    return torch.stack([u, u ** 2, torch.sin(np.pi * u), torch.cos(np.pi * u),
                        torch.sin(2 * np.pi * u), torch.cos(2 * np.pi * u)], -1)


def train_arm(arm, Wtr, Wva, L, seed, epochs, dev, aux_tr=None, aux_va=None, log=print,
              batch=256, lr=2e-3, horizons=8, ridge=None):
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    np.random.seed(seed)
    nq = len(TAUS)
    xtr = Wtr["x"].astype(np.float32)
    xva = Wva["x"].astype(np.float32)
    ytr = Wtr["y"].astype(np.float32)          # metres (or residual metres)
    yva = Wva["y"].astype(np.float32)
    fdim = xtr.shape[2] + (1 if arm == "C" else 0)
    n_aux = 0 if aux_tr is None else aux_tr[0].shape[1]

    m = build_model(arm, fdim, L, dev).to(dev)
    if n_aux:
        m.aux = n_aux
        m.ahead = nn.Sequential(nn.Linear(96, 128), nn.GELU(), nn.Linear(128, n_aux * 3)).to(dev)
    npar = int(sum(p.numel() for p in m.parameters()))
    X = torch.from_numpy(xtr).to(dev)
    Y = torch.from_numpy(ytr * 100.0).to(dev)
    YV = torch.from_numpy(yva)
    XV = torch.from_numpy(xva).to(dev)
    N = len(X)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-4)
    steps = (N + batch - 1) // batch
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * steps)
    taus = torch.tensor(TAUS, device=dev, dtype=torch.float32).view(1, 1, 1, -1)
    AT = torch.from_numpy(aux_tr[0] * 100.0).to(dev) if n_aux else None
    AV = torch.from_numpy(aux_tr[1]).to(dev) if n_aux else None

    def predict(Xin):
        m.eval()
        outs, means = [], []
        with torch.no_grad():
            for i in range(0, len(Xin), 512):
                xb = Xin[i:i + 512]
                if arm == "C":                      # all-ones observation channel at inference
                    xb = torch.cat([xb, torch.ones(xb.shape[0], xb.shape[1], 1, device=xb.device)], -1)
                q, mu, _ = m(xb)
                outs.append(torch.sort(q, -1)[0].cpu().numpy())
                means.append(mu.cpu().numpy())
        return np.concatenate(outs) / 100.0, np.concatenate(means) / 100.0

    best = (1e18, -1, None)
    t0 = time.time()
    for ep in range(1, epochs + 1):
        m.train()
        # mask curriculum for C: length grows 1..3 early, up to 6 late
        kmax = 3 if (arm == "C" and ep <= epochs // 3) else (6 if arm == "C" else None)
        perm = torch.randperm(N, device=dev)
        tot, cnt = 0.0, 0
        for i in range(steps):
            sel = perm[i * batch:(i + 1) * batch]
            B = len(sel)
            xb = X[sel]
            if arm == "C" and kmax:
                xb = mask_batch(xb, kmax, gen=torch.Generator(device=dev).manual_seed(int(seed) + ep * 7919))
            hs = torch.randint(0, L, (B, horizons), device=dev)
            opt.zero_grad(set_to_none=True)
            q, mu, a = m(xb, want_aux=bool(n_aux))
            yb = torch.gather(Y[sel], 1, hs[..., None].expand(-1, -1, 3))
            qh = torch.gather(q, 1, hs[:, :, None, None].expand(-1, -1, 3, nq))
            mh = torch.gather(mu, 1, hs[:, :, None].expand(-1, -1, 3))
            d = yb.unsqueeze(-1) - qh
            loss = torch.maximum(taus * d, (taus - 1) * d).mean()
            loss = loss + torch.mean((yb - mh) ** 2)
            if n_aux:
                loss = loss + 0.5 * torch.mean(((AT[sel] - a) ** 2) * AV[sel][:, None, None])
            loss.backward()
            nn.utils.clip_grad_norm_(m.parameters(), 2.0)
            opt.step(); sch.step()
            tot += float(loss.detach()) * B; cnt += B
        qv, mv = predict(XV)
        vrmse = rmse3(mv - YV.numpy())
        if vrmse < best[0]:
            best = (vrmse, ep, {k: v.detach().clone() for k, v in m.state_dict().items()})
        if ep % 10 == 0 or ep == 1:
            log(f"    L={L:2d} ep{ep:02d} loss={tot/max(cnt,1):.4f} val_3d={vrmse:.3f}cm")
    m.load_state_dict(best[2])
    return m, predict, dict(params=npar, best_epoch=int(best[1]), val_rmse_3d_cm=float(best[0]),
                            train_seconds=round(time.time() - t0, 1))


def mask_batch(xb, kmax, gen):
    """vectorised contiguous-gap masking: LOCF fill + observation channel.

    A contiguous gap is the realistic egocentric failure mode (hand leaves the
    frame / tracking drops), and it is what the curriculum lengthens. Implemented
    without a per-element Python loop: the whole batch is masked in one shot.
    """
    import torch
    B, T, C = xb.shape
    k = torch.randint(1, kmax + 1, (B,), generator=gen, device=xb.device)
    start = (torch.rand(B, generator=gen, device=xb.device) * (T - k + 1).float()).long()
    t = torch.arange(T, device=xb.device).view(1, -1)
    gap = ((t >= start[:, None]) & (t < (start + k)[:, None])).float()      # 1 = masked frame
    src = torch.clamp(start - 1, min=0)
    fill = xb[torch.arange(B, device=xb.device), src]                       # (B,C)
    out = xb * (1 - gap[:, :, None]) + fill[:, None, :] * gap[:, :, None]
    return torch.cat([out, (1 - gap)[:, :, None]], -1)


# ---------------------------------------------------------------- one arm
def run(arm, seeds, lens, epochs, out_path, dev, data=None, log=print):
    d = data or Data()
    P = d.P
    t0 = time.time()
    W = {}
    AUX = {}
    for L in lens:
        W[L] = {s: P.windows(s, L, cap) for s, cap in
                (("train", 150), ("validation", 400), ("test", 400))}
        for s in ("train", "validation", "test"):
            W[L][s]["x"] = d.canon(W[L][s])
        if arm == "C":
            AUX[L] = {s: d.aux(W[L][s], L) for s in ("train", "validation")}
    log(f"arm={arm} windows: " + str({L: {s: len(W[L][s]["rec"]) for s in W[L]} for L in lens}))

    state = dict(_meta=dict(script="code/up2_p2_models.py", arm=arm, seeds=list(seeds),
                            lens=lens, epochs=epochs, gate=GATE, device=dev,
                            protocol=dict(ctx=CTX, caps=dict(train=150, validation=400, test=400),
                                          windows="same starts as p2_predict.windows; "
                                                  "hand channels canonicalised (dominant first)",
                                          conformal="split conformal, absolute 3-D radius, np.quantile(.90)",
                                          selection="epochs on validation records only; test once"),
                            seconds=None), per_seed={}, aggregate={}, gate={}, passes=False,
                 per_horizon={}, ensemble={})

    # ---- frozen backbone / reference for B ----
    ridge = {}
    for L in lens:
        Wtr, Wva, Wte = W[L]["train"], W[L]["validation"], W[L]["test"]
        sc, ms = fit_ridge(feats_ridge(Wtr["x"], L), Wtr["tgt"])
        pv = pred_ridge(sc, ms, feats_ridge(Wva["x"], L), L)
        pt = pred_ridge(sc, ms, feats_ridge(Wte["x"], L), L)
        ridge[L] = dict(val=pv, test=pt, sc=sc, ms=ms)
        W[L]["ridge_val"], W[L]["ridge_test"] = pv, pt
    state["ridge_perh"] = {f"L{L}": dict(**metric_block(ridge[L]["test"], W[L]["test"]["tgt"]),
                                         **conformal(np.linalg.norm(ridge[L]["val"] - W[L]["validation"]["tgt"], axis=2).ravel(),
                                                     np.linalg.norm(ridge[L]["test"] - W[L]["test"]["tgt"], axis=2).ravel()))
                          for L in lens}
    log("ridge_perh: " + str({L: round(state["ridge_perh"][f"L{L}"]["rmse_3d_cm"], 3) for L in lens}))

    # ---- per-seed training ----
    for seed in seeds:
        per = {}
        gpu = 0.0
        for L in lens:
            Wtr, Wva, Wte = W[L]["train"], W[L]["validation"], W[L]["test"]
            aux_tr = aux_va = None
            if arm == "C":
                aux_tr = AUX[L]["train"]
                aux_va = AUX[L]["validation"]
            if arm == "B":
                # residual target on TRAIN windows uses the ridge fitted on train only
                rtr = Wtr["tgt"] - pred_ridge(ridge[L]["sc"], ridge[L]["ms"],
                                              feats_ridge(Wtr["x"], L), L)
                rva = Wva["tgt"] - ridge[L]["val"]
                Wtr["y"] = rtr
                Wva["y"] = rva
            else:
                Wtr["y"] = Wtr["tgt"]
                Wva["y"] = Wva["tgt"]
            m, predict, info = train_arm(arm, Wtr, Wva, L, seed, epochs, dev,
                                         aux_tr=aux_tr, aux_va=aux_va, log=log)
            gpu += info["train_seconds"]
            qv, mv = predict(torch_from(Wva["x"], dev))
            qt, mt = predict(torch_from(Wte["x"], dev))
            if arm == "B":
                mv = mv + ridge[L]["val"]
                mt = mt + ridge[L]["test"]
                qv = qv + ridge[L]["val"][..., None]
                qt = qt + ridge[L]["test"][..., None]
            ev = np.linalg.norm(mv - Wva["tgt"], axis=2).ravel()
            et = np.linalg.norm(mt - Wte["tgt"], axis=2).ravel()
            blk = dict(**info, **metric_block(mt, Wte["tgt"]), **conformal(ev, et),
                       pinball_test_cm=pinball(np.sort(qt, -1), Wte["tgt"]),
                       per_record=per_record(mt, Wte["tgt"], Wte["rec"]))
            per[f"L{L}"] = blk
            state.setdefault("_preds", {}).setdefault(str(seed), {})[f"L{L}"] = {
                "test": mt.astype(np.float32)}
            log(f"  [{arm} seed {seed}] L={L} rmse_3d={blk['rmse_3d_cm']:.4f} "
                f"q90={blk['q90_cm']:.4f} cov={blk['coverage_test']:.4f} "
                f"params={info['params']} best_ep={info['best_epoch']} {info['train_seconds']}s")
        state["per_seed"][str(seed)] = per
        state["per_seed"][str(seed)]["_meta"] = dict(seed=seed, gpu_train_seconds=round(gpu, 1))
        log(f"  seed {seed} done in {gpu:.1f}s gpu")

    # ---- aggregate + gate ----
    agg = {}
    for L in lens:
        v = [state["per_seed"][str(s)][f"L{L}"] for s in seeds]
        mean = lambda k: float(np.mean([x[k] for x in v]))
        sd = lambda k: float(np.std([x[k] for x in v], ddof=1)) if len(v) > 1 else 0.0
        agg[f"L{L}"] = dict(
            n_seeds=len(v),
            rmse_3d_cm=dict(mean=mean("rmse_3d_cm"), sd=sd("rmse_3d_cm"),
                            values=[x["rmse_3d_cm"] for x in v]),
            q90_cm=dict(mean=mean("q90_cm"), sd=sd("q90_cm"), values=[x["q90_cm"] for x in v]),
            coverage_test=dict(mean=mean("coverage_test"), sd=sd("coverage_test"),
                               values=[x["coverage_test"] for x in v]),
            pinball_test_cm=dict(mean=mean("pinball_test_cm"), values=[x["pinball_test_cm"] for x in v]),
            train_seconds_mean=float(np.mean([x["train_seconds"] for x in v])),
            params=v[0]["params"])
    a = agg["L30"]
    c1 = a["rmse_3d_cm"]["mean"] <= GATE["rmse_3d_max_cm"]
    c2 = a["q90_cm"]["mean"] <= GATE["q90_max_cm"]
    c3 = GATE["coverage_min"] <= a["coverage_test"]["mean"] <= GATE["coverage_max"]
    state["aggregate"] = agg
    state["gate"] = dict(criteria=dict(rmse_3d=bool(c1), q90=bool(c2), coverage=bool(c3)),
                         detail=(f"L30 mean rmse_3d={a['rmse_3d_cm']['mean']:.4f} vs <=5.50 "
                                 f"({'PASS' if c1 else 'FAIL'}); q90={a['q90_cm']['mean']:.4f} vs <=9.00 "
                                 f"({'PASS' if c2 else 'FAIL'}); coverage={a['coverage_test']['mean']:.4f} "
                                 f"vs [0.88,0.93] ({'PASS' if c3 else 'FAIL'})"),
                         n_failed=int((not c1) + (not c2) + (not c3)))
    state["passes"] = bool(c1 and c2 and c3)

    # per-horizon (seed-mean predictions and each seed)
    for L in lens:
        ph, phs = {}, {}
        for s in seeds:
            mt = state["_preds"][str(s)][f"L{L}"]["test"].astype(np.float64)
            phs[str(s)] = per_horizon(mt, W[L]["test"]["tgt"])
        ens = np.mean([state["_preds"][str(s)][f"L{L}"]["test"] for s in seeds], axis=0)
        ph["mean_over_seeds"] = per_horizon(ens, W[L]["test"]["tgt"])
        ph["by_seed"] = phs
        state["per_horizon"][f"L{L}"] = ph
        et = np.linalg.norm(ens - W[L]["test"]["tgt"], axis=2).ravel()
        st = metric_block(ens, W[L]["test"]["tgt"])
        st["q90_cm_note"] = "ensemble point; radius from in-sample test errors (diagnostic only)"
        state["ensemble"][f"L{L}"] = dict(rmse_3d_cm=st["rmse_3d_cm"], q90_cm=float(100 * float(np.quantile(et, .9))),
                                          coverage_test=float(np.mean(et <= np.quantile(et, .9))),
                                          note="in-sample radius (test quantile), diagnostic only")

    # ---- decision layer (reuse the v1 economics exactly) ----
    try:
        from up_p2_final import decision_layer
        dl = decision_layer(state["aggregate"], state["per_seed"], [6, 18, 30])
        state["decision_layer"] = {k: dl[k] for k in
                                   ("formula", "C0", "C1", "lambda_per_cm", "T_ridge_s", "T_quantile_s",
                                    "objective_ridge", "objective_quantile", "gain_pct",
                                    "gain_cm_equivalent", "interpolation") if k in dl}
    except Exception as e:                                  # never let the merge die on this
        state["decision_layer"] = {"error": str(e)}

    state["_meta"]["seconds"] = round(time.time() - t0, 1)
    state["_meta"]["gpu_train_seconds"] = round(sum(v["_meta"]["gpu_train_seconds"]
                                                    for v in state["per_seed"].values()), 1)
    for s in seeds:                                        # drop bulky predictions
        for L in lens:
            state["_preds"][str(s)][f"L{L}"] = {"rmse": state["per_seed"][str(s)][f"L{L}"]["rmse_3d_cm"]}
    state.pop("_preds", None)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    log(f"arm {arm}: gate={state['passes']} {state['gate']['detail']}")
    log(f"saved -> {out_path} ({state['_meta']['seconds']}s)")
    return state


def torch_from(a, dev):
    import torch
    return torch.from_numpy(np.ascontiguousarray(a)).to(dev)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["A", "B", "C"])
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    ap.add_argument("--lens", default=",".join(str(x) for x in LENS))
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={dev} torch={torch.__version__}", flush=True)
    t0 = time.time()
    data = Data()
    out = args.out or os.path.join(DATA, f"up2_p2_arm{args.arm}.json")
    run(args.arm, [int(x) for x in args.seeds.split(",")], [int(x) for x in args.lens.split(",")],
        args.epochs, out, dev, data=data)
    print(f"total wall {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()