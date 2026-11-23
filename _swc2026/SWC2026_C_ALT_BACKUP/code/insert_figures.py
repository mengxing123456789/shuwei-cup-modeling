# -*- coding: utf-8 -*-
"""Insert the five figure blocks into main.tex by section anchor lines."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"

F_FRAME = r"""\begin{figure}[htbp]\centering
\includegraphics[width=1.0\linewidth]{figures/fig0_framework.pdf}
\caption{The three layers share one state definition. A record is reduced to a
panel indexed by (record, time) with 21 keypoints and two hands in the head frame;
Q1 segments it and scores each segment, Q2 filters it under masking, and Q3 turns
durations into reservations. The two cross-question links are the Q1 posterior
variance, which enters Q2 as process noise, and the Q1 reliability, which enters Q3
as the reservation floor.}
\label{fig:framework}
\end{figure}
"""

F_P1 = r"""\begin{figure}[htbp]\centering
\includegraphics[width=1.0\linewidth]{figures/fig1_p1_agreement.pdf}
\caption{Boundary agreement and coverage. (a) Greedy one-to-one $F_1$ against the
280 annotated boundaries at four tolerances; the fixed-threshold baseline is better
at strict tolerance. (b) Share of annotated segments that contain at least one
detected change point, at three tolerances. Coverage is bought with
over-segmentation: BOCPD returns 1.14 detections per annotated segment against 0.79
for the threshold.}
\label{fig:p1agree}
\end{figure}

\begin{figure}[htbp]\centering
\includegraphics[width=1.0\linewidth]{figures/fig2_p1_reliability.pdf}
\caption{The reliability layer against an external label. The positive class is a
segment that contains at least one bad frame (51 of 349, prevalence 14.6\%). The
record-level posterior bound separates them (AUC 0.914) while the released
\texttt{eligible} flag is indistinguishable from chance (AUC 0.490). The outer bar
is AUC; the dark inner bar is the best achievable $F_1$ at the optimal threshold.}
\label{fig:p1rel}
\end{figure}
"""

F_P2 = r"""\begin{figure}[htbp]\centering
\includegraphics[width=1.0\linewidth]{figures/fig3_p2_error.pdf}
\caption{Mean 3D error against the hidden-window length on the seven test records,
300 windows per length, prefix 0.2~s. Annotations below the blue points give the
factor by which constant-velocity extrapolation exceeds the damped filter. The
damped filter is never worse than holding the last state and is a factor of 2.3
better than ballistic extrapolation at the longest window.}
\label{fig:p2err}
\end{figure}

\begin{figure}[htbp]\centering
\includegraphics[width=1.0\linewidth]{figures/fig4_p2_voi.pdf}
\caption{The three information options of the statement. Because the position
covariance of a linear--Gaussian filter does not depend on the observations, the
second look is worth exactly as much as the first, so the value of information is a
step function: buy none or buy both. The dashed line joins the two interior points
of the frontier; the break-even price is annotated.}
\label{fig:p2voi}
\end{figure}
"""


def insert_before(lines: list[str], marker: str, block: str, guard: str, nth: int = 0) -> list[str]:
    if guard in "".join(lines):
        print(f"  skip {guard} (already present)")
        return lines
    hits = [i for i, ln in enumerate(lines) if marker in ln]
    if len(hits) <= nth:
        raise SystemExit(f"anchor not found: {marker!r} #{nth}")
    i = hits[nth]
    return lines[:i] + block.splitlines(True) + ["\n"] + lines[i:]


def main() -> int:
    lines = TEX.read_text(encoding="utf-8").splitlines(True)

    lines = insert_before(
        lines,
        "\\section{A Unified View: Events, Observability, Decisions}",
        F_FRAME,
        "fig:framework",
    )
    lines = insert_before(
        lines, "\\subsection{Robustness and Conclusion}", F_P1, "fig:p1agree", nth=0
    )
    lines = insert_before(
        lines, "\\subsection{Robustness and Conclusion}", F_P2, "fig:p2err", nth=1
    )

    text = "".join(lines)
    TEX.write_text(text, encoding="utf-8", newline="\n")
    print(f"main.tex now {TEX.stat().st_size} B")
    print(f"includegraphics: {text.count('includegraphics')}")
    print(f"figure envs: {text.count(chr(92) + 'begin{figure}')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
