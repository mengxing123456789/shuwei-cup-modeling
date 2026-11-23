# -*- coding: utf-8 -*-
"""Rigorous scale factor: compare the drawing-union width inside each figure
PDF with the drawing-union width of the same figure as placed on the page.

Both unions use the same rule (all drawing rects), so the ratio is the true
typesetting scale -- immune to padding differences between canvas and ink.
"""
import pymupdf

ROOT = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP"
FIGS = [(4, "fig0_framework"), (10, "fig1_p1_agreement"), (10, "fig2_p1_reliability"),
        (14, "fig3_p2_error"), (15, "fig4_p2_voi")]


def union_width(page, skip_header=False):
    xs0, xs1 = [], []
    for d in page.get_drawings():
        r = d["rect"]
        if skip_header and r.width > 440 and r.height < 2:
            continue
        xs0.append(r.x0); xs1.append(r.x1)
    if not xs0:
        return None, None
    return min(xs0), max(xs1)


print("figure                canvas   ink[nat] w   ink[page] w    scale")
main = pymupdf.open(ROOT + r"\main.pdf")
for pno, name in FIGS:
    fig = pymupdf.open(ROOT + r"\figures\%s.pdf" % name)
    fp = fig[0]
    a0, a1 = union_width(fp)
    nat_w = a1 - a0
    canvas = fp.rect.width
    p = main[pno - 1]
    b0, b1 = union_width(p, skip_header=True)
    page_w = b1 - b0
    print("%-20s  %6.2f  %9.2f  %11.2f  %7.4f"
          % (name, canvas, nat_w, page_w, page_w / nat_w))
    fig.close()
main.close()
print()
print("note: page 10 holds two figures side by side; its page union spans both.")
print("canvas width of every figure PDF = 416.5488 pt; \\textwidth = 455.24411 pt")
