# -*- coding: utf-8 -*-
"""Insert the drawio pipeline figure into the Part I solution section."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

old = "The pipeline is a chain of scripts, each writing one artefact."
new = "The pipeline is a chain of scripts, each writing one artefact (Figure~\\ref{fig:p1pipeline})."
assert old in s
s = s.replace(old, new, 1)

anchor = "frames can only merge when their clusters are adjacent in time.\n"
assert anchor in s
fig = (
    "frames can only merge when their clusters are adjacent in time.\n\n"
    "\\begin{figure}[t]\n"
    "\\centering\n"
    "\\includegraphics[width=0.95\\linewidth]{figures/fig_p1_pipeline.png}\n"
    "\\caption{The Part I pipeline: the panel is assembled once, a dilated bi-TCN cuts the "
    "32-dimensional description into boundary scores, and a constrained dynamic program turns "
    "the scores into stages, carrying one reliability weight per interval.}\n"
    "\\label{fig:p1pipeline}\n"
    "\\end{figure}\n"
)
s = s.replace(anchor, fig, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("inserted fig:p1pipeline")
