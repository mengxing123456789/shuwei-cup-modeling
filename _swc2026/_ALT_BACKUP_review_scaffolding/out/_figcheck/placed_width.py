# -*- coding: utf-8 -*-
"""Measure the placed width of each figure image on its PDF page.

Confirms the real scale factor: natural width 416.5488 pt vs placed width.
"""
import fitz

PDF = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.pdf"
pages = {4: "fig0", 10: "fig1+fig2", 14: "fig3", 15: "fig4"}

doc = fitz.open(PDF)
print("page  figure      placed bbox (x0,y0,x1,y1)                 w      h     scale")
for pno, name in pages.items():
    p = doc[pno - 1]
    for img in p.get_images(full=True):
        xref = img[0]
        for r in p.get_image_rects(xref):
            w = r.x1 - r.x0
            h = r.y1 - r.y0
            print("%4d  %-10s  (%8.2f,%8.2f,%8.2f,%8.2f)  %7.2f %6.2f  %6.4f"
                  % (pno, name, r.x0, r.y0, r.x1, r.y1, w, h, w / 416.5488))
    # also report drawing-based extent (vector figures are not images)
    if not p.get_images():
        print("%4d  %-10s  (vector, no raster image)" % (pno, name))
print()
print("textwidth from main.log = 455.24411 pt ; 455.24411/416.5488 = %.4f" % (455.24411 / 416.5488))
doc.close()
