"""Derived scalars + slots for the cost-threshold experiment."""
import io
import json
import os

C = r"E:\数学建模\_swc2026\SWC2026_C"
J = os.path.join(C, "data", "p1b_cost_threshold.json")
FN = os.path.join(C, "code", "fill_numbers.py")

d = json.load(io.open(J, encoding="utf-8"))
rows = d["rows"]
by_r = {round(r["ratio"], 4): r for r in rows}
r1 = by_r[1.0]
r001 = by_r[0.01]
der = {
    "ratio_min": d["_meta"]["ratios"][0],
    "ratio_max": d["_meta"]["ratios"][-1],
    "cost_keep_all_at_r1": r1["test_cost"],
    "cost_drop_all_at_r001": r001["test_cost"],
    "cost_half_raw_at_r1": r1["cost_raw_at_half"],
    "cost_half_platt_at_r1": r1["cost_platt_at_half"],
    "half_rule_multiple": round(r1["cost_raw_at_half"] / r1["test_cost"], 1),
    "n_interior_optima": 0,
    "n_ratios": len(rows),
    "interior_rule": ("no row selected an interior tau: at ratio >= 0.05 the minimum is "
                      "keep-everything, at ratio 0.01 it is drop-everything"),
}
d["_derived"] = der
io.open(J, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2))
print("derived:", der)

fn = io.open(FN, encoding="utf-8").read()
anchor = "add(\"PLotoNClass\", \"p1b_loto\", ['summary', 'n_train_classes'], \"int\")"
assert fn.count(anchor) == 1, "anchor missing"
SLOTS = [
    ("PCostRatioLow", ["_derived", "ratio_min"], "f2"),
    ("PCostRatioHigh", ["_derived", "ratio_max"], "f2"),
    ("PCostKeepAll", ["_derived", "cost_keep_all_at_r1"], "f5"),
    ("PCostDropAll", ["_derived", "cost_drop_all_at_r001"], "f5"),
    ("PCostHalfRaw", ["_derived", "cost_half_raw_at_r1"], "f5"),
    ("PCostHalfPlatt", ["_derived", "cost_half_platt_at_r1"], "f5"),
    ("PCostHalfMult", ["_derived", "half_rule_multiple"], "f1"),
    ("PCostAUC", ["auc_by_transform", "raw"], "f4"),
    ("PCostNVal", ["n_validation"], "int"),
    ("PCostNTest", ["n_test"], "int"),
]
block = "\n\n# --- keep/drop is a threshold decision, not a calibration problem (p1b_cost_threshold)\n" + "\n".join(
    'add("%s", "p1b_cost_threshold", %r, "%s")' % (n, p, f) for n, p, f in SLOTS)
assert "PCostRatioLow" not in fn
io.open(FN, "w", encoding="utf-8", newline="\n").write(fn.replace(anchor, anchor + block))
print("slots added:", len(SLOTS))