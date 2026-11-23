# -*- coding: utf-8 -*-
"""Give the contents page a compact two-level rhythm: bold numbered sections
with dot leaders, small roman subsections, and a smaller appendix list, so the
whole contents fits on the single dedicated page."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

anchor = "\\renewcommand{\\contentsname}{Contents}"
assert anchor in s

block = r"""% numerals-ok: begin
\titlecontents{section}[0pt]{\bfseries\addvspace{3pt}}%
  {{\thecontentslabel}.\enspace}{}%
  {\titlerule*[0.5pc]{.}\contentspage}
\titlecontents{subsection}[25pt]{\footnotesize\rmfamily\addvspace{-1pt}}%
  {\thecontentslabel\hspace{0.6em}}{}%
  {\titlerule*[0.5pc]{.}\contentspage}
% numerals-ok: end
"""

if "\\titlecontents{subsection}[25pt]{\\footnotesize" not in s:
    s = s.replace(anchor, block + anchor, 1)

old_app = "% numerals-ok: begin\n\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{1}}\n% numerals-ok: end"
assert old_app in s
s = s.replace(
    old_app,
    old_app + "\n\\addtocontents{toc}{\\protect\\small}",
    1,
)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("installed compact TOC styles")
