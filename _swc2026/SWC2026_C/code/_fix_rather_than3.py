# -*- coding: utf-8 -*-
"""Rewrite every 'rather than' in main.tex: gerund tails become 'instead of',
everything else becomes ', not'. Two awkward results are then hand-patched."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
MAIN = os.path.join(PROJ, "main.tex")

APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()
n0 = len(re.findall(r"\brather than\b", src, re.I))


def gerund_after(text, pos):
    m = re.match(r"\s+(\w+)", text[pos:])
    return bool(m and m.group(1).lower().endswith("ing"))


pieces, last, sites = [], 0, []
for m in re.finditer(r"\brather than\b", src):
    rep = " instead of" if gerund_after(src, m.end()) else ", not"
    pieces.append(src[last:m.start()])
    pieces.append(rep)
    sites.append(rep.strip())
    last = m.end()
pieces.append(src[last:])
new = "".join(pieces)

# two results that read badly as pure substitution
POST = [
    (", not claimed homogeneous", "and not claimed to be homogeneous"),
    (", not conditional on one", ", not conditional on any one"),
]
for a, b in POST:
    if a in new:
        new = new.replace(a, b, 1)

print("sites before: %d | after: %d" % (n0, len(re.findall(r"\brather than\b", new, re.I))))
print("', not' insertions: %d | 'instead of' insertions: %d"
      % (sites.count(", not"), sites.count("instead of")))
print("chars %d -> %d" % (len(src), len(new)))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
print("written", MAIN)
