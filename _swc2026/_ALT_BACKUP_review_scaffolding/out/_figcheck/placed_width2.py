# -*- coding: utf-8 -*-
"""Find the placed bbox of the vector figure on each figure page.

The five figures are PDF Form XObjects (vector), so get_images() is empty.
Use the content-stream bbox log to read the actual placement rectangle.
"""
import pymupdf

PDF = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.pdf"
NAT = 416.5488  # natural width of every figure PDF, in pt

doc = pymupdf.open(PDF)
for pno in (4, 10, 14, 15):
    p = doc[pno - 1]
    print("=== page %d  (mediabox %s) ===" % (pno, tuple(round(v, 2) for v in p.rect)))
    for kind, bbox in p.get_bboxlog():
        if "xobject" in kind:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            print("   %-28s (%8.2f,%8.2f,%8.2f,%8.2f)  w=%7.2f h=%7.2f  scale=%.4f"
                  % (kind, bbox[0], bbox[1], bbox[2], bbox[3], w, h, w / NAT))
print()
print("textwidth 455.24411 / 416.5488 = %.4f" % (455.24411 / NAT))
print("linewidth 416.5488 / 416.5488 = %.4f" % (416.5488 / NAT))
doc.close()
