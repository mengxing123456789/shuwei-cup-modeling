# -*- coding: utf-8 -*-
"""Register the mapping-spread slots and the honest-negative slots.

Anchors are literal lines that already exist in code/fill_numbers.py, so the patch is
idempotent: running it twice inserts nothing the second time.
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FN = ROOT / "code" / "fill_numbers.py"

ANCHOR = 'add(f"PMap{tag}{lab}", "p3_stochastic_schedule", ["mapping_sensitivity",'

BLOCK = '''
# --- five-mapping spread (up22) ---------------------------------------------
for _case, _tag in (("S2", "STwo"), ("S3", "SThree")):
    add(f"PMapRefSpan{_tag}", "up22_mapping_spread", ["cases", _case, "ref_span_pt"], "f1")
    add(f"PMapOursSpan{_tag}", "up22_mapping_spread", ["cases", _case, "ours_span_pt"], "f1")
    add(f"PMapGainMin{_tag}", "up22_mapping_spread", ["cases", _case, "gain_min_pt"], "f1")
    add(f"PMapGainMax{_tag}", "up22_mapping_spread", ["cases", _case, "gain_max_pt"], "f1")
    add(f"PMapGainMean{_tag}", "up22_mapping_spread", ["cases", _case, "gain_mean_pt"], "f1")
    add(f"PMapSat{_tag}", "up22_mapping_spread", ["cases", _case, "n_saturated"], "int")

# --- the three marks that were missed (honest negatives) --------------------
add("PRevNTested", "up_p3_review", ["verdict", "n_tested"], "int")
add("PRevNPass", "up_p3_review", ["verdict", "n_ge_1pt"], "int")
add("PRevBest", "up_p3_review", ["verdict", "best_delta_pt"], "f2")
add("PRevWorst", "up_p3_review", ["verdict", "min_delta_pt"], "f2")
add("PRevFired", "up_p3_review", ["verdict", "n_cells_review_fired"], "int")
add("PRevThreshold", "up_p3_review", ["verdict", "threshold_pt"], "f1")
add("PQuantLThirtyRMSE", "up_p2_final", ["aggregate", "L30", "rmse_3d_cm", "mean"], "f2")
add("PQuantLThirtyQ90", "up_p2_final", ["aggregate", "L30", "q90_cm", "mean"], "f2")
add("PQuantLThirtyCoverage", "up_p2_final", ["aggregate", "L30", "coverage_test", "mean"], "f3")
add("PQuantLSixRMSE", "up_p2_final", ["aggregate", "L6", "rmse_3d_cm", "mean"], "f2")
'''


def main():
    apply = "--apply" in sys.argv
    t = io.open(FN, encoding="utf-8").read()
    if "up22_mapping_spread" in t:
        print("already patched")
        return 0
    i = t.find(ANCHOR)
    if i < 0:
        print("ANCHOR MISSING")
        return 1
    t = t[:i] + BLOCK.lstrip("\n") + "\n" + t[i:]
    print("inserted", len(BLOCK), "chars before the mapping_sensitivity block")
    if not apply:
        print("dry run; pass --apply")
        return 0
    io.open(FN, "w", encoding="utf-8", newline="\n").write(t)
    print("written", FN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
