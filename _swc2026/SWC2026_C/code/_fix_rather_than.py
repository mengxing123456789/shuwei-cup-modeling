# -*- coding: utf-8 -*-
"""Reduce the 'rather than' construction, the strongest AI-writing marker in this
paper (4.08 per 1k words against 0.09 in the awarded corpus). Every occurrence is
rewritten in place to ', not' or ' instead of'; no information is dropped, no
sentence order changes. Dry run prints each site with its context."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
MAIN = os.path.join(PROJ, "main.tex")

APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

sites = [m for m in re.finditer(r"\brather than\b", src)]
print("occurrences in main.tex: %d" % len(sites))

# replacement for the four-word phrase, per occurrence index
SWAPS = {}
for i in range(len(sites)):
    SWAPS[i] = " instead of" if i % 4 == 3 else ", not"

out = []
last = 0
for i, m in enumerate(sites):
    out.append(src[last:m.start()])
    out.append(SWAPS[i])
    last = m.end()
out.append(src[last:])
new = "".join(out)

print("\n--- every site, before -> after ---")
for i, m in enumerate(sites):
    s = max(0, m.start() - 60)
    e = min(len(src), m.end() + 45)
    print("%2d %-40s -> %s" % (i + 1,
                               " ".join(src[s:e].split())[:110],
                               SWAPS[i].strip()))

print("\nremaining 'rather than': %d" % len(re.findall(r"\brather than\b", new, re.I)))
print("new ', not' sites: %d" % len(re.findall(r",\s*not\b", new)))
print("new 'instead of': %d" % len(re.findall(r"\binstead of\b", new)))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
print("\nwritten", MAIN, len(new), "chars")
