# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""verify_p1_badtype.py -- 从 data/badtype_frames.csv + data/p1_badtype.json 复算
p1_badtype.py 打印出的每一个数字。任何一条对不上即 FAIL（退出码 1）。
只读：不改动任何已有文件。
"""
import os, csv, json, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from scipy.stats import binomtest

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSVP = os.path.join(PROJ, "data", "badtype_frames.csv")
JSN = os.path.join(PROJ, "data", "p1_badtype.json")

fails = []
def chk(name, got, want, tol=1e-9):
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    print("%-4s %-58s got=%s want=%s" % ("PASS" if ok else "FAIL", name, got, want))
    if not ok:
        fails.append(name)

J = json.load(open(JSN, encoding="utf-8"))
rows = list(csv.DictReader(open(CSVP, encoding="utf-8", newline="")))
recs = {r["uuid"]: r for r in J["records"]}

# 1 schema
chk("csv.header", list(rows[0].keys()),
    ["dataset", "uuid", "record_index", "frame_index", "offset_s", "side", "reason_code", "reason"])
chk("csv.n_rows", len(rows), 841)

# 2 frames / events / empty
frames = {(r["uuid"], int(r["frame_index"])) for r in rows}
chk("unique_bad_frames", len(frames), J["composition"]["total_bad_frames"])
chk("empty_reason_frames", J["composition"]["empty_reason_frames"],
    J["composition"]["total_bad_frames"] - J["composition"]["resolvable_bad_frames"])
chk("events=rows", len(rows), J["composition"]["total_bad_frame_side_events"])

# 3 composition table
c = collections.Counter((r["dataset"], r["side"], r["reason"]) for r in rows)
for t in J["composition"]["table_total"]:
    chk("comp.ALL.%s.%s" % (t["side"], t["reason"]), c[("EgoPro", t["side"], t["reason"])] +
        c[("EgoStandard", t["side"], t["reason"])], t["n"])
chk("sum_cells", sum(c.values()), 841)
for ds in ("EgoPro", "EgoStandard"):
    d = J["composition"]["by_dataset"][ds]
    chk("%s.n_bad_frames" % ds, len({(r["uuid"], int(r["frame_index"])) for r in rows if r["dataset"] == ds}),
        d["n_bad_frames"])
    chk("%s.n_events" % ds, len([r for r in rows if r["dataset"] == ds]), d["n_events"])

chk("bad_frame_rate", J["composition"]["bad_frame_rate"],
    len(frames) / J["composition"]["total_frames_scanned"], 1e-12)
chk("frame_reason_sets.sum", sum(x["n_frames"] for x in J["composition"]["frame_reason_sets"]), 720)
_of = collections.defaultdict(set)
for r in rows:
    _of[(r["uuid"], int(r["frame_index"]))].add(r["reason"])
chk("frames_with_occlusion", J["composition"]["frames_with_occlusion"],
    sum(1 for v in _of.values() if "occlusion" in v))
chk("frames_with_near_edge", J["composition"]["frames_with_near_edge"],
    sum(1 for v in _of.values() if "near edge" in v))

# 4 thirds (frame level + event level + per dataset + per side/reason)
def thirds(fracs):
    n = len(fracs)
    c1 = sum(1 for x in fracs if x < 1 / 3)
    c2 = sum(1 for x in fracs if 1 / 3 <= x < 2 / 3)
    return n, c1, c2, n - c1 - c2

ev_frac = [float(r["offset_s"]) / recs[r["uuid"]]["duration_s"] for r in rows]
n, a, b, d3 = thirds(ev_frac)
t = J["time_within_record"]["overall"]
chk("thirds.events.n", t["n"], n); chk("thirds.events.first", t["first_third"], a)
chk("thirds.events.middle", t["middle_third"], b); chk("thirds.events.last", t["last_third"], d3)

fr_frac = [float(r["offset_s"]) / recs[r["uuid"]]["duration_s"]
           for r in {(r["uuid"], r["frame_index"]): r for r in rows}.values()]
n, a, b, d3 = thirds(fr_frac)
t = J["time_within_record"]["frame_level"]
chk("thirds.frames.n", t["n"], n); chk("thirds.frames.first", t["first_third"], a)
chk("thirds.frames.middle", t["middle_third"], b); chk("thirds.frames.last", t["last_third"], d3)

for ds in ("EgoPro", "EgoStandard"):
    f = [float(r["offset_s"]) / recs[r["uuid"]]["duration_s"] for r in rows if r["dataset"] == ds]
    n, a, b, d3 = thirds(f)
    t = J["time_within_record"]["by_dataset"][ds]
    chk("thirds.%s.n" % ds, t["n"], n); chk("thirds.%s.last" % ds, t["last_third"], d3)

for key, t in J["time_within_record"]["by_side_reason"].items():
    s, rr = key.split(":", 1)
    f = [float(r["offset_s"]) / recs[r["uuid"]]["duration_s"]
         for r in rows if r["side"] == s and r["reason"] == rr]
    n, a, b, d3 = thirds(f)
    chk("thirds.%s.n" % key, t["n"], n); chk("thirds.%s.first" % key, t["first_third"], a)
    chk("thirds.%s.middle" % key, t["middle_third"], b); chk("thirds.%s.last" % key, t["last_third"], d3)

# 5 boundary: pooled from per_record
bv = J["boundary_vs_interior"]["primary_all_interior_boundaries_w05"]
pr = bv["per_record"]
chk("bound.n", bv["n_bad_frames"], sum(x["n_bad"] for x in pr))
chk("bound.k", bv["k_in_window"], sum(x["k_in_window"] for x in pr))
chk("bound.base_rate", bv["base_rate"], sum(x["window_s"] for x in pr) / sum(x["duration_s"] for x in pr), 1e-12)
chk("bound.frac", bv["frac_in_window"], bv["k_in_window"] / bv["n_bad_frames"], 1e-12)
chk("bound.ratio", bv["ratio_obs_over_base"], bv["frac_in_window"] / bv["base_rate"], 1e-9)
chk("bound.p_greater", bv["binom"]["p_greater"],
    float(binomtest(bv["k_in_window"], bv["n_bad_frames"], bv["base_rate"], alternative="greater").pvalue), 1e-12)

# recompute k directly from CSV + interior boundaries
def rec_k(rec, w):
    bs = rec["interior_boundaries"]
    rr = {r["frame_index"]: float(r["offset_s"]) for r in rows if r["uuid"] == rec["uuid"]}
    return sum(1 for fi, off in rr.items() if any(abs(off - b) <= w for b in bs)), len(rr)

bad = 0
for rec in J["records"]:
    k, n = rec_k(rec, 0.5)
    prm = next(x for x in pr if x["uuid"] == rec["uuid"])
    if k != prm["k_in_window"] or n != prm["n_bad"]:
        bad += 1
chk("bound.recompute_from_csv_per_record", bad, 0)

# by reason
for key, v in J["boundary_vs_interior"]["by_reason_w05"].items():
    s, rr = key.split(":", 1)
    k = 0
    n = 0
    for r in rows:
        if r["side"] == s and r["reason"] == rr:
            n += 1
            bs = recs[r["uuid"]]["interior_boundaries"]
            if any(abs(float(r["offset_s"]) - b) <= 0.5 for b in bs):
                k += 1
    chk("byreason.%s.k" % key, v["k_in_window"], k)
    chk("byreason.%s.n" % key, v["n_events"], n)

# 6 alignment + reason codes
chk("alignment.all_rows_equal", J["alignment_check"]["rows_equal_all_records"], True)
chk("alignment.n_records", J["alignment_check"]["n_records_checked"], 38)
chk("reason.numeric_slots", J["reason_code_resolution"]["numeric_enum_codes_found_in_problem_type_slots"], 0)
chk("reason.slot_combo_sum",
    sum(x["n_rows"] for x in J["reason_code_resolution"]["slot_combinations"]), 720)
chk("records.with_bad", J["composition"]["records_with_bad_frames"], 17)

# 7 every CSV row must carry a resolvable side/reason
chk("csv.no_empty_reason", sum(1 for r in rows if not r["reason"]), 0)
chk("csv.no_unknown_side", sum(1 for r in rows if r["side"] == "unknown"), 0)

print()
print("VERDICT:", "ALL PASS" if not fails else ("%d FAIL: %s" % (len(fails), fails)))
sys.exit(0 if not fails else 1)