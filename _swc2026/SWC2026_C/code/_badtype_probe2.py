# -*- coding: utf-8 -*-
"""Probe 2: combinations of problem_type slots on bad rows; alignment check vs pose tables."""
import os, csv, collections, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"Restocking_Problem_and_Data_EN"
DS = ["EgoPro", "EgoStandard"]

def recs(ds):
    d = os.path.join(ROOT, "Raw_Data", ds)
    return sorted([p for p in os.listdir(d) if os.path.isdir(os.path.join(d, p))])

combos = collections.Counter()
slot_pairs = collections.Counter()
nbad = 0
nlen_mismatch = 0
examples = {}
for ds in DS:
    for u in recs(ds):
        p = os.path.join(ROOT, "Raw_Data", ds, u, "tables", "annotation_bad_frame_pose_hand.csv")
        with open(p, "r", encoding="utf-8", newline="") as f:
            rd = csv.reader(f)
            h = [c.lstrip("\ufeff") for c in next(rd)]
            ix = {c: i for i, c in enumerate(h)}
            for r in rd:
                if r[ix["is_bad"]].strip().lower() not in ("true", "1"):
                    continue
                nbad += 1
                L = r[ix["problem_type.length"]] if "problem_type.length" in ix else ""
                slots = []
                for k in range(2):
                    nm = "problem_type[%d]" % k
                    slots.append(r[ix[nm]] if nm in ix else "")
                filled = [s for s in slots if s != ""]
                combos[tuple(slots)] += 1
                # declared length vs filled count
                try:
                    if int(L) != len(filled):
                        nlen_mismatch += 1
                except Exception:
                    pass
                if slots[0] in ("1", "2") or slots[1] in ("1", "2"):
                    examples.setdefault((slots[0], slots[1]), (ds, u, r[ix["_message_index"]]))

print("total is_bad rows:", nbad)
print("rows where int(length) != count(filled slots):", nlen_mismatch)
print()
print("slot combinations (n=%d distinct):" % len(combos))
for k, v in combos.most_common():
    print("  %-45s %d" % (str(k), v))
print()
print("numeric-code examples:")
for k, v in examples.items():
    print("  slots=%s  first at %s" % (str(k), v))