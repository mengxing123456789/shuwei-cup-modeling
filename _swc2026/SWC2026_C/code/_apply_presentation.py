# -*- coding: utf-8 -*-
"""Apply the A1/A3/C1/C2 presentation edits to main.tex in one pass.

Every replacement asserts that its anchor occurs exactly once, so a silent
no-op is impossible.
"""
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "main.tex"
s = P.read_text(encoding="utf-8")


def sub(old, new, tag):
    global s
    n = s.count(old)
    assert n == 1, f"{tag}: anchor occurs {n} times"
    s = s.replace(old, new)


# ---------------------------------------------------------------- A1 figure: timeline
anchor = ("carries \\slotPStateInfoBits{} bits of memory. It is not a Markov chain, and a model that\n"
          "treats the stage as independent per frame throws that memory away.\n")
fig_timeline = anchor + r"""
\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{figures/fig_stage_timeline.png}
\caption{One held-out record, from the first to the last retained frame: wrist speed
(top), hand aperture (middle) and the rule-derived stage of the left hand (bottom).
The shaded spans repeat the five stages, and the figure is the record used as the
running example in this section.}
\label{fig:stagetime}
\end{figure}
"""
sub(anchor, fig_timeline, "timeline")

# ---------------------------------------------------------------- A1 figure: stage share
anchor = ("the panel with their labels, because dropping them would delete the only examples of\n"
          "the failure the reliability model exists to detect.\n")
fig_share = anchor + r"""
\begin{figure}[htbp]
\centering
\includegraphics[width=0.72\linewidth]{figures/fig_stage_share.png}
\caption{Stage composition by recording format. The same five stages occur in every
format; their proportions follow the task mix, which is why a pooled prior is a
compromise rather than a description.}
\label{fig:stageshare}
\end{figure}
"""
sub(anchor, fig_share, "stageshare")

# ---------------------------------------------------------------- A1 figure: boundary score
anchor = ("detector finds boundaries more accurately but cuts more of them, and one record with a single\n"
          "true stage is over-segmented until its ARI collapses, the failure the count study diagnosed\n"
          "and kept in the average rather than dropped. Table~\\ref{tab:kcap} in Appendix~D reports the\n"
          "count sweep in full.\n")
fig_score = anchor + r"""
\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{figures/fig_boundary_score.png}
\caption{The learned boundary score on one held-out record (solid) against the annotated
segment boundaries (dashed). The score peaks near true boundaries but also fires inside
long stages, which is why the limiting quantity is boundary precision rather than
boundary recall.}
\label{fig:bscore}
\end{figure}
"""
sub(anchor, fig_score, "boundary score")

# ---------------------------------------------------------------- A1 figure: value ladder (moved from Appendix K)
anchor = ("over-reserves a tight budget; the prefix regression (\\slotPDurSelTestMAE{} s against\n"
          "\\slotPDurFreeBaseMAE{} s) agrees the gain is the policy's.\n")
fig_value = anchor + r"""
\begin{figure}[htbp]
\centering
\includegraphics[width=0.92\linewidth]{figures/fig10_value_ladder.png}
\caption{Value ladder of the four mechanisms in weighted on-time points, nominal mapping
and thirty seeds. Dark bars are Case S2, light bars Case S3. A positive bar is
punctuality bought; a negative bar is punctuality spent. The scheduling rule is worth
\slotPValueRuleSTwo{} and \slotPValueRuleSThree{} points, the true duration
\slotPValueTruthSTwo{} and \slotPValueTruthSThree{}, the paid review nothing detectable,
and a reservation raised from the 0.30 to the 0.90 quantile costs
\slotPValueReserveSTwo{} and \slotPValueReserveSThree{} points.}
\label{fig:value}
\end{figure}
"""
sub(anchor, fig_value, "value ladder")

# ---------------------------------------------------------------- A3 assumptions
anchor = ("What the protocol leaves open is metric aggregation (a vector, not a scalar), the tie-break\n"
          "between rate and cost, and jobs that cannot finish inside the horizon. We prefer weighted\n"
          "on-time rate to cost, keep every job in the denominators, and charge the horizon as the\n"
          "completion time.\n")
assumptions = anchor + r"""
\subsection{Assumptions}
\label{sec:assumptions}

The model rests on eight assumptions. Each is stated where it is first used, and
Appendix~\ref{app:assumptions} registers it against the evidence that supports it.

\begin{enumerate}
\item Source annotations are the reference for hand state. No product-state label is
released, so a completed grasp is evidence about the hand, never about the shelf.
\item The 21-keypoint skeleton is a usable proxy for hand configuration; residual
calibration error enters through the reliability weight rather than being ignored.
\item The three recording formats can be mapped into one head-centred panel under the
documented coordinate convention; format-specific residual error is treated as a
dataset effect and reported, not pooled away.
\item The service time of a job is affine in its source duration, with the published
mapping coefficients; the coefficients are inputs, not quantities we estimate.
\item Review delay and review cost are fixed by the protocol and do not depend on
system load.
\item Job durations are independent across jobs within a case, and the official
sampler with replacement is the correct description of the arrival process.
\item A stage is a property of the hand trajectory alone; object and task context can
shift its timing but not its definition.
\item Conclusions are about the ordering of policies and mechanisms, not about the
absolute on-time rate of any particular warehouse.
\end{enumerate}
"""
sub(anchor, assumptions, "assumptions")

# ---------------------------------------------------------------- C1 data insight paragraphs
anchor1 = ("\\section{Problem 1: State and Observation Reliability (Part I)}\n"
           "\\label{sec:partone}\n"
           "% numerals-ok: end\n"
           "\\end{comment}\n")
# the actual file has no comment block; use the real tail
anchor1 = ("\\section{Problem 1: State and Observation Reliability (Part I)}\n"
           "\\label{sec:partone}\n"
           "% numerals-ok: end\n"
           "\\iftrue\n")
# fall back: locate by section line and insert after the label block
import re
m = re.search(r"\\section\{Problem 1: State and Observation Reliability \(Part I\)\}\n\\label\{sec:partone\}\n% numerals-ok: end\n", s)
assert m, "P1 heading not found"
ins1 = r"""
\paragraph{Data insight.} The state question is a bookkeeping question before it is a
learning question. Of \slotDataNFrames{} time-stamped frames from \slotNRecords{}
recordings in \slotNEnv{} environments, \slotPStateRetRate{}\% survive the retention
funnel, and the survivors are unevenly distributed across formats: two EgoStandard
recordings carry almost every flagged frame, while EgoPro and EgoDemo are close to
clean. Any model that reports one pooled number therefore hides the only failure the
reliability weight exists to catch. The first modelling decision is what to do with
those two recordings; we keep them and model the flag instead of deleting it.
"""
s = s[:m.end()] + ins1 + s[m.end():]

m = re.search(r"\\section\{Problem 2: Prediction under Missing Observations \(Part II\)\}\n\\label\{sec:parttwo\}\n% numerals-ok: end\n", s)
assert m, "P2 heading not found"
ins2 = r"""
\paragraph{Data insight.} The prediction question is decided by what the released
prefix contains, not by the capacity of the predictor. A mask of length $L$ hides the
last $L$ seconds before the target; at the shortest mask hold-last already reads
\slotPTwoARidgeRMSE{} cm and at the longest it reads \slotPTwoCHoldRMSE{} cm, so the
signal decays smoothly rather than abruptly. The practical question is therefore where
on that curve a paid observation stops being worth its cost, and the answer has to be
read off the same windows that define the mask. We report the full curve rather than a
single operating point, because the curve is what the decision layer consumes.
"""
s = s[:m.end()] + ins2 + s[m.end():]

m = re.search(r"\\section\{Problem 3: Stochastic Scheduling \(Part III\)\}\n\\label\{sec:partthree\}\n% numerals-ok: end\n", s)
assert m, "P3 heading not found"
ins3 = r"""
\paragraph{Data insight.} The scheduling instances are small in job count and tight in
capacity: \slotJobsSOne{}, \slotJobsSTwo{} and \slotJobsSThree{} jobs against horizons of
\slotHSOne{}, \slotHSTwo{} and \slotHSThree{} seconds. Almost every loss comes from a
handful of jobs whose predicted completion lands just after their due time, so the
interesting quantity is not the mean lateness but the shape of the on-time
distribution. That shape is what a reservation moves, and it is why the policy layer
reports weighted on-time rate rather than tardiness: two policies can have the same
mean lateness and very different on-time rates.
"""
s = s[:m.end()] + ins3 + s[m.end():]

# ---------------------------------------------------------------- C2 sensitivity subsection
anchor = ("\\section{Model Evaluation}\n\\label{sec:eval}\n")
c2 = r"""
\subsection{Sensitivity of the two decision layers}
\label{sec:sensitivity}

Two layers carry the decision: the predictor that turns a prefix into a completion
time, and the rule that turns a completion time into a start time. We perturb each
layer separately and report what moves.

The predictor layer is tested by refitting the ridge model under four feature subsets
and four context lengths, holding the mask and the split fixed. No subset moves the
error by more than a rounding step, and the context length moves it by less than
\slotPTwoCtxRange{} cm across five to forty frames; the binding constraint is the
released prefix, not the feature set. The conformal radius is more fragile: it grows by
an order of magnitude between the shortest and the longest mask, so a single radius
cannot serve both ends and the paper reports the interval rather than a point.

The rule layer is tested in two ways. One-at-a-time moves of the seven rule knobs
change the on-time rate by at most \slotPFactRangeSTwo{} points in Case S2 and
\slotPFactRangeSThree{} in Case S3, and the two knobs that look structural (the slack
coefficient and the quantile shift) have exactly zero effect under the selected rules,
because those rules never read them. A full $3^5$ design over the five knobs that do
matter shows that the response surface is curved and almost everywhere concave: every
knob away from its frozen value loses more than a linear reading would predict, and no
pair of knobs restores the loss. The practical conclusion is that the frozen rule is
not a lucky corner of a flat surface but a genuine interior optimum of a curved one.
Appendix~\ref{app:sensitivity} reports both designs in full.
"""
# insert before Model Evaluation
i = s.index(anchor)
s = s[:i] + c2 + "\n" + s[i:]

P.write_text(s, encoding="utf-8")
print("main.tex bytes", len(s.encode("utf-8")))

