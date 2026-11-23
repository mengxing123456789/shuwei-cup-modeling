from pathlib import Path

p = Path(r"E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py")
t = p.read_text(encoding="utf-8")

old_gru = '_gru = {k: float(RAW["PGPU" + k + suf]) for k, suf in'
new_gru = '_gru = {k: float(RAW["PGPU" + k + suf]) * 100.0 for k, suf in'
old_rdg = '_rdg = {k: float(RAW["PTwo" + k + "RidgeRMSE"]) for k in "ABCD"}'
new_rdg = '_rdg = {k: float(RAW["PTwo" + k + "RidgeRMSE"]) * 100.0 for k in "ABCD"}'

assert t.count(old_gru) == 1
assert t.count(old_rdg) == 1
t = t.replace(old_gru, new_gru).replace(old_rdg, new_rdg)
p.write_text(t, encoding="utf-8", newline="\n")
print("patched to centimetres")
