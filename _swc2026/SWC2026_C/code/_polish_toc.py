# -*- coding: utf-8 -*-
"""Polish pass: empty header/footer on the summary+contents pages, and a
two-level table of contents (subsections in the body, sections only in the
appendices) modelled on the alternate draft's TOC."""
import io
import sys

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

old_style = (
    "\\fancypagestyle{summarysheet}{%\n"
    "  \\fancyhf{}%\n"
    "  \\renewcommand{\\headrulewidth}{0pt}%\n"
    "  \\renewcommand{\\footrulewidth}{0pt}%\n"
    "  \\fancyfoot[R]{\\small Page \\thepage\\ of \\pageref{BodyLastPage}}}"
)
new_style = (
    "\\fancypagestyle{summarysheet}{%\n"
    "  \\fancyhf{}%\n"
    "  \\renewcommand{\\headrulewidth}{0pt}%\n"
    "  \\renewcommand{\\footrulewidth}{0pt}}"
)
assert old_style in s, "summarysheet block not found"
s = s.replace(old_style, new_style, 1)

old_depth = "\\setcounter{tocdepth}{\\slotTocDepth}"
assert old_depth in s, "tocdepth line not found"
s = s.replace(old_depth, "\\setcounter{tocdepth}{2}", 1)

old_app = "\\addtocontents{toc}{\\protect\\tocgroup{Appendices}}"
assert old_app in s, "appendix toc group not found"
s = s.replace(
    old_app,
    "\\addtocontents{toc}{\\protect\\setcounter{tocdepth}{1}}\n"
    + old_app,
    1,
)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched main.tex: summarysheet empty, tocdepth 2 in body, 1 in appendices")
