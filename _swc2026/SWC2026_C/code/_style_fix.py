# -*- coding: utf-8 -*-
"""Bring three style markers inside the range the five awarded C-problem papers
occupy (see _aigc_bench2.py): split semicolons into sentences, drop the
'First,/Second,/Third,' discourse enumerators, and delete redundant
'therefore/thus/hence'. No number, claim, hedge or ordering is touched."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(os.path.dirname(HERE), "main.tex")
APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

# ---- 1. discourse enumerators -> plain clause openings -------------------
ENUM = [
    ("First, the service time is a deterministic affine map",
     "The service time is a deterministic affine map"),
    ("Second, the information rule forbids looking at the future",
     "The information rule forbids looking at the future"),
    ("Third, source sampling is uniform within a job's family",
     "Source sampling is uniform within a job's family"),
    ("The first asks what the bad-frame flag contains",
     "One question asks what the bad-frame flag contains"),
    ("The second asks what an unseen task class costs",
     "The other asks what an unseen task class costs"),
    ("The second half of the mechanism is also measured",
     "The other half of the mechanism is also measured"),
    ("The first version of this paper trained one model per task",
     "The draft of this paper trained one model per task"),
    ("so the second round trained four families",
     "so a later round trained four families"),
    ("A second-round detector, adding left-right symmetric augmentation",
     "A later detector, adding left-right symmetric augmentation"),
    ("is the first item in the failure list",
     "is the leading item in the failure list"),
]

# ---- 2. redundant therefore / thus / hence -------------------------------
CONN = [
    ("We therefore work in the head frame", "We work in the head frame"),
    ("We therefore claim no better agglomerative partition",
     "We claim no better agglomerative partition"),
    ("Part II is therefore not a fitting problem",
     "Part II is not a fitting problem"),
    ("Free waiting thus dominates not waiting", "Free waiting dominates not waiting"),
    ("The two curves are therefore reported separately",
     "The two curves are reported separately"),
    ("Section~\\ref{sec:limits} therefore reads the gap",
     "Section~\\ref{sec:limits} reads the gap"),
    ("A reader can therefore rerun any number",
     "A reader can rerun any number"),
]

def sub_flexible(text, needle, repl):
    """Replace needle allowing any run of whitespace (including line breaks)
    between its tokens, which is what LaTeX source actually contains."""
    toks = needle.split()
    pat = r"\s+".join(re.escape(t) for t in toks)
    m = re.search(pat, text)
    if not m:
        return text, False
    return text[:m.start()] + repl + text[m.end():], True


out = src
hits = 0
for a, b in ENUM + CONN:
    out, ok = sub_flexible(out, a, b)
    if ok:
        hits += 1
    else:
        print("MISS:", a[:60])
print("explicit rewrites applied: %d / %d" % (hits, len(ENUM) + len(CONN)))

# ---- 3. split semicolons that join two plain prose clauses ---------------
def prose_after(text, pos, span=90):
    seg = text[pos:pos + span]
    return ("\\" not in seg) and ("$" not in seg)


pieces, last, split = [], 0, 0
for m in re.finditer(r";\s+", out):
    nxt = out[m.end():m.end() + 1]
    if prose_after(out, m.end()) and nxt.islower():
        pieces.append(out[last:m.start()])
        pieces.append(". " + nxt.upper())
        last = m.end() + 1
        split += 1
    else:
        pieces.append(out[last:m.end()])
        last = m.end()
pieces.append(out[last:])
new = "".join(pieces)
print("semicolons split: %d" % split)

for name, pat in [("semicolon", r";"), ("rather than", r"\brather than\b"),
                  ("therefore/thus/hence", r"\b(therefore|thus|hence)\b"),
                  ("first/second/third", r"\b(first|second|third)\b")]:
    print("%-24s %d -> %d" % (name, len(re.findall(pat, src, re.I)),
                              len(re.findall(pat, new, re.I))))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
print("written", MAIN, len(src), "->", len(new))
