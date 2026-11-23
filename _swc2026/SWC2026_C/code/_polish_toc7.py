# -*- coding: utf-8 -*-
"""Tighten the leading of the contents page only (body leading untouched), so
the full two-level contents plus the appendix index fits one page."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

old = "\\tableofcontents\n\\thispagestyle{summarysheet}"
assert old in s
new = (
    "% numerals-ok: begin\n"
    "{\\linespread{1.0}\\selectfont\n"
    "\\tableofcontents}\n"
    "% numerals-ok: end\n"
    "\\thispagestyle{summarysheet}"
)
s = s.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("contents typeset at linespread 1.0")
