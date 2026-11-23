# -*- coding: utf-8 -*-
"""Final compliance spot-check on the shipped PDF."""
import io
import re
import pymupdf

P = r"E:\数学建模\_swc2026\SWC2026_C\CSWBMCM2634892.pdf"
d = pymupdf.open(P)
texts = [p.get_text() for p in d]
full = "\n".join(texts)

print("pages:", d.page_count)
for w in ("Nanchang", "University", "Shuping", "2990096174", "19721012529"):
    print("  %-14s %d" % (w, full.count(w)))
print("  CJK chars      %d" % len(re.findall(r"[\u4e00-\u9fff]", full)))
print("  page1 Key word %s" % ("Key word" in texts[0]))
print("  page1 Problem  %s" % ("Problem Chosen" in texts[0]))
print("  page2 Content  %s" % ("Content" in texts[1]))
print("  p2 header      %s" % ("Team CSWBMCM2634892" in texts[1]))
print("  p25 header     %s" % ("Page 25 of 25" in texts[24]))
print("  p26 appendix   %s" % ("Appendix" in texts[25]))
body = "\n".join(texts[:25])
print("  refs in body   %d" % len(re.findall(r"^\[\d+\]", body, re.M)))
