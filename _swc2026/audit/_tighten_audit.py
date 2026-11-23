"""Tighten the two new body paragraphs, and wrap the LOTO table in numerals-ok."""
import io
import os

TEX = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"

OLD_BAD = r"""
What the annotations themselves say is in Appendix~\ref{app:audit}: the flag marks an
occlusion rather than a stage boundary, since \slotPBTOcclPct{}\% of the
\slotPBTBadFrames{} flagged frames are occlusions and only \slotPBTNearPct{}\% sit near
the frame edge, the share of flagged frames within half a second of a boundary is
\slotPBTBndObsPct{}\% against a baseline of \slotPBTBndBasePct{}\% (ratio
\slotPBTBndRatio{}, one-sided $p=\slotPBTBndP{}$, and no at the record level), and
\slotPBTRecsWithBad{} of the \slotPBTRecsTotal{} records hold every flag. Average
precision therefore estimates a small set of episodes rather than a mechanism we can
repair, and we read it that way.
"""

NEW_BAD = r"""Appendix~\ref{app:audit} reads the flag itself: \slotPBTOcclPct{}\% of the
\slotPBTBadFrames{} flagged frames are occlusions, the share within half a second of a
stage boundary is \slotPBTBndObsPct{}\% against a \slotPBTBndBasePct{}\% baseline
(ratio \slotPBTBndRatio{}, $p=\slotPBTBndP{}$), and \slotPBTRecsWithBad{} of
\slotPBTRecsTotal{} records hold every flag. Average precision therefore estimates a
handful of episodes rather than a mechanism we can repair.
"""

OLD_LOTO = r"""
The split separates task classes as well as environments, and that separation can be
priced. The training half carries \slotPLotoNClass{} semantic task classes and the test
half shares none of them, so every test number here is a transfer number; retraining the
detector once per held-out class gives AUC \slotPLotoMean{} against \slotPLotoRef{} on the
same windows, a gap of \slotPLotoGap{}. Only \slotPLotoNEval{} classes carry enough
positives to score at all and \slotPLotoNSkip{} are skipped by a rule fixed before any
training began; each of the three also leaves its environment behind, so
\slotPLotoFrac{} of the published gap is an upper bound on the task share, at
$n=\slotPLotoNEval{}$.
"""

NEW_LOTO = r"""The split separates task classes as well as environments, and the
separation can be priced: retraining the detector once per held-out class of the
\slotPLotoNClass{} in the training half gives AUC \slotPLotoMean{} against
\slotPLotoRef{} on the same windows, a gap of \slotPLotoGap{}. Only
\slotPLotoNEval{} classes carry enough positives to score and \slotPLotoNSkip{} are
skipped by a pre-registered rule; each of the three also leaves its environment unseen,
so \slotPLotoFrac{} is an upper bound on the task share at $n=\slotPLotoNEval{}$.
"""

MARK_BEFORE = "\\begin{table}[htbp]\n\\centering\n\\caption{Leave-one-task-out"
MARK_BEFORE_NEW = "% numerals-ok: begin\n\\begin{table}[htbp]\n\\centering\n\\caption{Leave-one-task-out"


def main():
    t = io.open(TEX, encoding="utf-8").read()
    for old, new, tag in ((OLD_BAD, NEW_BAD, "bad"), (OLD_LOTO, NEW_LOTO, "loto")):
        assert t.count(old) == 1, (tag, t.count(old))
        t = t.replace(old, new)
    assert t.count(MARK_BEFORE) == 1
    t = t.replace(MARK_BEFORE, MARK_BEFORE_NEW)
    # close the marker right after the loto table
    i = t.index(MARK_BEFORE_NEW)
    j = t.index("\\end{table}", i) + len("\\end{table}")
    t = t[:j] + "\n% numerals-ok: end" + t[j:]
    io.open(TEX, "w", encoding="utf-8", newline="\n").write(t)
    print("tightened; bytes", os.path.getsize(TEX))


if __name__ == "__main__":
    main()