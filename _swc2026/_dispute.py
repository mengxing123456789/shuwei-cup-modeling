# -*- coding: utf-8 -*-
"""Settle the disputed rows with hard numbers."""
import io
import json
import os
import re

ROOT = r"E:\数学建模\_swc2026"
M = os.path.join(ROOT, "SWC2026_C")
A = os.path.join(ROOT, "SWC2026_C_ALT_BACKUP")

main = io.open(os.path.join(M, "main.tex"), encoding="utf-8").read()
alt = io.open(os.path.join(A, "main.tex"), encoding="utf-8").read()
body = main.split(r"\section{Notation}")[0]

print("=== em dash: every possible definition ===")
for name, t in (("MAIN body", body), ("MAIN all", main), ("ALT all", alt)):
    w = len(t.split())
    print("  %-10s words %5d  '---' %3d  '--' %3d  U+2014 %3d  U+2013 %3d"
          % (name, w, t.count("---"), t.count("--"), t.count("\u2014"), t.count("\u2013")))

print("\n=== does MAIN report the five mappings with numbers in the body? ===")
for s in ("PMapSTwoLowAlpha", "PMapSTwoHighAlpha", "PMapSThreeLowAlpha", "PMapSThreeHighAlpha"):
    m = re.search(r"\\slot%s\b" % s, body)
    print("  %-22s in body: %s" % (s, bool(m)))
i = body.find("mapping dominates")
print("  body sentence:", body[max(0, i - 260):i + 320].replace("\n", " ")[:560] if i > 0 else "not found")

print("\n=== honest negatives: count of failing statements ===")
for name, t in (("MAIN", main), ("ALT", alt)):
    print("  %-4s  tab:negatives=%d  'did not'=%d  'fails'=%d  'we do not'=%d  'no gain'=%d"
          % (name, t.count("tab:negatives"), t.count("did not"), t.count("fails"),
             t.count("we do not"), t.count("no gain")))

print("\n=== ALT front matter vs the official rule (p1 title+summary+keywords; p2 TOC only) ===")
import pymupdf
d = pymupdf.open(os.path.join(A, "CSWBMCM2634892.pdf"))
for i in range(3):
    t = d[i].get_text()
    print("  p%d: KeyWord=%-5s Content=%-5s Summary=%-5s" % (i + 1, "Key word" in t,
                                                             "Content" in t, "Summary" in t))
print("  ALT header p4 :", d[3].get_text().split("\n")[0])
d2 = pymupdf.open(os.path.join(M, "CSWBMCM2634892.pdf"))
print("  MAIN header p2:", d2[1].get_text().split("\n")[0])

print("\n=== structural gates: does ALT have a verify_claims equivalent? ===")
alt_audit = os.path.join(A, "audit")
print("  ALT audit dir exists:", os.path.isdir(alt_audit))
if os.path.isdir(alt_audit):
    print("  ALT audit files:", os.listdir(alt_audit))
main_audit = os.path.join(ROOT, "audit")
print("  MAIN audit files:", [f for f in os.listdir(main_audit) if f.endswith(".py")])

print("\n=== how do numbers enter each paper? ===")
print("  MAIN slots.tex macros:", len(re.findall(r"\\newcommand\{\\slot", io.open(os.path.join(M, "slots.tex"), encoding="utf-8").read())))
print("  ALT has slots.tex    :", os.path.exists(os.path.join(A, "slots.tex")))
print("  ALT numeric literals in body (rough):", len(re.findall(r"(?<![\w{])\d+\.\d{2,}", alt)))
print("  MAIN numeric literals in body (rough):", len(re.findall(r"(?<![\w{])\d+\.\d{2,}", body)))
