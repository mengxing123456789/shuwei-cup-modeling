import os
# -*- coding: utf-8 -*-
"""Audit the paper against the official format PDF (论文格式规范.pdf), item by item.

Items (Chinese spec numbering):
 一.2  p1 = title + Summary + keywords; p2 = contents only
 一.3  body pages carry team id + page number in the header
 一.4  12pt Times New Roman, English, <=25 pages incl. front matter
 一.5  references numbered in brackets, in citation order
 一.6  all source code in appendix or support material, noted in the paper
 一.7  no identity / school information
 二.1  table caption above, figure caption below; no Chinese in figures
 二.3  commitment letter naming
"""
import re
import pymupdf
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = ROOT / "main.pdf"
TEX = (ROOT / "main.tex").read_text(encoding="utf-8")

doc = pymupdf.open(PDF)
n = doc.page_count
print("total pages:", n)

# --- fonts used in the body
fonts = {}
for i in range(n):
    for f in doc[i].get_fonts():
        # (xref, ext, type, basefont, name, encoding)
        base = f[3]
        fonts[base] = fonts.get(base, 0) + 1
print("fonts:", sorted(fonts.items(), key=lambda kv: -kv[1])[:8])

# --- page 1 content
p1 = doc[0].get_text()
print("p1 has Summary:", "Summary" in p1, "| Key word:", "Key word" in p1)
print("p1 first 60 chars:", repr(p1[:60]))

# --- page 2 must be contents only
p2 = doc[1].get_text()
p2_lines = [l.strip() for l in p2.splitlines() if l.strip()]
print("p2 line count:", len(p2_lines), "| first:", p2_lines[:3])
body_words = len(re.findall(r"[A-Za-z]{3,}", p2))
print("p2 alphabetic words (excl. toc entries):", body_words)

# --- header presence per page
def header_ok(i):
    t = doc[i].get_text()
    top = t.splitlines()[:4]
    head = " ".join(top)
    return ("CSWBMCM2634892" in head) and ("Page" in head)

missing = [i + 1 for i in range(2, n) if not header_ok(i)]
print("pages missing team/page header (1-based, from p3):", missing[:10], "count", len(missing))

# --- Chinese characters anywhere
cjk = 0
for i in range(n):
    t = doc[i].get_text()
    cjk += len(re.findall(r"[\u4e00-\u9fff]", t))
print("CJK chars in PDF:", cjk)

# --- identity strings
for w in ("Nanchang", "University", "Shuping", "Zhang", "2990096174", "19721012529"):
    c = sum(doc[i].get_text().count(w) for i in range(n))
    print("identity %-12s %d" % (w, c))

# --- references: bracketed numbers, citation order
print("bib bracket style in tex:", r"\bibitem" in TEX, "| thebibliography:", "thebibliography" in TEX)
refs = re.findall(r"\\bibitem\{([^}]*)\}", TEX)
print("bibitem order:", refs)
cites = []
for m in re.finditer(r"\\cite\{([^}]*)\}", TEX):
    for k in m.group(1).split(","):
        cites.append(k.strip())
first_seen = []
for c in cites:
    if c not in first_seen:
        first_seen.append(c)
print("first citation order:", first_seen)
print("order matches bibitem order:", first_seen == [r for r in refs if r in first_seen])

# --- support material note
for pat in ("support material", "supporting material", "source code", "Appendix~\\ref{app:repro}"):
    print("note %-24s %d" % (pat, TEX.count(pat)))

# --- caption placement
print("table caption position:", "position=top" in (ROOT / "swmcmthesis.cls").read_text(encoding="utf-8", errors="ignore"))
print("figure caption position:", "position=bottom" in (ROOT / "swmcmthesis.cls").read_text(encoding="utf-8", errors="ignore"))