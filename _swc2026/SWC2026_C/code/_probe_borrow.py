import os
import io, json, os, re

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# 1) P2 by length -> scaling law inputs
p = os.path.join(D, "p2_by_length.csv")
if os.path.exists(p):
    rows = io.open(p, encoding="utf-8").read().strip().split("\n")
    print("p2_by_length.csv header:", rows[0])
    for r in rows[1:]:
        if ",ridge," in r:
            print("  ", r)

# 2) P1 boundary data for coverage metric
for name in ["p1a_segmentation_compare.json", "p1a_gpu_segmentation_final.json", "segments.csv"]:
    q = os.path.join(D, name)
    print(name, "exists", os.path.exists(q), os.path.getsize(q) if os.path.exists(q) else "")

# 3) check keys of segmentation compare
q = os.path.join(D, "p1a_segmentation_compare.json")
if os.path.exists(q):
    d = json.loads(io.open(q, encoding="utf-8").read())
    print("top keys:", list(d.keys()))
    if "ari" in d:
        print("ari keys:", list(d["ari"].keys()))