# AI 辅助：DeepSeek Harness 助手生成的一次性补丁：为零假设表补百分比标量，并给 fill_numbers 加可辨识性槽位。
# -*- coding: utf-8 -*-
import json
import pathlib
import re

D = pathlib.Path(__file__).resolve().parent.parent / "data"
p = D / "phase_null_check.json"
d = json.loads(p.read_text(encoding="utf-8"))
d["share_pos_ge_half_p2_pct"] = round(100 * d["share_pos_ge_half_p2"], 1)
d["share_neg_ge_half_p2_pct"] = round(100 * d["share_neg_ge_half_p2"], 1)
p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("pct:", d["share_pos_ge_half_p2_pct"], d["share_neg_ge_half_p2_pct"])

F = pathlib.Path(__file__).resolve().parent / "fill_numbers.py"
src = F.read_text(encoding="utf-8")
anchor = 'add("POracleGapSThreeCI", "p3_oracle_same_rule", ["cases", "S3", "gap_ci95"], "f4")'
assert anchor in src, "anchor missing"
block = anchor + """

# --- P1-a boundary identifiability: separation does not predict detection (phase_identifiability2 / _null_check)
add("PIdNBound", "phase_identifiability2", ["summary", "n_boundaries"], "d")
add("PIdSpearmanMax", "phase_identifiability2", ["summary", "max_abs_spearman"], "f3")
add("PIdMinP", "phase_identifiability2", ["summary", "min_p"], "f2")
add("PIdAucTwo", "phase_null_check", ["auc_at_2_frames"], "f3")
add("PIdMeanTrue", "phase_null_check", ["mean_pos_p2"], "f3")
add("PIdMeanNull", "phase_null_check", ["mean_neg_p2"], "f3")
add("PIdTrueHalf", "phase_null_check", ["share_pos_ge_half_p2_pct"], "f1")
add("PIdNullHalf", "phase_null_check", ["share_neg_ge_half_p2_pct"], "f1")"""
src = src.replace(anchor, block, 1)
F.write_text(src, encoding="utf-8", newline="\n")
print("slots added: PIdNBound..PIdNullHalf (8)")