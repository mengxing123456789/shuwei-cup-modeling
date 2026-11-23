# -*- coding: utf-8 -*-
"""Check appendix headers, body font size, and line spacing against the spec."""
import os
import re
import pymupdf
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
doc = pymupdf.open(ROOT / "main.pdf")
n = doc.page_count

print("== appendix page headers (p26, p40, p69)")
for p in (26, 40, 69):
    if p <= n:
        lines = [l for l in doc[p - 1].get_text().splitlines() if l.strip()][:3]
        print("  p%d: %r" % (p, lines))

print("== body font sizes (p3..p25), top sizes by char count")
from collections import Counter
cnt = Counter()
for i in range(2, 25):
    d = doc[i].get_text("dict")
    for b in d["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s["text"].strip():
                    cnt[round(s["size"], 1)] += len(s["text"])
for size, c in cnt.most_common(6):
    print("  %.1f pt : %d chars" % (size, c))

print("== header font size (p3)")
d = doc[2].get_text("dict")
for b in d["blocks"]:
    if b["bbox"][1] < 70:
        for l in b.get("lines", []):
            for s in l["spans"]:
                print("  %r %.1f pt" % (s["text"][:40], s["size"]))