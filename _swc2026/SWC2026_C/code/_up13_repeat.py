"""Determinism check: rerun P1-a on the wrist shadow dir and compare with the
first run.  If the two runs disagree, the pipeline is not seed-stable and the
anchor table's deltas cannot be attributed to the anchor."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p1a_gpu_segmentation as M  # noqa: E402

SH = os.path.join(os.path.dirname(HERE), "data", "shadow_anchor_wrist")
M.DATA = SH
M.MODELS = os.path.join(SH, "models_rep")
os.makedirs(M.MODELS, exist_ok=True)
sys.argv = ["p1a", "--seeds", "3", "--epochs", "40"]
M.main()

j = json.load(open(os.path.join(SH, "p1a_gpu_segmentation.json"), encoding="utf-8"))
first = json.load(open(os.path.join(os.path.dirname(HERE), "data",
                                    "up13_p1a_anchor_wrist.json"), encoding="utf-8"))
row = dict(height=j["_meta"]["height"], distance=j["_meta"]["distance"],
           val=j["_meta"]["val_mean_ari"], ari=j["test"]["mean_ari"],
           bf1=j["test"]["mean_boundary_f1"])
row0 = dict(height=first["_meta"]["height"], distance=first["_meta"]["distance"],
            val=first["_meta"]["val_mean_ari"], ari=first["test"]["mean_ari"],
            bf1=first["test"]["mean_boundary_f1"])
print("FIRST", row0)
print("REPEAT", row)
print("IDENTICAL", row == row0)
out = os.path.join(os.path.dirname(HERE), "data", "up13_repeat_check.json")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump(dict(first=row0, repeat=row, identical=row == row0), f, indent=1)
print("wrote", out)
