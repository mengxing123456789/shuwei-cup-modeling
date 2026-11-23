# -*- coding: utf-8 -*-
"""Probe 4: (a) truncation risk in 10/11-column files; (b) per-record spread of right:near edge."""
import os, csv, sys, io, collections, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"Restocking_Problem_and_Data_EN"
DS = ["EgoPro", "EgoStandard"]

def recs(ds):
    d = os.path.join(ROOT, "Raw_Data", ds)
    return sorted([p for p in os.listdir(d) if os.path.isdir(os.path.join(d, p))])

print("%-11s %-38s %3s %5s %5s %s" % ("dataset", "uuid", "nc", "nbad", "maxL", "len_hist"))
trunc = []
for ds in DS:
    for u in recs(ds):
        p = os.path.join(ROOT, "Raw_Data", ds, u, "tables", "annotation_bad_frame_pose_hand.csv")
        with open(p, "r", encoding="utf-8", newline="") as f:
            rd = csv.reader(f)
            h = [c.lstrip("\ufeff") for c in next(rd)]
            ix = {c: i for i, c in enumerate(h)}
            nc = len(h)
            nbad = 0
            hist = collections.Counter()
            for r in rd:
                if r[ix["is_bad"]].strip().lower() not in ("true", "1"):
                    continue
                nbad += 1
                L = int(float(r[ix["problem_type.length"]]))
                hist[L] += 1
                if nc < 12 and L >= 2:
                    trunc.append((ds, u, nc, L))
            mx = max(hist) if hist else 0
            if nbad:
                print("%-11s %-38s %3d %5d %5d %s" % (ds, u[:36], nc, nbad, mx, dict(hist)))
print()
print("TRUNCATION RISK (ncols<12 with length>=2):", len(trunc), trunc)

# (b) right:near edge per record
print()
print("right:near edge events per record (side=right, reason='near edge'):")
for ds in DS:
    for u in recs(ds):
        p = os.path.join(ROOT, "Raw_Data", ds, u, "tables", "annotation_bad_frame_pose_hand.csv")
        k = 0
        with open(p, "r", encoding="utf-8", newline="") as f:
            rd = csv.reader(f)
            h = [c.lstrip("\ufeff") for c in next(rd)]
            ix = {c: i for i, c in enumerate(h)}
            sc = [c for c in h if c.startswith("problem_type[")]
            for r in rd:
                if r[ix["is_bad"]].strip().lower() not in ("true", "1"):
                    continue
                for c in sc:
                    if r[ix[c]].strip() == "right:near edge":
                        k += 1
        if k:
            print("  %-11s %-38s %d" % (ds, u[:36], k))