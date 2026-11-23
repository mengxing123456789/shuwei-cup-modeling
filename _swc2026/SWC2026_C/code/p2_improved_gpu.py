
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 improved GPU sequence models.

Candidates (same windows/splits as train_gpu_p2.py and p2_masked.py):
  gru_plain       : exact GRU(128x2) + MLP head / 80-dim rich input (baseline control)
  gru_static_mt   : GRU + static anchor/head-motion token, residual-over-CV output,
                    auxiliary velocity head (multi-task)
  tf_static_mt    : 2-layer 4-head Transformer encoder + static token, residual-over-CV,
                    auxiliary velocity head
  tf_static       : same Transformer, direct displacement, position loss only

Model selection uses validation per-coordinate RMSE only.  Test is evaluated once
per trained candidate at its best validation epoch.  Metrics report both the
per-coordinate and 3-D RMSE, and within-2cm over all horizons and at the endpoint
(the two existing scripts used different conventions; both are reported here).

Usage:
  python p2_improved_gpu.py --models gru_plain,gru_static_mt,tf_static_mt --lens 30
  python p2_improved_gpu.py --models ... --lens 6,18,30,60 --seeds 20261120,20261121
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CTX = 10
WRIST_L = slice(0, 3)
WRIST_R = slice(32, 35)
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def quat_to_R(q):
    q = np.asarray(q, dtype=np.float64)
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3), np.float64)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z)
    R[:, 0, 1] = 2 * (x * y - z * w)
    R[:, 0, 2] = 2 * (x * z + y * w)
    R[:, 1, 0] = 2 * (x * y + z * w)
    R[:, 1, 1] = 1 - 2 * (x * x + z * z)
    R[:, 1, 2] = 2 * (y * z - x * w)
    R[:, 2, 0] = 2 * (x * z - y * w)
    R[:, 2, 1] = 2 * (y * z + x * w)
    R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def load():
    st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    z = np.load(os.path.join(DATA, "panel.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    rec, dom = st["rec"].astype(np.int64), st["dom"].astype(np.int64)
    rich = np.concatenate([st["fl"], st["fr"], st["gl"], st["gr"]], axis=1).astype(np.float32)
    badL, badR = st["badL"].astype(bool), st["badR"].astype(bool)
    slices = {}
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        slices[int(r)] = (int(ii[0]), int(ii[-1]) + 1)
    R = quat_to_R(z["Q"])
    Rh = np.transpose(R, (0, 2, 1))
    grav = np.einsum("nij,j->ni", Rh, np.array([0.0, 0.0, -1.0])).astype(np.float32)
    H = z["H"].astype(np.float64)
    hv = np.zeros_like(H)
    hv[1:] = np.diff(H, axis=0) * 30.0
    hvh = np.einsum("nij,nj->ni", Rh, hv).astype(np.float32)
    ang = np.zeros_like(H)
    rel = np.einsum("nji,njk->nik", R[:-1], R[1:])
    vee = np.stack([rel[:, 2, 1] - rel[:, 1, 2],
                    rel[:, 0, 2] - rel[:, 2, 0],
                    rel[:, 1, 0] - rel[:, 0, 1]], axis=1) * 0.5
    ang[1:] = vee * 30.0
    angh = np.einsum("nij,nj->ni", Rh, ang).astype(np.float32)
    return recs, rec, dom, badL, badR, rich, slices, grav, hvh, angh


def windows(recs, rec, dom, badL, badR, rich, slices, grav, hv, ang, split, L):
    X, S, Y, V, RID, ENV = [], [], [], [], [], []
    for row in recs[recs.split == split].itertuples():
        r = int(row.rec)
        lo, hi = slices[r]
        d = int(dom[r])
        bad = (badL[lo:hi] if d == 0 else badR[lo:hi]).astype(bool)
        wrist = rich[lo:hi, WRIST_L if d == 0 else WRIST_R]
        n = hi - lo
        span = CTX + L
        if n <= span:
            continue
        clean = np.lib.stride_tricks.sliding_window_view(bad, span).sum(axis=1) == 0
        idx = np.flatnonzero(clean)
        if len(idx) == 0:
            continue
        anchor_i = idx + CTX - 1
        anchor = wrist[anchor_i]
        seg = np.lib.stride_tricks.sliding_window_view(rich[lo:hi], CTX, axis=0)
        seg = np.transpose(seg, (0, 2, 1))[idx].copy()
        seg[:, :, 0:3] -= anchor[:, None, :]
        seg[:, :, 32:35] -= anchor[:, None, :]
        y = wrist[anchor_i[:, None] + 1 + np.arange(L)[None, :]] - anchor[:, None, :]
        ai = lo + anchor_i
        s = np.concatenate([anchor, grav[ai], hv[ai], ang[ai], rich[ai, 64:80]], axis=1)
        vlast = wrist[anchor_i] - wrist[anchor_i - 1]
        X.append(np.nan_to_num(seg.astype(np.float32)))
        S.append(np.nan_to_num(s.astype(np.float32)))
        Y.append(np.nan_to_num(y.astype(np.float32)))
        V.append(np.nan_to_num(vlast.astype(np.float32)))
        RID.append(np.full(len(idx), r, np.int32))
        ENV.append(np.full(len(idx), str(row.env), dtype=object))
    if not X:
        return None
    return dict(x=np.concatenate(X), static=np.concatenate(S), y=np.concatenate(Y),
                vlast=np.concatenate(V), rec=np.concatenate(RID), env=np.concatenate(ENV))


def norm_stats(tr):
    mu = tr["x"].mean(axis=(0, 1), keepdims=True)
    sd = tr["x"].std(axis=(0, 1), keepdims=True) + 1e-6
    smu = tr["static"].mean(axis=0, keepdims=True)
    ssd = tr["static"].std(axis=0, keepdims=True) + 1e-6
    return mu, sd, smu, ssd


def apply_norm(p, mu, sd, smu, ssd):
    p["x"] = np.clip((p["x"] - mu) / sd, -10, 10).astype(np.float32)
    p["static"] = np.clip((p["static"] - smu) / ssd, -10, 10).astype(np.float32)
    return p


class GRUModel(nn.Module):
    def __init__(self, fdim, L, static_dim, resid, multi_task, hidden=128, dropout=0.10):
        super().__init__()
        self.gru = nn.GRU(fdim, hidden, num_layers=2, batch_first=True, dropout=dropout)
        self.static = nn.Sequential(nn.Linear(static_dim, hidden), nn.GELU()) if static_dim else None
        self.head = nn.Sequential(nn.Linear(hidden * (2 if static_dim else 1), 256), nn.GELU(),
                                  nn.Dropout(dropout), nn.Linear(256, L * 3))
        self.vhead = nn.Sequential(nn.Linear(hidden, 128), nn.GELU(), nn.Linear(128, L * 3)) \
            if multi_task else None
        self.L, self.resid = L, resid
        nn.init.zeros_(self.head[-1].weight); nn.init.zeros_(self.head[-1].bias)

    def forward(self, x, s):
        _, hn = self.gru(x)
        z = hn[-1]
        v = self.vhead(z).view(-1, self.L, 3) if self.vhead is not None else None
        if self.static is not None:
            z = torch.cat([z, self.static(s)], dim=1)
        out = self.head(z).view(-1, self.L, 3)
        return out, v


class TFModel(nn.Module):
    def __init__(self, fdim, L, static_dim, resid, multi_task, d=96, layers=2, heads=4):
        super().__init__()
        self.proj = nn.Linear(fdim, d)
        self.sproj = nn.Linear(static_dim, d) if static_dim else None
        self.cls = nn.Parameter(torch.zeros(1, 1, d))
        self.pos = nn.Parameter(torch.zeros(1, CTX + 2, d))
        nn.init.normal_(self.pos, std=0.02)
        enc = nn.TransformerEncoderLayer(d_model=d, nhead=heads, dim_feedforward=2 * d,
                                         dropout=0.10, activation="gelu", batch_first=True,
                                         norm_first=True)
        self.enc = nn.TransformerEncoder(enc, num_layers=layers)
        self.norm = nn.LayerNorm(d)
        self.head = nn.Sequential(nn.Linear(d, 192), nn.GELU(), nn.Dropout(0.10),
                                  nn.Linear(192, L * 3))
        self.vhead = nn.Sequential(nn.Linear(d, 128), nn.GELU(), nn.Linear(128, L * 3)) \
            if multi_task else None
        self.L, self.resid = L, resid
        nn.init.zeros_(self.head[-1].weight); nn.init.zeros_(self.head[-1].bias)

    def forward(self, x, s):
        z = self.proj(x)
        if self.sproj is not None:
            z = torch.cat([self.cls.expand(len(x), -1, -1), self.sproj(s)[:, None, :], z], dim=1)
        z = self.enc(z + self.pos[:, :z.shape[1]])
        z = self.norm(z[:, 0])
        v = self.vhead(z).view(-1, self.L, 3) if self.vhead is not None else None
        return self.head(z).view(-1, self.L, 3), v


def make_model(kind, L, static_dim):
    if kind == "gru_plain":
        return GRUModel(80, L, 0, False, False)
    if kind == "gru_plain_mt":
        return GRUModel(80, L, 0, False, True)
    if kind == "gru_static":
        return GRUModel(80, L, static_dim, False, False)
    if kind == "gru_static_mt":
        return GRUModel(80, L, static_dim, True, True)
    if kind == "gru_small":
        return GRUModel(80, L, 0, False, False, hidden=64, dropout=0.30)
    if kind == "gru_small_static":
        return GRUModel(80, L, static_dim, False, False, hidden=64, dropout=0.30)
    if kind == "tf_plain":
        return TFModel(80, L, 0, False, False)
    if kind == "tf_plain_mt":
        return TFModel(80, L, 0, False, True)
    if kind == "tf_static_mt":
        return TFModel(80, L, static_dim, True, True)
    if kind == "tf_static":
        return TFModel(80, L, static_dim, False, False)
    raise ValueError(kind)


def metrics(pred, y):
    e = pred - y
    d = np.sqrt((e ** 2).sum(axis=2))
    return dict(rmse_3d_cm=float(np.sqrt((d ** 2).mean()) * 100),
                rmse_coord_cm=float(np.sqrt((e ** 2).mean()) * 100),
                end_rmse_3d_cm=float(np.sqrt((d[:, -1] ** 2).mean()) * 100),
                within_2cm_all=float((d <= 0.02).mean()),
                within_2cm_end=float((d[:, -1] <= 0.02).mean()),
                median_end_cm=float(np.median(d[:, -1]) * 100))


def run_one(kind, L, tr, va, te, seed, epochs=40, batch=512, pred_dir=None):
    torch.manual_seed(seed)
    np.random.seed(seed)
    xa = torch.from_numpy(tr["x"]); sa = torch.from_numpy(tr["static"])
    ya = torch.from_numpy(tr["y"])
    xv = torch.from_numpy(va["x"]).to(DEV); sv = torch.from_numpy(va["static"]).to(DEV)
    yv = va["y"]
    xt = torch.from_numpy(te["x"]).to(DEV); stt = torch.from_numpy(te["static"]).to(DEV)
    yt = te["y"]
    # constant-velocity base from the last observed frames, in metres/frame
    vtr = tr["vlast"]
    vva = va["vlast"]
    vte = te["vlast"]
    h = np.arange(1, L + 1, dtype=np.float32)[None, :, None]
    base_tr = vtr[:, None, :] * h
    base_va = vva[:, None, :] * h
    base_te = vte[:, None, :] * h
    static_dim = tr["static"].shape[1]
    model = make_model(kind, L, static_dim).to(DEV)
    resid = kind in ("gru_static_mt", "tf_static_mt")
    mt = kind.endswith("_mt") or kind == "tf_static_mt"
    lr0 = 1e-3 if kind.startswith("tf") else (1e-3 if "small" in kind else 2e-3)
    wd = 1e-2 if "small" in kind else 1e-4
    opt = torch.optim.AdamW(model.parameters(), lr=lr0, weight_decay=wd)
    steps = (len(xa) + batch - 1) // batch
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr0, total_steps=epochs * steps)
    lossf = nn.MSELoss()
    best = (1e9, -1, None,
            None)
    t0 = time.time()
    for ep in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(len(xa))
        tot = 0.0
        for i in range(steps):
            sel = perm[i * batch:(i + 1) * batch]
            xb = xa[sel].to(DEV, non_blocking=True)
            if "small" in kind:
                xb = xb + 0.05 * torch.randn_like(xb)
            sb = sa[sel].to(DEV, non_blocking=True)
            yb = ya[sel].to(DEV, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            out, vout = model(xb, sb)
            if resid:
                out = out + torch.from_numpy(base_tr[sel.numpy()]).to(DEV)
            loss = lossf(out, yb)
            if mt:
                vel_tgt = yb[:, 1:] - yb[:, :-1] if L > 1 else yb
                loss = loss + 0.5 * lossf(vout[:, :L - 1], vel_tgt)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step(); sch.step()
            tot += loss.item() * len(sel)
        model.eval()
        with torch.no_grad():
            pv, _ = model(xv, sv)
            pv = pv.cpu().numpy()
        if resid:
            pv = pv + base_va
        vm = float(np.sqrt(np.mean((pv - yv) ** 2)) * 100)
        if vm < best[0]:
            best = (vm, ep, {k: v.detach().clone() for k, v in model.state_dict().items()}, pv)
        if ep % 10 == 0 or ep == 1:
            print(f"    {kind} L={L} ep{ep:02d} val_coord={vm:.3f}cm", flush=True)
    model.load_state_dict(best[2])
    model.eval()
    with torch.no_grad():
        pt, _ = model(xt, stt)
        pt = pt.cpu().numpy()
    if resid:
        pt = pt + base_te
    res = dict(model=kind, L=L, seed=seed, best_epoch=best[1], val_rmse_coord_cm=best[0],
               n_train=int(len(tr["y"])), n_val=int(len(va["y"])), n_test=int(len(te["y"])),
               seconds=round(time.time() - t0, 1), test=metrics(pt, te["y"]))
    # per-environment test metrics
    per = {}
    for env in sorted(set(te["env"].tolist())):
        m = te["env"] == env
        per[str(env)] = metrics(pt[m], te["y"][m])
    res["test_per_env"] = per
    if pred_dir:
        os.makedirs(pred_dir, exist_ok=True)
        tag = f"{kind}_L{L}_s{seed}"
        path = os.path.join(pred_dir, tag + ".npz")
        np.savez_compressed(path, val_pred=best[3], test_pred=pt,
                            val_y=va["y"], test_y=te["y"],
                            val_rec=va["rec"], test_rec=te["rec"],
                            val_env=va["env"], test_env=te["env"],
                            val_vlast=va["vlast"], test_vlast=te["vlast"])
        res["pred_file"] = path
    print(f"  -> {kind} L={L} val={best[0]:.3f} test_coord={res['test']['rmse_coord_cm']:.3f} "
          f"3D={res['test']['rmse_3d_cm']:.3f} w2all={res['test']['within_2cm_all']:.3f} "
          f"w2end={res['test']['within_2cm_end']:.3f} ep={best[1]} ({res['seconds']}s)", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gru_plain,gru_static_mt,tf_static_mt")
    ap.add_argument("--lens", default="30")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--seeds", default="20261120")
    ap.add_argument("--out", default=os.path.join(DATA, "p2_improved_gpu.json"))
    ap.add_argument("--pred-dir", default=os.path.join(DATA, "p2_improved_preds"))
    a = ap.parse_args()
    assert torch.cuda.is_available(), "GPU required"
    print("device", torch.cuda.get_device_name(0), "torch", torch.__version__, flush=True)
    recs, rec, dom, badL, badR, rich, slices, grav, hv, ang = load()
    rows, cache = [], {}
    for L in [int(x) for x in a.lens.split(",")]:
        tr = windows(recs, rec, dom, badL, badR, rich, slices, grav, hv, ang, "train", L)
        va = windows(recs, rec, dom, badL, badR, rich, slices, grav, hv, ang, "validation", L)
        te = windows(recs, rec, dom, badL, badR, rich, slices, grav, hv, ang, "test", L)
        mu, sd, smu, ssd = norm_stats(tr)
        tr = apply_norm(tr, mu, sd, smu, ssd)
        va = apply_norm(va, mu, sd, smu, ssd)
        te = apply_norm(te, mu, sd, smu, ssd)
        print(f"L={L}: train={len(tr['y'])} val={len(va['y'])} test={len(te['y'])}", flush=True)
        for kind in a.models.split(","):
            for seed in [int(x) for x in a.seeds.split(",")]:
                rows.append(run_one(kind, L, tr, va, te, seed, epochs=a.epochs, pred_dir=a.pred_dir))
    out = {"_meta": {
        "script": "p2_improved_gpu.py", "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__, "context": CTX, "models": a.models.split(","),
        "epochs": a.epochs, "seeds": a.seeds.split(","), "lens": a.lens.split(","),
        "protocol": "same all-clean windows as train_gpu_p2/p2_masked; selection on validation coordinate RMSE; test once",
        "note": "gru_plain is the exact architecture/input of train_gpu_p2 v2 for control",
    }, "rows": rows, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()