
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P3 v2: progress-aware, structure-preserving prefix representation.

Replaces the old 8 aggregate statistics with features that can represent progress:
  - prefix duration / frame count (mandatory; old model accidentally made longer
    prefixes look worse partly because prefix duration was not identified well)
  - current pose relative to first/last observed pose, path length, displacement
  - endpoint velocity and acceleration, robust linear trends, curvature
  - aperture/open-close phase, contact likelihood, hand-head configuration
  - motion-energy distribution over the released prefix
  - task family and task type (from official source_segment_index, no UUID leakage)

No future frame, true duration, source UUID, sample ID or validation label is used
as an input. Duration is used only as the supervised target in the training split.
"""
import os
import numpy as np
import pandas as pd
from common import DATA, load_index, write_json

Z = np.load(os.path.join(DATA, "panel.npz"))
ST = np.load(os.path.join(DATA, "state.npz"))
REC = Z["rec"].astype(int)
T = Z["t"]
L, R, H, Q = Z["L"], Z["R"], Z["H"], Z["Q"]
DOM = ST["dom"].astype(int)
badL, badR = Z["badL"], Z["badR"]
recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
idx = load_index()


def safe(v):
    a = np.asarray(v, dtype=float)
    return np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)


def stats(a):
    a = safe(a)
    if len(a) == 0:
        return [0.0] * 7
    return [float(a[-1]), float(a.mean()), float(a.std()), float(a.min()),
            float(a.max()), float(np.median(a)),
            float(np.polyfit(np.arange(len(a)), a, 1)[0]) if len(a) >= 3 else 0.0]


def make_features(P, O, times, family):
    """P: dominant-hand (n,21,3); O: other hand; times: seconds."""
    n = len(P)
    if n < 2:
        return None
    tt = times - times[0]
    w = safe(P[:, 0, :])
    wo = safe(O[:, 0, :])
    palm = np.linalg.norm(P[:, 5] - P[:, 17], axis=1) + 1e-5
    ap = np.linalg.norm(P[:, 4] - P[:, 8], axis=1) / palm
    reach = np.linalg.norm(P[:, 8] - w, axis=1) / palm
    palm = safe(palm)
    ap, reach = safe(ap), safe(reach)
    # Causal finite differences within the released prefix only.
    vel = np.gradient(w, tt, axis=0) if n >= 3 else np.diff(w, axis=0, prepend=w[:1]) / np.maximum(np.diff(tt, prepend=tt[0])[:, None], 1 / 30)
    acc = np.gradient(vel, tt, axis=0) if n >= 3 else np.zeros_like(vel)
    speed = safe(np.linalg.norm(vel, axis=1))
    accn = safe(np.linalg.norm(acc, axis=1))
    step = np.linalg.norm(np.diff(w, axis=0), axis=1)
    path = float(step.sum())
    disp = w - w[0]
    net = float(np.linalg.norm(w[-1] - w[0]))
    # Endpoint direction and curvature, robust to one-frame spikes.
    tail = max(2, min(8, n // 2))
    trend = np.polyfit(tt[-tail:], w[-tail:], 1)[0] if n >= 4 else vel[-1]
    curv = float(np.linalg.norm(vel[-1] - vel[max(0, n - 4)])) if n >= 4 else 0.0
    # Contact proxy: fingertips close and hand nearly stationary.
    contact = (ap < np.median(ap)) & (speed < np.median(speed) + 1e-6)
    # Energy distribution: early vs late motion tells whether task is still starting.
    thirds = np.array_split(speed, 3)
    energy = [float(np.mean(x)) if len(x) else 0.0 for x in thirds]
    energy_ratio = energy[-1] / (energy[0] + 1e-5)
    # Head-relative bilateral configuration and independent-hand motion.
    hand_gap = float(np.linalg.norm(w[-1] - wo[-1]) / (palm[-1] + 1e-5))
    both_speed = safe(np.linalg.norm(np.gradient(wo, tt, axis=0), axis=1)) if n >= 3 else np.zeros(n)
    synergy = float(np.corrcoef(speed, both_speed)[0, 1]) if n >= 4 and speed.std() > 1e-8 and both_speed.std() > 1e-8 else 0.0

    x = [tt[-1], n, path, net, path / (net + 1e-4),
         *list(disp[-1]), *list(w[-1]), *list(w[-1] - w[0]),
         *list(vel[-1]), *list(acc[-1]), *list(trend), curv,
         hand_gap, synergy, float(contact.mean()), energy_ratio,
         float(ap[-1] - ap[0]), float(reach[-1] - reach[0])]
    for a in (speed, accn, ap, reach, palm, w[:, 0], w[:, 1], w[:, 2]):
        x.extend(stats(a))
    x.extend(energy)
    # Signed aperture trend is useful for grasp/release; curvature for rearrangement.
    if n >= 3:
        x.append(float(np.polyfit(tt, ap, 1)[0]))
        x.append(float(np.polyfit(tt, speed, 1)[0]))
    else:
        x.extend([0.0, 0.0])
    # Official family is metadata, not source identity.
    x.extend([float(family == "A"), float(family == "L"), float(family == "P")])
    return np.asarray(x, dtype=np.float32)


rows = []
missing = 0
for _, u in idx.iterrows():
    rr = recs[(recs.dataset == u.dataset) & (recs["sample"].astype(str) == str(u["sample"]))]
    if not len(rr):
        missing += 1
        continue
    rid = int(rr.rec.iloc[0])
    ii = np.flatnonzero(REC == rid)
    k = DOM[rid]
    P0, O0 = (L[ii], R[ii]) if k == 0 else (R[ii], L[ii])
    times = T[ii]
    t0 = float(u.start_s)
    for pre in (0.2, 0.6, 1.0):
        m = (times >= t0) & (times < t0 + pre)
        if m.sum() < 2:
            m = (times >= t0) & (times <= t0 + pre + 0.05)
        if m.sum() < 2:
            continue
        feat = make_features(P0[m], O0[m], times[m], u.family_id)
        if feat is None:
            continue
        rows.append(dict(unit_id=u.unit_id, split=u.split, family=u.family_id,
                         task=u.task, source_segment_index=int(u.source_segment_index),
                         env=u.environment_id, duration=float(u.duration_s),
                         prefix=float(pre), **{f"x{i}": float(v) for i, v in enumerate(feat)}))

out = pd.DataFrame(rows)
fp = os.path.join(DATA, "prefix_progress_features.csv")
out.to_csv(fp, index=False, encoding="utf-8")
write_json("prefix_progress_meta.json", {
    "n_rows": len(out), "n_units": int(out.unit_id.nunique()),
    "n_features": len([c for c in out.columns if c.startswith("x")]),
    "feature_file": "data/prefix_progress_features.csv",
    "prefix_seconds": [0.2, 0.6, 1.0],
    "allowed_inputs": ["released prefix only", "official family/task metadata"],
    "forbidden_inputs": ["future frames", "true duration", "source UUID", "sample ID", "segment index as feature"],
    "target": "duration only in train split",
    "missing_record_links": missing,
})
print("saved", fp, out.shape)
print(out.groupby("prefix").size())
print("features", len([c for c in out.columns if c.startswith("x")]))