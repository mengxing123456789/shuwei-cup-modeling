# -*- coding: utf-8 -*-
"""Check the two remaining AI-notice items: in-text marking of AI-generated
material, and per-script AI notes in the support package."""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
CODE = os.path.join(PROJ, "code")

main = io.open(os.path.join(PROJ, "main.tex"), encoding="utf-8").read()
body = main[:main.find(r"\section{Notation}")]
print("body chars %d" % len(body))

pats = [r"assistant", r"generative", r"AI[- ]generated", r"AI[- ]assisted",
        r"language model", r"written with", r"drafted with"]
print("\n--- in-text marking candidates (whole body) ---")
for p in pats:
    print("  %-22s %d" % (p, len(re.findall(p, body, re.I))))

print("\n--- scripts: header note coverage ---")
files = sorted(f for f in os.listdir(CODE) if f.endswith(".py"))
no_note, with_note = [], []
for f in files:
    head = io.open(os.path.join(CODE, f), encoding="utf-8", errors="replace").read(900)
    if re.search(r"\bAI\b|DeepSeek|assisted", head, re.I):
        with_note.append(f)
    else:
        no_note.append(f)
print("  total %d | with note %d | without %d" % (len(files), len(with_note), len(no_note)))
print("  sample without note:", ", ".join(no_note[:12]))

print("\n--- deliverable naming and size ---")
for f in ("CSWBMCM2634892.pdf", "CSWBMCM2634892cns.pdf", "CSWBMCM2634892fj.zip"):
    p = os.path.join(PROJ, f)
    print("  %-28s %s" % (f, os.path.getsize(p) if os.path.exists(p) else "MISSING"))
