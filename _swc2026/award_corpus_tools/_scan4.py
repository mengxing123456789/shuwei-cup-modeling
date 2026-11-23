# -*- coding: utf-8 -*-
"""Part C: targeted deep reads — test/eval, sensitivity, strengths/weakness, refs, assumptions."""
import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pymupdf as fitz

DIR = r"E:\数学建模\_swc2026\award_corpus_2025"

def dump(doc, pno, maxc, tag):
    if pno < 0 or pno >= len(doc): return
    t = doc[pno].get_text("text")
    t = re.sub(r"\n{3,}", "\n\n", t)
    print(f"----- [{tag}] p{pno+1} -----")
    print(t[:maxc])
    if len(t) > maxc: print(f"...(trunc {len(t)-maxc})")

jobs = {
 "C6711": ("CSHUWEICUP2556711.pdf", {
    # body pages: model section begins p7 (pdf), test models p40, sensitivity p44, S&W p46, conclusion p47, refs p48
    "assumptions": [(6, 2200)],        # pdf p7 area
    "test_models": [(39, 3500), (40, 2200), (41, 2000), (42, 2200)],   # pdf p40-43
    "sensitivity": [(43, 3000), (44, 2600), (45, 1800)],
    "sw": [(45, 2600), (46, 2000)],
    "conclusion": [(46, 2200), (47, 2200)],
    "refs": [(47, 2600)],
 }),
 "C1760": ("CSHUWEICUP2551760.pdf", {
    "sensitivity": [(39, 2800), (40, 2800), (41, 2200), (42, 1600)],  # pdf p40-43 = TOC 10.1/10.2
    "sw": [(42, 2200), (43, 2400)],  # TOC 11 around p43
    "refs": [(43, 2400)],
 }),
 "C6821": ("CSHUWEICUP2556821.pdf", {
    "sw": [(35, 2600), (36, 1800)],   # pdf p36-37
    "conclusion": [(36, 1800), (37, 1800)],
    "refs": [(37, 2200)],
    "sens_q1": [(9, 2400)],           # 4.1.6 validation & sensitivity (pdf p10)
 }),
 "C9001": ("CSHUWEICUP2559001.pdf", {
    "assumptions": [(5, 2200)],
    "sw": [(36, 2400), (37, 1600)],
    "refs": [(37, 2400)],
 }),
 "C1635": ("CSHUWEICUP2561635.pdf", {
    "assumptions": [(4, 2400)],
    "refs": [(29, 2400), (30, 1200)],
    "sensitivity": [(10, 1800)],
 }),
}

for key, (fn, secs) in jobs.items():
    doc = fitz.open(os.path.join(DIR, fn))
    print("#"*90)
    print(f"###### {key}")
    for sec, plist in secs.items():
        for pg, mc in plist:
            dump(doc, pg, mc, f"{key}/{sec}")
    doc.close()
print("END-PART-C")
