import re
import pathlib

txt = pathlib.Path(r"code\fill_numbers.py").read_text(encoding="utf-8")
names = set(re.findall(r'"([A-Za-z0-9_.]+\.(?:json|csv|npz))"', txt))
for n in ("results_swc2026.json", "video_features_part000_006.csv", "uncertainty_consistency.json",
          "uncertainty_reliability.json", "up2_p2_armA.json", "p2_masked_v1_valk3.json",
          "up13_p1a_anchor_palm.json", "up13_p1b_anchor_wrist.json"):
    print(n, n in names)
print("fill_numbers sources:", len(names))
