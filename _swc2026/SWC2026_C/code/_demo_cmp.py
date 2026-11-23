# -*- coding: utf-8 -*-
"""Compare our front matter with the official demo.pdf page by page (text bands)."""
import pymupdf
from pathlib import Path

BASE = Path(r".\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题")
DEMO = BASE / "2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）LaTeX模版" / "demo.pdf"
OURS = Path(r"main.pdf")

for name, path in (("DEMO", DEMO), ("OURS", OURS)):
    d = pymupdf.open(path)
    print("=====", name, path.name, "pages", d.page_count, "size", d[0].rect)
    for i in range(min(3, d.page_count)):
        pg = d[i]
        blocks = pg.get_text("blocks")
        top = [b for b in blocks if b[1] < 100]
        bot = [b for b in blocks if b[3] > pg.rect.height - 70]
        print("  -- page", i + 1)
        for b in top:
            print("     TOP y=%.1f..%.1f %r" % (b[1], b[3], b[4][:90].replace("\n", " / ")))
        for b in bot:
            print("     BOT y=%.1f..%.1f %r" % (b[1], b[3], b[4][:90].replace("\n", " / ")))
        for dr in pg.get_drawings():
            r = dr["rect"]
            if r.y0 < 140 and r.height < 5:
                w = dr.get("width") or 0
                print("     RULE y=%.1f x=%.1f..%.1f w=%.1f" % (r.y0, r.x0, r.x1, w))
