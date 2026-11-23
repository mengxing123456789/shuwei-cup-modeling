# -*- coding: utf-8 -*-
"""Guard the pipeline figure block against the prose-numeral heuristic."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

start = "\\begin{figure}[t]\n\\centering\n\\includegraphics[width=0.95\\linewidth]{figures/fig_p1_pipeline.png}"
assert start in s
s = s.replace(start, "% numerals-ok: begin\n" + start, 1)

end = "\\label{fig:p1pipeline}\n\\end{figure}"
assert end in s
s = s.replace(end, end + "\n% numerals-ok: end", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("guarded pipeline figure block")
