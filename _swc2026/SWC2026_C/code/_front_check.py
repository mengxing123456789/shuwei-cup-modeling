# -*- coding: utf-8 -*-
"""Render the first pages to PNG and print the header/foot text bands, so the
front-matter layout can be checked without eyeballing a whole page."""
import sys
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "main.pdf"
OUT = ROOT / "logs" / "_front"
OUT.mkdir(parents=True, exist_ok=True)

pages = [int(x) for x in (sys.argv[1:] or ["1", "2", "3"])]
doc = pymupdf.open(PDF)
print("pages", doc.page_count, "page size", doc[0].rect)
for p in pages:
    page = doc[p - 1]
    blocks = page.get_text("blocks")
    top = [b for b in blocks if b[1] < 90]
    bot = [b for b in blocks if b[3] > page.rect.height - 70]
    print("---- page", p)
    for b in top:
        print("  TOP  y0=%.1f y1=%.1f  %r" % (b[1], b[3], b[4][:110].replace("\n", " / ")))
    for b in bot:
        print("  BOT  y0=%.1f y1=%.1f  %r" % (b[1], b[3], b[4][:110].replace("\n", " / ")))
    # rules drawn as lines in the top 120pt
    for d in page.get_drawings():
        r = d["rect"]
        if r.y0 < 130 and r.height < 4:
            print("  RULE y=%.1f..%.1f  x=%.1f..%.1f w=%.1f" % (r.y0, r.y1, r.x0, r.x1, d.get("width", 0)))
    page.get_pixmap(dpi=170).save(OUT / ("p%02d.png" % p))
print("written", OUT)
