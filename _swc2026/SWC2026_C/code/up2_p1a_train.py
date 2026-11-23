# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a v2 training: multi-task temporal encoder (boundary + contrastive stage + bad frame),
optionally preceded by masked-keypoint self-supervised pretraining on all 69 records.

PREREGISTRATION (fixed before this script ran):
  gate: test mean ARI >= 0.62 AND test mean boundary F1 >= 0.30
  bf1 = up_p1a_final.py definition (+-2 frames, greedy nearest match)
  every hyper-parameter is selected on VALIDATION only; test is scored once by
  up2_p1a_final.py, which reads checkpoints written here.

Why these heads:
  * boundary head: focal BCE against a SHARP soft target (sigma=1.0 frame).  The v1 run
    used sigma=2.5, and its peaks land >2 frames off on validation (probe2: only 21%
    within +-2), which is exactly the bf1 failure.
  * contrastive stage head: frames of the same annotated subtask are pulled together,
    frames across a boundary pushed apart; 1-cos(emb_t, emb_t+1) is a second,
    representation-level change-point score that does not rely on the boundary head.
  * bad-frame head: predicts the annotated occlusion/edge flags (auxiliary, label
    available for train records), forcing the trunk to model hand visibility.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import up2_p1a_lib as L
import p1a_gpu_segmentation as M

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CHUNK = 384
FEAT = os.path.join(L.DATA, "up2_p1a_feats.npz")


# ------------------------------------------------------------- features ----
def kinematics(x):
    """14 label-free motion descriptors, computed on the normalised frame matrix."""
    x = np.asarray(x, np.float64)
    n = len(x)
    v = np.zeros_like(x)
    v[1:] = np.diff(x, axis=0)
    a = np.zeros_like(x)
    a[1:] = np.diff(v, axis=0)
    left, right = x[:, 0:32], x[:, 32:64]
    vl, vr = v[:, 0:32], v[:, 32:64]
    al, ar = a[:, 0:32], a[:, 32:64]
    sp_l = np.linalg.norm(vl, axis=1)
    sp_r = np.linalg.norm(vr, axis=1)
    sp = np.linalg.norm(v[:, 0:64], axis=1)
    ac = np.linalg.norm(a[:, 0:64], axis=1)
    wl = np.linalg.norm(v[:, 0:3], axis=1)
    wr = np.linalg.norm(v[:, 32:35], axis=1)
    rel = np.linalg.norm(vl - vr, axis=1)
    med = np.median(sp) + 1e-6
    k = np.exp(-0.5 * (np.arange(-2, 3) / 2.0) ** 2)
    k /= k.sum()
    sp_s = np.convolve(sp, k, mode="same")
    ac_s = np.convolve(ac, k, mode="same")
    feats = np.stack([sp_l, sp_r, sp, ac, wl, wr, rel, sp / med, ac / (med + 1e-6),
                      sp_s, ac_s, (sp < 0.15 * med).astype(float),
                      np.maximum(sp_l, sp_r), np.abs(sp_l - sp_r)], axis=1)
    return np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def build_features(verbose=True):
    D = L.load_cache()
    tr = L.ids(D, "train")
    kin = [kinematics(D["X"][i]) for i in range(len(D["rec"]))]
    K = np.concatenate(kin, 0)
    frame_mask = np.concatenate([np.full(len(kin[i]), D["split"][i] == "train")
                                 for i in range(len(kin))])
    mu, sd = K[frame_mask].mean(0), K[frame_mask].std(0) + 1e-6
    kin = [np.clip((k - mu) / sd, -8, 8).astype(np.float32) for k in kin]
    Xf = [np.concatenate([D["X"][i], kin[i]], 1).astype(np.float32) for i in range(len(D["rec"]))]
    np.savez_compressed(FEAT, rec=np.array(D["rec"], dtype=object),
                        X=np.array(Xf, dtype=object), kin_mu=mu, kin_sd=sd)
    if verbose:
        print(f"features: dim {Xf[0].shape[1]} (84 raw + {kin[0].shape[1]} kinematic)", flush=True)
    return D, Xf


def load_features():
    if not os.path.exists(FEAT):
        return build_features()
    z = np.load(FEAT, allow_pickle=True)
    D = L.load_cache()
    return D, [np.asarray(a, np.float32) for a in z["X"]]


# ----------------------------------------------------------------- model ----
class Block(nn.Module):
    def __init__(self, c, d, k=5, p=0.10):
        super().__init__()
        self.c1 = nn.Conv1d(c, c, k, padding=d * (k - 1) // 2, dilation=d)
        self.c2 = nn.Conv1d(c, c, k, padding=d * (k - 1) // 2, dilation=d)
        self.n1, self.n2 = nn.GroupNorm(8, c), nn.GroupNorm(8, c)
        self.p = nn.Dropout(p)

    def forward(self, x):
        h = self.p(F.gelu(self.n1(self.c1(x))))
        h = self.n2(self.c2(h))
        return F.gelu(x + self.p(h))


class Trunk(nn.Module):
    def __init__(self, fin, c=96, dil=(1, 2, 4, 8, 4)):
        super().__init__()
        self.inp = nn.Conv1d(fin, c, 1)
        self.blocks = nn.Sequential(*[Block(c, d) for d in dil])
        self.out_dim = c

    def forward(self, x):
        return self.blocks(self.inp(x))


class MultiTask(nn.Module):
    def __init__(self, fin, c=96, emb=24):
        super().__init__()
        self.trunk = Trunk(fin, c)
        self.b_head = nn.Sequential(nn.Conv1d(c, 48, 1), nn.GELU(), nn.Conv1d(48, 1, 1))
        self.e_head = nn.Sequential(nn.Conv1d(c, 32, 1), nn.GELU(), nn.Conv1d(32, emb, 1))
        self.bad_head = nn.Sequential(nn.Conv1d(c, 32, 1), nn.GELU(), nn.Conv1d(32, 2, 1))

    def forward(self, x):
        h = self.trunk(x)
        return self.b_head(h).squeeze(1), self.e_head(h), self.bad_head(h)

    def forward_bidir(self, x):
        """Offline labelling: average forward and time-reversed passes."""
        b1, e1, d1 = self.forward(x)
        b2, e2, d2 = self.forward(torch.flip(x, dims=[2]))
        return (0.5 * (b1 + torch.flip(b2, dims=[1])),
                0.5 * (e1 + torch.flip(e2, dims=[2])),
                0.5 * (d1 + torch.flip(d2, dims=[2])))


class Recon(nn.Module):
    def __init__(self, trunk, fin):
        super().__init__()
        self.trunk = trunk
        self.dec = nn.Sequential(nn.Conv1d(trunk.out_dim, 64, 1), nn.GELU(),
                                 nn.Conv1d(64, fin, 1))

    def forward(self, x):
        return self.dec(self.trunk(x))


# ------------------------------------------------------------- tensors -----
def to_t(x):
    return torch.from_numpy(np.ascontiguousarray(x)).unsqueeze(0).float().to(DEVICE)


def chunk_aug(x, kin_split=84, p_flip=0.5, p_noise=0.5):
    """Mirror the two hands with probability p_flip, add small noise."""
    y = x.copy()
    if np.random.rand() < p_flip:
        y[:, 0:32], y[:, 32:64] = x[:, 32:64].copy(), x[:, 0:32].copy()
        y[:, 64:72], y[:, 72:80] = x[:, 72:80].copy(), x[:, 64:72].copy()
        y[:, 80], y[:, 81] = x[:, 81], x[:, 80]
    if np.random.rand() < p_noise:
        y[:, :kin_split] += np.random.randn(*y[:, :kin_split].shape).astype(np.float32) * 0.05
    return y


def make_target(d, r, sigma):
    """Sharp soft boundary target from the segment ids (inside the annotated region)."""
    i = L.pos(d, r)
    sb = d["sub"][i]
    n = d["n"][i]
    hard = L.true_bounds(d, r)
    soft = np.zeros(n, np.float32)
    if sigma and len(hard):
        r0 = int(np.ceil(4 * sigma))
        for j in hard:
            lo, hi = max(0, j - r0), min(n, j + r0 + 1)
            dd = np.arange(lo, hi) - j
            soft[lo:hi] = np.maximum(soft[lo:hi], np.exp(-0.5 * (dd / sigma) ** 2))
    elif len(hard):
        soft[hard] = 1.0
    return soft, d["inside"][i].astype(np.float32), hard


def focal_bce(logit, target, weight, alpha=0.8, gamma=2.0):
    p = torch.sigmoid(logit)
    ce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    pt = torch.where(target > 0.5, p, 1 - p)
    at = torch.where(target > 0.5, torch.full_like(target, alpha),
                     torch.full_like(target, 1 - alpha))
    return (ce * at * (1 - pt).pow(gamma) * weight).sum() / weight.sum().clamp_min(1)


def contrastive_loss(emb, seg, valid, tau=0.2, max_frames=96):
    """NT-Xent over frames of a chunk: positives share the annotated segment id."""
    idx = torch.where(valid > 0)[0]
    if len(idx) < 8:
        return torch.zeros((), device=emb.device)
    if len(idx) > max_frames:
        sel = idx[torch.randperm(len(idx), device=emb.device)[:max_frames]]
    else:
        sel = idx
    e = emb[0][:, sel].T                      # frames x emb
    s = seg[sel]
    e = F.normalize(e, dim=1)
    sim = e @ e.T / tau
    same = (s[:, None] == s[None, :])
    eye = torch.eye(len(sel), device=emb.device, dtype=torch.bool)
    pos = same & ~eye
    if pos.sum() == 0:
        return torch.zeros((), device=emb.device)
    logprob = sim - torch.logsumexp(sim.masked_fill(eye, -1e4), dim=1, keepdim=True)
    loss = -(logprob * pos).sum() / pos.sum().clamp_min(1)
    return loss


# ------------------------------------------------------------- training ----
def infer_scores(net, Xf, recs, D):
    net.eval()
    out = {}
    with torch.no_grad():
        for r in recs:
            i = L.pos(D, r)
            x = Xf[i]
            if len(x) <= 4096:
                b, e, _ = net.forward_bidir(to_t(x.T))
                sc = torch.sigmoid(b).squeeze(0).cpu().numpy()
                emb = F.normalize(e.squeeze(0).T, dim=1).cpu().numpy()
            else:
                sc = np.zeros(len(x), np.float32)
                emb = np.zeros((len(x), net.e_head[-1].out_channels), np.float32)
                for a in range(0, len(x), 2048):
                    seg = x[a:a + 2048]
                    b, e, _ = net.forward_bidir(to_t(seg.T))
                    sc[a:a + len(seg)] = torch.sigmoid(b).squeeze(0).cpu().numpy()
                    emb[a:a + len(seg)] = F.normalize(e.squeeze(0).T, dim=1).cpu().numpy()
            chg = np.zeros(len(x), np.float32)
            if len(x) > 1:
                chg[1:] = 1.0 - np.sum(emb[1:] * emb[:-1], axis=1)
            out[r] = dict(score=sc.astype(np.float32), chg=chg.astype(np.float32))
    return out


def val_objective(net, Xf, D, VA):
    """Validation criterion: mean ARI + 0.5 * mean bf1 under ONE fixed decoder."""
    pred = infer_scores(net, Xf, VA, D)
    pk = {r: L.decode_dp(pred[r]["score"], sigma=0.7, min_len=20, lam=0.5,
                         cand_dist=5, prom_floor=0.02, n=D["n"][L.pos(D, r)]) for r in VA}
    ev = L.eval_peaks(pk, D, VA)
    return ev["mean_ari"], ev["mean_bf1"], ev


def train_mtask(D, Xf, seeds, epochs, lr=2e-3, sigma=1.0, ssl_ckpt=None, tag="mtask",
                verbose=True):
    TR, VA = L.ids(D, "train"), L.ids(D, "validation")
    tgt = {r: make_target(D, r, sigma) for r in TR + VA}
    outs, hist = [], []
    for seed in seeds:
        t0 = time.time()
        torch.manual_seed(seed)
        np.random.seed(seed)
        net = MultiTask(Xf[0].shape[1]).to(DEVICE)
        if ssl_ckpt:
            sd = torch.load(ssl_ckpt, map_location=DEVICE)
            net.trunk.load_state_dict(sd["trunk"])
            if verbose:
                print(f"  seed {seed}: trunk initialised from SSL ({ssl_ckpt})", flush=True)
        opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)
        steps = epochs * len(TR)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps,
                                                    pct_start=0.25)
        best = (-1e9, None, -1)
        for ep in range(epochs):
            net.train()
            order = np.random.permutation(len(TR))
            tot = nb = 0.0
            for j in order:
                r = TR[j]
                i = L.pos(D, r)
                x = Xf[i]
                n = len(x)
                if n <= 8:
                    continue
                a = np.random.randint(0, max(1, n - CHUNK))
                b = min(n, a + CHUNK)
                xb = chunk_aug(x[a:b])
                sb, mb, _ = tgt[r]
                sb_t = torch.from_numpy(sb[a:b]).unsqueeze(0).to(DEVICE)
                mb_t = torch.from_numpy(mb[a:b]).unsqueeze(0).to(DEVICE)
                seg_t = torch.from_numpy(D["sub"][i][a:b].astype(np.int64)).to(DEVICE)
                bad_t = torch.from_numpy(D["bad"][i][a:b].T).unsqueeze(0).to(DEVICE)
                logit, emb, bad = net.forward(to_t(xb.T))
                w = mb_t * (1.0 + 20.0 * sb_t)
                l_b = focal_bce(logit, sb_t, w)
                l_c = contrastive_loss(emb, seg_t, mb_t)
                l_bad = F.binary_cross_entropy_with_logits(bad, bad_t, reduction="none")
                wb = mb_t.unsqueeze(1).expand_as(l_bad)
                l_bad = (l_bad * wb).sum() / wb.sum().clamp_min(1)
                loss = l_b + 0.30 * l_c + 0.10 * l_bad
                opt.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 2.0)
                opt.step()
                sched.step()
                tot += float(loss.detach())
                nb += 1
            if ep % 5 == 4 or ep == epochs - 1:
                ari, bf1, _ = val_objective(net, Xf, D, VA)
                sc = ari + 0.5 * bf1
                if verbose:
                    print(f"  seed {seed} ep {ep+1:2d}/{epochs} loss {tot/max(nb,1):.4f} "
                          f"| val ARI {ari:.4f} bf1 {bf1:.4f} obj {sc:.4f}", flush=True)
                if sc > best[0]:
                    best = (sc, {k: v.detach().cpu().clone() for k, v in net.state_dict().items()},
                            ep + 1)
        if best[1] is not None:
            net.load_state_dict(best[1])
        path = os.path.join(L.MODELS, f"up2_p1a_{tag}_seed{seed}.pt")
        torch.save(net.state_dict(), path)
        ari, bf1, _ = val_objective(net, Xf, D, VA)
        hist.append(dict(seed=seed, val_ari=ari, val_bf1=bf1, best_epoch=best[2],
                         seconds=round(time.time() - t0, 1), ckpt=path))
        outs.append(net)
        torch.cuda.empty_cache()
        if verbose:
            print(f"  seed {seed} done {time.time()-t0:.1f}s val ARI {ari:.4f} bf1 {bf1:.4f} "
                  f"(best ep {best[2]})", flush=True)
    return outs, hist


def pretrain_ssl(D, Xf, epochs=15, mask_frac=0.15, span=10, lr=1e-3, seed=20261121):
    """Masked keypoint modelling on ALL 69 records (inputs only, no labels)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    allrec = list(D["rec"])
    trunk = Trunk(Xf[0].shape[1]).to(DEVICE)
    net = Recon(trunk, Xf[0].shape[1]).to(DEVICE)
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)
    t0 = time.time()
    for ep in range(epochs):
        net.train()
        order = np.random.permutation(len(allrec))
        tot = nb = 0.0
        for j in order:
            i = j
            x = Xf[i]
            n = len(x)
            if n <= 8:
                continue
            a = np.random.randint(0, max(1, n - CHUNK))
            xb = x[a:min(n, a + CHUNK)].copy()
            Lc = len(xb)
            mask = np.zeros((Lc, xb.shape[1]), bool)
            nspan = max(1, int(mask_frac * Lc / span))
            for _ in range(nspan):
                s = np.random.randint(0, max(1, Lc - span))
                mask[s:s + span] = True
            cmask = np.random.rand(xb.shape[1]) < mask_frac
            mask |= cmask[None, :]
            if mask.sum() == 0:
                continue
            xm = xb.copy()
            xm[mask] = 0.0
            rec = net(to_t(xm.T)).squeeze(0).T
            tgt = torch.from_numpy(xb).to(DEVICE)
            m = torch.from_numpy(mask.astype(np.float32)).to(DEVICE)
            loss = (((rec - tgt) ** 2) * m).sum() / m.sum().clamp_min(1)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 2.0)
            opt.step()
            tot += float(loss.detach())
            nb += 1
        print(f"  ssl ep {ep+1:2d}/{epochs} masked MSE {tot/max(nb,1):.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    path = os.path.join(L.MODELS, "up2_p1a_ssl_trunk.pt")
    torch.save(dict(trunk=trunk.state_dict(), epochs=epochs, mask_frac=mask_frac,
                    span=span, seconds=round(time.time() - t0, 1)), path)
    print(f"  ssl trunk saved {path}", flush=True)
    return path


def save_scores(D, Xf, nets, tag, recs):
    """Ensemble scores of the seed nets for the given records (never mix test in here)."""
    mem = []
    for net in nets:
        mem.append(infer_scores(net, Xf, recs, D))
    score = {r: np.mean([m[r]["score"] for m in mem], 0) for r in recs}
    chg = {r: np.mean([m[r]["chg"] for m in mem], 0) for r in recs}
    np.savez_compressed(os.path.join(L.DATA, f"up2_p1a_scores_{tag}.npz"),
                        rec=np.array(recs), score=np.array([score[r] for r in recs], dtype=object),
                        chg=np.array([chg[r] for r in recs], dtype=object))
    return score, chg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="mtask")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--sigma", type=float, default=1.0)
    ap.add_argument("--ssl", action="store_true", help="run masked-keypoint pretraining first")
    ap.add_argument("--ssl-epochs", type=int, default=15)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    D, Xf = load_features()
    TR, VA = L.ids(D, "train"), L.ids(D, "validation")
    print(f"device {DEVICE} | train {len(TR)} val {len(VA)} | dim {Xf[0].shape[1]} "
          f"| mode {a.tag}", flush=True)
    seeds = [20261121 + i for i in range(a.seeds)]
    epochs = 3 if a.smoke else a.epochs
    ckpt = None
    if a.ssl:
        ckpt = pretrain_ssl(D, Xf, epochs=(3 if a.smoke else a.ssl_epochs))
    nets, hist = train_mtask(D, Xf, seeds, epochs, sigma=a.sigma, ssl_ckpt=ckpt, tag=a.tag)
    score, chg = save_scores(D, Xf, nets, a.tag, TR + VA)
    # quick reference decode on validation (selection proper happens in up2_p1a_select.py)
    pk = {r: L.decode_dp(score[r], sigma=0.7, min_len=20, lam=0.5, cand_dist=5,
                         prom_floor=0.02, n=D["n"][L.pos(D, r)]) for r in VA}
    ev = L.eval_peaks(pk, D, VA, "ref_dp")
    print(f"val reference DP: ARI {ev['mean_ari']:.4f} bf1 {ev['mean_bf1']:.4f}", flush=True)
    print(ev["frame"].round(3).to_string(index=False), flush=True)
    params = int(sum(p.numel() for p in nets[0].parameters()))
    L.save_json(os.path.join(L.DATA, f"up2_p1a_train_{a.tag}.json"),
                dict(tag=a.tag, seeds=seeds, epochs=epochs, sigma=a.sigma, ssl=bool(a.ssl),
                     ssl_ckpt=ckpt, params=params, history=hist,
                     val_reference=dict(ari=ev["mean_ari"], bf1=ev["mean_bf1"],
                                         per_record=ev["per_record"]),
                     seconds=round(time.time() - t0, 1)))
    print(f"total {time.time()-t0:.1f}s params {params}", flush=True)


if __name__ == "__main__":
    main()