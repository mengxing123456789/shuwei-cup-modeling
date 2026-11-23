# -*- coding: utf-8 -*-
"""Probe 3: alignment of annotation table vs pose tables; segment index coverage."""
import os, csv, collections, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"Restocking_Problem_and_Data_EN"
DS = ["EgoPro", "EgoStandard"]

def recs(ds):
    d = os.path.join(ROOT, "Raw_Data", ds)
    return sorted([p for p in os.listdir(d) if os.path.isdir(os.path.join(d, p))])

def head_cols(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return [c.lstrip("\ufeff") for c in next(csv.reader(f))]

def count_and_index(p):
    idxs = []
    tmax = 0.0
    with open(p, "r", encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        h = [c.lstrip("\ufeff") for c in next(rd)]
        ix = {c: i for i, c in enumerate(h)}
        for r in rd:
            idxs.append(int(float(r[ix["_message_index"]])))
            tmax = max(tmax, float(r[ix["_offset_from_first_log_s"]]))
    return len(idxs), set(idxs), tmax

# alignment for every record
mismatch = []
print("%-11s %-38s %6s %6s %6s %9s %9s %s" % ("dataset", "uuid", "ann", "L", "R", "tmax_ann", "tmax_L", "idx_equal"))
for ds in DS:
    for u in recs(ds):
        tp = os.path.join(ROOT, "Raw_Data", ds, u, "tables")
        na, ia, ta = count_and_index(os.path.join(tp, "annotation_bad_frame_pose_hand.csv"))
        nl, il, tl = count_and_index(os.path.join(tp, "pose_left_hand.csv"))
        nr, ir, tr = count_and_index(os.path.join(tp, "pose_right_hand.csv"))
        ok = (na == nl == nr) and (ia == il) and (il == ir)
        if not ok:
            mismatch.append((ds, u, na, nl, nr, ia == il, il == ir))
        print("%-11s %-38s %6d %6d %6d %9.3f %9.3f %s" % (ds, u[:36], na, nl, nr, ta, tl,
              (ia == il == ir) and (na == nl == nr)))

print()
print("records with any mismatch:", len(mismatch))
for m in mismatch:
    print("  ", m)

# header check of pose files
p0 = os.path.join(ROOT, "Raw_Data", DS[0], recs(DS[0])[0], "tables", "pose_left_hand.csv")
h = head_cols(p0)
print()
print("pose_left_hand ncols:", len(h), " first 9:", h[:9])

# segment index
sp = os.path.join(ROOT, "Restocking_Tasks_and_Constraints", "source_segment_index.csv")
seg = collections.defaultdict(list)
with open(sp, "r", encoding="utf-8", newline="") as f:
    rd = csv.DictReader(f)
    for r in rd:
        seg[(r["dataset"], r["episode_uuid"])].append(r)
print()
print("segment index rows:", sum(len(v) for v in seg.values()), " keys:", len(seg))
print("datasets in segment index:", collections.Counter(k[0] for k in seg))
# coverage of our 38 records
cov = 0
for ds in DS:
    for u in recs(ds):
        if (ds, u) in seg:
            cov += 1
print("our 38 records present in segment index:", cov)