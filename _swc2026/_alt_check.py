# -*- coding: utf-8 -*-
"""Same compliance probe on the ALT paper, so the choice is evidence-based."""
import io
import re
import pymupdf

P = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\CSWBMCM2634892.pdf"
d = pymupdf.open(P)
texts = [p.get_text() for p in d]
full = "\n".join(texts)

print("pages:", d.page_count)
for w in ("Nanchang", "University", "Shuping", "2990096174", "19721012529"):
    print("  %-14s %d" % (w, full.count(w)))
print("  CJK chars      %d" % len(re.findall(r"[\u4e00-\u9fff]", full)))
print("  p1 Problem     %s" % ("Problem Chosen" in texts[0]))
print("  p1 Key word    %s" % ("Key word" in texts[0]))
print("  p2 Content     %s" % ("Content" in texts[1]))
print("  p2 header Team %s" % ("Team CSWBMCM2634892" in texts[1]))
print("  p2 header Page %s" % bool(re.search(r"Page \d+ of \d+", texts[1])))

# where does the body end?  find the first page whose header says Appendix
body_end = None
for i, t in enumerate(texts):
    if "Appendix" in t and re.search(r"Appendix, p\.", t):
        body_end = i
        break
print("  first appendix page (1-based):", (body_end + 1) if body_end is not None else "none")

# count "Page n of N" occurrences to infer declared body length
m = re.findall(r"Page (\d+) of (\d+)", full)
if m:
    print("  declared body total (from header):", sorted({x[1] for x in m}))
    print("  max body page number seen        :", max(int(x[0]) for x in m))
