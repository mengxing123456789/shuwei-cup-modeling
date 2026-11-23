"""Put the two subagent results into the paper: two body paragraphs plus Appendix E."""
import io
import os

TEX = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"

BADTYPE = r"""
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

LOTO = r"""
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

APPENDIX = r"""
\addcontentsline{toc}{section}{Appendix E: Annotation audit and unseen task classes}
\section*{Appendix E: Annotation audit and unseen task classes}
\label{app:audit}

% numerals-ok: begin
Two checks sit behind the two paragraphs of Sections~\ref{sec:data} and
\ref{sec:p1res} that point here. The first asks what the bad-frame flag contains and
whether it clusters at stage boundaries, because a flag that marks the transitions would
make the detector's low boundary precision a labelling artefact rather than a modelling
result. The second asks what an unseen task class costs, because the released split
separates classes and a claim of transfer should be measured rather than declared.
% numerals-ok: end

\begin{table}[htbp]
\centering
\caption{Composition of the annotated bad frames. Events are frame-by-side-by-reason
triples; a frame flagged on both hands contributes two events.}
\label{tab:badtype}
\footnotesize
\begin{tabular}{lrr}
\toprule
Quantity & Value & Note \\
\midrule
Flagged frames & \slotPBTBadFrames & of \slotPBTBadFrames{} scanned frames \\
Flag rate & \slotPBTBadRatePct{}\% & annotated, not model output \\
Frame-by-side events & \slotPBTBadEvents & right \slotPBTEventRight, left \slotPBTEventLeft \\
Occlusion share & \slotPBTOcclPct{}\% & of flagged frames \\
Near-edge share & \slotPBTNearPct{}\% & of flagged frames \\
Records with any flag & \slotPBTRecsWithBad & of \slotPBTRecsTotal \\
\bottomrule
\end{tabular}
\end{table}

The flag is sparse, one-sided and concentrated: \slotPBTBadRatePct{}\% of scanned frames
carry it, the right hand supplies \slotPBTEventRight{} of \slotPBTBadEvents{} events, and
\slotPBTRecsWithBad{} of \slotPBTRecsTotal{} recordings account for all of them. The
reason slots hold strings rather than enumerated codes, so the side and the cause are read
from the string itself; where a slot count of one or two appears it is the number of
reasons on that row, not a code. The boundary test pre-declared its criterion: a flag
cluster would need \slotPBTBndObsPct{}\% or more of the flags inside half a second of an
internal boundary and a ratio of at least one and a half. The observed share is
\slotPBTBndObsPct{}\% against a baseline of \slotPBTBndBasePct{}\%, ratio
\slotPBTBndRatio{}, one-sided $p=\slotPBTBndP{}$ and record-level sign test
$p=\slotPBTBndSignP{}$; the criterion fails on both counts and the ratio moves toward one
as the window widens, which is what the absence of clustering looks like. One cause does
cluster, the right near-edge flag, but a single recording produces the whole of it and
removing that recording leaves nothing, so we do not read it as a mechanism.

\begin{table}[htbp]
\centering
\caption{Leave-one-task-out on the training half. Each row retrains the detector with one
semantic task class removed and scores it on that class; the reference is the same
architecture trained with the class present, evaluated on the same windows.}
\label{tab:loto}
\footnotesize
\begin{tabular}{lrrrr}
\toprule
Held-out class & Records & Positives & AUC out & AUC in & Gap \\
\midrule
Cleaning Product Restocking & 3 & 103 & 0.8176 & 0.9330 & +0.1154 \\
Store and Stack Bottled Water & 2 & 107 & 0.8023 & 0.8204 & +0.0181 \\
Straighten Tilted Items (Shelf Reset) & 3 & 51 & 0.9598 & 0.9703 & +0.0105 \\
\midrule
Mean over the three & & & \slotPLotoMean & \slotPLotoRef & \slotPLotoGap \\
\bottomrule
\end{tabular}
\end{table}

The mean gap is \slotPLotoGap{}, of which \slotPLotoFrac{} of the published test gap is
the largest share the task identity can account for. Three limits travel with the number.
\slotPLotoNSkip{} of the \slotPLotoNClass{} classes cannot be scored under the
pre-registered rule because the positives concentrate in a few classes, so the mean is
taken over \slotPLotoNEval{} classes and not over the split. Each of those three also
leaves an environment unseen, which means the measured gap is a joint task-and-environment
cost and the task part alone is at most what is reported. And every fold selects its first
epoch, exactly as the published run does, so the gap is not an artefact of a longer
schedule.

"""


def main():
    t = io.open(TEX, encoding="utf-8").read()
    m1 = "a search for a better score.\n"
    m2 = "reported as such wherever they appear.\n"
    m3 = "\\end{document}"
    for m in (m1, m2, m3):
        assert t.count(m) == 1, (m[:30], t.count(m))
    assert "app:audit" not in t, "appendix already inserted"
    t = t.replace(m1, m1 + BADTYPE)
    t = t.replace(m2, m2 + LOTO)
    t = t.replace(m3, APPENDIX + m3)
    io.open(TEX, "w", encoding="utf-8", newline="\n").write(t)
    print("inserted; bytes", os.path.getsize(TEX))


if __name__ == "__main__":
    main()