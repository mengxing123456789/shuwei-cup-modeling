# -*- coding: utf-8 -*-
"""Second style pass, generic: split semicolons that join two independent prose
clauses, and replace the remaining discourse ordinals with ordinary nouns.
Technical ordinals (first quartile, every third frame, half a second) stay."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(os.path.dirname(HERE), "main.tex")
APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

# ---------- 1. discourse ordinals -> plain nouns --------------------------
ORD = [
    ("EgoPro and EgoStandard ship per-hand CSV tables plus MP4, the first with head stereo and both wrist views, the second with head stereo only",
     "EgoPro ships per-hand CSV tables plus MP4 with head stereo and both wrist views, and EgoStandard ships the same tables with head stereo only"),
    ("silently corrupts the first column name",
     "silently corrupts the leading column name"),
    ("the information channel of the first proposition empty",
     "the information channel of the information proposition empty"),
    ("because the first question has two halves",
     "because the state question has two halves"),
    ("For the state half the baseline is",
     "For the state half the baseline is"),
]

out = src
hits = 0
for a, b in ORD:
    pat = r"\s+".join(re.escape(t) for t in a.split())
    m = re.search(pat, out)
    if m:
        out = out[:m.start()] + b + out[m.end():]
        hits += 1
    else:
        print("ORD MISS:", a[:50])
print("ordinal rewrites: %d / %d" % (hits, len(ORD)))

# ---------- 2. generic semicolon split ------------------------------------
# A split is safe when the text on both sides is prose (no LaTeX control
# sequence, no inline math) and the right side starts with a lowercase word.
def prose(seg):
    return ("\\" not in seg) and ("$" not in seg)


pieces, last, split = [], 0, 0
for m in re.finditer(r";\s+", out):
    left = out[max(0, m.start() - 70):m.start()]
    right = out[m.end():m.end() + 70]
    nxt = out[m.end():m.end() + 1]
    if prose(left) and prose(right) and nxt.islower() and len(left.split()) >= 4:
        pieces.append(out[last:m.start()])
        pieces.append(". " + nxt.upper())
        last = m.end() + 1
        split += 1
    else:
        pieces.append(out[last:m.end()])
        last = m.end()
pieces.append(out[last:])
new = "".join(pieces)
print("generic semicolon splits: %d | total %d -> %d"
      % (split, out.count(";"), new.count(";")))

# ---------- 3. honest ordinal count --------------------------------------
def discourse_ordinals(text):
    keep = []
    for m in re.finditer(r"\b(first|second|third)\b", text, re.I):
        w = m.group(1).lower()
        before = text[max(0, m.start() - 14):m.start()].lower()
        after = text[m.end():m.end() + 8].lower()
        if w == "second" and (re.search(r"(half\s+a\s+|a\s+|one\s+|two\s+|\d\s*|quarter\s*)$", before)
                              or after.startswith(("~s", " s", "s ", "-s"))):
            continue
        if w == "third" and re.search(r"every\s+$", before):
            continue
        if w == "first" and re.search(r"(quartile|column)\s*$", after):
            continue
        keep.append(m.group(0))
    return keep


print("discourse ordinals %d -> %d" % (len(discourse_ordinals(src)),
                                       len(discourse_ordinals(new))))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
print("written", MAIN, len(src), "->", len(new))
