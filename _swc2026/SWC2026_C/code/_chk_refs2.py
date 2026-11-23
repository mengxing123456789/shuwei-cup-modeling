import os
import json
import pathlib
import sys

ROOT = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT = ROOT.parent / "audit"
parts = []
for pat in ("code/*.py", "tables/*.tex", "*.tex", "snippets/*"):
    parts += [p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.glob(pat)]
parts += [p.read_text(encoding="utf-8", errors="ignore") for p in AUDIT.glob("*.py")]
text = "\n".join(parts)

cands = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")) if len(sys.argv) > 1 else []
names = """p1a_gpu_segmentation.prev.json
p1a_gpu_segmentation.rerun20261122.json
p1a_gpu_segmentation_final.prev.json
p2_improved_gpu_L30.json
p2_improved_gpu_L30b.json
p2_improved_gpu_smoke.json
p2_interval.bak_quadbranch.json
p2_masked_v1_valk3.json
phase_identifiability.bak_probs20261120.json
phase_identifiability2.bak_probs20261120.json
phase_null_check.bak_probs20261120.json
results_swc2026.json
uncertainty_consistency.json
uncertainty_reliability.json
uncertainty_smoke.json
up13_p1a_anchor_palm.json
up13_p1a_anchor_tips.json
up13_p1b_anchor_palm.json
up13_p1b_anchor_tips.json
up13_p1b_anchor_wrist.json
up2_p1a_train_mtask.json
up2_p1a_train_smoke.json
up2_p1a_train_sslmtask.json
up2_p2_armA.json
up2_p2_armB.json
up2_p2_armC.json
video_features_part000_006.csv
video_features_part124_184.csv""".split()

for n in names:
    stem = n.rsplit(".", 1)[0]
    full_hit = n in text
    stem_hit = stem in text
    print(f"{n:52s} full={full_hit!s:5s} stem={stem_hit!s:5s}")