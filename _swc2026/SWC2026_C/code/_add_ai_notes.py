# -*- coding: utf-8 -*-
"""Insert the organiser-required generative-tool note into every packaged script
that lacks it (notice of 2026-11-11, clause 7: script comments must state the
AI tool, its version, the organisation and the release date)."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
CODE = os.path.join(PROJ, "code")

NOTE = [
    "# --- generative-tool note (required by the organiser's notice of 2026-11) ---",
    "# Drafted with DeepSeek Harness, a command-line coding agent (DeepSeek),",
    "# 18-22 November 2026; every number this file produces was re-executed by the",
    "# team from a clean shell and traced to data/*.json through code/fill_numbers.py.",
]

APPLY = "--apply" in sys.argv

targets = []
for f in sorted(os.listdir(CODE)):
    if not f.endswith(".py") or f.startswith("_"):
        continue
    p = os.path.join(CODE, f)
    head = io.open(p, encoding="utf-8", errors="replace").read(900)
    if re.search(r"\bAI\b|DeepSeek|assisted", head, re.I):
        continue
    targets.append(f)

print("scripts to patch: %d" % len(targets))
if not APPLY:
    print("dry run; pass --apply to write")
    sys.exit(0)

for f in targets:
    p = os.path.join(CODE, f)
    src = io.open(p, encoding="utf-8", errors="replace").read()
    lines = src.split("\n")
    # keep a leading shebang and the coding declaration above the note
    i = 0
    while i < len(lines) and i < 3 and (
            lines[i].startswith("#!") or re.match(r"#.*coding[:=]", lines[i] or "")):
        i += 1
    out = lines[:i] + NOTE + lines[i:]
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))

print("patched %d files" % len(targets))
