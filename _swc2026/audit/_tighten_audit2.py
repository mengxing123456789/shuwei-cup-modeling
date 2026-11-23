"""Second tightening pass: short pointer for the annotation audit, one-clause counting note."""
import io
import os

TEX = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"

PAIRS = [
    # (old, new, tag)
    (
        r"""Appendix~\ref{app:audit} reads the flag itself: \slotPBTOcclPct{}\% of the
\slotPBTBadFrames{} flagged frames are occlusions, the share within half a second of a
stage boundary is \slotPBTBndObsPct{}\% against a \slotPBTBndBasePct{}\% baseline
(ratio \slotPBTBndRatio{}, $p=\slotPBTBndP{}$), and \slotPBTRecsWithBad{} of
\slotPBTRecsTotal{} records hold every flag. Average precision therefore estimates a
handful of episodes rather than a mechanism we can repair.
""",
        r"""Appendix~\ref{app:audit} shows the flag is an occlusion annotation rather than a
boundary artefact, and that \slotPBTRecsWithBad{} of \slotPBTRecsTotal{} records hold
every flag, so average precision estimates a handful of episodes rather than a mechanism
we can repair.
""",
        "bad",
    ),
    (
        r"""The split separates task classes as well as environments, and the
separation can be priced: retraining the detector once per held-out class of the
\slotPLotoNClass{} in the training half gives AUC \slotPLotoMean{} against
\slotPLotoRef{} on the same windows, a gap of \slotPLotoGap{}. Only
\slotPLotoNEval{} classes carry enough positives to score and \slotPLotoNSkip{} are
skipped by a pre-registered rule; each of the three also leaves its environment unseen,
so \slotPLotoFrac{} is an upper bound on the task share at $n=\slotPLotoNEval{}$.
""",
        r"""The split separates task classes, not only environments, and that separation
can be priced: retraining per held-out class gives AUC \slotPLotoMean{} against
\slotPLotoRef{}, a gap of \slotPLotoGap{}. Only \slotPLotoNEval{} of the
\slotPLotoNClass{} classes score at all; each also leaves its environment unseen, so
\slotPLotoFrac{} bounds the task share from above at $n=\slotPLotoNEval{}$
(Appendix~\ref{app:audit}).
""",
        "loto",
    ),
    (
        r"""One counting detail is also
boundary-sensitive: \slotNIntervals{} intervals are listed and \slotNEligible{} clear
the duration threshold, but three of them sit exactly on that threshold, so a
strict comparison returns a smaller eligible set. We take the non-strict reading and
say so rather than silently choosing the luckier denominator.
""",
        r"""Three of the \slotNIntervals{} intervals sit exactly on the duration
threshold, so \slotNEligible{} clear it only under a non-strict reading; we take that
reading and say so.
""",
        "counting",
    ),
]


def main():
    t = io.open(TEX, encoding="utf-8").read()
    for old, new, tag in PAIRS:
        assert t.count(old) == 1, (tag, t.count(old))
        t = t.replace(old, new)
    io.open(TEX, "w", encoding="utf-8", newline="\n").write(t)
    print("pass 2 done; bytes", os.path.getsize(TEX))


if __name__ == "__main__":
    main()