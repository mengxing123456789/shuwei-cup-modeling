# -*- coding: utf-8 -*-
"""Fact-check every row of the comparison screenshot against the actual files."""
import io
import json
import os
import re

ROOT = r"E:\数学建模\_swc2026"
M = os.path.join(ROOT, "SWC2026_C")
A = os.path.join(ROOT, "SWC2026_C_ALT_BACKUP")

main = io.open(os.path.join(M, "main.tex"), encoding="utf-8").read()
body = main.split(r"\section{Notation}")[0]

print("=== 1. five service mappings in the BODY of the main paper? ===")
for kw in ("five mappings", "five service", "mapping", "0.75", "1.5", "beta = 0", r"\beta=0"):
    print("  %-16s body %3d | whole %3d" % (kw, body.count(kw), main.count(kw)))
print("  body has tab:p3nom ?", "tab:p3nom" in body)
print("  body references it ?", "ref{tab:p3nom}" in body)

print("\n=== 2. Q1 positive rate (bad-frame prevalence) ===")
for f in ("p1b_loto.json", "up_p1b_align.json", "up2_p1b.json", "p1b_reliability.json"):
    p = os.path.join(M, "data", f)
    if not os.path.exists(p):
        continue
    d = json.loads(io.open(p, encoding="utf-8").read())
    s = json.dumps(d)
    hits = re.findall(r'"(?:prevalence|pos_rate|positive_rate|base_rate)[^"]*":\s*([0-9.eE+-]+)', s)
    print("  %-24s prevalence-ish keys: %s" % (f, hits[:6]))

print("\n=== 3. em-dash: body count and the corpus band the screenshot cites ===")
print("  main.tex raw '---' occurrences:", main.count("---"))
print("  main.tex raw '—' occurrences  :", main.count("\u2014"))
band = os.path.join(A, "refs", "official_standard.json")
if os.path.exists(band):
    d = json.loads(io.open(band, encoding="utf-8").read())
    print("  ALT refs/official_standard.json keys:", list(d.keys())[:12])
    for k in ("em_dash", "emdash", "band", "bands", "features"):
        if k in d:
            print("   ", k, "=", json.dumps(d[k], ensure_ascii=False)[:300])

print("\n=== 4. ALT front matter (official rule: p1 title+summary+keywords, p2 TOC only) ===")
import pymupdf
d = pymupdf.open(os.path.join(A, "CSWBMCM2634892.pdf"))
for i in (0, 1, 2):
    t = d[i].get_text()
    print("  p%d  KeyWord=%-5s Content=%-5s Summary=%-5s chars=%d"
          % (i + 1, "Key word" in t, "Content" in t, "Summary" in t, len(t)))
print("  header spelling on p4:", d[3].get_text().split("\n")[0:2])
print("  header spelling on p4 (main):")
d2 = pymupdf.open(os.path.join(M, "CSWBMCM2634892.pdf"))
print("   ", d2[1].get_text().split("\n")[0:2])

print("\n=== 5. honest negative results present in each ===")
for name, t in (("MAIN", main), ("ALT", io.open(os.path.join(A, "main.tex"), encoding="utf-8").read())):
    print("  %-4s tab:negatives=%d  'we do not'=%d  'fails'=%d  'did not'=%d"
          % (name, t.count("tab:negatives"), t.count("we do not"),
             t.count("fails"), t.count("did not")))
