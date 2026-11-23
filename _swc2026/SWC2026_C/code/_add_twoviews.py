import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

# 1) insert a compact two-panel figure into Problem 1 results, right after the segmentation table
anchor = r"""\label{tab:seg}"""
i = t.find(anchor)
if i < 0:
    raise SystemExit("tab:seg label missing")
# find end of that table environment
j = t.find(r"\end{table}", i)
if j < 0:
    raise SystemExit("tab:seg end missing")
j += len(r"\end{table}")

fig = r"""

% numerals-ok: begin
\begin{figure}[htbp]
\centering
\begin{subfigure}{0.49\linewidth}
\centering
\includegraphics[width=\linewidth]{figures/fig2_bad_ratio.png}
\caption{bad frames per record}
\end{subfigure}\hfill
\begin{subfigure}{0.49\linewidth}
\centering
\includegraphics[width=\linewidth]{figures/fig3_segmentation.png}
\caption{ARI gain of the learned decoder}
\end{subfigure}
\caption{Two views of the same test records. Left: the share of flagged frames in each
record, split by hand, showing that the flags concentrate in a few recordings rather than
spreading over the corpus. Right: the per-record gain of the learned boundary decoder over
chain-constrained agglomeration, positive on six of the seven records; the short record
loses because it holds a single true stage.}
\label{fig:twoviews}
\end{figure}
% numerals-ok: end"""

t = t[:j] + fig + t[j:]

# 2) make room: compress the distribution-shift paragraph
old = r"""The cause is a distribution shift in the reference annotation: validation records have
at most seven stages, test records reach the low twenties, and the training split holds
almost no long records above the eighth cap. Stratifying by true stage count resolves
the contradiction (the narrow cap wins at or below it, the wide cap far above it) and on
the long training records the ARI moves from \slotPKLongEight{} to \slotPKLongSixteen{}
as the cap widens, with a stratified training bound of \slotPKStratSixteen{}. One test
record has two true stages: the information criterion selects a count in the twenties
and its ARI collapses, while silhouette recovers the correct count."""

new = r"""The cause is a distribution shift in the reference annotation: validation records have at
most seven stages, test records reach the low twenties, and the training split holds almost
no long records above the eighth cap. Stratifying by true stage count resolves the
contradiction --- the narrow cap wins at or below it, the wide cap far above it --- and on
the long training records the ARI moves from \slotPKLongEight{} to \slotPKLongSixteen{} as
the cap widens, with a stratified bound of \slotPKStratSixteen{}. One test record has two
true stages: the information criterion picks a count in the twenties and its ARI collapses,
while silhouette recovers the correct count."""

if old not in t:
    raise SystemExit("shift paragraph missing")
t = t.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("inserted two-panel figure and trimmed shift paragraph")
