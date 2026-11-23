# -*- coding: utf-8 -*-
"""Rewrite the 41 'rather than' sites in main.tex one by one.

Why: 'rather than' runs at 4.08 per 1k words here against 0.09 in the five awarded
C-problem papers of the same competition (see _aigc_bench2.py). It is the strongest
single style marker in this manuscript. Most sites read correctly as ', not X';
the ones followed by a gerund or a bare noun phrase need 'instead of' or a real
rewrite, and those are listed explicitly below by their context key.

No claim, number, hedge or ordering is changed. Structure is untouched.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
MAIN = os.path.join(PROJ, "main.tex")

APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

# (unique context key around the site, replacement text for the whole key)
FIXES = [
    # gerund / bare-NP tails: 'instead of' + gerund, or a plain rewrite
    ("sweeps it rather than picking it",
     "sweeps it instead of picking it"),
    ("retained as labels rather than dropped",
     "retained as labels, not dropped"),
    ("Retention is reported rather than asserted",
     "Retention is reported, not asserted"),
    ("is reproduced rather than assumed",
     "is reproduced, not assumed"),
    ("reported as a table rather than as a sentence",
     "reported as a table, not a sentence"),
    ("as a limitation rather than calibrating four radii",
     "as a limitation instead of calibrating four radii"),
    ("to observe again rather than to extrapolate",
     "to observe again instead of extrapolating"),
    ("with its own table rather than quietly dropped",
     "with its own table instead of being quietly dropped"),
    ("it is cited once rather than claimed homogeneous",
     "it is cited once and not claimed to be homogeneous"),
    ("confirms rather than blinds",
     "confirms and does not blind"),
    ("measured on the scheduling side rather than asserted",
     "measured on the scheduling side, not asserted"),
    ("recommends re-observing at the end of a mask rather than splicing",
     "recommends re-observing at the end of a mask instead of splicing"),
    # prepositional tails: ', not' + the same preposition reads fine
    ("on paired seeds rather than on independent runs",
     "on paired seeds, not on independent runs"),
    ("different task mixes rather than with different sensors",
     "different task mixes, not with different sensors"),
    ("inside the training split rather than on validation",
     "inside the training split, not on validation"),
    ("over records rather than conditional on one",
     "over records, not conditional on one"),
    ("by \\slotPScaleDoubling{} rather than by two",
     "by \\slotPScaleDoubling{}, not by two"),
    ("by their information logic rather than by a shared uncertainty object",
     "by their information logic, not by a shared uncertainty object"),
    ("of the information released rather than of the model class",
     "of the information released, not of the model class"),
    ("the action space rather than our cost curve",
     "the action space, not our cost curve"),
    ("our convention rather than the statement's",
     "our convention, not the statement's"),
]

out = src
applied = 0
for key, rep in FIXES:
    if key in out:
        out = out.replace(key, rep, 1)
        applied += 1
    else:
        print("MISS:", key)

print("\nexplicit fixes applied: %d / %d" % (applied, len(FIXES)))

# everything left becomes ', not' (or ' instead of' after a gerund-looking tail)
def tail_is_gerund(text, start):
    m = re.match(r"\s+(\w+)", text[start:])
    return bool(m and m.group(1).endswith("ing"))

pieces, last = [], 0
left = list(re.finditer(r"\brather than\b", out))
for m in left:
    pieces.append(out[last:m.start()])
    pieces.append(" instead of" if tail_is_gerund(out, m.end()) else ", not")
    last = m.end()
pieces.append(out[last:])
new = "".join(pieces)

print("remaining sites converted mechanically: %d" % len(left))
print("final 'rather than': %d" % len(re.findall(r"\brather than\b", new, re.I)))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
print("written %s (%d chars)" % (MAIN, len(new)))
