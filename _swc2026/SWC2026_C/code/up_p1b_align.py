# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p1b_align.py -- align per-frame bad-frame REASON labels onto the state.npz frames.

Why this file exists
--------------------
`data/state.npz` only carries `badL/badR` (whether a hand frame is bad). The REASON
(`occlusion` / `near edge`) lives in two different raw sources:

  * EgoDemo  : Raw_Data/EgoDemo/<sample>/bad_frame_ratio.json
               {"total_frames": int, "hand_bad_frame_details":[
                   {"frame": int, "left_bad_reason": str|null, "right_bad_reason": str|null}, ...]}
               frame index is 1-based when it reaches total_frames (see build_panel.py).
  * EgoPro / EgoStandard : Raw_Data/<ds>/<uuid>/tables/annotation_bad_frame_pose_hand.csv
               row i  <-> frame i ; `is_bad` ; `problem_type.length` ; `problem_type[0..k]`
               slot values look like "left:occlusion", "right:near edge", or a bare numeric
               code "1"/"2" (reason unknown in this table).

`build_panel.py` truncated every pose record to
    n = min(len(pose_left_hand), len(pose_right_hand), len(pose_head), len(annotation_bad_frame))
so row order is preserved and frame i of the CSV is frame i of state.npz.  EgoDemo frames
come from the parquet rows, so the JSON `frame` field is the index.  This script re-derives
the bad flag from the raw source and compares it with `state.npz`'s badL|badR: the disagreement
rate IS the alignment failure rate reported upstream.

Outputs (new files only):
  data/up_p1b_aux.npz    occ, edge, bad_derived, aux_mask, reason_known, rec  (N = 66070)
  data/up_p1b_align.json alignment diagnostics + failure rates
"""
import csv
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"Restocking_Problem_and_Data_EN"
PROJ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA = os.path.join(PROJ, "data")
OUT_NPZ = os.path.join(DATA, "up_p1b_aux.npz")
OUT_JSON = os.path.join(DATA, "up_p1b_align.json")

NUMERIC_REASONS = {"1", "2", "3", "4"}  # bare codes: bad frame, reason NOT resolved here


def classify(reason_strings):
    """-> (occ, edge, unknown_only) for one frame given its per-side reason strings."""
    occ = edge = False
    seen_text = False
    for s in reason_strings:
        if not s:
            continue
        t = str(s).strip().lower()
        if not t:
            continue
        if t in NUMERIC_REASONS:
            continue
        seen_text = True
        if "occlusion" in t:
            occ = True
        elif "near" in t and "edge" in t:
            edge = True
    return occ, edge, (not seen_text)


def load_demo(sample):
    p = os.path.join(ROOT, "Raw_Data", "EgoDemo", sample, "bad_frame_ratio.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    total = int(d.get("total_frames", -1))
    rows = []
    for it in d.get("hand_bad_frame_details", []):
        f = int(it["frame"])
        if total > 0 and f >= total:
            f -= 1
        rows.append((f, it.get("left_bad_reason"), it.get("right_bad_reason")))
    return rows


def load_pose(ds, sample):
    p = os.path.join(ROOT, "Raw_Data", ds, sample, "tables", "annotation_bad_frame_pose_hand.csv")
    if not os.path.exists(p):
        return None
    rows = []
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        slot_cols = [c for c in rd.fieldnames if c and c.startswith("problem_type[")]
        for i, r in enumerate(rd):
            bad = str(r.get("is_bad", "")).strip().lower() in ("true", "1")
            if not bad:
                continue
            rows.append((i, [r.get(c) for c in slot_cols]))
    return rows


def main():
    z = np.load(os.path.join(DATA, "state.npz"))
    rec = z["rec"].astype(np.int64)
    bad = (z["badL"] | z["badR"])
    N = len(rec)

    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"), encoding="utf-8-sig")
    row_of = {int(r.rec): r for r in meta.itertuples()}

    occ = np.zeros(N, bool)
    edge = np.zeros(N, bool)
    derived = np.zeros(N, bool)
    reason_known = np.ones(N, bool)   # True: the frame's reason is fully resolved
    aux_mask = np.zeros(N, bool)      # True: frame may contribute to the auxiliary loss
    has_reason_source = np.zeros(N, bool)

    per_rec = []
    missing_src_frames = 0
    mismatch_frames = 0
    pos_mismatch_records = []

    for r in np.unique(rec):
        m = np.flatnonzero(rec == r)
        lo, hi = int(m[0]), int(m[-1]) + 1
        n = hi - lo
        rr = row_of[int(r)]
        ds, sample = str(rr.dataset), str(rr.sample)

        if ds == "EgoDemo":
            rows = load_demo(sample)
            src = "bad_frame_ratio.json"
        else:
            rows = load_pose(ds, sample)
            src = "annotation_bad_frame_pose_hand.csv"

        if rows is None:
            missing_src_frames += n
            per_rec.append(dict(rec=int(r), dataset=ds, sample=sample, source=src,
                                status="MISSING", n=n, bad_in_state=int(bad[lo:hi].sum()),
                                matched=None))
            continue

        has_reason_source[lo:hi] = True
        n_out = 0
        n_occ = n_edge = n_unknown = 0
        for item in rows:
            f = item[0]
            if f < 0 or f >= n:
                n_out += 1
                continue
            if ds == "EgoDemo":
                strs = [item[1], item[2]]
            else:
                strs = item[1]
            o, e, unk = classify(strs)
            occ[lo + f] |= o
            edge[lo + f] |= e
            derived[lo + f] = True
            reason_known[lo + f] = not unk
            n_occ += int(o); n_edge += int(e); n_unknown += int(unk)

        dis = int((derived[lo:hi] != bad[lo:hi]).sum())
        mismatch_frames += dis
        if dis:
            pos_mismatch_records.append(dict(rec=int(r), dataset=ds, sample=sample,
                                            n=n, disagree=dis,
                                            bad_state=int(bad[lo:hi].sum()),
                                            bad_derived=int(derived[lo:hi].sum())))
        per_rec.append(dict(rec=int(r), dataset=ds, sample=sample, source=src, n=n,
                            source_rows=len(rows), rows_out_of_range=n_out,
                            bad_in_state=int(bad[lo:hi].sum()),
                            bad_derived=int(derived[lo:hi].sum()),
                            occ_frames=int(occ[lo:hi].sum()),
                            edge_frames=int(edge[lo:hi].sum()),
                            unknown_reason_frames=n_unknown,
                            disagree=dis))

    # aux mask: record has a reason source AND (frame not bad OR reason resolved)
    aux_mask = has_reason_source & (reason_known | (~bad))
    # a resolved non-bad frame must have occ=edge=0 by construction
    assert not (occ & ~bad).any() and not (edge & ~bad).any(), "reason on a non-bad frame"

    total_missing_or_mismatch = missing_src_frames + mismatch_frames
    failure_rate = total_missing_or_mismatch / float(N)

    tr = np.zeros(N, bool)
    va = np.zeros(N, bool)
    te = np.zeros(N, bool)
    for r in np.unique(rec):
        mm = rec == r
        sp = str(row_of[int(r)].split)
        if sp == "train":
            tr |= mm
        elif sp == "validation":
            va |= mm
        elif sp == "test":
            te |= mm

    def rate(mask):
        return dict(frames=int(mask.sum()),
                    bad=int(bad[mask].sum()),
                    occ=int(occ[mask].sum()),
                    edge=int(edge[mask].sum()),
                    aux_mask=int((aux_mask & mask).sum()),
                    aux_pos_occ=int((occ & aux_mask & mask).sum()),
                    aux_pos_edge=int((edge & aux_mask & mask).sum()))

    res = dict(
        _meta=dict(script="up_p1b_align.py",
                   question="can the reason labels be aligned frame-exactly onto state.npz?",
                   sources=dict(EgoDemo="bad_frame_ratio.json / hand_bad_frame_details[].{left,right}_bad_reason",
                                pose="tables/annotation_bad_frame_pose_hand.csv row index, is_bad + problem_type[*]"),
                   numeric_codes=sorted(NUMERIC_REASONS),
                   mask_rule=("aux_mask = record has a reason source AND (frame not bad OR reason resolved); "
                              "bad frames whose only reason is a bare numeric code are masked out of the aux loss"),
                   gate="alignment failure rate > 5%  -> drop the multi-task step, keep step 1 only"),
        frames=int(N),
        records=int(len(np.unique(rec))),
        missing_source_frames=int(missing_src_frames),
        label_mismatch_frames=int(mismatch_frames),
        alignment_failure_rate=float(failure_rate),
        alignment_failure_pct=round(100.0 * failure_rate, 4),
        reason_vocab=dict(occlusion_frames=int(occ.sum()), near_edge_frames=int(edge.sum()),
                          bad_frames=int(bad.sum()),
                          bad_frames_reason_resolved=int((bad & reason_known).sum()),
                          bad_frames_reason_unknown=int((bad & ~reason_known).sum())),
        aux_mask_frames=int(aux_mask.sum()),
        per_split=dict(train=rate(tr), validation=rate(va), test=rate(te)),
        mismatch_records=pos_mismatch_records,
        per_record=per_rec,
    )
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    np.savez_compressed(OUT_NPZ, occ=occ, edge=edge, bad_derived=derived,
                        aux_mask=aux_mask, reason_known=reason_known, rec=rec)

    print(f"frames={N:,}  records={res['records']}")
    print(f"missing_source_frames={missing_src_frames:,}  label_mismatch_frames={mismatch_frames:,}")
    print(f"ALIGNMENT FAILURE RATE = {100*failure_rate:.4f}%   (gate: <= 5%)")
    print(f"occ frames={occ.sum():,}  near-edge frames={edge.sum():,}  bad frames={bad.sum():,}")
    print(f"bad with resolved reason={int((bad & reason_known).sum()):,}   "
          f"bad with unknown(numeric-only) reason={int((bad & ~reason_known).sum()):,}")
    print(f"aux_mask frames={int(aux_mask.sum()):,} / {N:,}")
    for k, v in res["per_split"].items():
        print(f"  {k:11s} frames={v['frames']:,} bad={v['bad']:,} aux={v['aux_mask']:,} "
              f"occ+={v['aux_pos_occ']:,} edge+={v['aux_pos_edge']:,}")
    if pos_mismatch_records:
        print("mismatching records:", json.dumps(pos_mismatch_records[:10], ensure_ascii=False))
    print(f"saved -> {OUT_NPZ}\nsaved -> {OUT_JSON}")


if __name__ == "__main__":
    main()