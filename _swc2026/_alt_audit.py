# -*- coding: utf-8 -*-
"""Audit the ALT paper against the same official checks the main paper passes."""
import re
import pymupdf

P = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\CSWBMCM2634892.pdf"
d = pymupdf.open(P)

print("total PDF pages:", d.page_count)
print()

# where do References / Appendix start, and what header do those pages carry?
for i, p in enumerate(d):
    t = p.get_text()
    head = t[:120].replace("\n", " | ")
    if "References" in t[:400] or "Appendix" in t[:400]:
        print("p%-3d %s" % (i + 1, head[:110]))
print()

# header scheme on a few pages
print("--- header sample ---")
for i in (3, 20, 26, 40, 100, 124):
    if i < d.page_count:
        first = d[i].get_text().split("\n")[0]
        print("p%-3d  %s" % (i + 1, first))
print()

# declared page totals
m = re.findall(r"Page (\d+) of (\d+)", "\n".join(p.get_text() for p in d))
print("declared 'Page n of N' pairs seen:", len(m))
if m:
    print("  distinct N:", sorted({x[1] for x in m}))
    print("  max n     :", max(int(x[0]) for x in m))
print()

# where is the body-only part if any page declares a small N?
small = [(i + 1, x) for i, p in enumerate(d)
         for x in re.findall(r"Page (\d+) of (\d+)", p.get_text()) if int(x[1]) <= 30]
print("pages whose header declares N<=30:", small[:10])
