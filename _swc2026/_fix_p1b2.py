import py_compile, os

dst = r"E:\数学建模\_swc2026\SWC2026_C\code\p1b_calib.py"
t = open(dst, encoding="utf-8").read()
anchor = "    for env in sorted(set(Ete)):"
assert anchor in t
if 'res["calibration"]=calib' not in t:
    t = t.replace(anchor, '    res["calibration"]=calib\n' + anchor, 1)
open(dst, "w", encoding="utf-8", newline="\n").write(t)
py_compile.compile(dst, doraise=True)
print("res[calibration] present:", 'res["calibration"]=calib' in t)
print("block before res:", t.index("calibration block") < t.index("    res = {"))
p = r"E:\数学建模\_swc2026\SWC2026_C\data\p1b_probs.npz"
print("npz exists:", os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0)