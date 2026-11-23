"""Fourth pass: reclaim the ~7 lines that push the bibliography onto page 26."""
import io
import os

TEX = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"

PAIRS = [
    (r"""Table~\ref{tab:pass} in Appendix~\ref{app:calib} lists the pass marks we declared
before the experiments against what was observed, and names the three that were not met.""",
     r"""Appendix~\ref{app:calib} scores us against marks declared before the experiments
and names the three that were not met.""", "pass-pointer"),
    (r"""The reliability weight is cross-environment only after recalibration, and the
courier-station environment demonstrates the failure. Stage agreement depends on the
segment count: fixed by BIC it is stable, wrong it degrades quickly. Prediction is
useful only up to the crossover horizon. The economic optimum is an optimum
of our cost model, not of the problem's. The scheduling result is weighted-on-time-first. Under a tardiness-first reading the ranking changes.""",
     r"""The reliability weight crosses environments only after recalibration, and the
courier-station recording shows the failure. Stage agreement is stable when the segment
count is fixed by BIC and degrades quickly when it is not. Prediction is useful only up to
the crossover horizon, the economic optimum is an optimum of our cost model, and the
scheduling result is weighted-on-time-first; under a tardiness-first reading the ranking
changes.""", "limits"),
    (r"""One gap stays open, and it is the only one: the Part II conformal radius never
becomes the Part III reservation quantile.""",
     r"""One gap stays open: the Part II conformal radius never becomes the Part III
reservation quantile.""", "gap2"),
    (r"""Three answers, one per question. A two-layer hand state with a soft reliability
weight is recoverable, and its reliability transfers across environments only after local
calibration, though as a training weight it moves prediction by millimetres. Prediction
substitutes for observation up to a crossover horizon of about a quarter of a second, and
inside the protocol's action set free waiting dominates not waiting, the shorter paid
prefix and the first paid request alike. Under an unknown affine service time a slack-aware
policy with an explicit reservation quantile raises the weighted on-time rate over EDF in
the two capacity-constrained cases, and the truth is worth three to four points once the
rule is fixed. The negative results come with the condition that would reverse each.""",
     r"""Three answers, one per question. A two-layer hand state with a soft reliability
weight is recoverable and transfers across environments only after local calibration,
though as a training weight it moves prediction by millimetres. Prediction substitutes for
observation up to a crossover horizon of about a quarter of a second, and inside the
protocol's action set free waiting dominates every paid request. Under an unknown affine
service time a slack-aware policy with an explicit reservation quantile raises the weighted
on-time rate over EDF in both capacity-constrained cases, while the truth is worth only
three to four points once the rule is fixed. Each negative result arrives with the
condition that would reverse it.""", "conclusion2"),
]


def main():
    t = io.open(TEX, encoding="utf-8").read()
    for old, new, tag in PAIRS:
        assert t.count(old) == 1, (tag, t.count(old))
        t = t.replace(old, new)
    io.open(TEX, "w", encoding="utf-8", newline="\n").write(t)
    print("pass 4 done; bytes", os.path.getsize(TEX))


if __name__ == "__main__":
    main()