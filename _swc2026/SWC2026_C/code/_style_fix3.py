# -*- coding: utf-8 -*-
"""Generic prose-semicolon split for main.tex.

A semicolon is split only when the 30 characters on each side contain no LaTeX
control sequence, no inline math and no braces, and the right-hand side starts
lowercase. That leaves the definitional list in the notation paragraph, the
parallel code lists in Solution paragraphs, and every semicolon inside math
untouched. Single pass, so offsets never shift.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(os.path.dirname(HERE), "main.tex")
APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

W = 30


def clean(seg):
    return ("\\" not in seg) and ("$" not in seg) and ("{" not in seg)


parts, last, n = [], 0, 0
for m in re.finditer(r";(\s+)", src):
    left = src[max(0, m.start() - W):m.start()]
    right = src[m.end():m.end() + W]
    nxt = src[m.end():m.end() + 1]
    parts.append(src[last:m.start()])
    if clean(left) and clean(right) and nxt.islower() and len(left.split()) >= 3:
        parts.append(". " + nxt.upper())
        last = m.end() + 1
        n += 1
    else:
        parts.append(";" + m.group(1))
        last = m.end()
parts.append(src[last:])
new = "".join(parts)

print("splits: %d | semicolons %d -> %d" % (n, src.count(";"), new.count(";")))
print("chars %d -> %d" % (len(src), len(new)))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
print("written", MAIN)
