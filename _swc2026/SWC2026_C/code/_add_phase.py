import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

anchor = (r"The full table, one row per policy and one column per measure, is "
          r"Table~\ref{tab:p3score} in Appendix~\ref{app:ablation}.")
if anchor not in t:
    raise SystemExit("anchor missing")

fig = r"""
% numerals-ok: begin
\begin{figure}[htbp]
\centering
\resizebox{0.80\linewidth}{!}{\includegraphics{figures/fig9_phase.png}}
\caption{Phase diagram of the reservation, on the same seeds as the tables. Rows are the
service multiplier, columns the residual quantile; the upper row is the weighted on-time
rate and the lower row the mean cost. The horizontal gradient is small and one-signed, the
vertical gradient is large: the service law moves the rate and the reservation only spends
it.}
\label{fig:phase}
\end{figure}
% numerals-ok: end
"""

if r"\label{fig:phase}" in t:
    raise SystemExit("phase figure already in body")

t = t.replace(anchor, anchor + "\n" + fig)
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("phase figure re-inserted into body")
