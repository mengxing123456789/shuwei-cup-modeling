# -*- coding: utf-8 -*-
"""Deep-dump key sections of each C paper."""
import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pymupdf as fitz

DIR = r"E:\数学建模\_swc2026\award_corpus_2025"
PAPERS = {
 "C1760": "CSHUWEICUP2551760.pdf",
 "C6711": "CSHUWEICUP2556711.pdf",
 "C6821": "CSHUWEICUP2556821.pdf",
 "C9001": "CSHUWEICUP2559001.pdf",
 "C1635": "CSHUWEICUP2561635.pdf",
}

def dump(doc, pno, maxc=3200, tag=""):
    if pno < 0 or pno >= len(doc): 
        print(f"  [{tag}] page {pno+1} OOB"); return
    t = doc[pno].get_text("text")
    t = re.sub(r"\n{3,}", "\n\n", t)
    print(f"----- [{tag}] PDF-page {pno+1} -----")
    print(t[:maxc])
    if len(t) > maxc: print(f"...(truncated {len(t)-maxc} chars)")

for key, fn in PAPERS.items():
    doc = fitz.open(os.path.join(DIR, fn))
    print("#"*100)
    print(f"###### {key}  {fn}  total={len(doc)}")
    # image count
    nimg = 0
    for i in range(len(doc)):
        try: nimg += len(doc[i].get_images(full=True))
        except: pass
    print(f"embedded images total={nimg}")
    # cover/abstract pages 1-4
    for i in range(0, 4):
        dump(doc, i, 3000, f"{key}/front")
    doc.close()
print("END-PART-A")
