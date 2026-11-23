# -*- coding: utf-8 -*-
"""Reduce the remaining discourse ordinals ('first/second/third' used to
enumerate or to mean 'earliest') to ordinary nouns. Technical uses stay:
'first quartile', 'every third frame', 'a second look', 'a second independent
fit', 'first epoch'. Each key must occur exactly once."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(os.path.dirname(HERE), "main.tex")
APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

FIX = [
    ("the fixed-interval rule is the third comparison the statement names",
     "the fixed-interval rule completes the three comparisons the statement names"),
    ("the first truly observed one",
     "the earliest truly observed one"),
    ("between the free prefix and the first paid review",
     "between the free prefix and the earliest paid review"),
    ("the first \\slotPFreePrefix", "the opening \\slotPFreePrefix"),
    ("taking weighted on-time rate first and cost second",
     "taking weighted on-time rate ahead of cost"),
    ("were scored on the first fifteen seeds only",
     "were scored on the earlier fifteen seeds only"),
    ("a third is the train-to-validation shift",
     "a further one is the train-to-validation shift"),
    ("the ranking is weighted-on-time-first",
     "the ranking puts weighted on-time ahead"),
    ("that removed the largest error in our first draft",
     "that removed the largest error in the draft of this paper"),
    ("Second-round experiments", "Later experiments"),
]

out = src
n = 0
for a, b in FIX:
    pat = r"\s+".join(re.escape(t) for t in a.split())
    hits = list(re.finditer(pat, out))
    if not hits:
        print("MISS:", a[:52])
        continue
    if len(hits) > 1:
        print("MULTI(%d): %s -> replacing all" % (len(hits), a[:40]))
        for m in reversed(hits):
            out = out[:m.start()] + b + out[m.end():]
    else:
        m = hits[0]
        out = out[:m.start()] + b + out[m.end():]
    n += 1

print("rewrites applied: %d / %d" % (n, len(FIX)))
print("raw ordinals %d -> %d"
      % (len(re.findall(r"\b(first|second|third)\b", src, re.I)),
         len(re.findall(r"\b(first|second|third)\b", out, re.I))))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(out)
print("written", MAIN)
