"""Make the plateau claim exactly true: measure the wiggles, expose them, and stop
saying "monotone".  Patches the JSON, fill_numbers, main.tex and verify_claims in one
atomic pass (all assertions first, then a single write each)."""
import io
import json
import os

C = r"E:\数学建模\_swc2026\SWC2026_C"
J = os.path.join(C, "data", "p3_quantile_curve.json")
FN = os.path.join(C, "code", "fill_numbers.py")
TEX = os.path.join(C, "main.tex")
VC = r"E:\数学建模\_swc2026\audit\verify_claims.py"

# ---- 1. measure -----------------------------------------------------------
d = json.load(io.open(J, encoding="utf-8"))
wig = 0.0
for c in ("S2", "S3"):
    t = [float(x) for x in d["cases"][c]["tune_curve"]]
    for a, b in zip(t, t[1:]):
        wig = max(wig, b - a)
wig_pts = round(wig * 100.0, 2)
d["_meta"]["max_wiggle_points"] = wig_pts
d["_meta"]["max_wiggle_definition"] = (
    "largest increase between adjacent grid points of the tuning curve, in "
    "percentage points; the trend is decreasing but not strictly monotone")
print("max wiggle (points):", wig_pts)

# ---- 2. slot --------------------------------------------------------------
fn = io.open(FN, encoding="utf-8").read()
anchor = '    add("PQHoldHighSThree", "p3_quantile_curve", ["cases", "S3", "holdout_curve"], "f4")'
if anchor not in fn:
    anchor = [ln for ln in fn.splitlines() if "PQHoldHighSThree" in ln][0]
assert fn.count(anchor) == 1, "anchor for PQHoldHighSThree is ambiguous"
assert '"PQWiggleMax"' not in fn, "slot already present"
new_line = (
    '    add("PQWiggleMax", "p3_quantile_curve", ["_meta", "max_wiggle_points"], "f2")\n'
)
fn2 = fn.replace(anchor, anchor + "\n" + new_line.rstrip("\n"))

# ---- 3. sentence ----------------------------------------------------------
tex = io.open(TEX, encoding="utf-8").read()
old = ("seeds, the on-time rate falls monotonically: \\slotPQTuneLowSTwo{} to")
new = ("seeds, the on-time rate falls with the level, by no more than "
       "\\slotPQWiggleMax{} points of local reversal: \\slotPQTuneLowSTwo{} to")
assert tex.count(old) == 1, ("sentence", tex.count(old))
tex2 = tex.replace(old, new)

# ---- 4. assertion ---------------------------------------------------------
vc = io.open(VC, encoding="utf-8").read()
old_chk = '''    _tc = [float(x) for x in _q["cases"]["S2"]["tune_curve"]]
    _mono = all(b <= a + 1e-12 for a, b in zip(_tc, _tc[1:]))
    check("S2 调优曲线随 q 单调不增（过度预留是失效模式）", _mono,
          "tune_curve S2 monotone non-increasing", True, _mono)'''
new_chk = '''    _tc = [float(x) for x in _q["cases"]["S2"]["tune_curve"]]
    _tc3 = [float(x) for x in _q["cases"]["S3"]["tune_curve"]]
    _argmax_left = (max(_tc) == _tc[0]) and (max(_tc3) == _tc3[0])
    check("两个 case 的调优曲线最大值都落在网格左端（而非内部最优点）", _argmax_left,
          f"S2 argmax={_tc.index(max(_tc))} S3 argmax={_tc3.index(max(_tc3))}", 0, 0)
    _wig = max([b - a for a, b in zip(_tc, _tc[1:])] +
               [b - a for a, b in zip(_tc3, _tc3[1:])])
    check("调优曲线的局部回升不超过 2 个百分点", _wig <= 0.02 + 1e-12,
          f"max rise={_wig*100:.2f} points", "<= 2 points", round(_wig * 100, 2))
    _drop = min(max(_tc) - _tc[-1], max(_tc3) - _tc3[-1])
    check("从网格左端到右端至少掉 10 个百分点", _drop >= 0.10,
          f"min drop={_drop*100:.2f} points", ">= 10 points", round(_drop * 100, 2))'''
assert vc.count(old_chk) == 1, ("assertion block", vc.count(old_chk))
vc2 = vc.replace(old_chk, new_chk)

# ---- 5. commit ------------------------------------------------------------
io.open(J, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2))
io.open(FN, "w", encoding="utf-8", newline="\n").write(fn2)
io.open(TEX, "w", encoding="utf-8", newline="\n").write(tex2)
io.open(VC, "w", encoding="utf-8", newline="\n").write(vc2)
print("written: json/fill_numbers/main.tex/verify_claims")