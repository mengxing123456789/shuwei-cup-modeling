"""Reference scan that excludes the scanners themselves.

Both ``quarantine_superseded.py`` and this probe name artefacts in their own
source, so a naive ``code/*.py`` haystack reports every candidate as
"referenced".  Excluding the two scanner files (and anything starting with an
underscore) is what makes the scan honest.
"""
import os
import pathlib

ROOT = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT = ROOT.parent / "audit"
SELF = {"quarantine_superseded.py", "_chk_refs.py", "_chk_refs2.py", "_chk_refs3.py"}

parts = []
for p in ROOT.glob("code/*.py"):
    if p.name in SELF or p.name.startswith("_"):
        continue
    parts.append(p.read_text(encoding="utf-8", errors="ignore"))
for pat in ("tables/*.tex", "*.tex"):
    parts += [p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.glob(pat)]
for p in AUDIT.glob("*.py"):
    parts.append(p.read_text(encoding="utf-8", errors="ignore"))
text = "\n".join(parts)
print("haystack chars:", len(text))

NAMES = """p1a_gpu_segmentation.prev.json
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

for n in NAMES:
    stem = n.rsplit(".", 1)[0]
    print(f"{n:50s} full={n in text!s:5s} stem={stem in text!s:5s}")