"""Claim-first presentation: the answer table in Section 1, the cost-threshold result in
Section 3.3, and one table of rejected moves in Appendix E."""

import io
import os

MAIN = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"
t = io.open(MAIN, encoding="utf-8", newline="").read()

EDITS = []

# ---------------------------------------------------------------- 1. preamble
old = "\\documentclass{swmcmthesis}\n"
new = ("\\documentclass{swmcmthesis}\n"
       "\\renewcommand{\\arraystretch}{0.94}\n")
EDITS.append(("preamble", old, new))

# ------------------------------------------------- 2. Section 1.2 plus the answer table
old = r"""\textbf{Part I} asks for a state, a reliability notion, a reproducible baseline and
failure cases, noting that a qualified record is a reference, not ground truth.
\textbf{Part II} asks how error grows once observation stops and when a new look is
worth its cost, with windows, budgets, per-request costs and return delays fixed in
advance and no use of information before its delay elapses. \textbf{Part III} asks
for a policy under an unknown service time with a reserved buffer, a paid review
budget and a capacity limit, on the official seeds.

Part I gives a point and a soft weight, Part II predicts that point and prices the next
look, Part III consumes the price and the error scale but not the trajectory. The weight was
carried across and moved the prediction by millimetres, as Section~\ref{sec:p2res} reports.
"""
new = r"""\textbf{Part I} asks for a state, a reliability notion, a reproducible baseline and
failure cases, noting that a qualified record is a reference, not ground truth.
\textbf{Part II} asks how error grows once observation stops and when a new look is worth
its cost, with windows, budgets, per-request costs and return delays fixed in advance.
\textbf{Part III} asks for a policy under an unknown service time with a reserved buffer, a
paid review budget and a capacity limit, on the official seeds. Table~\ref{tab:answers}
states what each part concludes before any of it is derived.

Part I gives a point and a soft weight, Part II predicts that point and prices the next
look, Part III consumes the price and the error scale but not the trajectory.

\begin{table}[htbp]
\centering
\caption{The three questions, the single number each rests on, where it is established and
the condition under which it fails.}
\label{tab:answers}
% numerals-ok: begin
\small
\begin{tabular}{p{0.22\linewidth}p{0.26\linewidth}p{0.10\linewidth}p{0.32\linewidth}}
\toprule
Question & Answer & Shown in & Where it fails \\
\midrule
P1: is the hand state recoverable? & stage agreement \slotPSegGPUARI, boundary F1
\slotPSegGPUBFOne & Sec.~3.3, App.~C & records of one stage, which the decoder splits \\
P2: does a request buy information? & no: \slotPFrPaidOne{} against \slotPFrFreeWait{} cm,
interval covering zero & Sec.~4.2, App.~D & the second request, which shortens the horizon and
pays \\
P3: what is the truth worth? & \slotPOracleGapSTwo{} and \slotPOracleGapSThree{} points
inside one rule & Sec.~5, 6 & nothing measured: small, but the interval excludes zero \\
\bottomrule
\end{tabular}
% numerals-ok: end
\end{table}
"""
EDITS.append(("sec1.2+answers", old, new))

# ------------------------------------------- 3. cost minimisation replaces the recommended tau
old = r"""We report no Brier score for this route, and the omission is a finding: a Brier score is a
proper scoring rule and therefore punishes a mis-calibrated probability \cite{gneiting2007},
whereas the weight was built to rank. The same arithmetic that stops this route from being a probability is worked
through in Appendix~D; it is why we use the weight as a filter and never
as a probability. Tightening to $\tau=\slotPTauFourTau$ keeps \slotPTauFourRetained{}\% of frames at
recall \slotPTauFourRecall{}\%, the operating point we recommend.
"""
new = r"""We report no Brier score for this route, and the omission is a finding: a Brier score
punishes a mis-calibrated probability \cite{gneiting2007}, whereas the weight was built to
rank, and Appendix~D works through the arithmetic that keeps it from being a probability.

Offered a threshold to choose, the weight refuses one. With the asymmetric cost
$\kappa(\tau)=\big(k(\tau)+r\,g(\tau)\big)/n$ on the validation split, where $k$ counts bad
frames kept and $g$ good frames dropped, no ratio from \slotPCostRatioLow{} to
\slotPCostRatioHigh{} selects an interior $\tau$: above the smallest ratio the minimiser keeps
every frame at \slotPCostKeepAll, and at that ratio it drops every frame at
\slotPCostDropAll. Ranking is invariant to calibration as well, the three scores agreeing to
the last digit, so the customary calibrated $0.5$ cut would drop most of the training set at
\slotPCostHalfMult{} times the cost of keeping it all. The filter therefore exists and cost
minimisation says it should not be used, which is why the weight enters Part II as a weight.
"""
EDITS.append(("sec3.3-cost", old, new))

# --------------------------------------------- 4. rejected moves, kept out of the body budget
old = r"""\end{document}
"""
new = r"""\subsection*{What was tried, measured and rejected}

\begin{table}[htbp]
\centering
\caption{Seven moves that were built and measured before being rejected, the bar each had to
pass and what its failure rules out. The bars were fixed before the runs; the numbers appear
with the slots that own them.}
\label{tab:negatives}
\footnotesize
\begin{tabular}{p{0.24\linewidth}p{0.26\linewidth}p{0.22\linewidth}p{0.20\linewidth}}
\toprule
Move & Bar set before the run & Outcome & What it rules out \\
\midrule
mask channel, held or interpolated & beat the clean arm at six masked frames &
\slotPCleanSix{} / \slotPLocfSix{} / \slotPInterpSix{} cm & input-side robustness \\
sample weight from reliability & paired gain over clean-only &
\slotPRelArmA{} against \slotPRelArmB{} cm, interval covering zero & the weight as a signal \\
self-supervised pretraining & ten per cent at one and two seconds, three seeds &
worse in every seed & initialisation as the limit \\
raising the segment cap & beat the frozen baseline on validation &
\slotPSegWardARI{} at the selected cap & a larger hypothesis class \\
task-difference statistic & rank boundaries by stage difference &
no statistic above \slotPIdSpearmanMax & distinguishability as detectability \\
calibrated probability at half & cost below keep-everything &
\slotPCostHalfMult{} times the cost & a threshold as a consumer of probability \\
duration-aware reference & beat the adaptive rule &
\slotPOracleGapSTwo{} and \slotPOracleGapSThree{} points & knowledge as the headroom \\
\bottomrule
\end{tabular}
\end{table}

\emph{The five other negative results that shape the text are the unreported $0.6$ s prefix,
the two-request frontier when the cost of a request is set to zero, the per-environment spread
of the conformal radius, the plan-level advantage of the learned duration model, and the
absence of a usable skill label in the segmentation annotation; each is stated where it bears
on a claim.}

\end{document}
"""
EDITS.append(("appendix-negatives", old, new))

for name, old, new in EDITS:
    n = t.count(old)
    assert n == 1, "%s: matched %d times" % (name, n)
    t = t.replace(old, new)
    print("EDIT %-20s ok" % name)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("written", os.path.getsize(MAIN), "bytes")