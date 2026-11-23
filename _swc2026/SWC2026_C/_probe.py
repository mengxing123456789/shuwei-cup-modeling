import pathlib
import pymupdf
import re

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C")
doc = pymupdf.open(str(P / "main.pdf"))
print("pages", doc.page_count)
for i in (24, 25, 26):
    if i < doc.page_count:
        print(f"p{i+1} chars", len(doc[i].get_text()))

lines = (P / "main.tex").read_text(encoding="utf-8").splitlines()
for i, ln in enumerate(lines, 1):
    if "temporal route shows why in sharper form" in ln:
        print("found L", i)
        for j in range(i - 1, min(i + 10, len(lines))):
            print(f"{j+1:5d} {lines[j]}")
        break