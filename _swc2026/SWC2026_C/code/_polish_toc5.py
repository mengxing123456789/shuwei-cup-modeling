# -*- coding: utf-8 -*-
"""Show subsection entries only for the three modelling chapters (Problems
1-3), where the sub-structure carries the argument; keep chapters and the
appendix list at section level so the whole contents stays on one page."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

p1 = "\\section{Problem 1: State and Observation Reliability (Part I)}"
p6 = "\\section{Empirical Decision Limits of the Task}"
assert p1 in s and p6 in s

up = "% numerals-ok: begin\n\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{2}}\n% numerals-ok: end\n"
down = "% numerals-ok: begin\n\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{1}}\n% numerals-ok: end\n"

if "\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{2}}" not in s:
    s = s.replace(p1, up + p1, 1)
    s = s.replace(p6, down + p6, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("scoped tocdepth: 2 for Problems 1-3 only")
