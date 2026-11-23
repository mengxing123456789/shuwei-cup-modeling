
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1 step 1: head-frame normalisation, low-dimensional operational state,
geometric observability features, and executable-prefix features for P3.

Outputs data/state.npz, data/feature_names.json, data/prefix_features.csv,
data/p1_state_summary.json
"""
import os, json
import numpy as np
import pandas as pd
from common import DATA, ensure_dirs, quat_to_R, write_json, load_index

ensure_dirs()
Z = np.load(os.path.join(DATA, "panel.npz"))
L, R, H, Q, T, REC = Z["L"], Z["R"], Z["H"], Z["Q"], Z["t"], Z["rec"]
badL, badR = Z["badL"], Z["badR"]
recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
N = len(T)
Rh = quat_to_R(Q)                      # (N,3,3) world->head? R maps head->world
Rht = np.transpose(Rh, (0, 2, 1))      # world->head
meta = recs.set_index("rec")


def to_head(P):
    return np.einsum("nij,nkj->nki", Rht, P - H[:, None, :])


def hand_feats(P, side):
    """P: (N,21,3) already in head frame. Returns (N,D) and names."""
    wrist, thumb_tip, index_tip = P[:, 0], P[:, 4], P[:, 8]
    index_mcp, little_mcp = P[:, 5], P[:, 17]
    mid_mcp = P[:, 9]
    palm_w = np.linalg.norm(index_mcp - little_mcp, axis=1) + 1e-6
    aperture = np.linalg.norm(thumb_tip - index_tip, axis=1) / palm_w
    reach = np.linalg.norm(index_tip - wrist, axis=1) / palm_w
    n = np.cross(index_mcp - wrist, little_mcp - wrist)
    n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    fwd = mid_mcp - wrist
    fwd = fwd / (np.linalg.norm(fwd, axis=1, keepdims=True) + 1e-9)
    v = np.zeros_like(wrist); a = np.zeros_like(wrist)
    for r, g in pd.DataFrame({"rec": REC}).groupby("rec").groups.items():
        ii = np.asarray(g)
        tt = T[ii]
        if len(ii) < 4:
            continue
        for k in range(3):
            v[ii, k] = np.gradient(wrist[ii, k], tt)
            a[ii, k] = np.gradient(v[ii, k], tt)
    feats = np.concatenate([
        wrist, thumb_tip, index_tip, index_mcp, little_mcp,
        aperture[:, None], reach[:, None], palm_w[:, None],
        n, fwd, v, a,
        np.linalg.norm(v, axis=1)[:, None], np.linalg.norm(a, axis=1)[:, None],
    ], axis=1)
    names = ([f"{side}_wrist_{ax}" for ax in "xyz"] +
             [f"{side}_thumbTip_{ax}" for ax in "xyz"] +
             [f"{side}_indexTip_{ax}" for ax in "xyz"] +
             [f"{side}_indexMCP_{ax}" for ax in "xyz"] +
             [f"{side}_littleMCP_{ax}" for ax in "xyz"] +
             [f"{side}_aperture_norm", f"{side}_reach_norm", f"{side}_palm_width",
              f"{side}_normal_x", f"{side}_normal_y", f"{side}_normal_z",
              f"{side}_fwd_x", f"{side}_fwd_y", f"{side}_fwd_z",
              f"{side}_vel_x", f"{side}_vel_y", f"{side}_vel_z",
              f"{side}_acc_x", f"{side}_acc_y", f"{side}_acc_z",
              f"{side}_speed", f"{side}_accnorm"])
    return feats.astype(np.float32), names


def geom_feats(P, side):
    """Observability proxies from geometry only (no labels)."""
    n = len(P)
    d = np.linalg.norm(np.diff(P, axis=1), axis=2)  # (N,20) bones
    med = np.median(d, axis=1)[:, None]
    bone_cv = np.std(d / (med + 1e-6), axis=1)
    # finger collinearity: SVD on each finger's 4 points
    fingers = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]
    coll = np.zeros(n)
    for fi in fingers:
        Qf = P[:, fi, :] - P[:, fi, :].mean(axis=1, keepdims=True)
        s = np.linalg.svd(Qf, compute_uv=False)  # (N,4)
        coll += (np.sqrt(s[:, 1] ** 2 + s[:, 2] ** 2) / (s[:, 0] + 1e-9))
    coll /= 5
    # minimum pairwise distance among 21 points
    pair = np.linalg.norm(P[:, :, None, :] - P[:, None, :, :], axis=-1)
    pair[:, np.arange(21), np.arange(21)] = np.inf
    min_gap = pair.reshape(n, -1).min(axis=1) / (med[:, 0] + 1e-6)
    bbox = P.max(axis=1) - P.min(axis=1)
    vol = bbox[:, 0] * bbox[:, 1] * bbox[:, 2]
    z_std = P[:, :, 2].std(axis=1)
    palm_w = np.linalg.norm(P[:, 5] - P[:, 17], axis=1)
    step = np.linalg.norm(np.diff(P, axis=0), axis=2)  # (N-1,21)
    jump = np.concatenate([[0.0], np.median(step, axis=1)]) / (med[:, 0] + 1e-6)
    jmax = np.concatenate([[0.0], step.max(axis=1)]) / (med[:, 0] + 1e-6)
    feats = np.stack([coll, bone_cv, min_gap, vol, z_std, palm_w, jump, jmax], axis=1)
    return feats.astype(np.float32), [f"{side}_{x}" for x in
                                      ["collinearity", "bone_cv", "min_gap", "bbox_vol", "z_std", "palm_width", "jump", "jump_max"]]


Pl, Pr = to_head(L), to_head(R)
fl, names_l = hand_feats(Pl, "L")
fr, names_r = hand_feats(Pr, "R")
gl, gn_l = geom_feats(Pl, "L")
gr, gn_r = geom_feats(Pr, "R")

# dominant hand per record = larger wrist path length
dom = np.zeros(len(recs), np.int8)
for r in range(len(recs)):
    ii = np.where(REC == r)[0]
    dl = np.linalg.norm(np.diff(Pl[ii, 0], axis=0), axis=1).sum()
    dr = np.linalg.norm(np.diff(Pr[ii, 0], axis=0), axis=1).sum()
    dom[r] = 0 if dl >= dr else 1

np.savez_compressed(os.path.join(DATA, "state.npz"),
                    fl=fl, fr=fr, gl=gl, gr=gr, dom=dom,
                    badL=badL, badR=badR, rec=REC, t=T,
                    validL=np.isfinite(fl).all(1), validR=np.isfinite(fr).all(1))
write_json("feature_names.json", dict(_meta=dict(note="column names for the 32-dim per-hand state and 8-dim geometry features; dominant maps record index to dominant hand"), state_l=names_l, state_r=names_r,
                                      geom_l=gn_l, geom_r=gn_r,
                                      dominant={str(i): ("L" if d == 0 else "R") for i, d in enumerate(dom)}))

# ---- summary of head-normalised state by dataset ----
rows = []
for r in range(len(recs)):
    ii = np.where(REC == r)[0]
    s = recs.iloc[r]
    k = 0 if dom[r] == 0 else 1
    F = fl[ii] if k == 0 else fr[ii]
    G = gl[ii] if k == 0 else gr[ii]
    rows.append(dict(rec=r, dataset=s.dataset, split=s.split, env=s.env,
                     n=len(ii), speed_mean=float(np.nanmean(F[:, -2])),
                     speed_p95=float(np.nanpercentile(F[:, -2], 95)),
                     acc_mean=float(np.nanmean(F[:, -1])),
                     aperture_mean=float(np.nanmean(F[:, (names_l if k==0 else names_r).index(('L' if k==0 else 'R')+'_aperture_norm')])),
                     palm_width=float(np.nanmean(G[:, 5])),
                     collinearity=float(np.nanmean(G[:, 0])),
                     min_gap=float(np.nanmean(G[:, 2])),
                     bad=float(np.mean((badL if k == 0 else badR)[ii]))))
summ = pd.DataFrame(rows)
summ.to_csv(os.path.join(DATA, "p1_state_by_record.csv"), index=False, encoding="utf-8")
print(summ.groupby("dataset")[["speed_mean", "aperture_mean", "palm_width", "bad"]].mean().round(4))
print("dominant L/R", int((dom == 0).sum()), int((dom == 1).sum()))
print("finite", float(np.isfinite(fl).all(1).mean()), float(np.isfinite(fr).all(1).mean()))
write_json("p1_state_summary.json", dict(
    _meta=dict(source="data/panel.npz", fps=30, split="record_split.csv 16/4/4 environments", units="m; normalised ratios dimensionless", method="head-frame rotation, finite-difference velocity/acceleration"),
    n_records=int(len(recs)), n_frames=int(N),
    dominant_left=int((dom == 0).sum()), dominant_right=int((dom == 1).sum()),
    state_dim_per_hand=int(fl.shape[1]), geom_dim_per_hand=int(gl.shape[1]),
    dataset_means=summ.groupby("dataset")[["speed_mean", "aperture_mean", "palm_width", "bad"]].mean().round(5).to_dict(),
    note="coordinates are head-frame; aperture/reach normalised by palm width"))

# ---- executable prefix features for every indexed unit ----
idx = load_index()
pf_rows = []
for _, u in idx.iterrows():
    rr = recs[(recs.dataset == u.dataset) & (recs["sample"].astype(str) == str(u["sample"]))]
    if len(rr) == 0:
        continue
    r = int(rr.rec.iloc[0]); ii = np.where(REC == r)[0]
    t0 = float(u.start_s); dur = float(u.duration_s)
    k = 0 if dom[r] == 0 else 1
    F = fl[ii] if k == 0 else fr[ii]
    for pre in (0.2, 0.6, 1.0):
        m = (T[ii] >= t0) & (T[ii] < t0 + pre)
        if m.sum() < 2:
            m = (T[ii] >= t0) & (T[ii] <= t0 + pre + 0.05)
        f = F[m]
        speed = f[:, -2] if len(f) else np.array([np.nan])
        acc = f[:, -1] if len(f) else np.array([np.nan])
        aperture = f[:, (names_l if k==0 else names_r).index(("L" if k == 0 else "R") + "_aperture_norm")] if len(f) else np.array([np.nan])
        wz = f[:, 2] if len(f) else np.array([np.nan])
        pf_rows.append(dict(unit_id=u.unit_id, dataset=u.dataset, sample=u["sample"], split=u.split,
                            family=u.family_id, env=u.environment_id, duration=dur, prefix=pre,
                            n=len(f), speed_mean=float(np.nanmean(speed)),
                            speed_std=float(np.nanstd(speed)), speed_max=float(np.nanmax(speed)),
                            acc_mean=float(np.nanmean(acc)), aperture_mean=float(np.nanmean(aperture)),
                            aperture_std=float(np.nanstd(aperture)), depth_mean=float(np.nanmean(wz)),
                            depth_std=float(np.nanstd(wz))))
pf = pd.DataFrame(pf_rows)
pf.to_csv(os.path.join(DATA, "prefix_features.csv"), index=False, encoding="utf-8")
print("prefix rows", len(pf), "units", pf.unit_id.nunique())
print(pf.groupby(["split", "prefix"]).size().unstack().to_string())