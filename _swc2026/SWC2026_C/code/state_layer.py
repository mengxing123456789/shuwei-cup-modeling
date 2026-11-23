
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1 foundation: a two-layer hand-state definition.

Continuous layer (feeds P2)
    per hand, per frame, in the head frame:
      pos(3)  representative-point position
      quat(4) hand orientation (wxyz, sign-continuous)
      dir(3)  main direction (wrist -> middle MCP)
      vel(3)  d/dt of the head-frame position
      speed   world-frame speed |d p_world / dt|
      omega   angular speed of the orientation (rad/s)
      aperture  thumb-tip to index-tip distance / palm width
      spread    mean fingertip-to-palm-centre distance / palm width
      static    1 if world speed stayed below the stillness threshold >= 5 frames
    plus conf (0..1) observation/geometry confidence.

Discrete layer (feeds P3)
    stage in {reach, pick, place, transport, arrange}, derived by deterministic
    threshold rules from the continuous layer (hysteresis segmentation on speed,
    aperture trend inside still segments, aperture level inside moving segments).
    No manual labels are used anywhere.

Public API
    build_state(rec) -> dict          (numPy only, no training)
    build_all()      -> dict rec->state
    main()           -> writes data/state_layer.json and data/state_layer.npz

Everything the report quotes is computed here; the JSON is the single source.
"""
import os
import json
import argparse
import numpy as np
import pandas as pd

from common import DATA, ensure_dirs, quat_to_R, load_split

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------
# MediaPipe-style 21-keypoint topology, verified on the records (see report):
#   0 wrist; thumb 1-4; index 5-8; middle 9-12; ring 13-16; pinky 17-20
WRIST = 0
THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP = 4, 8, 12, 16, 20
PALM = (0, 5, 9, 13, 17)            # wrist + five metacarpophalangeal joints
TIPS = (4, 8, 12, 16, 20)
FINGERS = ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
BONES = [(0, 1), (0, 5), (0, 9), (0, 13), (0, 17)] + \
        [(i, i + 1) for base in (1, 5, 9, 13, 17) for i in (base, base + 1, base + 2)]

STAGES = ("reach", "pick", "place", "transport", "arrange")
STAGE_ID = {s: i for i, s in enumerate(STAGES)}

VEC_NAMES = ["px", "py", "pz", "qw", "qx", "qy", "qz", "dx", "dy", "dz",
             "vx", "vy", "vz", "speed_world", "omega", "aperture", "spread", "static"]

# default thresholds (chosen from pooled feature quantiles, then sensitivity-tested)
THR = dict(
    v_hi=0.10,        # enter motion (m/s) on 5-frame smoothed speed ~ p30
    v_lo=0.05,        # leave motion  (m/s) on 5-frame smoothed speed ~ p12
    a_grasp=0.15,     # aperture change inside a still segment that counts as grasp/release
    t_arrange=0.8,    # still-segment duration (s) that counts as arranging
    a_closed=0.55,    # mean aperture below which a moving hand is carrying
    min_seg=3,        # frames, shortest admissible segment
    static_run=5,     # frames, stillness run for the static flag
)
THR_LABEL = dict(v_hi="v_hi (enter motion, m/s)", v_lo="v_lo (leave motion, m/s)",
                 a_grasp="a_grasp (aperture change for grasp/release)",
                 t_arrange="t_arrange (arrange dwell, s)",
                 a_closed="a_closed (closed-hand aperture level)")

_PANEL = None
_RECS = None


def panel():
    global _PANEL, _RECS
    if _PANEL is None:
        z = np.load(os.path.join(DATA, "panel.npz"))
        _PANEL = {k: z[k] for k in ("L", "R", "H", "Q", "t", "badL", "badR", "rec")}
        _RECS = pd.read_csv(os.path.join(DATA, "panel_records.csv"), encoding="utf-8-sig")
    return _PANEL, _RECS


# ----------------------------------------------------------------------------
# geometry helpers
# ----------------------------------------------------------------------------
def head_frame(P, H, Q):
    """World point(s) -> head frame:  p_h = R(q)^T (p_w - H).

    P (N,K,3) or (N,3); H (N,3); Q (N,4) wxyz. Returns same shape as P.
    Verified convention: wxyz (source columns quat.w,x,y,z); applying wxyz gives
    a median within-record std of 3.91 cm against 7.98 cm for xyzw.
    """
    R = quat_to_R(Q)                              # head -> world
    Rt = np.transpose(R, (0, 2, 1))               # world -> head
    d = P - H.reshape((-1,) + (1,) * (P.ndim - 2) + (3,))
    return np.einsum("nij,nkj->nki", Rt, d) if P.ndim == 3 else np.einsum("nij,nj->ni", Rt, d)


def palm_width(P):
    return np.linalg.norm(P[:, 5] - P[:, 17], axis=1)


def hand_axes(P):
    """Palm frame from wrist(0), index MCP(5), middle MCP(9), ring MCP(13), pinky MCP(17).

    x = wrist -> middle MCP (main direction), z = palm normal, y = z x x.
    Returns x (N,3), n (N,3), R (N,3,3) with columns [x, y, z].
    """
    x = P[:, 9] - P[:, WRIST]
    x = x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-12)
    n = np.cross(P[:, 5] - P[:, WRIST], P[:, 17] - P[:, WRIST])
    n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    z = n - np.sum(n * x, axis=1, keepdims=True) * x
    z = z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-12)
    y = np.cross(z, x)
    R = np.stack([x, y, z], axis=2)
    return x, z, R


def quat_from_R(R):
    """Rotation matrix (N,3,3) -> quaternion (N,4) wxyz, w >= 0."""
    n = len(R)
    q = np.empty((n, 4))
    tr = R[:, 0, 0] + R[:, 1, 1] + R[:, 2, 2]
    for i in range(n):
        m = R[i]
        t = tr[i]
        if t > 0:
            s = np.sqrt(t + 1.0) * 2
            w = 0.25 * s
            x = (m[2, 1] - m[1, 2]) / s
            y = (m[0, 2] - m[2, 0]) / s
            z = (m[1, 0] - m[0, 1]) / s
        elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
            s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
            w = (m[2, 1] - m[1, 2]) / s
            x = 0.25 * s
            y = (m[0, 1] + m[1, 0]) / s
            z = (m[0, 2] + m[2, 0]) / s
        elif m[1, 1] > m[2, 2]:
            s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
            w = (m[0, 2] - m[2, 0]) / s
            x = (m[0, 1] + m[1, 0]) / s
            y = 0.25 * s
            z = (m[1, 2] + m[2, 1]) / s
        else:
            s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
            w = (m[1, 0] - m[0, 1]) / s
            x = (m[0, 2] + m[2, 0]) / s
            y = (m[1, 2] + m[2, 1]) / s
            z = 0.25 * s
        q[i] = (w, x, y, z)
    q *= np.where(q[:, :1] < 0, -1.0, 1.0)
    return q


def quat_angle(q1, q2):
    """geodesic angle between unit quaternions, rad."""
    d = np.abs(np.sum(q1 * q2, axis=1))
    return 2.0 * np.arccos(np.clip(d, -1.0, 1.0))


def bone_deviation(P):
    """max over bones of |L_bone(t) / median_t L_bone - 1|, computed per record.

    Called with the frames of a single record.
    """
    dd = np.stack([np.linalg.norm(P[:, i] - P[:, j], axis=1) for i, j in BONES], axis=1)
    med = np.median(dd, axis=0)
    return np.max(np.abs(dd / (med[None, :] + 1e-9) - 1.0), axis=1)


def min_gap(P):
    pair = np.linalg.norm(P[:, :, None, :] - P[:, None, :, :], axis=-1)
    pair[:, np.arange(21), np.arange(21)] = np.inf
    med = np.median(np.stack([np.linalg.norm(P[:, i] - P[:, j], axis=1)
                              for i, j in BONES], axis=1), axis=1)
    return pair.reshape(len(P), -1).min(axis=1) / (med + 1e-9)


# ----------------------------------------------------------------------------
# discrete layer
# ----------------------------------------------------------------------------
def _runs(mask):
    """[(start, stop_exclusive), ...] for runs of True."""
    if len(mask) == 0:
        return []
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    starts = np.where(d == 1)[0]
    stops = np.where(d == -1)[0]
    return list(zip(starts.tolist(), stops.tolist()))


def _hysteresis(speed, v_hi, v_lo):
    state = np.empty(len(speed), bool)
    cur = bool(speed[0] > v_hi)
    for i in range(len(speed)):
        if speed[i] > v_hi:
            cur = True
        elif speed[i] < v_lo:
            cur = False
        state[i] = cur
    return state


def _merge_short(state, min_seg):
    """Flip runs shorter than min_seg to the previous run's value."""
    for _ in range(3):
        changed = False
        for a, b in _runs(~state):        # still runs
            if b - a < min_seg and a > 0:
                state[a:b] = True
                changed = True
        for a, b in _runs(state):
            if b - a < min_seg and a > 0:
                state[a:b] = False
                changed = True
        if not changed:
            break
    return state


def _segments(state):
    """[(start, stop_exclusive), ...] for every run of a constant value in `state`."""
    s = np.asarray(state, np.int8)
    if len(s) == 0:
        return []
    cut = np.flatnonzero(np.diff(s) != 0) + 1
    edges = np.concatenate([[0], cut, [len(s)]])
    return [(int(edges[i]), int(edges[i + 1])) for i in range(len(edges) - 1)]


def _smooth(x, k=5):
    from scipy.ndimage import uniform_filter1d
    return uniform_filter1d(np.asarray(x, float), size=k, mode="nearest")


def derive_stages(speed, aperture, height, thr=None, fps=30.0):
    """Deterministic rules from the continuous layer.

    speed    (N,) world speed m/s
    aperture (N,) thumb-index span / palm width
    height   (N,) palm-centre world z minus head world z (m)

    1. hysteresis segmentation: moving = speed > v_hi, still = speed < v_lo
    2. still segment labels:
         aperture drop  >= a_grasp over the segment (+-3-frame margin) -> pick
         aperture rise  >= a_grasp                                    -> place
         |change| < a_grasp and duration >= t_arrange                  -> arrange
         otherwise                                                     -> pick if height < 0 else place
    3. moving segment labels (finite state on the neighbouring dwell labels):
         previous dwell = pick and next dwell in {place, arrange}  -> transport
         next dwell = pick                                          -> reach
         previous dwell in {place, arrange} and no next dwell        -> reach
         otherwise: mean aperture < a_closed -> transport, else reach
    """
    thr = dict(THR if thr is None else thr)
    n = len(speed)
    sm = _smooth(speed, 5)
    state = _merge_short(_hysteresis(sm, thr["v_hi"], thr["v_lo"]), thr["min_seg"])
    seg = _segments(state)
    stage = np.zeros(n, np.int8)
    conf = np.zeros(n, np.float32)
    seg_len = []
    lab_of = {}
    # ---- pass 1: dwell (still) segments -------------------------------------
    for a, b in seg:
        seg_len.append(b - a)
        if state[a] or b - a < 2:
            continue
        w0, w1 = max(0, a - 5), min(n, b + 5)
        af = float(np.median(aperture[w0:min(w0 + 3, n)]))
        al = float(np.median(aperture[max(w1 - 3, 0):w1]))
        da = al - af
        dur = (b - a) / fps
        if da <= -thr["a_grasp"]:
            lab, c = "pick", min(1.0, abs(da) / (2 * thr["a_grasp"]) + 0.35)
        elif da >= thr["a_grasp"]:
            lab, c = "place", min(1.0, abs(da) / (2 * thr["a_grasp"]) + 0.35)
        elif dur >= thr["t_arrange"]:
            lab, c = "arrange", min(1.0, dur / (2 * thr["t_arrange"]) + 0.35)
        else:
            lab = "pick" if float(np.median(height[a:b])) < 0 else "place"
            c = 0.4
        stage[a:b] = STAGE_ID[lab]
        conf[a:b] = c
        lab_of[a] = lab
    # ---- pass 2: moving segments, finite-state on the neighbouring dwells ---
    for k, (a, b) in enumerate(seg):
        if not state[a] or b - a < 2:
            continue
        prev_lab = lab_of.get(seg[k - 1][0]) if k > 0 and not state[seg[k - 1][0]] else None
        next_lab = lab_of.get(seg[k + 1][0]) if k + 1 < len(seg) and not state[seg[k + 1][0]] else None
        am = float(np.median(aperture[a:b]))
        if prev_lab == "pick" and next_lab in ("place", "arrange"):
            lab, c = "transport", 0.9
        elif next_lab == "pick":
            lab, c = "reach", 0.8
        elif prev_lab in ("place", "arrange") and next_lab is None:
            lab, c = "reach", 0.7
        else:
            lab = "transport" if am < thr["a_closed"] else "reach"
            c = float(np.clip(abs(am - thr["a_closed"]) / 0.25, 0.35, 1.0))
        stage[a:b] = STAGE_ID[lab]
        conf[a:b] = c
    seg_len = np.asarray(seg_len, float)
    return stage, conf, seg_len, state


# ----------------------------------------------------------------------------
# continuous layer
# ----------------------------------------------------------------------------
def _hand_state(P_world, H, Q, t, bad, thr):
    N = len(P_world)
    Ph = head_frame(P_world, H, Q)
    pos = Ph[:, list(PALM), :].mean(axis=1)
    pw = palm_width(P_world)
    x_dir, palm_n, Rhand = hand_axes(P_world)
    q = quat_from_R(Rhand)
    for i in range(1, N):                  # sign continuity within the record
        if np.dot(q[i], q[i - 1]) < 0:
            q[i] = -q[i]
            Rhand[i, :, :2] *= -1.0
    vel = np.gradient(pos, t, axis=0)
    speed = np.linalg.norm(np.gradient(_to_world(pos, H, Q), t, axis=0), axis=1)
    omega = np.concatenate([[0.0], quat_angle(q[1:], q[:-1]) / np.maximum(np.diff(t), 1e-6)])
    ap = np.linalg.norm(P_world[:, THUMB_TIP] - P_world[:, INDEX_TIP], axis=1) / (pw + 1e-9)
    spread = np.mean(np.linalg.norm(P_world[:, list(TIPS), :] - pos[:, None, :], axis=2), axis=1) / (pw + 1e-9)
    height = P_world[:, list(PALM), 2].mean(axis=1) - H[:, 2]
    static = np.zeros(N, np.float32)
    for a, b in _runs(speed < thr["v_lo"]):
        if b - a >= thr["static_run"]:
            static[a:b] = 1.0
    bdev = bone_deviation(P_world)
    gap = min_gap(P_world)
    q_geom = np.clip(1.0 - np.maximum(bdev / 0.35 - 1.0, 0.0) - np.maximum(0.15 / (gap + 1e-9) - 1.0, 0.0), 0.2, 1.0)
    conf = np.clip(q_geom * (1.0 - 0.5 * bad.astype(np.float32)), 0.0, 1.0)
    stage, stage_conf, seg_len, moving = derive_stages(
        speed, ap, height, thr, fps=float(1.0 / np.median(np.diff(t))))
    vec = np.stack([pos[:, 0], pos[:, 1], pos[:, 2], q[:, 0], q[:, 1], q[:, 2], q[:, 3],
                    x_dir[:, 0], x_dir[:, 1], x_dir[:, 2], vel[:, 0], vel[:, 1], vel[:, 2],
                    speed, omega, ap, spread, static], axis=1).astype(np.float32)
    return dict(pos=pos.astype(np.float32), quat=q.astype(np.float32), dir=x_dir.astype(np.float32),
                palm_normal=palm_n.astype(np.float32), vel=vel.astype(np.float32),
                speed=speed.astype(np.float32), omega=omega.astype(np.float32),
                aperture=ap.astype(np.float32), spread=spread.astype(np.float32),
                static=static, height=height.astype(np.float32),
                conf=conf.astype(np.float32), stage=stage, stage_conf=stage_conf.astype(np.float32),
                vector=vec, bone_dev=bdev.astype(np.float32), min_gap=gap.astype(np.float32),
                moving=moving, n_segments=int(len(seg_len)),
                mean_seg_len=float(seg_len.mean()) if len(seg_len) else 0.0)


def _to_world(pos_h, H, Q):
    R = quat_to_R(Q)
    return np.einsum("nij,nj->ni", R, pos_h) + H


def build_state(rec):
    """Return the two-layer state of one record. Pure numPy, no training."""
    P, recs = panel()
    row = recs[recs.rec == rec].iloc[0]
    m = P["rec"] == rec
    idx = np.where(m)[0]
    t = P["t"][idx].astype(np.float64)
    t = t - t[0]
    H = P["H"][idx].astype(np.float64)
    Q = P["Q"][idx].astype(np.float64)
    out = dict(rec=int(rec), dataset=str(row.dataset), sample=str(row["sample"]),
               env=str(row.env), split=str(row.split), n=int(m.sum()), t=t,
               frames=idx, thr=dict(THR), H=H.astype(np.float32), Q=Q.astype(np.float32))
    for side, key, badkey in (("L", "L", "badL"), ("R", "R", "badR")):
        X = P[key][idx].astype(np.float64)
        out[side] = _hand_state(X, H, Q, t, P[badkey][idx], THR)
        out[side]["pos_world"] = (np.einsum("nij,nj->ni", quat_to_R(Q),
                                            out[side]["pos"].astype(np.float64)) + H).astype(np.float32)
    out["vector_names"] = list(VEC_NAMES)
    return out


_ALL = None


def build_all():
    global _ALL
    if _ALL is None:
        P, recs = panel()
        _ALL = {int(r): build_state(int(r)) for r in recs.rec.values}
    return _ALL


# ----------------------------------------------------------------------------
# representative-point selection
# ----------------------------------------------------------------------------
def candidate_metrics():
    """Compare wrist / palm centre / fingertip centroid on the same 66,070 frames."""
    P, recs = panel()
    L, R, H, Q, t, rec = P["L"].astype(np.float64), P["R"].astype(np.float64), \
        P["H"].astype(np.float64), P["Q"].astype(np.float64), P["t"].astype(np.float64), P["rec"]
    cand = {"wrist_kp0": [0], "palm_centre_0_5_9_13_17": list(PALM),
            "fingertip_centroid_4_8_12_16_20": list(TIPS)}
    ds_of = recs.set_index("rec")["dataset"]
    acc = {k: dict(resid=[], jitter=[], finger_std=[], pinch=[], cent=[]) for k in cand}
    dist = {k: [] for k in cand}
    for side, X in (("L", L), ("R", R)):
        # palm frame anchored at 9, axes e1 = 5-9, e3 = normal, e2 = e3 x e1
        e1 = X[:, 5] - X[:, 9]
        e1 = e1 / (np.linalg.norm(e1, axis=1, keepdims=True) + 1e-12)
        e3 = np.cross(e1, X[:, 13] - X[:, 9])
        e3 = e3 / (np.linalg.norm(e3, axis=1, keepdims=True) + 1e-12)
        e2 = np.cross(e3, e1)
        pc = X[:, list(PALM), :].mean(axis=1)
        pinch = 0.5 * (X[:, 4] + X[:, 8])
        hand_c = X.mean(axis=1)
        for k, pts in cand.items():
            p = X[:, pts, :].mean(axis=1)
            rel = p - X[:, 9]
            loc = np.stack([np.sum(rel * e1, 1), np.sum(rel * e2, 1), np.sum(rel * e3, 1)], 1)
            dist[k].append(np.linalg.norm(head_frame(p, H, Q), axis=1))
            for r in np.unique(rec):
                mm = rec == r
                acc[k]["resid"].append(float(np.linalg.norm(loc[mm] - loc[mm].mean(0), axis=1).mean()))
                acc[k]["finger_std"].append(float(np.std(np.linalg.norm(p[mm] - pc[mm], axis=1))))
                acc[k]["pinch"].append(float(np.median(np.linalg.norm(p[mm] - pinch[mm], axis=1))))
                acc[k]["cent"].append(float(np.median(np.linalg.norm(p[mm] - hand_c[mm], axis=1))))
            step = np.linalg.norm(np.diff(p, axis=0), axis=1)
            jit = np.linalg.norm(p[1:-1] - 0.5 * (p[:-2] + p[2:]), axis=1)
            m0 = step[1:] > 1e-9
            acc[k]["jitter"].append(float(np.median(jit) / (np.median(step[step > 1e-9]) + 1e-12)))
    out = {}
    rec2 = np.concatenate([rec, rec])
    for k in cand:
        d = np.concatenate(dist[k])
        by_ds = {}
        for ds in ("EgoDemo", "EgoPro", "EgoStandard"):
            m = np.isin(rec2, ds_of[ds_of == ds].index.values)
            by_ds[ds] = float(d[m].mean())
        out[k] = dict(
            rigidity_cm=float(np.mean(acc[k]["resid"]) * 100),
            jitter_ratio=float(np.mean(acc[k]["jitter"])),
            finger_pose_sensitivity_cm=float(np.mean(acc[k]["finger_std"]) * 100),
            pinch_dist_cm=float(np.median(acc[k]["pinch"]) * 100),
            centroid_dist_cm=float(np.median(acc[k]["cent"]) * 100),
            dhead_by_dataset_m={dk: round(dv, 4) for dk, dv in by_ds.items()},
            cross_dataset_spread_m=float(max(by_ds.values()) - min(by_ds.values())),
        )
    out["_note"] = ("rigidity_cm: mean within-record std of the point in the palm frame "
                    "(lower = the point is rigidly attached to the hand); "
                    "jitter_ratio: median 2nd-difference / median 1st-difference (lower = less noise); "
                    "finger_pose_sensitivity_cm: within-record std of the distance to the palm "
                    "centre (higher = the point moves when fingers flex); "
                    "pinch_dist_cm: median distance to the thumb-tip/index-tip midpoint (grasp point); "
                    "centroid_dist_cm: median distance to the centroid of all 21 keypoints; "
                    "cross_dataset_spread_m: max-min of the dataset mean distance to head.")
    return out


# ----------------------------------------------------------------------------
# retention
# ----------------------------------------------------------------------------
RET = dict(max_bad=0.05, max_bone_dev_frac=0.02, bone_dev=0.35, min_gap=0.15,
           max_gap_s=0.1, fps_range=(24.0, 32.0))


def retention():
    P, recs = panel()
    L, R, H, Q, t, rec = P["L"], P["R"], P["H"], P["Q"], P["t"], P["rec"]
    badL, badR = P["badL"], P["badR"]
    rows = []
    frame_keep = np.zeros(len(t), bool)
    for _, s in recs.iterrows():
        r = int(s.rec)
        m = rec == r
        idx = np.where(m)[0]
        tt = t[idx]
        dt = np.diff(tt)
        reasons = []
        detail = {}
        # R1 completeness
        fin = float(np.mean(np.isfinite(L[idx]).all((1, 2)) & np.isfinite(R[idx]).all((1, 2))
                            & np.isfinite(H[idx]).all(1) & np.isfinite(Q[idx]).all(1)))
        detail["finite"] = fin
        if fin < 0.98:
            reasons.append("completeness")
        # R2 timing
        fps = float(1.0 / np.median(dt)) if len(dt) else float(s.fps)
        gap = float(dt.max()) if len(dt) else 0.0
        detail.update(fps=fps, max_gap=gap)
        if not (RET["fps_range"][0] <= fps <= RET["fps_range"][1]) or gap > RET["max_gap_s"]:
            reasons.append("timing")
        # R3 quality flags
        bl, br = float(badL[idx].mean()), float(badR[idx].mean())
        detail.update(badL=bl, badR=br)
        if max(bl, br) > RET["max_bad"]:
            reasons.append("quality_flag")
        # R4 geometry (per hand, record fails if either hand is bad)
        devL, devR = bone_deviation(L[idx].astype(np.float64)), bone_deviation(R[idx].astype(np.float64))
        gapL, gapR = min_gap(L[idx].astype(np.float64)), min_gap(R[idx].astype(np.float64))
        anL = float(np.mean((devL > RET["bone_dev"]) | (gapL < RET["min_gap"])))
        anR = float(np.mean((devR > RET["bone_dev"]) | (gapR < RET["min_gap"])))
        detail.update(geomL=anL, geomR=anR)
        if max(anL, anR) > RET["max_bone_dev_frac"]:
            reasons.append("geometry")
        ok = len(reasons) == 0
        goodL = (~badL[idx]) & (devL <= RET["bone_dev"]) & (gapL >= RET["min_gap"])
        goodR = (~badR[idx]) & (devR <= RET["bone_dev"]) & (gapR >= RET["min_gap"])
        frame_keep[idx] = ok & (goodL | goodR)
        rows.append(dict(rec=r, dataset=s.dataset, split=s.split, env=s.env, n=int(m.sum()),
                         pass_=bool(ok), reasons=reasons, frames_kept=int((ok & (goodL | goodR)).sum()),
                         kept_L=int(goodL.sum()), kept_R=int(goodR.sum()), detail=detail))
    by_reason = {}
    for x in rows:
        for rr in x["reasons"]:
            by_reason[rr] = by_reason.get(rr, 0) + 1
    split_stat = {}
    for sp in ("train", "validation", "test"):
        sel = [x for x in rows if x["split"] == sp]
        split_stat[sp] = dict(records=len(sel), pass_=int(sum(x["pass_"] for x in sel)),
                              frames=int(sum(x["n"] for x in sel)),
                              frames_kept=int(sum(x["frames_kept"] for x in sel)))
    return dict(criteria=RET, per_record=rows,
                records_total=len(rows), records_pass=int(sum(x["pass_"] for x in rows)),
                records_fail=int(sum(not x["pass_"] for x in rows)),
                reasons=by_reason, by_split=split_stat,
                frames_total=int(len(t)), frames_kept=int(frame_keep.sum()),
                frame_rate=float(frame_keep.mean()),
                hand_frames_total=int(len(t) * 2),
                hand_frames_kept=int(sum(x["kept_L"] + x["kept_R"] for x in rows)))


# ----------------------------------------------------------------------------
# baselines on the continuous layer
# ----------------------------------------------------------------------------
def _design(st, side, h=1):
    S = st[side]
    pos, vel, ap = S["pos"], S["vel"], S["aperture"]
    n = len(pos)
    X = np.column_stack([np.ones(n), pos, vel, ap])
    # target: the palm centre h frames ahead, expressed in the head frame at t
    R = quat_to_R(st["Q"].astype(np.float64))[:-h].transpose(0, 2, 1)   # world -> head frame
    y = np.einsum("nij,nj->ni", R, S["pos_world"].astype(np.float64)[h:] - st["H"].astype(np.float64)[:-h])
    return X[:-h], y, pos[:-h]


def baselines(seed=0):
    P, recs = panel()
    st_all = build_all()
    # records that failed the quality screen are excluded from fitting and evaluation
    failed = {int(x["rec"]) for x in retention()["per_record"] if not x["pass_"]}
    tr = np.array([r for r in recs[recs.split == "train"].rec.values if int(r) not in failed])
    te = np.array([r for r in recs[recs.split == "test"].rec.values if int(r) not in failed])
    # ---- fit ridge on train records ----
    Xt, Yt = [], []
    for r in tr:
        for side in ("L", "R"):
            X, y, _ = _design(st_all[int(r)], side)
            Xt.append(X); Yt.append(y)
    Xt = np.concatenate(Xt); Yt = np.concatenate(Yt)
    A = np.linalg.solve(Xt.T @ Xt + 1e-3 * np.eye(Xt.shape[1]), Xt.T @ Yt)

    # ---- bootstrap coefficients over train records ----
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(200):
        pick = rng.choice(tr, size=len(tr), replace=True)
        Xb, Yb = [], []
        for r in pick:
            for side in ("L", "R"):
                X, y, _ = _design(st_all[int(r)], side)
                Xb.append(X); Yb.append(y)
        Xb = np.concatenate(Xb); Yb = np.concatenate(Yb)
        boots.append(np.linalg.solve(Xb.T @ Xb + 1e-3 * np.eye(Xb.shape[1]), Xb.T @ Yb))
    boots = np.stack(boots)
    coef_sd = boots.std(axis=0)

    # ---- evaluate on test records ----
    per = []
    for r in te:
        s = recs[recs.rec == r].iloc[0]
        for side in ("L", "R"):
            st = st_all[int(r)]
            X, y, y0 = _design(st, side)
            e_const = np.linalg.norm(y - y0, axis=1)
            e_lin = np.linalg.norm(y - X @ A, axis=1)
            per.append(dict(rec=int(r), env=str(s.env), side=side, n=len(y),
                            const_mean=float(e_const.mean()), const_med=float(np.median(e_const)),
                            const_q90=float(np.percentile(e_const, 90)),
                            lin_mean=float(e_lin.mean()), lin_med=float(np.median(e_lin)),
                            lin_q90=float(np.percentile(e_lin, 90)),
                            const=e_const, lin=e_lin))
    # bootstrap over test records
    rng = np.random.default_rng(seed + 1)
    rec_ids = np.array(sorted({p["rec"] for p in per}))
    ci = {"const_mean": [], "lin_mean": [], "const_q90": [], "lin_q90": []}
    for _ in range(500):
        pick = rng.choice(rec_ids, size=len(rec_ids), replace=True)
        ec = np.concatenate([p["const"] for p in per if p["rec"] in set(pick.tolist())])
        el = np.concatenate([p["lin"] for p in per if p["rec"] in set(pick.tolist())])
        ci["const_mean"].append(ec.mean()); ci["lin_mean"].append(el.mean())
        ci["const_q90"].append(np.percentile(ec, 90)); ci["lin_q90"].append(np.percentile(el, 90))
    allc = np.concatenate([p["const"] for p in per])
    alll = np.concatenate([p["lin"] for p in per])
    out = dict(train_records=int(len(tr)), test_records=int(len(te)),
               n_train_frames=int(len(Xt)), n_test_frames=int(len(allc)),
               coefficients=A.tolist(), coef_sd=coef_sd.tolist(),
               coef_names=["const"] + ["px", "py", "pz"] + ["vx", "vy", "vz"] + ["aperture"],
               constant=dict(mean=float(allc.mean()), median=float(np.median(allc)),
                             q90=float(np.percentile(allc, 90)),
                             mean_ci=[float(np.percentile(ci["const_mean"], 2.5)),
                                      float(np.percentile(ci["const_mean"], 97.5))],
                             q90_ci=[float(np.percentile(ci["const_q90"], 2.5)),
                                     float(np.percentile(ci["const_q90"], 97.5))]),
               linear=dict(mean=float(alll.mean()), median=float(np.median(alll)),
                           q90=float(np.percentile(alll, 90)),
                           mean_ci=[float(np.percentile(ci["lin_mean"], 2.5)),
                                    float(np.percentile(ci["lin_mean"], 97.5))],
                           q90_ci=[float(np.percentile(ci["lin_q90"], 2.5)),
                                   float(np.percentile(ci["lin_q90"], 97.5))]),
               improvement_mean=float(1 - alll.mean() / allc.mean()),
               per_record=[{k: v for k, v in p.items() if k not in ("const", "lin")} for p in per],
               note=("target = palm-centre position at t+1 expressed in the head frame at t; "
                     "features = [1, pos_t, vel_t, aperture_t]; ridge alpha=1e-3; "
                     "errors are Euclidean, metres, on test environments only."))
    # ---- second horizon: 5 frames = 0.167 s, no bootstrap (cost) ----
    hz = {}
    for h in (1, 5):
        if h == 1:
            ce, le = allc, alll
        else:
            Xh, Yh = [], []
            for r in tr:
                for side in ("L", "R"):
                    X_, y_, _ = _design(st_all[int(r)], side, h)
                    Xh.append(X_); Yh.append(y_)
            Xh = np.concatenate(Xh); Yh = np.concatenate(Yh)
            Ah = np.linalg.solve(Xh.T @ Xh + 1e-3 * np.eye(Xh.shape[1]), Xh.T @ Yh)
            ec, el = [], []
            for r in te:
                for side in ("L", "R"):
                    X_, y_, y0_ = _design(st_all[int(r)], side, h)
                    ec.append(np.linalg.norm(y_ - y0_, axis=1))
                    el.append(np.linalg.norm(y_ - X_ @ Ah, axis=1))
            ce, le = np.concatenate(ec), np.concatenate(el)
        hz["h%d" % h] = dict(horizon_frames=h, horizon_s=h / 30.0, n_frames=int(len(ce)),
                             constant=dict(mean=float(ce.mean()), median=float(np.median(ce)),
                                           q90=float(np.percentile(ce, 90))),
                             linear=dict(mean=float(le.mean()), median=float(np.median(le)),
                                         q90=float(np.percentile(le, 90))),
                             improvement_mean=float(1 - le.mean() / ce.mean()))
    out["by_horizon"] = hz
    return out


# ----------------------------------------------------------------------------
# cross-environment stage statistics
# ----------------------------------------------------------------------------
def stage_stats():
    P, recs = panel()
    st_all = build_all()
    # pooled matrices
    pooled = np.zeros((5, 5), np.float64)
    pooled_share = np.zeros(5)
    per_rec = []
    seg_lens_all = []
    for _, s in recs.iterrows():
        r = int(s.rec)
        counts = np.zeros(5)
        trans = np.zeros((5, 5))
        lens = []
        for side in ("L", "R"):
            stg = st_all[r][side]["stage"]
            counts += np.bincount(stg, minlength=5)
            # segment-level transitions: collapse runs, then count label changes
            cuts = np.where(np.diff(stg) != 0)[0] + 1
            parts = [p for p in np.split(stg, cuts) if len(p)]
            lens += [len(p) for p in parts]
            labs = [int(p[0]) for p in parts]
            for a in range(len(labs) - 1):
                trans[labs[a], labs[a + 1]] += 1
        share = counts / counts.sum()
        seq_trans = trans
        per_rec.append(dict(rec=r, dataset=s.dataset, split=s.split, env=s.env, n=int(s.n),
                            counts=counts.astype(int).tolist(),
                            share={STAGES[i]: float(share[i]) for i in range(5)},
                            trans=seq_trans.tolist(),
                            mean_seg_len_frames=float(np.mean(lens)) if lens else 0.0, lens=[int(x) for x in lens]))
        pooled += trans
        pooled_share += counts
        seg_lens_all += lens

    def agg(keys, keyname):
        groups = {}
        for x in per_rec:
            groups.setdefault(x[keyname], []).append(x)
        out = {}
        for g, xs in groups.items():
            c = np.sum([x["counts"] for x in xs], axis=0)
            tr = np.sum([np.asarray(x["trans"]) for x in xs], axis=0)
            lens = np.concatenate([np.asarray(x["lens"]) for x in xs])
            out[str(g)] = dict(records=len(xs), frames=int(c.sum()),
                               share={STAGES[i]: float(c[i] / max(c.sum(), 1)) for i in range(5)},
                               mean_seg_len_frames=float(lens.mean()),
                               median_seg_len_frames=float(np.median(lens)),
                               n_segments=int(len(lens)),
                               trans=tr.tolist())
        return out

    by_env = agg(None, "env")
    by_ds = agg(None, "dataset")

    # chi-square env x stage (frame counts) + Cramer's V
    from scipy import stats as sps
    tab = np.array([[x["counts"][i] for i in range(5)] for x in per_rec])  # record x stage
    env_tab = {}
    for x in per_rec:
        env_tab.setdefault(x["env"], np.zeros(5))
        env_tab[x["env"]] += np.array(x["counts"], float)
    E = np.array(list(env_tab.values()))
    chi2, p, dof, exp = sps.chi2_contingency(E + 1e-9, correction=False)
    n = E.sum()
    V = float(np.sqrt(chi2 / (n * (min(E.shape) - 1))))
    # KL of each env from pooled
    p0 = pooled_share / pooled_share.sum()
    kl = {}
    for env, c in env_tab.items():
        q = c / c.sum()
        kl[str(env)] = float(np.sum(q * np.log((q + 1e-12) / (p0 + 1e-12))))
    # transition informativeness: H(next) vs H(next|current), bits
    Pt = pooled / pooled.sum()
    rows_tot = pooled.sum(1, keepdims=True)
    Pc = np.where(rows_tot > 0, pooled / np.maximum(rows_tot, 1e-12), 0.0)   # row-conditional
    pn = Pt.sum(0)
    Hn = float(-np.sum(pn * np.log2(pn + 1e-12)))
    cond = {}
    for i in range(5):
        if rows_tot[i, 0] <= 0:
            cond[STAGES[i]] = None
            continue
        pr = Pc[i]
        cond[STAGES[i]] = float(-np.sum(pr * np.log2(pr + 1e-12)))
    w = np.array([Pt[i].sum() for i in range(5)])
    ok = np.array([cond[STAGES[i]] is not None for i in range(5)])
    vals = np.array([cond[STAGES[i]] if ok[i] else 0.0 for i in range(5)])
    Hcond = float(np.sum(w[ok] * vals[ok]) / max(w[ok].sum(), 1e-12)) if ok.any() else None
    # segment length distribution (frames)
    seg = np.array(seg_lens_all, float)
    out = dict(
        pooled_share={STAGES[i]: float(p0[i]) for i in range(5)},
        pooled_transition=Pc.tolist(),
        pooled_transition_counts=pooled.astype(int).tolist(),
        pooled_mean_seg_len_frames=float(seg.mean()), pooled_median_seg_len_frames=float(np.median(seg)),
        seg_len_p90=float(np.percentile(seg, 90)),
        by_env=by_env, by_dataset=by_ds,
        chi2_env=dict(chi2=float(chi2), dof=int(dof), p=float(p), cramers_v=V,
                      n_frames=int(n), groups=int(E.shape[0])),
        kl_env_from_pooled=kl,
        entropy=dict(H_next_bits=Hn, H_next_given_current_bits=Hcond,
                     info_bits=Hn - Hcond, per_state_cond_entropy=cond),
        per_record=per_rec,
        note=("frames inside a record are autocorrelated, so the chi-square p-value is "
              "anti-conservative; Cramer's V and the KL table are the effect-size read-out."))
    return out


# ----------------------------------------------------------------------------
# agreement with the reference segmentation (secondary, NOT accuracy)
# ----------------------------------------------------------------------------
def reference_agreement():
    P, recs = panel()
    st_all = build_all()
    seg = pd.read_csv(os.path.join(DATA, "segments.csv"), encoding="utf-8-sig")

    def mapped(txt):
        t = txt.lower()
        if any(k in t for k in ("pick up", "take ", "grab", "lift")):
            return "pick"
        if any(k in t for k in ("place", "put ", "drop", "set ")):
            return "place"
        if any(k in t for k in ("arrange", "rearrange", "flip", "push", "open", "close", "upright", "turn")):
            return "arrange"
        return None

    rows = []
    covered = 0
    ivs = {}                                    # (rec, class) -> [(t0, t1), ...]
    for _, s in seg.iterrows():
        lab = mapped(str(s.label))
        if lab is None:
            continue
        r = int(s.rec)
        st = st_all[r]
        t0, t1 = s.start, s.end
        ivs.setdefault((r, lab), []).append((float(t0), float(t1)))
        best = None
        anyhit = 0.0
        for side in ("L", "R"):
            tt = st["t"]
            m = (tt >= t0) & (tt <= t1)
            if m.sum() == 0:
                continue
            hit = float(np.mean(st[side]["stage"][m] == STAGE_ID[lab]))
            anyhit = max(anyhit, float(np.any(st[side]["stage"][m] == STAGE_ID[lab])))
            best = hit if best is None else max(best, hit)
        if best is None:
            continue
        covered += 1
        rows.append(dict(rec=r, label=lab, hit=best, anyhit=anyhit, dur=float(s.end - s.start)))
    df = pd.DataFrame(rows)
    # frame-level precision: of the frames WE label c, how many fall in a reference c interval
    prec = {}
    for cl in ("pick", "place", "arrange"):
        num = den = 0
        for r, st in st_all.items():
            t = st["t"]
            iv = ivs.get((int(r), cl), [])
            mask_ref = np.zeros(len(t), bool)
            for a, b in iv:
                mask_ref |= (t >= a) & (t <= b)
            for side in ("L", "R"):
                m = st[side]["stage"] == STAGE_ID[cl]
                den += int(m.sum()); num += int((m & mask_ref).sum())
        prec[cl] = dict(n_frames=int(den), in_reference_frac=float(num / den) if den else None)
    out = dict(n_segments_total=int(len(seg)), n_mapped=int(len(rows)),
               frames_covered_frac=None, by_class={}, mean=float(df.hit.mean()),
               median=float(df.hit.median()),
               segment_coverage_any_hit=float(df.anyhit.mean()),
               frame_precision_in_reference=prec,
               chance={s: float(stage_stats_share().get(s, 0)) for s in ("pick", "place", "arrange")},
               note=("agreement = share of frames inside a reference segment whose rule-derived stage "
                     "equals the class implied by the segment text, taking the better hand. "
                     "segment_coverage_any_hit = share of reference segments in which the predicted "
                     "class appears at least once. This is agreement with a reference annotation, not "
                     "accuracy: the reference is neither error-free nor independent physical ground "
                     "truth, and reach/transport have no reference labels."))
    for lab, g in df.groupby("label"):
        out["by_class"][lab] = dict(n=int(len(g)), mean=float(g.hit.mean()),
                                    median=float(g.hit.median()),
                                    coverage_any_hit=float(g.anyhit.mean()))
    return out


_SHARE_CACHE = None


def stage_stats_share():
    global _SHARE_CACHE
    if _SHARE_CACHE is None:
        st = stage_stats()
        _SHARE_CACHE = st["pooled_share"]
    return _SHARE_CACHE


# ----------------------------------------------------------------------------
# threshold sensitivity
# ----------------------------------------------------------------------------
def sensitivity():
    st_all = build_all()
    base = None
    table = []
    keys = ["v_hi", "v_lo", "a_grasp", "t_arrange", "a_closed"]
    for k in keys:
        for mult in (0.8, 1.0, 1.2):
            thr = dict(THR)
            thr[k] = THR[k] * mult
            counts = np.zeros(5)
            lens = []
            for r, st in st_all.items():
                for side in ("L", "R"):
                    S = st[side]
                    stg, _, sl, _ = derive_stages(S["speed"], S["aperture"], S["height"], thr)
                    counts += np.bincount(stg, minlength=5)
                    cuts = np.where(np.diff(stg) != 0)[0] + 1
                    lens += [len(p) for p in np.split(stg, cuts)]
            share = counts / counts.sum()
            row = dict(param=k, mult=mult, value=thr[k],
                       share={STAGES[i]: float(share[i]) for i in range(5)},
                       mean_seg_len_frames=float(np.mean(lens)), n_segments=len(lens))
            if mult == 1.0:
                base = row
            table.append(row)
    out = dict(base=base, rows=table, thr=THR)
    # max effect per parameter
    eff = {}
    for k in keys:
        rs = [r for r in table if r["param"] == k]
        ds = max(abs(r["share"][s] - base["share"][s]) for r in rs for s in STAGES)
        dl = max(abs(r["mean_seg_len_frames"] / base["mean_seg_len_frames"] - 1) for r in rs)
        eff[k] = dict(max_share_shift_pp=float(ds * 100), max_seg_len_change=float(dl))
    out["effect"] = eff
    out["worst"] = max(eff.items(), key=lambda kv: kv[1]["max_share_shift_pp"])[0]
    return out


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    ensure_dirs()
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", default="", help="comma list: baselines,sensitivity")
    a = ap.parse_args()
    skip = set(x for x in a.skip.split(",") if x)

    print("representative-point candidates ...")
    cmet = candidate_metrics()
    print(json.dumps({k: v for k, v in cmet.items() if k != "_note"}, indent=1)[:1200])

    print("stage statistics ...")
    sst = stage_stats()
    print("pooled share", {k: round(v, 4) for k, v in sst["pooled_share"].items()})
    print("chi2", sst["chi2_env"])

    print("retention ...")
    ret = retention()
    print("records pass/fail", ret["records_pass"], ret["records_fail"], "reasons", ret["reasons"])
    print("frame rate", round(ret["frame_rate"], 5))

    print("reference agreement ...")
    agr = reference_agreement()
    print({k: agr[k] for k in ("n_mapped", "mean", "median")})

    sens = {"note": "skipped"} if "sensitivity" in skip else sensitivity()
    if "sensitivity" not in skip:
        print("worst threshold", sens["worst"], sens["effect"][sens["worst"]])

    bas = {"note": "skipped"} if "baselines" in skip else baselines()
    if "baselines" not in skip:
        print("baseline const", bas["constant"]["mean"], "lin", bas["linear"]["mean"])

    # assemble JSON
    recs = panel()[1]
    per_record = []
    for x in sst["per_record"]:
        rr = ret["per_record"][x["rec"]]
        per_record.append(dict(rec=x["rec"], dataset=x["dataset"], split=x["split"], env=x["env"],
                               n=x["n"], stage_share=x["share"],
                               mean_seg_len_frames=x["mean_seg_len_frames"],
                               retention=dict(pass_=rr["pass_"], reasons=rr["reasons"],
                                              frames_kept=rr["frames_kept"])))
    meta = dict(
        source="data/panel.npz + data/panel_records.csv",
        n_records=int(len(recs)), n_frames=int(len(panel()[0]["t"])),
        units="metres, seconds; ratios dimensionless",
        quat_order="wxyz (source columns quat.w,x,y,z; wxyz gives head-frame within-record std 3.91 cm vs 7.98 cm for xyzw)",
        keypoints="21 per hand, MediaPipe topology: 0 wrist, thumb 1-4, index 5-8, middle 9-12, ring 13-16, pinky 17-20",
        head_frame="p_h = R(q)^T (p_w - H); R maps head->world",
        state_vector=VEC_NAMES,
        representative_point="palm_centre_0_5_9_13_17",
    )
    obj = dict(_meta=meta, thresholds=THR, threshold_labels=THR_LABEL,
               representative_point=dict(chosen="palm_centre_0_5_9_13_17", candidates=cmet),
               retention=ret, stages=dict(
                   pooled_share=sst["pooled_share"], pooled_transition=sst["pooled_transition"],
                   pooled_mean_seg_len_frames=sst["pooled_mean_seg_len_frames"],
                   pooled_median_seg_len_frames=sst["pooled_median_seg_len_frames"],
                   seg_len_p90=sst["seg_len_p90"],
                   by_env=sst["by_env"], by_dataset=sst["by_dataset"],
                   chi2_env=sst["chi2_env"], kl_env_from_pooled=sst["kl_env_from_pooled"],
                   entropy=sst["entropy"], note=sst["note"]),
               agreement_with_reference=agr,
               sensitivity=sens, baselines=bas, records=per_record)
    p = os.path.join(DATA, "state_layer.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print("wrote", p, os.path.getsize(p))

    # compact npz for P2/P3 reuse
    st_all = build_all()
    rec_ids = sorted(st_all)
    np.savez_compressed(os.path.join(DATA, "state_layer.npz"),
                        rec=np.array(rec_ids),
                        **{f"{side}_{k}": np.concatenate([st_all[r][side][k] for r in rec_ids])
                           for side in ("L", "R")
                           for k in ("pos", "quat", "dir", "vel", "speed", "omega",
                                     "aperture", "spread", "static", "height", "conf",
                                     "stage", "stage_conf", "vector")})
    print("wrote state_layer.npz")


if __name__ == "__main__":
    main()