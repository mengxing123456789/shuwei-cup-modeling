# -*- coding: utf-8 -*-
"""Move the three Validation subsections from the body to a new Appendix O.

The body keeps its Results and Discussion; the validation prose is preserved
verbatim in the appendix, so nothing is lost and the 25-page limit is respected.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
main = ROOT / "main.tex"
s = main.read_text(encoding="utf-8")

blocks = {}
specs = [
    ("p1", r"\\subsection\{Validation\}\n\\label\{sec:p1val\}\n", r"\\subsection\{Discussion: where the state model fails\}"),
    ("p2", r"\\subsection\{Validation\}\n", r"\\subsection\{Discussion: the net effect of looking again\}"),
    ("p3", r"\\subsection\{Validation\}\n\\label\{sec:p3val\}\n", r"\\subsection\{Discussion\}\n\\label\{sec:p3disc\}"),
]
for name, start_pat, end_pat in specs:
    m = re.search(start_pat, s)
    assert m, f"{name}: start not found"
    m2 = re.search(end_pat, s[m.end():])
    assert m2, f"{name}: end not found"
    body = s[m.end():m.end() + m2.start()].strip()
    # P3: keep the tables/tab_maps.tex include in the body
    keep_input = ""
    if name == "p3":
        im = re.search(r"\\input\{tables/tab_maps\.tex\}", body)
        if im:
            keep_input = "\\input{tables/tab_maps.tex}\n\n"
            body = (body[:im.start()] + body[im.end():]).strip()
    blocks[name] = body
    s = s[:m.start()] + keep_input + s[m.end() + m2.start():]

notes = ["% Validation notes moved from the body during the presentation pass.",
         "% Every number is produced by the same slots as the body.",
         r"\subsection*{Validation notes moved from the body}", ""]
for name, title in (("p1", "Part I"), ("p2", "Part II"), ("p3", "Part III")):
    notes.append(r"\noindent\textbf{%s.} %s" % (title, blocks[name]))
    notes.append("")
(ROOT / "tables" / "app_notes.tex").write_text("\n".join(notes), encoding="utf-8")

anchor = "\\end{appendices}"
assert s.count(anchor) == 1
s = s.replace(anchor, "\\section{Validation notes}\n\\label{app:valnotes}\n\n\\input{tables/app_notes.tex}\n\n" + anchor)

# TOC compact list gains O
old_tail = r"\textperiodcentered\ N Ablation and check register}"
assert s.count(old_tail) == 1
s = s.replace(old_tail, r"\textperiodcentered\ N Ablation and check register \textperiodcentered\ O Validation notes}")

main.write_text(s, encoding="utf-8")
print("main.tex", len(s.encode("utf-8")), "bytes")
for k, v in blocks.items():
    print(k, len(v.split()), "words moved")
