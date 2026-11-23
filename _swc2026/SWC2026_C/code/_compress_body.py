# -*- coding: utf-8 -*-
"""A2: compress selected body paragraphs while keeping every number."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
main = ROOT / "main.tex"
s = main.read_text(encoding="utf-8")

paras = s.split("\n\n")


def replace_para(startswith: str, new: str):
    hits = [i for i, p in enumerate(paras) if p.lstrip().startswith(startswith)]
    assert len(hits) == 1, f"{startswith!r}: {len(hits)} hits"
    paras[hits[0]] = new.strip()


replace_para(
    "The sensitivity study trains three arms",
    r"""The sensitivity study trains three arms of the same architecture (an exact replica, a
standardisation-only variant, and an augmentation variant with a longer schedule) and
bootstraps them over \slotPBootNCluster{} record clusters. Their test AUCs are
\slotPArmAAUC{}, \slotPArmBAUC{} and \slotPArmCAUC{}, with paired differences
\slotPBootBADiff{} (\slotPBootBALo{} to \slotPBootBAHi) and \slotPBootCADiff{}
(\slotPBootCALo{} to \slotPBootCAHi). Neither interval excludes zero and none reaches the
production score, so the replica is a stress test of the recipe, not a replacement. The one
realised move is calibration: the Brier score falls from \slotPArmABrier{} to
\slotPArmBBrier{} and the calibration error from \slotPArmAECE{} to \slotPArmBECE{}. At
$\tau=\slotPTauOneTau$ the sweep retains \slotPTauOneRetained{}\% with recall
\slotPTauOneRecall{}\% and precision \slotPTauOnePrec{}\%, so the weight separates the
extreme tail and nothing more; we print no Brier score of our own because that score
punishes a mis-calibrated probability \cite{gneiting2007}, whereas this weight was built
to rank.""",
)

replace_para(
    "Offered a threshold to choose",
    r"""Offered a threshold to choose, the weight refuses one: under the asymmetric cost
$\kappa(\tau)=(k(\tau)+r\,g(\tau))/n$ on the validation split, no ratio from
\slotPCostRatioLow{} to \slotPCostRatioHigh{} selects an interior $\tau$ (the minimiser
keeps every frame, then drops every frame), and a calibrated $0.5$ cut would cost
\slotPCostHalfMult{} times as much as keeping every frame. The filter exists and cost
minimisation says it should not be used, so the weight enters Part II as a rank score.""",
)

replace_para(
    "Inside the agglomerative family",
    r"""Inside the agglomerative family the best defensible score stays at the frozen
baseline \slotPSegWardARI{}: the wider caps that look better on test are rejected by
selection inside the training split, where the mean is \slotPKTrainCvEight{} at the
\slotKMax{} cap against \slotPKTrainCvTwoFive{} at the widest. The cap on the segment
count, not the partition, is thus the binding constraint, and its best value cannot be
identified from this split: the held-out ARI moves from \slotPKCapEightTest{} to
\slotPKCapTwoFiveTest{} while validation moves the other way, and silhouette gives
\slotPKCapSilEightTest{} against \slotPKCapSilTwoFiveTest{}. The cause is a distribution
shift in the reference annotation: validation records have at most seven stages, test
records reach the low twenties, and stratifying by true stage count resolves the
contradiction, with the narrow cap winning at or below it and the wide cap far above,
where the ARI moves from \slotPKLongEight{} to \slotPKLongSixteen{}. One two-stage test
record collapses under the information criterion while silhouette recovers its count.""",
)

replace_para(
    "We also test the natural explanation",
    r"""We also test the natural explanation for the low boundary precision, that a boundary
is detectable only where the two stages differ enough. On the \slotPIdNBound{} test
boundaries we correlate the peak boundary probability within two frames with separation in
four spaces (graph eigenvalues, pose coordinates, wrist position and segment speed), each
scaled by the within-segment spread. No statistic reaches the criterion: the largest
absolute rank correlation is \slotPIdSpearmanMax{} (\slotPIdSpearmanRobust{} on a repeat,
independent fit) and the detection rate is the same above and below the median separation.
A null check rules out a blind detector: at true boundaries the mean peak is
\slotPIdMeanTrue{} against \slotPIdMeanNull{} at random frames, and \slotPIdTrueHalf{}\% of
boundaries clear the decoding threshold against \slotPIdNullHalf{}\% (AUC
\slotPIdAucTwo{}, or \slotPIdAucTwoRobust{} on the second fit). What limits the partition is
the height of that peak relative to the threshold, not the distinguishability of the
stages. The competing families in Appendix~\ref{app:ablation} are reported because they
lose: a hidden Markov model reaches \slotPSegHMMARI{} even with the true count
(\slotPSegHMMOracleARI{}), an autoencoder front end is worse (\slotPSegAEHMMARI{}),
multi-scale Ward lands at \slotPSegWardMSARI{} and autoencoder-plus-Ward at
\slotPSegAEWardARI{}. By format, agreement is \slotPSegDemoWard{} on EgoDemo,
\slotPSegProWard{} on EgoPro and \slotPSegStdWard{} on EgoStandard, against
\slotPSegDemoRaw{}, \slotPSegProRaw{} and \slotPSegStdRaw{} for the baseline; the drop on
the CSV tables matches their coarser annotation.""",
)

replace_para(
    "A temporal-convolutional reliability variant",
    r"""A temporal-convolutional reliability variant reached test AUC \slotPTCNAUC{} against
\slotPTCNValAUC{} on validation with \slotPTCNParams{} parameters and \slotPTCNSeconds{} s
of training, but its lift of \slotPTCNAPLift{} in average precision does not pay for the
loss of interpretability, so the linear route is the deliverable.""",
)

# P2: null training paragraph
replace_para(
    "Training for missing input does not help",
    r"""Training for missing input does not help at this horizon. Three arms share the
architecture, the seed and the windows: clean input, a mask-aware channel filled by the
previous value, and one filled by linear interpolation. At no masked frame they read
\slotPCleanZero{}, \slotPLocfZero{} and \slotPInterpZero{} cm per coordinate; at six masked
frames, \slotPCleanSix{}, \slotPLocfSix{} and \slotPInterpSix{}. The reliability score does
not fare better as a training weight: the arms read \slotPRelArmA{}, \slotPRelArmB{} and
\slotPRelArmC{}~cm, a paired change of \slotPRelAtoB{}~cm with interval \slotPRelAtoBCI{}.
The binding constraint is neither robustness to missing input nor the quality of the
reliability signal, but what the released prefix carries about the future.""",
)

# C2: shorten the sensitivity subsection to its two decisive paragraphs
replace_para(
    "The predictor layer is tested by refitting",
    r"""The predictor layer is tested by refitting the ridge model under four feature subsets
and four context lengths, holding the mask and the split fixed. No subset moves the error
by more than a rounding step, and the context length moves it by less than a tenth of a
centimetre across five to forty frames; the binding constraint is the released prefix, not
the feature set. The conformal radius is more fragile: it grows by an order of magnitude
between the shortest and the longest mask, so the paper reports the interval rather than a
point.""",
)

replace_para(
    "The rule layer is tested in two ways",
    r"""The rule layer is tested two ways. One-at-a-time moves of the seven rule knobs change
the on-time rate by at most \slotPFactRangeSTwo{} points in Case S2 and
\slotPFactRangeSThree{} in Case S3, and the slack coefficient and quantile shift have
exactly zero effect under the selected rules because those rules never read them. A full
$3^5$ design over the five knobs that do matter shows a curved, almost everywhere concave
surface: every knob away from its frozen value loses more than a linear reading predicts,
and no pair restores the loss. The frozen rule is therefore an interior optimum of a curved
surface, not a lucky corner of a flat one. Appendix~\ref{app:sensitivity} reports both
designs in full.""",
)

main.write_text("\n\n".join(paras), encoding="utf-8")
print("ok", len(main.read_text(encoding="utf-8").encode("utf-8")))
