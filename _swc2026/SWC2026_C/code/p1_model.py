
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1: reliability model (geometry vs annotated bad frames) and unsupervised
temporal segmentation aligned with subtask annotations.

Outputs data/p1_reliability.json, data/p1_segmentation.json,
data/p1_tables.csv, figures/fig1..fig3, fig7.
"""
import os, json, itertools
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import sparse
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import roc_auc_score, average_precision_score, adjusted_rand_score, f1_score
from scipy.optimize import linear_sum_assignment
from common import DATA, FIG, write_json, ensure_dirs

ensure_dirs()
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
Z = np.load(os.path.join(DATA, "state.npz"))
fl, fr, gl, gr, dom = Z["fl"], Z["fr"], Z["gl"], Z["gr"], Z["dom"]
badL, badR, rec, T = Z["badL"], Z["badR"], Z["rec"], Z["t"]
recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
segs = pd.read_csv(os.path.join(DATA, "segments.csv"))
names = json.load(open(os.path.join(DATA, "feature_names.json"), encoding="utf-8"))
splits = recs.set_index("rec")["split"].to_dict()
envs = recs.set_index("rec")["env"].to_dict()
ds = recs.set_index("rec")["dataset"].to_dict()


def frames_of(r):
    return np.where(rec == r)[0]


# ---------------- reliability ----------------
def build_geom(split):
    X, y, rid = [], [], []
    for r in recs[recs.split == split].rec:
        ii = frames_of(r)
        X.append(gl[ii]); y.append(badL[ii]); rid.append(np.full(len(ii), r))
        X.append(gr[ii]); y.append(badR[ii]); rid.append(np.full(len(ii), r))
    return np.vstack(X), np.concatenate(y), np.concatenate(rid)


Xtr, ytr, rtr = build_geom("train")
Xva, yva, rva = build_geom("validation")
Xte, yte, rte = build_geom("test")


def add_context(X):
    """5-frame trailing means of jump / jump_max: occlusion lasts many frames,
    single-frame geometry is noisy."""
    out = [X]
    for j in (6, 7):
        c = np.convolve(X[:, j], np.ones(5) / 5, mode="same")
        out.append(c[:, None])
    return np.hstack(out)


Xtr_c, Xva_c, Xte_c = add_context(Xtr), add_context(Xva), add_context(Xte)
sc = StandardScaler().fit(Xtr_c)
Xtr_s, Xva_s, Xte_s = sc.transform(Xtr_c), sc.transform(Xva_c), sc.transform(Xte_c)
clf = LogisticRegression(C=0.1, class_weight="balanced", max_iter=5000, solver="liblinear").fit(Xtr_s, ytr)
p_tr, p_va, p_te = clf.predict_proba(Xtr_s)[:, 1], clf.predict_proba(Xva_s)[:, 1], clf.predict_proba(Xte_s)[:, 1]
# geometry score is oriented so that LARGER = more likely bad, then mapped to reliability R.
# p_* is P(bad); reliability R = 1 - p.

# unsupervised geometry score: Mahalanobis distance from train distribution
cov = np.cov(Xtr_s.T) + np.eye(Xtr_s.shape[1]) * 1e-6
inv = np.linalg.pinv(cov)
d2_tr = np.einsum("ij,jk,ik->i", Xtr_s, inv, Xtr_s)
d2_va = np.einsum("ij,jk,ik->i", Xva_s, inv, Xva_s)
d2_te = np.einsum("ij,jk,ik->i", Xte_s, inv, Xte_s)
scale = np.median(d2_tr)
r_geo_tr, r_geo_va, r_geo_te = np.exp(-0.5 * d2_tr / scale), np.exp(-0.5 * d2_va / scale), np.exp(-0.5 * d2_te / scale)
r_fus_va = 0.5 * (1 - p_va) + 0.5 * r_geo_va
r_fus_te = 0.5 * (1 - p_te) + 0.5 * r_geo_te

# AUC convention: score_bad must INCREASE with P(bad). Geometry distance d2 and
# calibrated p are both such scores; reliability R is oriented the other way.
per_env = []
env_of = dict(zip(recs.rec, recs.env))
for e in sorted(set(env_of[r] for r in np.unique(rte))):
    sub = np.isin(rte, [r for r in np.unique(rte) if env_of[r] == e])
    if len(np.unique(yte[sub])) == 2:
        per_env.append(dict(env=str(e), n=int(sub.sum()), positives=int(yte[sub].sum()),
                            auc_bad=float(roc_auc_score(yte[sub], p_te[sub]))))
rel = dict(_meta=dict(n_train=int(len(ytr)), n_val=int(len(yva)), n_test=int(len(yte)),
                      positives_train=int(ytr.sum()), positives_val=int(yva.sum()), positives_test=int(yte.sum()),
                      positive_rate_test=float(yte.mean()),
                      features=names["geom_l"] + ["jump_mean5", "jump_max_mean5"],
                      label="annotated hand bad frame (occlusion/edge)",
                      auc_convention="AUC_bad: score increases with P(bad frame); 0.5 = chance"),
           auc_bad_calibrated=dict(train=float(roc_auc_score(ytr, p_tr)),
                                   validation=float(roc_auc_score(yva, p_va)),
                                   test=float(roc_auc_score(yte, p_te))),
           auc_bad_geometry=dict(train=float(roc_auc_score(ytr, d2_tr)),
                                 validation=float(roc_auc_score(yva, d2_va)),
                                 test=float(roc_auc_score(yte, d2_te))),
           auc_bad_fused=dict(validation=float(roc_auc_score(yva, 1 - r_fus_va)),
                              test=float(roc_auc_score(yte, 1 - r_fus_te))),
           ap_bad_calibrated=dict(validation=float(average_precision_score(yva, p_va)),
                                  test=float(average_precision_score(yte, p_te))),
           ap_bad_geometry=dict(validation=float(average_precision_score(yva, d2_va)),
                                test=float(average_precision_score(yte, d2_te))),
           ap_bad_fused=dict(validation=float(average_precision_score(yva, 1 - r_fus_va)),
                             test=float(average_precision_score(yte, 1 - r_fus_te))),
           ap_baseline_test=float(yte.mean()),
           per_env_test=per_env,
           coef={k: float(v) for k, v in zip(names["geom_l"] + ["jump_mean5", "jump_max_mean5"], clf.coef_[0])},
           formula="R = 0.5*(1 - sigma(w.x_geo + b)) + 0.5*exp(-0.5*Mahalanobis(x_geo)^2/median_train)",
           threshold_sensitivity=[])
for th in [0.3, 0.5, 0.6, 0.7, 0.8, 0.9]:
    keep = r_fus_te >= th
    tp = int((keep & (yte == 1)).sum()); fp = int((keep & (yte == 0)).sum())
    fn = int((~keep & (yte == 1)).sum())
    rel["threshold_sensitivity"].append(dict(threshold=th, retained=float(keep.mean()),
        bad_recall=float(tp / max(tp + fn, 1)), bad_precision=float(tp / max(tp + fp, 1)),
        f1=float(2 * tp / max(2 * tp + fp + fn, 1))))

# ---------------- segmentation ----------------
SEL_DIMS = None
def state_matrix(r):
    ii = frames_of(r)
    k = int(dom[r])
    F = fl[ii] if k == 0 else fr[ii]
    keep = [i for i, n in enumerate(names["state_l"]) if any(n.endswith(s) for s in
            ["aperture_norm", "reach_norm", "normal_x", "normal_y", "normal_z", "fwd_x", "fwd_y", "fwd_z", "speed"])]
    # positions of wrist / thumb tip / index tip
    keep += [0, 1, 2, 3, 4, 5, 6, 7, 8]
    return ii, F[:, sorted(set(keep))]


PANEL = np.load(os.path.join(DATA, "panel.npz"))


def raw_matrix(r):
    ii = frames_of(r)
    return ii, np.concatenate([PANEL["L"][ii].reshape(len(ii), -1),
                               PANEL["R"][ii].reshape(len(ii), -1)], axis=1)


def smooth(X, w=5):
    if len(X) < w:
        return X
    k = np.ones(w) / w
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, X)


def choose_k(X, kmax=8):
    Xs = X[::3]
    best, bk = None, 2
    for k in range(2, min(kmax, len(Xs) // 20) + 1):
        try:
            g = GaussianMixture(k, covariance_type="diag", random_state=0, n_init=2, max_iter=200).fit(Xs)
            b = g.bic(Xs)
        except Exception:
            continue
        if best is None or b < best:
            best, bk = b, k
    return bk


def ward_segments(X, K):
    n = len(X)
    if n < 3 or K < 2:
        return np.zeros(n, int)
    C = sparse.diags([np.ones(n - 1), np.ones(n - 1)], [1, -1], shape=(n, n), format="csr")
    lab = AgglomerativeClustering(n_clusters=K, connectivity=C, linkage="ward").fit_predict(X)
    # remove isolated flickers, then relabel contiguous runs
    for _ in range(2):
        for i in range(1, len(lab) - 1):
            if lab[i] != lab[i - 1] and lab[i] != lab[i + 1]:
                lab[i] = lab[i - 1]
    _, runs = np.unique(lab, return_inverse=True)
    # merge non-adjacent repeats of same label by run id
    run_id = np.zeros(len(lab), int); m = 0
    for i in range(1, len(lab)):
        if lab[i] != lab[i - 1]:
            m += 1
        run_id[i] = m
    return run_id


def kmeans_segments(X, K):
    from sklearn.cluster import KMeans
    n = len(X)
    lab = KMeans(K, n_init=5, random_state=0).fit_predict(X)
    for _ in range(2):
        for i in range(1, n - 1):
            if lab[i] != lab[i - 1] and lab[i] != lab[i + 1]:
                lab[i] = lab[i - 1]
    run_id = np.zeros(n, int); m = 0
    for i in range(1, n):
        if lab[i] != lab[i - 1]:
            m += 1
        run_id[i] = m
    return run_id


def true_labels(r, ii):
    g = segs[segs.rec == r]
    y = np.full(len(ii), -1)
    for _, s in g.iterrows():
        y[(T[ii] >= s.start) & (T[ii] < s.end)] = int(s.seg)
    return y


def boundaries(lab):
    return np.where(np.diff(lab) != 0)[0] + 1


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


def eval_record(r, method="ward", oracle_k=False, tol=5.0, feature=None):
    feat = feature or ("head" if method == "ward" else "raw")
    ii, X = (state_matrix(r) if feat == "head" else raw_matrix(r))
    y = true_labels(r, ii)
    good = y >= 0
    if good.sum() < 20 or len(np.unique(y[good])) < 2:
        return None
    X = X[good]; y = y[good]; tt = T[ii][good]
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X = smooth(X, 5)
    X = (X - X.mean(0)) / (X.std(0) + 1e-6)
    K = len(np.unique(y)) if oracle_k else choose_k(X)
    lab = ward_segments(X, K) if method == "ward" else kmeans_segments(X, K)
    ari = adjusted_rand_score(y, lab)
    # Hungarian frame F1
    yl, pl = np.unique(y), np.unique(lab)
    M = np.zeros((len(yl), len(pl)))
    for a in yl:
        for b in pl:
            M[a, b] = ((y == a) & (lab == b)).sum()
    ri, ci = linear_sum_assignment(-M)
    mp = {pl[c]: yl[rr] for rr, c in zip(ri, ci)}
    pred = np.array([mp.get(v, -1) for v in lab])
    f1 = f1_score(y, pred, average="micro")
    tbidx = np.where(np.diff(y) != 0)[0] + 1
    bm = boundary_metrics(boundaries(lab), tbidx, tt, tol)
    return dict(rec=r, dataset=ds[r], split=splits[r], env=envs[r], K=K, K_true=len(np.unique(y)),
                n=int(good.sum()), ari=float(ari), f1=float(f1), **bm)


recs_eval = [r for r in recs[recs.split == "test"].rec
             if len(segs[segs.rec == r]) >= 2]
rows = []
for r in recs_eval:
    for method, oracle, feat, tag in [
            ("ward", False, None, "ward"), ("raw", False, None, "raw"),
            ("ward", True, None, "ward_oracleK"),
            ("ward", False, "raw", "ward_rawfeat"), ("raw", False, "head", "kmeans_headfeat")]:
        e = eval_record(r, method, oracle, feature=feat)
        if e:
            e["method"] = tag
            rows.append(e)
segdf = pd.DataFrame(rows)
segdf.to_csv(os.path.join(DATA, "p1_segmentation_records.csv"), index=False, encoding="utf-8")
agg = segdf.groupby("method")[["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err"]].agg(["mean", "std", "count"])
seg_json = dict(_meta=dict(records=int(segdf.rec.nunique()), split="test",
                           feature_main="head-normalised low-dim state (19 dims/hand, dominant hand)",
                           feature_baseline="raw world 21x3 keypoints, both hands (126 dims)",
                           K_selection="BIC of diagonal GMM on 1/3 subsample", tol_s=5.0),
                by_method={m: {c: dict(mean=float(agg.loc[m, (c, "mean")]), std=float(agg.loc[m, (c, "std")]))
                               for c in ["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err"]}
                           for m in agg.index})
for m in ["ward", "raw"]:
    a, b = seg_json["by_method"][m], seg_json["by_method"]["raw"]
seg_json["improvement"] = {m: {c: float(seg_json["by_method"]["ward"][c]["mean"] -
                                         seg_json["by_method"]["raw"][c]["mean"])
                               for c in ["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err"]}
                           for m in ["ward"]}
# by dataset
seg_json["by_dataset"] = {d: {m: float(segdf[(segdf.dataset == d) & (segdf.method == m)].f1.mean())
                              for m in ["ward", "raw"]} for d in segdf.dataset.unique()}
seg_json["ablation"] = {m: {c: float(segdf[segdf.method == m][c].mean())
                            for c in ["ari", "f1"]}
                        for m in ["ward", "raw", "ward_rawfeat", "kmeans_headfeat"]}
write_json("p1_reliability.json", rel)
write_json("p1_segmentation.json", seg_json)

# ---------------- stage / dataset differences ----------------
st_rows = []
for _, s in segs.iterrows():
    r = int(s.rec); ii = np.where((rec == r) & (T >= s.start) & (T < s.end))[0]
    if len(ii) < 3:
        continue
    k = int(dom[r]); F = fl[ii] if k == 0 else fr[ii]
    G = gl[ii] if k == 0 else gr[ii]
    st_rows.append(dict(rec=r, dataset=ds[r], split=splits[r], env=envs[r], seg=int(s.seg),
                        dur=float(s.dur), label=s.label[:80],
                        speed=float(np.nanmean(F[:, -2])), acc=float(np.nanmean(F[:, -1])),
                        aperture=float(np.nanmean(F[:, 15])), palm=float(np.nanmean(G[:, 5])),
                        coll=float(np.nanmean(G[:, 0]))))
st = pd.DataFrame(st_rows)
st.to_csv(os.path.join(DATA, "p1_stage_table.csv"), index=False, encoding="utf-8")
write_json("p1_stage_stats.json", dict(
    _meta=dict(source="data/segments.csv + data/state.npz", n_segments=int(len(st)), units="m/s, m/s^2, dimensionless aperture, s", aggregation="per annotated subtask segment, then mean by dataset/position"),
    by_dataset=st.groupby("dataset")[["speed", "acc", "aperture", "dur"]].mean().round(5).to_dict(),
    by_position=st.assign(pos=np.where(st.groupby("rec").cumcount() == 0, "first",
                              np.where(st.groupby("rec").cumcount() == st.groupby("rec").seg.transform("max"), "last", "middle")))
      .groupby("pos")[["speed", "aperture", "dur"]].mean().round(5).to_dict()))

# ---------------- figures ----------------
# fig1 head-normalised keypoint families for one demo record with bad frames
cand = recs[(recs.dataset == "EgoDemo") & (recs.badL > 0.02)]
r = int(cand.rec.iloc[0]) if len(cand) else int(recs[recs.dataset == "EgoDemo"].rec.iloc[0])
ii = frames_of(r); k = int(dom[r]); P = PANEL["L"][ii] if k == 0 else PANEL["R"][ii]
Rh = np.transpose(__import__("common").quat_to_R(PANEL["Q"][ii]), (0, 2, 1))
Ph = np.einsum("nij,nkj->nki", Rh, P - PANEL["H"][ii][:, None, :])
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for j, c, lab in [(0, "#111", "wrist"), (4, "#c0392b", "thumb tip"), (8, "#2471a3", "index tip")]:
    ax[0].plot(T[ii], Ph[:, j, 0], color=c, lw=1.1, label=lab)
    ax[1].plot(Ph[:, j, 0], Ph[:, j, 2], color=c, lw=0.9, label=lab)
b = (badL if k == 0 else badR)[ii]
ax[0].fill_between(T[ii], *ax[0].get_ylim(), where=b, color="orange", alpha=.25, label="annotated bad")
ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("head-frame x (m)"); ax[0].legend(fontsize=7)
ax[1].set_xlabel("head-frame x (m)"); ax[1].set_ylabel("head-frame z (m)")
ax[0].set_title(f"head-normalised fingertip tracks, {recs.iloc[r]['sample']}")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_keypoint_tracks.png"), dpi=180); plt.close(fig)

# fig2 bad ratio distribution
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
for d, c in zip(["EgoDemo", "EgoPro", "EgoStandard"], ["#2c7fb8", "#e08214", "#31a354"]):
    v = 100 * recs[recs.dataset == d].badL.values
    ax[0].hist(v, bins=np.linspace(0, max(5, v.max()), 25), alpha=.6, label=d, color=c)
ax[0].set_xlabel("bad-frame share per record (%)"); ax[0].set_ylabel("records"); ax[0].legend(fontsize=8)
m = recs.groupby("dataset")[["badL", "badR"]].mean().loc[["EgoDemo", "EgoPro", "EgoStandard"]] * 100
ax[1].bar(np.arange(3) - .18, m.badL, .36, label="left", color="#4c72b0")
ax[1].bar(np.arange(3) + .18, m.badR, .36, label="right", color="#dd8452")
ax[1].set_xticks(range(3)); ax[1].set_xticklabels(m.index, fontsize=8)
ax[1].set_ylabel("mean bad-frame share (%)"); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig2_bad_ratio.png"), dpi=180); plt.close(fig)

# fig3 segmentation timeline (best median record)
rr = segdf[(segdf.method == "ward")].sort_values("f1").iloc[len(segdf[segdf.method == "ward"]) // 2].rec
ii, X = state_matrix(int(rr)); y = true_labels(int(rr), ii)
good = y >= 0; X = np.nan_to_num(smooth(X[good], 5)); y = y[good]; tt = T[ii][good]
X = (X - X.mean(0)) / (X.std(0) + 1e-6)
K = choose_k(X); lw = ward_segments(X, K); lr = kmeans_segments(raw_matrix(int(rr))[1][good], K)
fig, ax = plt.subplots(figsize=(10, 2.6))
ax.imshow(np.vstack([y, lw, lr]), aspect="auto", cmap="tab20", interpolation="nearest",
          extent=[tt[0], tt[-1], 0, 3])
ax.set_yticks([.5, 1.5, 2.5]); ax.set_yticklabels(["annotated", "head-norm Ward", "raw KMeans"], fontsize=8)
ax.set_xlabel("time (s)"); ax.set_title(f"segmentation alignment, {recs.iloc[int(rr)]['sample']} (K={K})")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_segmentation.png"), dpi=180); plt.close(fig)

# fig7 ROC / PR reliability
from sklearn.metrics import roc_curve, precision_recall_curve
fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
for name, sc_ in [("geometry only", d2_te), ("calibrated fusion", 1 - r_fus_te)]:
    fpr, tpr, _ = roc_curve(yte, sc_); ax[0].plot(fpr, tpr, lw=1.4, label=f"{name} AUC={roc_auc_score(yte,sc_):.3f}")
    pr, rc, _ = precision_recall_curve(yte, sc_); ax[1].plot(rc, pr, lw=1.4, label=name)
ax[0].plot([0, 1], [0, 1], "k--", lw=.8); ax[0].set_xlabel("FPR"); ax[0].set_ylabel("TPR"); ax[0].legend(fontsize=8)
ax[1].axhline(yte.mean(), color="k", ls="--", lw=.8); ax[1].set_xlabel("recall"); ax[1].set_ylabel("precision"); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig7_reliability_roc.png"), dpi=180); plt.close(fig)

print(json.dumps({k: v for k, v in rel.items() if k != "threshold_sensitivity"}, indent=1)[:900])
print(segdf.groupby("method")[["ari", "f1", "b_mae", "b_recall"]].mean().round(3))
print("figs written")