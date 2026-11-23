# -*- coding: utf-8 -*-
"""Part D: figure/table caption styles + page budget check + abstract keyword counts."""
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

for key, fn in PAPERS.items():
    doc = fitz.open(os.path.join(DIR, fn))
    caps_f, caps_t = [], []
    for i in range(len(doc)):
        t = doc[i].get_text("text")
        for ln in t.splitlines():
            s = ln.strip()
            m = re.match(r"^(Figure|Fig\.?)\s*\d+\s*[:.]?\s*(.{0,70})", s)
            if m: caps_f.append((i+1, (m.group(1)+m.group(2))[:72]))
            m = re.match(r"^Table\s*\d+\s*[:.]?\s*(.{0,70})", s)
            if m: caps_t.append((i+1, s[:72]))
    print("="*90)
    print(f"###### {key} figures-with-caption={len(caps_f)} tables-with-caption={len(caps_t)}")
    print("-- figure captions (up to 14) --")
    for pg, c in caps_f[:14]: print(f"  p{pg}: {c}")
    print("-- table captions (up to 14) --")
    for pg, c in caps_t[:14]: print(f"  p{pg}: {c}")
    # where does body end? find References page
    refp = None; appp = None
    for i in range(len(doc)):
        t = doc[i].get_text("text")
        if refp is None and re.search(r"^References\b", t, re.M): refp = i+1
        if appp is None and re.search(r"^Appendix\b", t, re.M): appp = i+1
    print(f"References first at pdf-page {refp}; Appendix first at {appp}")
    # abstract length: pages 1-2 word count
    wc = 0
    for i in range(0, 2):
        wc += len(doc[i].get_text("text").split())
    print(f"approx words on cover+summary pages(1-2): {wc}")
    doc.close()
print("END-PART-D")
