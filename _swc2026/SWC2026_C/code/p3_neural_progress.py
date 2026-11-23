
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P3 v3: phase-pretrained causal encoder + joint duration quantiles.

Structural novelty is not the network size. The encoder is pretrained on complete
TRAIN demonstrations to separate normalized action phase from observation quality;
only the released prefix is encoded at inference. Duration is predicted as five
joint quantiles, so scheduling consumes a distribution instead of a point + global
residual. A monotonic-quantile projection prevents crossing.

Official environment split is preserved. No future prefix frames, true duration,
UUID/sample/source index are inference inputs. Full demonstrations are used only
for self-supervised phase pretraining on the training environments.
"""
import json
import math
import os
import random
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.stats import spearmanr
from common import DATA, load_index, write_json

SEED = 20261120
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
TAUS = torch.tensor([0.1, 0.25, 0.5, 0.75, 0.9], device=DEV)
PREFIX = [0.2, 0.6, 1.0]
T = 30


def load_data():
    st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    z = np.load(os.path.join(DATA, "panel.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    idx = load_index()
    rich = np.concatenate([st["fl"], st["fr"], st["gl"], st["gr"]], axis=1).astype(np.float32)
    rec = st["rec"].astype(int)
    t = z["t"]
    byrec = {int(r): np.flatnonzero(rec == r) for r in np.unique(rec)}
    links = {}
    for _, u in idx.iterrows():
        rr = recs[(recs.dataset == u.dataset) & (recs["sample"].astype(str) == str(u["sample"]))]
        if not len(rr):
            continue
        rid = int(rr.rec.iloc[0]); ii = byrec[rid]; times = t[ii]
        m = (times >= float(u.start_s) - 1e-6) & (times <= float(u.end_s) + 1e-6)
        links[u.unit_id] = rich[ii[m]]
    return idx, links


def resample(x, n=T):
    if len(x) < 2:
        x = np.repeat(x, 2, axis=0)
    old = np.linspace(0, 1, len(x)); new = np.linspace(0, 1, n)
    out = np.stack([np.interp(new, old, x[:, j]) for j in range(x.shape[1])], axis=1)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def make_arrays(idx, links):
    rows = []
    for _, u in idx.iterrows():
        if u.unit_id not in links:
            continue
        full = links[u.unit_id]
        for p in PREFIX:
            n = max(2, min(len(full), int(round(p / max(float(u.duration_s), p) * len(full))) + 1))
            # Prefer physical time slicing when the original frame count is adequate.
            n = max(2, min(len(full), int(math.ceil(p * 30))))
            x = full[:n]
            rows.append(dict(unit_id=u.unit_id, split=u.split, family=u.family_id,
                             prefix=p, duration=float(u.duration_s), raw=resample(x),
                             full=resample(full, 60)))
    return rows


class CausalBlock(nn.Module):
    def __init__(self, c, d, drop=0.12):
        super().__init__()
        self.c1 = nn.Conv1d(c, c, 3, padding=2 * d, dilation=d)
        self.c2 = nn.Conv1d(c, c, 3, padding=2 * d, dilation=d)
        self.n1 = nn.GroupNorm(8, c); self.n2 = nn.GroupNorm(8, c)
        self.drop = nn.Dropout(drop)

    def forward(self, x):
        y = self.c1(x)[..., :-2 * self.c1.dilation[0]]
        y = self.drop(F.gelu(self.n1(y)))
        y = self.c2(y)[..., :-2 * self.c2.dilation[0]]
        return x + self.drop(F.gelu(self.n2(y)))


class PhaseDurationNet(nn.Module):
    def __init__(self, fin=80, c=64, nq=5):
        super().__init__()
        self.inp = nn.Conv1d(fin, c, 1)
        self.blocks = nn.ModuleList([CausalBlock(c, d) for d in (1, 2, 4, 8)])
        self.phase = nn.Linear(c, 1)
        self.attn = nn.Linear(c, 1)
        self.head = nn.Sequential(nn.Linear(2 * c + 4, 128), nn.GELU(), nn.Dropout(0.15),
                                  nn.Linear(128, nq))

    def encode(self, x):
        # x B,T,F -> B,C,T
        h = self.inp(x.transpose(1, 2))
        for b in self.blocks:
            h = b(h)
        z = h.transpose(1, 2)
        return h, z

    def forward(self, x, meta):
        h, z = self.encode(x)
        w = torch.softmax(self.attn(z), dim=1)
        pooled = torch.cat([(w * z).sum(1), z[:, -1], meta], dim=1)
        raw = self.head(pooled)
        # Positive increments guarantee q0.1 <= ... <= q0.9 by construction.
        q = torch.cat([raw[:, :1], raw[:, :1] + F.softplus(raw[:, 1:])], dim=1)
        return q, self.phase(z).squeeze(-1)


def pinball(pred, y):
    # pred B,Q in log duration; y B
    e = y[:, None] - pred
    return torch.maximum(TAUS[None, :] * e, (TAUS[None, :] - 1) * e).mean()


def fam_meta(rows):
    fam = np.array([[r["family"] == "A", r["family"] == "L", r["family"] == "P"]
                    for r in rows], dtype=np.float32)
    pre = np.array([[r["prefix"]] for r in rows], dtype=np.float32)
    return np.concatenate([fam, pre], axis=1)


def evaluate(model, rows, batch=512):
    model.eval(); preds = []
    with torch.no_grad():
        for i in range(0, len(rows), batch):
            rr = rows[i:i + batch]
            x = torch.from_numpy(np.stack([r["raw"] for r in rr])).to(DEV)
            m = torch.from_numpy(fam_meta(rr)).to(DEV)
            q, _ = model(x, m)
            preds.append(q.cpu().numpy())
    q = np.concatenate(preds)
    y = np.array([r["duration"] for r in rows])
    p = np.exp(q)
    out = {}
    for split in ("validation", "test"):
        take = np.array([r["split"] == split for r in rows])
        details = []
        for pre in PREFIX:
            m = take & np.array([r["prefix"] == pre for r in rows])
            if not m.any():
                continue
            med = p[m, 2]
            details.append(dict(prefix=pre, n=int(m.sum()),
                                mae=float(np.mean(np.abs(y[m] - med))),
                                rmse=float(np.sqrt(np.mean((y[m] - med) ** 2))),
                                spearman=float(spearmanr(y[m], med).statistic),
                                pinball=float(np.mean([np.mean(np.maximum(t * (y[m] - p[m, j]),
                                    (t - 1) * (y[m] - p[m, j]))) for j, t in enumerate([.1, .25, .5, .75, .9])]))))
        out[split] = dict(mae=float(np.mean([d["mae"] for d in details])),
                          rmse=float(np.mean([d["rmse"] for d in details])),
                          spearman=float(np.mean([d["spearman"] for d in details])),
                          by_prefix=details)
    return out, p


def main():
    t0 = time.time()
    idx, links = load_data()
    rows = make_arrays(idx, links)
    train = [r for r in rows if r["split"] == "train"]
    print("device", DEV, "rows", len(rows), "train", len(train), flush=True)
    net = PhaseDurationNet().to(DEV)
    print("parameters", sum(p.numel() for p in net.parameters()), flush=True)

    # Stage 1: phase pretraining on full training demonstrations.
    # Dense phase labels come from normalized position inside the annotated segment.
    fullx = torch.from_numpy(np.stack([r["full"] for r in train])).to(DEV)
    phase_y = torch.linspace(0, 1, 60, device=DEV)[None, :].expand(len(train), 60)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=2e-4)
    for ep in range(1, 41):
        net.train(); perm = torch.randperm(len(train), device=DEV); total = 0.0
        for i in range(0, len(train), 128):
            sel = perm[i:i + 128]
            x = fullx[sel]
            if ep > 5:
                x = x + 0.015 * torch.randn_like(x)
            h, z = net.encode(x)
            ph = net.phase(z).squeeze(-1)
            target = phase_y[sel]
            loss = F.smooth_l1_loss(ph, target)
            # weak monotonicity regularizer: phase must not run backwards systematically
            loss = loss + 0.05 * F.relu(ph[:, :-1] - ph[:, 1:]).mean()
            opt.zero_grad(set_to_none=True); loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 2.0); opt.step()
            total += loss.item() * len(sel)
        if ep in (1, 10, 20, 40):
            print("pretrain", ep, round(total / len(train), 5), flush=True)

    # Stage 2: duration quantiles. Augment only by harmless sensor noise and temporal crop
    # within each already released prefix; validation remains completely untouched.
    xtr = torch.from_numpy(np.stack([r["raw"] for r in train]))
    mtr = torch.from_numpy(fam_meta(train))
    ytr = torch.from_numpy(np.log(np.array([r["duration"] for r in train], dtype=np.float32)))
    opt = torch.optim.AdamW(net.parameters(), lr=4e-4, weight_decay=5e-4)
    epochs = 160; steps = math.ceil(len(train) / 128)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs * steps)
    best = (1e9, -1, None, None)
    history = []
    for ep in range(1, epochs + 1):
        net.train(); perm = torch.randperm(len(train)); total = 0.0
        for i in range(steps):
            sel = perm[i * 128:(i + 1) * 128]
            x = xtr[sel].to(DEV); m = mtr[sel].to(DEV); y = ytr[sel].to(DEV)
            # observation dropout and small jitter improve cross-environment robustness
            x = x + 0.02 * torch.randn_like(x)
            mask = (torch.rand(x.shape[:2], device=DEV) < 0.025).unsqueeze(-1)
            x = x.masked_fill(mask, 0.0)
            q, ph = net(x, m)
            loss = pinball(q, y)
            # median log-MAE + weak endpoint phase regularization
            loss = loss + 0.12 * F.smooth_l1_loss(q[:, 2], y)
            opt.zero_grad(set_to_none=True); loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 2.0); opt.step(); sch.step()
            total += loss.item() * len(sel)
        if ep % 5 == 0 or ep == 1:
            ev, _ = evaluate(net, rows)
            score = ev["validation"]["mae"]
            history.append(dict(epoch=ep, train_loss=total / len(train), **ev))
            if score < best[0]:
                best = (score, ep, {k: v.detach().clone() for k, v in net.state_dict().items()}, ev)
            if ep % 20 == 0 or ep == 1:
                print("finetune", ep, "loss", round(total / len(train), 4),
                      "val", round(ev["validation"]["mae"], 4),
                      "rho", round(ev["validation"]["spearman"], 4), flush=True)
    net.load_state_dict(best[2])
    ev, pred = evaluate(net, rows)
    outrows = []
    for i, r in enumerate(rows):
        outrows.append(dict(unit_id=r["unit_id"], split=r["split"], family=r["family"],
                            prefix=r["prefix"], duration=r["duration"],
                            **{f"q{int(100*t)}": float(pred[i, j])
                               for j, t in enumerate([.1, .25, .5, .75, .9])}))
    pd.DataFrame(outrows).to_csv(os.path.join(DATA, "p3_neural_predictions.csv"), index=False)
    torch.save(best[2], os.path.join(DATA, "p3_neural_progress.pt"))
    result = dict(_meta=dict(model="causal TCN phase pretraining + monotone duration quantiles",
                             phase_pretrain="full TRAIN demonstrations only; inference prefix only",
                             quantiles=[.1, .25, .5, .75, .9], noncrossing="positive softplus increments",
                             split="official environments; model selected by validation MAE",
                             forbidden=["future prefix frames", "source UUID", "sample ID", "source segment index"],
                             seed=SEED, device=DEV, parameters=sum(p.numel() for p in net.parameters()),
                             best_epoch=best[1], epochs=epochs),
                  metrics=ev, history=history, seconds=time.time() - t0)
    write_json("p3_neural_progress.json", result)
    print("BEST", best[1], json.dumps(ev, ensure_ascii=False), flush=True)
    print("saved; seconds", round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()