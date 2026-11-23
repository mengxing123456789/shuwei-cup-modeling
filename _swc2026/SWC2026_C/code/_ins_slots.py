
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import io, pathlib
p = pathlib.Path(r"code\fill_numbers.py")
s = p.read_text(encoding="utf-8")
anchor = 'add("PSegTestRecords", "p1_segmentation", ["_meta", "records"], "int")\n'
assert anchor in s, "anchor missing"
block = anchor + '''
# P1-a learned boundary detector (GPU) — decoding constants chosen on validation only
add("PSegGPUARI", "p1a_gpu_segmentation", ["test", "mean_ari"], "f4")
add("PSegGPUFOne", "p1a_gpu_segmentation", ["test", "mean_f1"], "f4")
add("PSegGPUStdARI", "p1a_gpu_segmentation", ["test", "std_ari"], "f4")
add("PSegGPUBFOne", "p1a_gpu_segmentation", ["test", "mean_boundary_f1"], "f4")
add("PSegGPUBMae", "p1a_gpu_segmentation", ["test", "mean_boundary_mae"], "f3")
add("PSegGPUParams", "p1a_gpu_segmentation", ["_meta", "params"], "int")
add("PSegGPUSeconds", "p1a_gpu_segmentation", ["_meta", "fit_seconds"], "f1")
add("PSegGPUValARI", "p1a_gpu_segmentation", ["_meta", "val_mean_ari"], "f4")
add("PSegGPUHeight", "p1a_gpu_segmentation", ["_meta", "height"], "f2")
add("PSegGPUDistance", "p1a_gpu_segmentation", ["_meta", "distance"], "int")
for _ds, _tag in (("EgoDemo", "Demo"), ("EgoPro", "Pro"), ("EgoStandard", "Std")):
    add("PSegGPUBy" + _tag, "p1a_gpu_segmentation", ["by_dataset", _ds], "f4")

# P3 adaptive-quantile reservation search: first 15 seeds select, last 15 hold out
add("PImpNCandidates", "p3_improved_search", ["_meta", "candidate_count"], "int")
add("PImpSeconds", "p3_improved_search", ["seconds"], "f1")
add("PImpMixedAllDelta", "p3_improved_search", ["mixed_policy", "all30_delta_mean"], "f4")
add("PImpMixedAllCI", "p3_improved_search", ["mixed_policy", "all30_delta_ci95"], "f4")
add("PImpMixedHoldDelta", "p3_improved_search", ["mixed_policy", "holdout_delta_mean"], "f4")
add("PImpMixedHoldCI", "p3_improved_search", ["mixed_policy", "holdout_delta_ci95"], "f4")
for _case, _tag in (("S2", "STwo"), ("S3", "SThree")):
    add("PImp" + _tag + "AllMean", "p3_improved_search", ["evidence", _case, "all30", "delta_mean"], "f4")
    add("PImp" + _tag + "AllCI", "p3_improved_search", ["evidence", _case, "all30", "delta_ci95"], "f4")
    add("PImp" + _tag + "AllCand", "p3_improved_search", ["evidence", _case, "selected_all30_mean"], "f4")
    add("PImp" + _tag + "AllBase", "p3_improved_search", ["evidence", _case, "baseline_all30_mean"], "f4")
    add("PImp" + _tag + "AllComp", "p3_improved_search", ["evidence", _case, "all30", "delta_completion_mean"], "f4")
    add("PImp" + _tag + "HoldDelta", "p3_improved_search", ["evidence", _case, "holdout", "delta_mean"], "f4")
    add("PImp" + _tag + "HoldCI", "p3_improved_search", ["evidence", _case, "holdout", "delta_ci95"], "f4")
'''
p.write_text(s.replace(anchor, block, 1), encoding="utf-8", newline="\n")
print("inserted slots; file now", len(block), "chars added")
