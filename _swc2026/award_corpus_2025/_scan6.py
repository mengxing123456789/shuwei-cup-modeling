# -*- coding: utf-8 -*-
"""Part E: body page budget (TOC target pages), C9001 data-preproc & sensitivity region, C1635 eval."""
import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pymupdf as fitz

DIR = r"E:\数学建模\_swc2026\award_corpus_2025"

def dump(doc, pno, maxc, tag):
    if pno is None or pno < 0 or pno >= len(doc): return
    t = doc[pno].get_text("text")
    t = re.sub(r"\n{3,}", "\n\n", t)
    print(f"----- [{tag}] p{pno+1} -----")
    print(t[:maxc])
    if len(t) > maxc: print(f"...(trunc {len(t)-maxc})")

doc = fitz.open(os.path.join(DIR, "CSHUWEICUP2559001.pdf"))
# data preprocessing section pdf p7-10
for pg in (6, 7, 8, 9):
    dump(doc, pg, 2400, "C9001/preproc")
# look for sensitivity keyword pages beyond TOC
for i in range(len(doc)):
    t = doc[i].get_text("text")
    if re.search(r"[Ss]ensitivity", t) and i > 3:
        dump(doc, i, 1800, "C9001/sens-hit")
doc.close()

doc = fitz.open(os.path.join(DIR, "CSHUWEICUP2561635.pdf"))
# Question-5 eval & conclusion region pdf p29-30
for pg in (28, 29):
    dump(doc, pg, 2200, "C1635/tail")
doc.close()

doc = fitz.open(os.path.join(DIR, "CSHUWEICUP2556821.pdf"))
# validation/sensitivity subsection 4.2.5 pdf p15, 4.3.4 p22, 4.4.5 p29
for pg in (14, 21, 28):
    dump(doc, pg, 1600, "C6821/sens")
doc.close()
print("END-PART-E")
