"""Add derived percentage fields to the two new JSONs and the matching slots."""
import io
import json
import os

C = r"E:\数学建模\_swc2026\SWC2026_C"
FN = os.path.join(C, "code", "fill_numbers.py")

# ---- 1. derived fields ----------------------------------------------------
p = os.path.join(C, "data", "p1_badtype.json")
d = json.load(io.open(p, encoding="utf-8"))
c = d["composition"]
der = {
    "bad_frame_rate_pct": round(100.0 * c["bad_frame_rate"], 2),
    "occlusion_share_pct": round(100.0 * c["frames_with_occlusion"] / c["total_bad_frames"], 2),
    "near_edge_share_pct": round(100.0 * c["frames_with_near_edge"] / c["total_bad_frames"], 2),
    "boundary_obs_pct": round(100.0 * d["boundary_vs_interior"]["primary_all_interior_boundaries_w05"]["frac_in_window"], 2),
    "boundary_base_pct": round(100.0 * d["boundary_vs_interior"]["primary_all_interior_boundaries_w05"]["base_rate"], 2),
}
d["_derived"] = der
d["_derived_note"] = ("percentages derived from composition and boundary_vs_interior; "
                      "nothing else in this file is modified")
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2))
print("badtype derived:", der)

# ---- 2. slots ------------------------------------------------------------
fn = io.open(FN, encoding="utf-8").read()
anchor = 'add("PIdNullHalf", "phase_null_check", ["share_neg_ge_half_p2_pct"], "f1")'
assert fn.count(anchor) == 1, "anchor missing or ambiguous"

BT = [
    ("PBTBadFrames", "p1_badtype", ["composition", "total_bad_frames"], "int"),
    ("PBTBadEvents", "p1_badtype", ["composition", "total_bad_frame_side_events"], "int"),
    ("PBTBadRatePct", "p1_badtype", ["_derived", "bad_frame_rate_pct"], "f2"),
    ("PBTOcclPct", "p1_badtype", ["_derived", "occlusion_share_pct"], "f2"),
    ("PBTNearPct", "p1_badtype", ["_derived", "near_edge_share_pct"], "f2"),
    ("PBTEventRight", "p1_badtype", ["composition", "side_totals", "right"], "int"),
    ("PBTEventLeft", "p1_badtype", ["composition", "side_totals", "left"], "int"),
    ("PBTBndObsPct", "p1_badtype", ["_derived", "boundary_obs_pct"], "f2"),
    ("PBTBndBasePct", "p1_badtype", ["_derived", "boundary_base_pct"], "f2"),
    ("PBTBndRatio", "p1_badtype", ["boundary_vs_interior", "primary_all_interior_boundaries_w05", "ratio_obs_over_base"], "f3"),
    ("PBTBndP", "p1_badtype", ["boundary_vs_interior", "primary_all_interior_boundaries_w05", "binom", "p_greater"], "f3"),
    ("PBTBndSignP", "p1_badtype", ["boundary_vs_interior", "primary_all_interior_boundaries_w05", "cluster", "sign_test_p"], "f3"),
    ("PBTRecsWithBad", "p1_badtype", ["composition", "records_with_bad_frames"], "int"),
    ("PBTRecsTotal", "p1_badtype", ["composition", "records_total"], "int"),
]
LT = [
    ("PLotoMean", "p1b_loto", ["summary", "mean_auc_loto"], "f4"),
    ("PLotoRef", "p1b_loto", ["summary", "mean_auc_in_sample_reference"], "f4"),
    ("PLotoGap", "p1b_loto", ["summary", "gap_mean"], "f4"),
    ("PLotoFrac", "p1b_loto", ["summary", "frac_unseen_task_gap_explained"], "f3"),
    ("PLotoNEval", "p1b_loto", ["summary", "n_classes_used"], "int"),
    ("PLotoNSkip", "p1b_loto", ["summary", "n_classes_skipped"], "int"),
    ("PLotoNClass", "p1b_loto", ["summary", "n_train_classes"], "int"),
]
lines = ["", "# --- annotated bad frames: what the flags actually contain (p1_badtype) ---"]
lines += ['add("%s", "%s", %r, "%s")' % (n, j, pth, f) for n, j, pth, f in BT]
lines.append("")
lines.append("# --- leave-one-task-out: the price of an unseen task class (p1b_loto) ---")
lines += ['add("%s", "%s", %r, "%s")' % (n, j, pth, f) for n, j, pth, f in LT]
block = "\n".join(lines)
assert "PBTBadFrames" not in fn, "already inserted"
io.open(FN, "w", encoding="utf-8", newline="\n").write(fn.replace(anchor, anchor + block))
print("slots added:", len(BT) + len(LT))