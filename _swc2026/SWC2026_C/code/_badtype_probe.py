# -*- coding: utf-8 -*-
"""Probe: inspect annotation_bad_frame_pose_hand.csv schema across all 38 records.
New file, read-only on the data package.
"""
import os, glob, csv, collections, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"Restocking_Problem_and_Data_EN"
DS = ["EgoPro", "EgoStandard"]

def recs(ds):
    d = os.path.join(ROOT, "Raw_Data", ds)
    return sorted([p for p in os.listdir(d) if os.path.isdir(os.path.join(d, p))])

hdrs = collections.Counter()
rows = {}
bad_rows = []
for ds in DS:
    for u in recs(ds):
        p = os.path.join(ROOT, "Raw_Data", ds, u, "tables", "annotation_bad_frame_pose_hand.csv")
        with open(p, "r", encoding="utf-8", newline="") as f:
            rd = csv.reader(f)
            h = [c.lstrip("\ufeff") for c in next(rd)]
            hdrs[tuple(h)] += 1
            n = 0
            for r in rd:
                n += 1
                if len(bad_rows) < 6:
                    d = dict(zip(h, r))
                    if d.get("is_bad", "").strip().lower() in ("true", "1"):
                        bad_rows.append((ds, u, len(h), d))
            rows[(ds, u)] = (len(h), n)

print("distinct headers:", len(hdrs))
for h, c in hdrs.most_common():
    print("  n_records=%d  ncols=%d  cols=%s" % (c, len(h), list(h)))
print()
print("row counts bottom 5:", sorted(rows.items(), key=lambda kv: kv[1][1])[:5])
print("row counts top 5:", sorted(rows.items(), key=lambda kv: -kv[1][1])[:5])
print()
for ds, u, ncol, d in bad_rows:
    print("BADROW", ds, u, ncol)
    for k, v in d.items():
        if v != "":
            print("    %-28s = %r" % (k, v))
    print()