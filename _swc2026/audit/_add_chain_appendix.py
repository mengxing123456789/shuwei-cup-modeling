"""Appendix F: the chain figure drawn with the canvas editor, plus a one-clause pointer in
the notation section that pays for itself with a shorter phrase on the line above."""

import io
import os

MAIN = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"
t = io.open(MAIN, encoding="utf-8", newline="").read()

old = r"""Three claims are stated in this language and each is settled later on evidence
rather than asserted. The phase is identifiable from geometry only when the stages
separate, which is tested and refuted in Section~\ref{sec:p1res}. The reservation
cancels out of the punctuality probability once the start time is fixed, which is
derived in Section~\ref{sec:p3closed}. The released prefix carries almost no
information about $d$, which is measured in Section~\ref{sec:p2res}.
"""
new = r"""Three claims are stated in this language and each is settled later on evidence
rather than asserted. The phase is identifiable from geometry only when the stages
separate, tested and refuted in Section~\ref{sec:p1res}. The reservation cancels out of
the punctuality probability once the start time is fixed, derived in
Section~\ref{sec:p3closed}. The released prefix carries almost no information about $d$,
measured in Section~\ref{sec:p2res}. Figure~\ref{fig:chain} in Appendix~F draws the chain.
"""
assert t.count(old) == 1, "notation paragraph: %d" % t.count(old)
t = t.replace(old, new)

old = "\\end{document}\n"
new = r"""\addcontentsline{toc}{section}{Appendix F: The chain in one picture}
\section*{Appendix F: The chain in one picture}
\label{app:chain}

\begin{figure}[htbp]
\centering
\resizebox{0.92\linewidth}{!}{\includegraphics{figures/chain.png}}
\caption{The chain as the paper uses it, read top to bottom: the observation becomes a latent
state, the state supports two forecasts, and the forecasts feed one decision. The right-hand
boxes are the claims each stage is tested against; a dashed line is an evidence path, not a
data flow. The editing source of this figure is the canvas file \texttt{figures/chain.drawio}.}
\label{fig:chain}
\end{figure}

% numerals-ok: begin
The picture is a map of the argument rather than a pipeline diagram. Every arrow on the left
is a place where a quantity is handed over, and every box on the right is a place where the
handed-over quantity is checked against the record: Claim 1 by the four statistics of
Section~\ref{sec:p1res}, Claim 2 by the calibration of the closed form in
Section~\ref{sec:p3closed} and Appendix~D, Claim 3 by the prefix experiments of
Section~\ref{sec:p2res}. The two forecasts are the only place where Part~II returns a number,
and the decision box is the only place where Part~III consumes one.
% numerals-ok: end

\end{document}
"""
assert t.count(old) == 1, "tail: %d" % t.count(old)
t = t.replace(old, new)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("written", os.path.getsize(MAIN), "bytes")