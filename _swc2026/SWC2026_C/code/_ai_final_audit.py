# -*- coding: utf-8 -*-
"""Final compliance checks: which packaged scripts lack the AI note, and whether
the AI report carries the seven fields the notice names."""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
CODE = os.path.join(PROJ, "code")

SHIPPED = []
for f in sorted(os.listdir(CODE)):
    if not f.endswith(".py"):
        continue
    if f.startswith("_"):
        continue          # package.py drops these
    SHIPPED.append(f)

missing = []
for f in SHIPPED:
    head = io.open(os.path.join(CODE, f), encoding="utf-8", errors="replace").read(900)
    if not re.search(r"\bAI\b|DeepSeek|assisted", head, re.I):
        missing.append(f)

print("packaged .py scripts: %d" % len(SHIPPED))
print("  with AI note in header: %d" % (len(SHIPPED) - len(missing)))
print("  WITHOUT AI note      : %d" % len(missing))
for f in missing:
    print("    -", f)

main = io.open(os.path.join(PROJ, "main.tex"), encoding="utf-8").read()
i = main.find("AI tool usage report")
block = main[i:i + 6000]
print("\n--- AI report field coverage ---")
for label, pat in [("tool name", r"Tool &"),
                   ("version/model", r"[Vv]ersion|v\d\.\d|model route"),
                   ("institution", r"DeepSeek"),
                   ("dates", r"Dates &"),
                   ("stages", r"Stages &"),
                   ("key prompts", r"Key prompts"),
                   ("outputs", r"Outputs adopted"),
                   ("team revision", r"Team revision")]:
    print("  %-16s %s" % (label, "YES" if re.search(pat, block) else "NO"))
