# -*- coding: utf-8 -*-
"""Tighten the contents page further so the appendix list also fits on the
single dedicated page: subsections at scriptsize, appendix entries at
footnotesize, and no extra space before the appendix group."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

s = s.replace(
    "\\titlecontents{subsection}[25pt]{\\footnotesize\\rmfamily\\addvspace{-1pt}}%",
    "\\titlecontents{subsection}[25pt]{\\scriptsize\\rmfamily\\addvspace{-1.5pt}}%",
    1,
)
s = s.replace(
    "\\addtocontents{toc}{\\protect\\small}",
    "\\addtocontents{toc}{\\protect\\footnotesize}",
    1,
)
s = s.replace(
    "\\newcommand{\\tocgroup}[1]{\\vspace{6pt}\\noindent\\textbf{#1}\\par\\vspace{1pt}}",
    "\\newcommand{\\tocgroup}[1]{\\vspace{3pt}\\noindent\\textbf{#1}\\par\\vspace{0pt}}",
    1,
)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("tightened TOC: scriptsize subsections, footnotesize appendix, compact group")
