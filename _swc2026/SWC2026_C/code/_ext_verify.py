
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Add the P1-a learned-detector and P3 adaptive-quantile claims to verify_numbers.py."""
import pathlib

p = pathlib.Path(r"code\verify_numbers.py")
s = p.read_text(encoding="utf-8")
anchor = "# figures\n"
assert anchor in s, "anchor missing"
block = '''# P1-a learned boundary detector (decoding constants chosen on validation only)
gpu = J("p1a_gpu_segmentation.json")
chk(abs(gpu["test"]["mean_ari"] - 0.5121381578780307) < 1e-9, "P1a learned detector test ARI reproduced")
chk(gpu["test"]["mean_ari"] > gpu["baseline_ward_ari"], "P1a learned detector beats the agglomeration baseline")
chk(gpu["_meta"]["height"] == 0.45 and gpu["_meta"]["distance"] == 55, "P1a decoding constants as reported")
chk(gpu["_meta"]["val_mean_ari"] > 0, "P1a selection value came from validation records")
chk(gpu["test"]["records"] == 7, "P1a test record count")
chk(abs(sum(gpu["by_dataset"].values()) / 3 - gpu["test"]["mean_ari"]) < 0.02,
    "P1a by-dataset averages bracket the pooled average")
chk(min(gpu["by_dataset"].values()) > 0, "P1a every source dataset has a positive ARI")

# P3 adaptive-quantile reservation search (first 15 seeds select, last 15 held out)
pimp = J("p3_improved_search.json")
chk(pimp["_meta"]["candidate_count"] == 121, "P3 search candidate count")
for c in ("S2", "S3"):
    e = pimp["evidence"][c]
    chk(e["verdict"]["usable_improvement"], f"P3 {c} verdict: usable improvement")
    chk(e["all30"]["delta_mean"] > 0, f"P3 {c} all-30 gain positive")
    chk(e["holdout"]["delta_mean"] > 0, f"P3 {c} hold-out gain positive")
    chk(abs(e["selected_all30_mean"] - e["baseline_all30_mean"] - e["all30"]["delta_mean"]) < 1e-9,
        f"P3 {c} selected minus baseline equals the paired mean")
    chk(e["all30"]["cand_mean"] >= e["all30"]["base_mean"], f"P3 {c} candidate not worse on completion")
mp = pimp["mixed_policy"]
chk(mp["all30_delta_mean"] > mp["all30_delta_ci95"], "P3 mixed all-30 interval excludes zero")
chk(mp["holdout_delta_mean"] > mp["holdout_delta_ci95"], "P3 mixed hold-out interval excludes zero")
chk(len(mp["per_seed_delta"]) == 30, "P3 mixed policy averaged over 30 seeds")

'''
p.write_text(s.replace(anchor, block + anchor, 1), encoding="utf-8", newline="\n")
print("verify_numbers.py extended")