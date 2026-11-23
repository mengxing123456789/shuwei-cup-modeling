import pathlib

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\main.tex")
lines = P.read_text(encoding="utf-8").splitlines()
for i, ln in enumerate(lines, 1):
    if "Three answers, one per question" in ln:
        for j in range(i - 1, min(i + 16, len(lines))):
            print(f"{j+1:5d} {lines[j]}")
        break