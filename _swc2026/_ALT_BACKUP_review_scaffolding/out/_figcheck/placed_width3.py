# -*- coding: utf-8 -*-
"""Measure the placed extent of each vector figure via its drawing bbox.

Restrict to drawings above the caption (captions start below the figure), and
report the union bbox width against the natural width 416.5488 pt.
"""
import pymupdf

PDF = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.pdf"
NAT = 416.5488

doc = pymupdf.open(PDF)
for pno in (4, 10, 14, 15):
    p = doc[pno - 1]
    dr = p.get_drawings()
    if not dr:
        print("page %d: no drawings" % pno)
        continue
    # figure sits at the top of the page; header rule is a thin full-width line near y~55
    xs0, ys0, xs1, ys1 = [], [], [], []
    for d in dr:
        r = d["rect"]
        # skip the header rule: full text width, height < 1 pt, near the top
        if r.width > 440 and r.height < 2:
            continue
        xs0.append(r.x0); ys0.append(r.y0); xs1.append(r.x1); ys1.append(r.y1)
    if not xs0:
        print("page %d: only header rule" % pno)
        continue
    w = max(xs1) - min(xs0)
    h = max(ys1) - min(ys0)
    print("page %2d  drawings=%3d  union bbox x[%7.2f..%7.2f] y[%7.2f..%7.2f]  w=%7.2f h=%7.2f  scale=%.4f"
          % (pno, len(dr), min(xs0), max(xs1), min(ys0), max(ys1), w, h, w / NAT))
doc.close()
print()
print("theory: \\linewidth == \\textwidth == 455.24411 pt -> scale 455.24411/416.5488 = %.4f"
      % (455.24411 / NAT))
