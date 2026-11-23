# -*- coding: utf-8 -*-
"""Sample the actual em-dash / colon / rather-than usages so the report can quote
real sentences instead of counts."""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
PLAIN = os.path.join(os.path.dirname(PROJ), "_paper_plain.txt")
txt = io.open(PLAIN, encoding="utf-8").read()

def ctx(m, pad=110):
    s = max(0, m.start() - pad)
    e = min(len(txt), m.end() + pad)
    return " ".join(txt[s:e].split())

print("=== em dash (---) samples ===")
for i, m in enumerate(re.finditer(r"---", txt)):
    if i >= 12:
        break
    print(" %2d. %s" % (i + 1, ctx(m)))

print("\n=== 'rather than' samples (first 10) ===")
for i, m in enumerate(re.finditer(r"\brather than\b", txt)):
    if i >= 10:
        break
    print(" %2d. %s" % (i + 1, ctx(m)))

print("\n=== colon samples (first 12) ===")
for i, m in enumerate(re.finditer(r":\s", txt)):
    if i >= 12:
        break
    print(" %2d. %s" % (i + 1, ctx(m)))
