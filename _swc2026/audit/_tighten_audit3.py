"""Third pass: kill the empty subsection, fold the pointer in, shorten the Conclusion."""
import io
import os

TEX = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"

PAIRS = [
    # remove the duplicate footnotesize I added earlier
    ("\\begin{thebibliography}{\\slotBibWidth}\n\\footnotesize\\setlength{\\itemsep}{1pt}\n",
     "\\begin{thebibliography}{\\slotBibWidth}\n", "bib-dup"),
    # empty subsection -> pointer folded into 7.2, and the two paragraphs merged
    (r"""\subsection{Validation summary}


\subsection{Limitations and failure conditions}

The reliability weight is cross-environment only after recalibration, and the
courier-station environment demonstrates the failure.""",
     r"""Table~\ref{tab:pass} in Appendix~\ref{app:calib} lists the pass marks we declared
before the experiments against what was observed, and names the three that were not met.

\subsection{Limitations and failure conditions}

The reliability weight is cross-environment only after recalibration, and the
courier-station environment demonstrates the failure.""", "empty-sub"),
    (r"""One gap stays open: the Part II conformal radius never becomes the Part III reservation
quantile. The reliability weight was tried as a sample weight in
Section~\ref{sec:p2res} and moves the number by millimetres.""",
     r"""One gap stays open, and it is the only one: the Part II conformal radius never
becomes the Part III reservation quantile.""", "gap"),
    # conclusion: drop the restatement of the negatives, keep the reversal conditions
    (r"""Three answers, one per question. A two-layer hand state with a soft reliability weight
is recoverable, and its reliability transfers across environments only after local
calibration, though as a training weight it moves prediction by millimetres. Prediction
substitutes for observation up to a crossover horizon of about a quarter of a second. Inside the protocol's action set free waiting dominates not waiting and the shorter paid
prefix, and only a second request pays. Under an unknown affine service time, a slack-aware
policy with an explicit reservation quantile raises the weighted on-time rate over EDF
in the two capacity-constrained cases, and the truth is worth only three to four points
once the rule is fixed. Negative results are part of the contribution (a label-free reliability route that fails on one environment, a longer prefix that
estimates worse, paid observation that does not pay) and each comes with the condition
that would reverse it.""",
     r"""Three answers, one per question. A two-layer hand state with a soft reliability
weight is recoverable, and its reliability transfers across environments only after local
calibration, though as a training weight it moves prediction by millimetres. Prediction
substitutes for observation up to a crossover horizon of about a quarter of a second, and
inside the protocol's action set free waiting dominates not waiting, the shorter paid
prefix and the first paid request alike. Under an unknown affine service time a slack-aware
policy with an explicit reservation quantile raises the weighted on-time rate over EDF in
the two capacity-constrained cases, and the truth is worth three to four points once the
rule is fixed. The negative results come with the condition that would reverse each.""",
     "conclusion"),
]


def main():
    t = io.open(TEX, encoding="utf-8").read()
    for old, new, tag in PAIRS:
        assert t.count(old) == 1, (tag, t.count(old))
        t = t.replace(old, new)
    io.open(TEX, "w", encoding="utf-8", newline="\n").write(t)
    print("pass 3 done; bytes", os.path.getsize(TEX))


if __name__ == "__main__":
    main()