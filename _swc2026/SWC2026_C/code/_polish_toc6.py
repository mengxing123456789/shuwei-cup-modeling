# -*- coding: utf-8 -*-
"""Final contents layout: list every section and subsection in the body at a
readable size, then close with a compact one-paragraph index of the fourteen
appendices instead of fourteen full leader lines, so the contents stays on its
single dedicated page."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

# 1. drop the scoped tocdepth switches: subsections everywhere in the body
for frag in (
    "% numerals-ok: begin\n\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{2}}\n% numerals-ok: end\n",
    "% numerals-ok: begin\n\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{1}}\n% numerals-ok: end\n",
):
    s = s.replace(frag, "", 1)

# 2. subsection entries back to \small (readable)
s = s.replace(
    "\\titlecontents{subsection}[25pt]{\\scriptsize\\rmfamily\\addvspace{-1.5pt}}%",
    "\\titlecontents{subsection}[25pt]{\\small\\rmfamily\\addvspace{-1pt}}%",
    1,
)

# 3. appendix index macro
macro = (
    "\\newcommand{\\tocappendix}[1]{\\vspace{4pt}\\noindent\\textbf{Appendices}\\par"
    "\\vspace{1pt}\\noindent\\footnotesize #1\\par}"
)
if "\\newcommand{\\tocappendix}" not in s:
    s = s.replace(
        "\\newcommand{\\tocgroup}[1]{\\vspace{3pt}\\noindent\\textbf{#1}\\par\\vspace{0pt}}",
        "\\newcommand{\\tocgroup}[1]{\\vspace{3pt}\\noindent\\textbf{#1}\\par\\vspace{0pt}}\n" + macro,
        1,
    )

appendix_index = (
    "A Notation \\textperiodcentered\\ B Key code \\textperiodcentered\\ "
    "C Reproduction commands \\textperiodcentered\\ D Closed-form calibration \\textperiodcentered\\ "
    "E Annotation audit and unseen task classes \\textperiodcentered\\ F The chain in one picture \\textperiodcentered\\ "
    "G Later experiments \\textperiodcentered\\ H The three algorithms in pseudocode \\textperiodcentered\\ "
    "I Three propositions and the seven tests between them \\textperiodcentered\\ J Assumptions register \\textperiodcentered\\ "
    "K Sensitivity of the two decision layers \\textperiodcentered\\ L Official scorecard, model ladder and re-scoring \\textperiodcentered\\ "
    "M Parameter register \\textperiodcentered\\ N Ablation and check register"
)

old = (
    "% numerals-ok: begin\n\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{1}}\n% numerals-ok: end\n"
    "\\addtocontents{toc}{\\protect\\footnotesize}\n"
    "\\addtocontents{toc}{\\protect\\tocgroup{Appendices}}"
)
new = (
    "% numerals-ok: begin\n\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{0}}\n% numerals-ok: end\n"
    "\\addtocontents{toc}{\\protect\\tocappendix{" + appendix_index + "}}"
)
assert old in s, "appendix toc block not found"
s = s.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("contents: all body subsections at small; appendices as a compact index paragraph")
