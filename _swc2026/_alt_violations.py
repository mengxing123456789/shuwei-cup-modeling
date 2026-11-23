# -*- coding: utf-8 -*-
"""Pin down the ALT paper's format-rule violations with exact page evidence."""
import re
import pymupdf

P = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\CSWBMCM2634892.pdf"
d = pymupdf.open(P)
t1 = d[0].get_text()
t2 = d[1].get_text()
t3 = d[2].get_text()

print("== page 1 ==")
print("has 'Team Control Number':", "Team Control Number" in t1)
print("team string present      :", re.findall(r"[A-Z]*SWBMCM\d+", t1))
print("has 'Key word'           :", "Key word" in t1)
print("has 'Summary'            :", "Summary" in t1)
print()
print("== page 2 ==")
print("has 'Content' (TOC)      :", "Content" in t2)
print("has 'Key word'           :", "Key word" in t2)
print("team string present      :", re.findall(r"[A-Z]*SWBMCM\d+", t2))
print("chars                    :", len(t2))
print()
print("== page 3 ==")
print("has 'Content' (TOC)      :", "Content" in t3)
print()
# all distinct team-number spellings in the whole document
full = "\n".join(p.get_text() for p in d)
print("== team spellings across the PDF ==")
for s, c in sorted({m: full.count(m) for m in set(re.findall(r"\w*SWBMCM\d+", full))}.items()):
    print("  %-20s %d" % (s, c))
print()
print("== AI / tool disclosure ==")
for kw in ("AI tool", "AI Tool", "DeepSeek", "generative", "ChatGPT", "AI 工具"):
    print("  %-14s %d" % (kw, full.count(kw)))
print()
print("== appendix / body boundary ==")
for i in (24, 25, 26):
    print("  PDF p%d header: %s" % (i + 1, d[i].get_text().split("\n")[0:2]))
