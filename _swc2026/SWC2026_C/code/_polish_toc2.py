# -*- coding: utf-8 -*-
"""Wrap the two literal tocdepth numerals in numerals-ok guards so the prose
numeral gate does not flag them, then report the TOC page extent."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

a = "\\setcounter{tocdepth}{2}"
assert a in s
s = s.replace(a, "% numerals-ok: begin\n" + a + "\n% numerals-ok: end", 1)

b = "\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{1}}"
assert b in s
s = s.replace(b, "% numerals-ok: begin\n" + b + "\n% numerals-ok: end", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("guarded tocdepth numerals")
