"""Scan all 38 annotated records for actual content in `segment.skill` and
`problem_type`.  The manifest recorded the *columns*; this checks the *values*.
Output: data/annotation_content_scan.json
"""
import collections
import csv
import json
import os

RAW = r"Restocking_Problem_and_Data_EN\Raw_Data"
DATASETS = ("EgoPro", "EgoStandard")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    skill_vals = collections.Counter()
    prob_vals = collections.Counter()
    per_rec = []
    for ds in DATASETS:
        base = os.path.join(RAW, ds)
        for u in sorted(os.listdir(base)):
            tab = os.path.join(base, u, "tables")
            sem_p = os.path.join(tab, "annotation_semantic_segments.csv")
            bad_p = os.path.join(tab, "annotation_bad_frame_pose_hand.csv")
            rec = dict(dataset=ds, uuid=u)
            if os.path.exists(sem_p):
                rows = read_csv(sem_p)
                rec["sem_segments"] = len(rows)
                cols = [c for c in rows[0] if "skill" in c.lower()]
                rec["sem_skill_cols"] = cols
                fill = 0
                for r in rows:
                    for c in cols:
                        v = (r[c] or "").strip()
                        if v and v not in ("0",):
                            fill += 1
                            skill_vals[v] += 1
                rec["sem_skill_nonempty"] = fill
            if os.path.exists(bad_p):
                rows = read_csv(bad_p)
                rec["bad_rows"] = len(rows)
                nbad = sum(1 for r in rows if str(r.get("is_bad", "")).strip().lower() == "true")
                rec["bad_true"] = nbad
                cols = [c for c in rows[0] if "problem" in c.lower() or "reason" in c.lower()]
                rec["bad_reason_cols"] = cols
                fill = 0
                for r in rows:
                    for c in cols:
                        v = (r[c] or "").strip()
                        if v and v not in ("0",):
                            fill += 1
                            prob_vals[v] += 1
                rec["bad_reason_nonempty"] = fill
            per_rec.append(rec)

    tot_skill = sum(r.get("sem_skill_nonempty", 0) for r in per_rec)
    tot_reason = sum(r.get("bad_reason_nonempty", 0) for r in per_rec)
    out = dict(
        _meta=dict(
            script="_scan_annotations.py",
            question="do the skill labels and the bad-frame reasons actually carry values?",
            note="the manifest recorded columns; this counts non-empty values",
        ),
        n_records=len(per_rec),
        skill_values_total=tot_skill,
        reason_values_total=tot_reason,
        skill_distinct=dict(skill_vals.most_common(40)),
        reason_distinct=dict(prob_vals.most_common(40)),
        bad_true_total=int(sum(r.get("bad_true", 0) for r in per_rec)),
        bad_rows_total=int(sum(r.get("bad_rows", 0) for r in per_rec)),
        per_record=per_rec,
    )
    dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data",
                       "annotation_content_scan.json")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("written", dst, os.path.getsize(dst), "B")
    print("records", len(per_rec), "skill non-empty", tot_skill, "reason non-empty", tot_reason,
          "bad_true", out["bad_true_total"], "/", out["bad_rows_total"])
    print("skill values:", dict(skill_vals.most_common(12)))
    print("reason values:", dict(prob_vals.most_common(12)))
    print("sample records:")
    for r in per_rec[:3]:
        print(" ", r)


if __name__ == "__main__":
    main()