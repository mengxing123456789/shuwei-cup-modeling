
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-a 最强单点：在**完全相同的评估协议**下比较 6 个操作状态分割候选。

协议（照抄 p1_model.py，用于与 ARI 0.4138 直接可比）：
  - 评估记录 = panel_records.csv split=='test' 且 segments>=2 的记录（7 条）
  - 真值 = segments.csv 的 seg（每条记录内部按时间编号的语义子任务段）
  - 特征 = 头坐标系低维状态（aperture/reach/normal/fwd/speed + wrist/thumbTip/indexTip）
  - 平滑 5 帧 -> 每条记录内 z-score -> 聚类 -> 连通段落实体化(run id)
  - ARI / Hungarian 帧 F1 / 边界指标(tol=5s)

候选：
  A ward_base      : 复现基线（BIC-GMM 选 K，kmax=8，Ward+链式连通）
  B ward_k25       : 同一 Ward，只把 K 上限从 8 提到 25（长记录 K_true 最大 21）
  C ward_ms        : 多尺度状态（原特征 + 5/15 帧滑动均值），K 上限 12
  D hmm            : 对角高斯 HMM（Baum-Welch + Viterbi），K 由 BIC 选（上限 12）
  E hmm_oracleK    : 同上，K=K_true（模型类上限，用于判断是模型弱还是选 K 弱）
  F hmm_mindur     : D + 最短段 6 帧合并（时间连续性约束）
  G ae_ward        : 自监督 1D 卷积自编码器表征（只在 train 记录上训练）+ Ward
  H ae_hmm         : 自编码器表征 + HMM

输出 data/best_p1a.json（不覆盖任何现有 data/*.json）。
"""
import json
import os
import time

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import adjusted_rand_score, f1_score
from sklearn.mixture import GaussianMixture

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "best_p1a.json")

Z = np.load(os.path.join(DATA, "state.npz"))
fl, fr, gl, gr, dom = Z["fl"], Z["fr"], Z["gl"], Z["gr"], Z["dom"]
rec, T = Z["rec"], Z["t"]
recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
segs = pd.read_csv(os.path.join(DATA, "segments.csv"))
names = json.load(open(os.path.join(DATA, "feature_names.json"), encoding="utf-8"))
splits = recs.set_index("rec")["split"].to_dict()
envs = recs.set_index("rec")["env"].to_dict()
ds = recs.set_index("rec")["dataset"].to_dict()

KEEP = [i for i, n in enumerate(names["state_l"])
        if any(n.endswith(s) for s in ["aperture_norm", "reach_norm", "normal_x",
                                       "normal_y", "normal_z", "fwd_x", "fwd_y",
                                       "fwd_z", "speed"])] + list(range(9))
KEEP = sorted(set(KEEP))


def frames_of(r):
    return np.where(rec == r)[0]


def state_matrix(r):
    ii = frames_of(r)
    k = int(dom[r])
    F = fl[ii] if k == 0 else fr[ii]
    return ii, F[:, KEEP].astype(np.float64)


def smooth(X, w=5):
    if len(X) < w:
        return X
    k = np.ones(w) / w
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, X)


def multiscale(X, ws=(5, 15)):
    out = [X]
    for w in ws:
        if len(X) >= w:
            k = np.ones(w) / w
            out.append(np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, X))
        else:
            out.append(X)
    return np.hstack(out)


def choose_k(X, kmax=8, seed=0):
    Xs = X[::3]
    best, bk = None, 2
    for k in range(2, min(kmax, len(Xs) // 20) + 1):
        try:
            g = GaussianMixture(k, covariance_type="diag", random_state=seed,
                                n_init=2, max_iter=200).fit(Xs)
            b = g.bic(Xs)
        except Exception:
            continue
        if best is None or b < best:
            best, bk = b, k
    return bk


def runs_of(lab):
    """[(start, end_exclusive, label), ...]"""
    out = []
    s = 0
    for i in range(1, len(lab)):
        if lab[i] != lab[i - 1]:
            out.append((s, i, lab[i - 1]))
            s = i
    out.append((s, len(lab), lab[-1]))
    return out


def to_run_id(lab):
    run = np.zeros(len(lab), int)
    m = 0
    for i in range(1, len(lab)):
        if lab[i] != lab[i - 1]:
            m += 1
        run[i] = m
    return run


def merge_short(lab, min_len=6):
    lab = lab.copy()
    for _ in range(200):
        runs = runs_of(lab)
        if len(runs) <= 1:
            break
        short = [(e - s, s, e) for s, e, _ in runs if e - s < min_len]
        if not short:
            break
        _, s, e = min(short)
        # merge into the longer neighbour
        idx = [j for j, (a, b, _) in enumerate(runs) if a == s and b == e][0]
        cand = []
        if idx > 0:
            cand.append(runs[idx - 1])
        if idx + 1 < len(runs):
            cand.append(runs[idx + 1])
        tgt = max(cand, key=lambda r: r[1] - r[0])
        lab[s:e] = lab[tgt[0]]
    return to_run_id(lab)


def ward_segments(X, K):
    n = len(X)
    if n < 3 or K < 2:
        return np.zeros(n, int)
    C = sparse.diags([np.ones(n - 1), np.ones(n - 1)], [1, -1], shape=(n, n), format="csr")
    lab = AgglomerativeClustering(n_clusters=K, connectivity=C, linkage="ward").fit_predict(X)
    for _ in range(2):
        for i in range(1, len(lab) - 1):
            if lab[i] != lab[i - 1] and lab[i] != lab[i + 1]:
                lab[i] = lab[i - 1]
    return to_run_id(lab)


# ---------------- diagonal Gaussian HMM (Baum-Welch, log space) ----------------
def _logsumexp(a, axis):
    m = np.max(a, axis=axis, keepdims=True)
    return np.squeeze(m, axis=axis) + np.log(np.sum(np.exp(a - m), axis=axis) + 1e-300)


def hmm_fit_predict(X, K, iters=45, var_floor=1e-3, seed=0):
    n, d = X.shape
    if K < 2 or n < K * 3:
        return np.zeros(n, int)
    km = KMeans(K, n_init=10, random_state=seed).fit(X)
    lab0 = km.labels_
    mu = np.stack([X[lab0 == k].mean(0) if (lab0 == k).any() else X.mean(0)
                   for k in range(K)])
    var = np.stack([X[lab0 == k].var(0) if (lab0 == k).sum() > 3 else X.var(0)
                    for k in range(K)]) + var_floor
    A = np.full((K, K), 0.5 / max(K - 1, 1))
    np.fill_diagonal(A, 0.5)
    pi = np.full(K, 1.0 / K)

    def emis_log(Xs):
        # (n,K) log N(x; mu_k, var_k)
        out = np.empty((len(Xs), K))
        for k in range(K):
            out[:, k] = (-0.5 * np.sum(np.log(2 * np.pi * var[k]))
                         - 0.5 * np.sum((Xs - mu[k]) ** 2 / var[k], axis=1))
        return out

    prev = -np.inf
    for it in range(iters):
        B = emis_log(X)
        la = np.log(A + 1e-12)
        lpi = np.log(pi + 1e-12)
        alpha = np.empty((n, K))
        alpha[0] = lpi + B[0]
        for t in range(1, n):
            alpha[t] = B[t] + _logsumexp(alpha[t - 1][:, None] + la, axis=0)
        ll = _logsumexp(alpha[-1], axis=0)
        beta = np.zeros((n, K))
        for t in range(n - 2, -1, -1):
            beta[t] = _logsumexp(la + (B[t + 1] + beta[t + 1])[None, :], axis=1)
        gamma = alpha + beta
        gamma -= _logsumexp(gamma, axis=1)[:, None]
        g = np.exp(gamma)
        xi_sum = np.zeros((K, K))
        for t in range(n - 1):
            m = alpha[t][:, None] + la + (B[t + 1] + beta[t + 1])[None, :]
            m -= _logsumexp(m.reshape(-1), axis=0)
            xi_sum += np.exp(m)
        pi = g[0] / g[0].sum()
        A = xi_sum / (xi_sum.sum(1, keepdims=True) + 1e-12)
        A = np.clip(A, 1e-6, None)
        A /= A.sum(1, keepdims=True)
        Nk = g.sum(0) + 1e-9
        mu = (g.T @ X) / Nk[:, None]
        for k in range(K):
            var[k] = ((g[:, k][:, None] * (X - mu[k]) ** 2).sum(0) / Nk[k]) + var_floor
        if abs(ll - prev) < 1e-3:
            break
        prev = ll

    # Viterbi
    B = emis_log(X)
    la = np.log(A + 1e-12)
    dp = np.empty((n, K))
    bp = np.zeros((n, K), int)
    dp[0] = la[0] * 0 + np.log(pi + 1e-12) + B[0]
    for t in range(1, n):
        m = dp[t - 1][:, None] + la
        bp[t] = np.argmax(m, axis=0)
        dp[t] = B[t] + np.max(m, axis=0)
    path = np.zeros(n, int)
    path[-1] = int(np.argmax(dp[-1]))
    for t in range(n - 2, -1, -1):
        path[t] = bp[t + 1, path[t + 1]]
    return path


# ---------------- self-supervised conv autoencoder (train records only) ----------------
def train_ae(epochs=18, win=15, emb=16, seed=20261120):
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    # 82-dim frame features on raw (pre-z-score) scale; standardise globally on train
    F = np.concatenate([fl, fr, gl, gr,
                        Z["validL"][:, None].astype(np.float32),
                        Z["validR"][:, None].astype(np.float32)], axis=1).astype(np.float32)
    tr_recs = [int(r) for r in recs[recs.split == "train"].rec]
    mu = np.nanmean(np.vstack([F[frames_of(r)] for r in tr_recs]), axis=0)
    sd = np.nanstd(np.vstack([F[frames_of(r)] for r in tr_recs]), axis=0) + 1e-6
    F = np.nan_to_num((F - mu) / sd, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    chunks = []
    for r in tr_recs:
        ii = frames_of(r)
        x = F[ii]
        if len(x) > win:
            w = np.lib.stride_tricks.sliding_window_view(x, win, axis=0)  # (N, 82, win)
            chunks.append(w.astype(np.float32))
    X = np.concatenate(chunks, axis=0)
    print(f"[ae] train windows {X.shape}")

    class AE(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Sequential(
                nn.Conv1d(82, 64, 5, padding=2), nn.GELU(),
                nn.Conv1d(64, 32, 5, padding=2), nn.GELU(),
                nn.Conv1d(32, emb, 3, padding=1), nn.GELU())
            self.dec = nn.Sequential(
                nn.Conv1d(emb, 32, 3, padding=1), nn.GELU(),
                nn.Conv1d(32, 64, 5, padding=2), nn.GELU(),
                nn.Conv1d(64, 82, 5, padding=2))

        def forward(self, x):
            z = self.enc(x)
            return self.dec(z), z

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = AE().to(dev)
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-4)
    B = 512
    steps = (len(X) + B - 1) // B
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=epochs * steps)
    lossf = nn.MSELoss()
    Xt = torch.from_numpy(X)
    for ep in range(1, epochs + 1):
        m.train()
        perm = torch.randperm(len(Xt))
        tot = 0.0
        for i in range(steps):
            sel = perm[i * B:(i + 1) * B]
            xb = Xt[sel].to(dev)
            opt.zero_grad(set_to_none=True)
            rec_, _ = m(xb)
            loss = lossf(rec_, xb)
            loss.backward()
            opt.step()
            sch.step()
            tot += float(loss) * len(sel)
        if ep % 6 == 0 or ep == 1:
            print(f"[ae] ep{ep:02d} mse={tot/len(Xt):.4f}")
    m.eval()
    return m, F, dev


def ae_embed(m, F, dev):
    import torch
    out = np.zeros((len(F), 16), np.float32)
    win = 15
    with torch.no_grad():
        for r in np.unique(rec):
            ii = frames_of(r)
            x = F[ii]
            if len(x) < win:
                x = np.pad(x, ((0, win - len(x)), (0, 0)))
            w = np.lib.stride_tricks.sliding_window_view(x, win, axis=0).astype(np.float32)
            zs = []
            for s in range(0, len(w), 2048):
                xb = torch.from_numpy(w[s:s + 2048]).to(dev)
                _, z = m(xb)
                zs.append(z[:, :, -1].cpu().numpy())
            z = np.concatenate(zs, 0)
            if len(z) < len(ii):
                z = np.pad(z, ((0, len(ii) - len(z)), (0, 0)), mode="edge")
            out[ii] = z
    return out


# ---------------- evaluation ----------------
def true_labels(r, ii):
    g = segs[segs.rec == r]
    y = np.full(len(ii), -1)
    for _, s in g.iterrows():
        y[(T[ii] >= s.start) & (T[ii] < s.end)] = int(s.seg)
    return y


def boundary_metrics(pred_b, true_b, t, tol=5.0):
    if len(true_b) == 0:
        return dict(b_mae=np.nan, b_recall=np.nan, b_precision=np.nan, b_count_err=len(pred_b))
    pt = t[pred_b] if len(pred_b) else np.array([])
    tt = t[true_b]
    if len(pt):
        D = np.abs(tt[:, None] - pt[None, :])
        ri, ci = linear_sum_assignment(D)
        ok = D[ri, ci] <= tol
        mae = float(np.mean(D[ri[ok], ci[ok]])) if ok.any() else np.nan
        recall = float(ok.sum() / len(tt))
        precision = float(ok.sum() / len(pt))
    else:
        mae, recall, precision = np.nan, 0.0, 0.0
    return dict(b_mae=mae, b_recall=recall, b_precision=precision,
                b_count_err=abs(len(pred_b) - len(true_b)))


def score(lab, y, tt):
    ari = adjusted_rand_score(y, lab)
    yl, pl = np.unique(y), np.unique(lab)
    M = np.zeros((len(yl), len(pl)))
    for a in yl:
        for b in pl:
            M[a, b] = ((y == a) & (lab == b)).sum()
    ri, ci = linear_sum_assignment(-M)
    mp = {pl[c]: yl[rr] for rr, c in zip(ri, ci)}
    pred = np.array([mp.get(v, -1) for v in lab])
    f1 = f1_score(y, pred, average="micro")
    tb = np.where(np.diff(y) != 0)[0] + 1
    bm = boundary_metrics(np.where(np.diff(lab) != 0)[0] + 1, tb, tt, 5.0)
    return dict(ari=float(ari), f1=float(f1), n_seg=int(len(np.unique(lab))), **bm)


def main():
    t0 = time.time()
    eval_recs = [int(r) for r in recs[recs.split == "test"].rec
                 if len(segs[segs.rec == r]) >= 2]
    print("eval records", eval_recs)

    # prepare per-record matrices once
    cache = {}
    for r in eval_recs:
        ii, X = state_matrix(r)
        y = true_labels(r, ii)
        good = y >= 0
        Xg = np.nan_to_num(X[good], nan=0.0, posinf=0.0, neginf=0.0)
        Xg = smooth(Xg, 5)
        Xg = (Xg - Xg.mean(0)) / (Xg.std(0) + 1e-6)
        cache[r] = dict(X=Xg, y=y[good], t=T[ii][good], Ktrue=int(len(np.unique(y[good]))),
                        n=int(good.sum()), ii=ii, good=good)
        print(f"  rec {r:02d} n={good.sum():5d} Ktrue={cache[r]['Ktrue']}")

    # AE representation
    print("\n=== self-supervised conv AE (train records only) ===")
    t_ae = time.time()
    m, Fae, dev = train_ae()
    E = ae_embed(m, Fae, dev)
    print(f"[ae] {time.time()-t_ae:.1f}s  emb={E.shape}")

    cands = {}

    def add(tag, r, lab):
        c = cache[r]
        cands.setdefault(tag, []).append(dict(rec=r, dataset=ds[r], env=envs[r],
                                              **score(lab, c["y"], c["t"])))

    for r in eval_recs:
        c = cache[r]
        X, Kt = c["X"], c["Ktrue"]

        # A baseline replication
        K8 = choose_k(X, kmax=8)
        add("ward_base", r, ward_segments(X, K8))
        # B k up to 25
        K25 = choose_k(X, kmax=25)
        add("ward_k25", r, ward_segments(X, K25))
        # C multiscale
        Xms = (lambda Zx: (Zx - Zx.mean(0)) / (Zx.std(0) + 1e-6))(multiscale(X))
        Kms = choose_k(Xms, kmax=12)
        add("ward_ms", r, ward_segments(Xms, Kms))
        # D HMM k12
        K12 = choose_k(X, kmax=12)
        lab_h = hmm_fit_predict(X, K12, iters=45, seed=20261120)
        add("hmm", r, to_run_id(lab_h))
        # E oracle K
        lab_ho = hmm_fit_predict(X, Kt, iters=45, seed=20261120)
        add("hmm_oracleK", r, to_run_id(lab_ho))
        # F min duration
        add("hmm_mindur", r, merge_short(lab_h, min_len=6))
        # G AE + Ward
        Xa = E[c["ii"]][c["good"]]
        Xa = smooth(np.nan_to_num(Xa), 5)
        Xa = (Xa - Xa.mean(0)) / (Xa.std(0) + 1e-6)
        Ka = choose_k(Xa, kmax=12)
        add("ae_ward", r, ward_segments(Xa, Ka))
        # H AE + HMM
        add("ae_hmm", r, to_run_id(hmm_fit_predict(Xa, Ka, iters=45, seed=20261120)))

    methods = {}
    for tag, rows in cands.items():
        df = pd.DataFrame(rows)
        methods[tag] = dict(
            records={int(x.rec): {k: (float(getattr(x, k)) if k != "n_seg" else int(getattr(x, k)))
                                  for k in ["ari", "f1", "b_mae", "b_recall",
                                            "b_precision", "b_count_err", "n_seg"]}
                     for x in df.itertuples()},
            mean={k: float(df[k].mean()) for k in
                  ["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err", "n_seg"]},
            std={k: float(df[k].std(ddof=1)) for k in
                 ["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err", "n_seg"]})

    baseline = 0.4138423666260523
    out = dict(
        _meta=dict(
            protocol="exactly p1_model.py: test records with >=2 segments, seg index labels, "
                     "head-frame 17-dim state, smooth5, per-record z-score, run-id conversion, "
                     "ARI + Hungarian F1 + boundary tol 5s",
            baseline_ward_ari=baseline, baseline_ward_f1=0.5613169824306583,
            baseline_source="data/p1_segmentation.json / ablation.ward",
            state_dims=int(len(KEEP)), state_feature_names=[names["state_l"][i] for i in KEEP],
            eval_records=eval_recs, seeds=20261120,
            note="all candidates recomputed in this file; ward_base reproduces the official baseline"),
        methods=methods,
        delta_ari_vs_baseline={k: float(v["mean"]["ari"] - baseline) for k, v in methods.items()},
        seconds=round(time.time() - t0, 1),
    )
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("\n=== summary (mean over 7 test records) ===")
    for k, v in sorted(methods.items(), key=lambda kv: -kv[1]["mean"]["ari"]):
        mm = v["mean"]
        print(f"{k:14s} ARI={mm['ari']:.4f}  F1={mm['f1']:.4f}  bMAE={mm['b_mae']:.2f}  "
              f"nseg={mm['n_seg']:.1f}")
    print(f"\nsaved -> {OUT}  ({out['seconds']}s)")


if __name__ == "__main__":
    main()