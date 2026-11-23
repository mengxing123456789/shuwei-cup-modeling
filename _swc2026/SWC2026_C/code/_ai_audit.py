# -*- coding: utf-8 -*-
"""Audit the paper against the official AI-tool rules (nmmcm News/220, 2026-11-11)."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

def read(name):
    with io.open(os.path.join(PROJ, name), encoding="utf-8") as f:
        return f.read()

main = read("main.tex")
print("main.tex bytes", os.path.getsize(os.path.join(PROJ, "main.tex")),
      "lines", main.count("\n") + 1)

print("\n--- sections ---")
for m in re.finditer(r"\\(section|subsection)\{([^}]*)\}", main):
    print("  ", m.group(1), "|", m.group(2))

print("\n--- keyword hits (whole file) ---")
kws = ["AI tool", "artificial intelligence", "DeepSeek", "generative tool",
       "AI-assisted", "AI usage", "language model", "Appendix"]
for kw in kws:
    print("  %-24s %d" % (kw, len(re.findall(re.escape(kw), main, re.I))))

print("\n--- sentences mentioning AI ---")
for m in re.finditer(r"[^.\n]*\bAI\b[^.\n]*\.", main):
    print("  *", " ".join(m.group(0).split())[:400])

print("\n--- AI report block (if any) ---")
i = main.lower().find("generative tool")
if i >= 0:
    print(main[max(0, i - 2500): i + 3500])
else:
    print("  NONE")

print("\n--- code headers: AI note present? ---")
code_dir = os.path.join(PROJ, "code")
files = sorted(f for f in os.listdir(code_dir) if f.endswith(".py"))
hit = 0
for f in files:
    with io.open(os.path.join(code_dir, f), encoding="utf-8", errors="replace") as fh:
        head = fh.read(1200)
    if re.search(r"\bAI\b|DeepSeek|assisted", head, re.I):
        hit += 1
print("  %d of %d .py files mention AI in the first 1200 chars" % (hit, len(files)))
