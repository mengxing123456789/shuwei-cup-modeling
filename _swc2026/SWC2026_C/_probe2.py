import pathlib
import pymupdf

doc = pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_C\main.pdf")
for i in (24, 25):
    t = doc[i].get_text()
    print(f"=== p{i+1} chars={len(t)} ===")
    print(t[:260].replace("\n", " | "))
    print()