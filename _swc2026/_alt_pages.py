# -*- coding: utf-8 -*-
"""Look closely at the ALT paper's first pages and its header/footer scheme."""
import re
import pymupdf

P = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\CSWBMCM2634892.pdf"
d = pymupdf.open(P)
for i in (0, 1, 2, 3, 24, 25, 26):
    t = d[i].get_text()
    print("=" * 20, "page", i + 1, "chars", len(t))
    print(t[:600].replace("\n", " | ")[:600])
    print()
