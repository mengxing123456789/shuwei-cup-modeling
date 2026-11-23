# -*- coding: utf-8 -*-
"""Last two checks: ALT body page count, and whether our P2 cost weights are swept."""
import io
import json
import os
import re
import pymupdf

ROOT = r"E:\数学建模\_swc2026"
M = os.path.join(ROOT, "SWC2026_C")
A = os.path.join(ROOT, "SWC2026_C_ALT_BACKUP")

print("=== ALT body page count (first Appendix page minus front matter) ===")
d = pymupdf.open(os.path.join(A, "CSWBMCM2634892.pdf"))
for i, p in enumerate(d):
    t = p.get_text()
    if "Appendix A" in t[:300]:
        print("  Appendix A starts at PDF page", i + 1, "header:", t.split("\n")[0:2])
        break
print("  front matter pages 1-3 (title/summary, keywords, TOC)")
print("  => body pages =", (i + 1) - 3 - 1)

print("\n=== our body: 25 pages, header denominator 25 ===")
d2 = pymupdf.open(os.path.join(M, "CSWBMCM2634892.pdf"))
print("  p2 header:", d2[1].get_text().split("\n")[0:2])
print("  p25 header:", d2[24].get_text().split("\n")[0:2])
print("  p26 header:", d2[25].get_text().split("\n")[0:2])

print("\n=== P2 cost weights: fixed or swept? ===")
main = io.open(os.path.join(M, "main.tex"), encoding="utf-8").read()
for kw in ("c_0", "c_1", "lambda", "cost weight", "priced"):
    print("  %-12s %d" % (kw, main.count(kw)))
i = main.find("priced")
print("\n  priced-rule passage:")
print("   ", main[max(0, i - 500):i + 700].replace("\n", " ")[:1000])

print("\n=== does the appendix sweep the cost weights? ===")
appn = io.open(os.path.join(M, "tables", "app_n.tex"), encoding="utf-8").read()
for kw in ("econ", "cost", "lambda", "c_0"):
    print("  app_n.tex %-8s %d" % (kw, appn.count(kw)))
m = re.search(r"tab:econ", appn)
if m:
    j = appn.find(r"\begin{table}", max(0, m.start() - 400))
    print("\n  tab:econ block head:")
    print("   ", appn[j:j + 700].replace("\n", " ")[:700])
