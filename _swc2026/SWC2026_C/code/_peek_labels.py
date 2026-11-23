"""Inspection: the two annotation tables that the paper never used."""
import collections
import csv
import os

CONS = r"Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"
FPRO = r"Restocking_Problem_and_Data_EN\Raw_Data\EgoPro"


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


uuid = sorted(os.listdir(FPRO))[0]
tab = os.path.join(FPRO, uuid, "tables")

for name in ("annotation_semantic_segments.csv", "annotation_bad_frame_pose_hand.csv"):
    p = os.path.join(tab, name)
    rows = read_csv(p)
    print("\n=== %s  rows=%d ===" % (name, len(rows)))
    print("cols:", list(rows[0].keys()))
    for r in rows[:3]:
        print("  ", {k: (v[:40] if isinstance(v, str) else v) for k, v in r.items()})

    if "bad_frame" in name:
        print("  is_bad counts:", collections.Counter(r.get("is_bad") for r in rows))
        cnt = collections.Counter()
        for r in rows:
            for k in r:
                if "problem" in k.lower() or "reason" in k.lower() or "type" in k.lower():
                    v = (r[k] or "").strip()
                    if v:
                        cnt[v] += 1
        print("  reason/value frequency:")
        for k, v in cnt.most_common(15):
            print("    %-70s %d" % (k[:70], v))
    else:
        cnt = collections.Counter(r.get("skill") for r in rows)
        print("  skill counts:", dict(cnt))

print("\n=== how many records carry each table ===")
n_sem = n_bad = 0
for ds in ("EgoPro", "EgoStandard"):
    base = os.path.join(r"Restocking_Problem_and_Data_EN\Raw_Data", ds)
    for u in sorted(os.listdir(base)):
        t = os.path.join(base, u, "tables")
        if os.path.exists(os.path.join(t, "annotation_semantic_segments.csv")):
            n_sem += 1
        if os.path.exists(os.path.join(t, "annotation_bad_frame_pose_hand.csv")):
            n_bad += 1
print("records with semantic segments:", n_sem, " with bad-frame reasons:", n_bad)