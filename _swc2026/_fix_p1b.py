import py_compile, re, sys

dst = r"E:\数学建模\_swc2026\SWC2026_C\code\p1b_calib.py"
t = open(dst, encoding="utf-8").read()

start_mark = "    # --- calibration block (added): raw vs temperature-scaled ---"
end_mark = 'np.savez(os.path.join(DATA,"p1b_probs.npz"),pt=pt,pcal=pcal,yte=yte,env=Ete)'
i = t.index(start_mark)
j = t.index(end_mark) + len(end_mark)
block = t[i:j]
t = t[:i] + t[j:]
t = t.replace('    res["calibration"]=calib\n', '', 1)

anchor = "    res = {"
assert anchor in t
t = t.replace(anchor, block + "\n\n" + anchor, 1)
open(dst, "w", encoding="utf-8", newline="\n").write(t)
py_compile.compile(dst, doraise=True)

L = t.split("\n")
for k, line in enumerate(L, 1):
    if "calib" in line or "res = {" in line or "pt = torch.sigmoid" in line:
        print(k, ":", line.strip()[:110])
print("OK")