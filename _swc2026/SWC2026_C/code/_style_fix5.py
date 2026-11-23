# -*- coding: utf-8 -*-
"""Final semicolon pass. Each entry names the text immediately after a semicolon
(no braces, no math), so the substitution cannot touch LaTeX internals. Only the
semicolon and the capital of the next word change."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(os.path.dirname(HERE), "main.tex")
APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

# the text that follows the semicolon, exactly as it appears (lowercase start)
AFTER = [
    "Part III turns the error scale",
    "Sections~3--5",
    "Sections~6--8",
    "each also leaves its environment unseen",
    "Appendices~",
    "at five frames the two are",
    "weakest environment",
    "boundary error",
]

out = src
n = 0
for a in AFTER:
    pat = r";\s*\n?\s*" + re.escape(a)
    m = re.search(pat, out)
    if not m:
        print("MISS:", a)
        continue
    rep = ". " + a[:1].upper() + a[1:]
    out = out[:m.start()] + rep + out[m.end():]
    n += 1

print("splits applied: %d / %d" % (n, len(AFTER)))
print("semicolons %d -> %d" % (src.count(";"), out.count(";")))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(out)
print("written", MAIN)
