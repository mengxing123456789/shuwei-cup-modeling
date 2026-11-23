import io

A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()
a = a.replace(r"Section~\ref{sec:p2} locates", r"Section~\ref{sec:p2model} locates")
io.open(A, "w", encoding="utf-8", newline="").write(a)
print("fixed sec:p2 ref")

P = "main.tex"
t = io.open(P, encoding="utf-8").read()
old = r"""\begin{subfigure}{0.49\linewidth}
\centering
\includegraphics[width=\linewidth]{figures/fig2_bad_ratio.png}
\caption{bad frames per record}
\end{subfigure}\hfill
\begin{subfigure}{0.49\linewidth}
\centering
\includegraphics[width=\linewidth]{figures/fig3_segmentation.png}
\caption{ARI gain of the learned decoder}
\end{subfigure}"""
new = r"""\begin{subfigure}{0.42\linewidth}
\centering
\includegraphics[width=\linewidth]{figures/fig2_bad_ratio.png}
\caption{bad frames per record}
\end{subfigure}\hfill
\begin{subfigure}{0.42\linewidth}
\centering
\includegraphics[width=\linewidth]{figures/fig3_segmentation.png}
\caption{ARI gain of the learned decoder}
\end{subfigure}"""
if old not in t:
    raise SystemExit("subfigure anchor missing")
t = t.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("shrunk subfigures to 0.42")
