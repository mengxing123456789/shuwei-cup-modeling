import re
s=open(r"E:\数学建模\_swc2026\SWC2026_A\main.log",encoding="utf-8",errors="ignore").read()
print("UNDEFINED:", len(re.findall(r"Reference .* undefined", s)))
print("CITATIONS:", len(re.findall(r"Citation .* undefined", s)))
ov=[l for l in s.splitlines() if "Overfull" in l]
print("OVERFULL:", len(ov)); [print(" ",x[:120]) for x in ov[:12]]
print("PAGES:", re.findall(r"Output written on .*?\((\d+) pages", s)[-1:])
