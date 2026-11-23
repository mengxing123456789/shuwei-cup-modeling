# -*- coding: utf-8 -*-
"""Third A2 pass: final ~320-word trim to land body on page 25."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
main = ROOT / "main.tex"
s = main.read_text(encoding="utf-8")
paras = s.split("\n\n")


def replace_para(startswith: str, new: str):
    hits = [i for i, p in enumerate(paras) if p.lstrip().startswith(startswith)]
    assert len(hits) == 1, f"{startswith!r}: {len(hits)}"
    paras[hits[0]] = new.strip()


replace_para(
    "Three failures are structural.",
    r"""Three failures are structural. The reliability weight does not transfer across
environments: the gap between \slotPEnvOneAUC{} and \slotPEnvTwoAUC{} means a target
environment needs on the order of \slotCtx{} to twice that many calibration frames before
the calibrated route is usable, and without them only the rank should be trusted. Stage
agreement depends on the segment count, and segments shorter than two seconds are
systematically merged; an explicit duration prior is out of scope here. Finally, the
head-frame normalisation is not an unconditional gain: alone it lowers ARI slightly, and
it pays only when combined with the chain constraint.""",
)

replace_para(
    "The headline of this part is negative",
    r"""The headline of this part is negative, and it is measured on the scheduling side, not
asserted: buying observations does not pay. The observation-free policy of Part III reaches
\slotPStochSTwoSlackOldETA{} in S\slotCaseTwo{} and \slotPStochSThreeSlackOldETA{} in
S\slotCaseThree{}. The variant that spends a cost unit and a scenario second on a review
before each job reaches \slotPStochSTwoRiskFusionETA{} and \slotPStochSThreeRiskFusionETA{},
and the paired intervals \slotPStochPairSTwoRiskFusionDiff{}$\pm$\slotPStochPairSTwoRiskFusionCI{}
and \slotPStochPairSThreeRiskFusionDiff{}$\pm$\slotPStochPairSThreeRiskFusionCI{} both cross
zero. A look costs \slotReviewCost{} cost unit and \slotReviewDelay{} s of scenario time, and
the duration error it removes is of the same order, so the ledger balances and the sign is
decided by the tie-break. The longest prefix does not even give the best estimate: duration
MAE is \slotPDurFreeMAE{} s at the free prefix, \slotPDurMidMAE{} s at the middle prefix and
\slotPDurLongMAE{} s at the long one, against \slotPDurFreeBaseMAE{} s for the family-median
constant, because a regression fitted on the short-prefix distribution transfers worse, not
better. This is a property of the features, not of the estimator, and it is why the review
gate in Part III almost never fires.""",
)

replace_para(
    "The marginal value of information is not monotone",
    r"""The marginal value of information is not monotone in the increment, which is why no
interior number of looks can be optimal: a free perfect prefix of six extra frames is worth
\slotPInfoFirstSTwo{} points in S\slotCaseTwo{}, but extending it to ten is worth
\slotPInfoSecondSTwo{}, because the longer prefix moves the optimal quantile and the rate
follows the quantile, not the accuracy. Only knowing the duration reaches the
\slotPInfoGate{} point gate (\slotPInfoTrueMax{} points); Appendix~\ref{app:propositions}
carries the argument.""",
)

replace_para(
    "Coverage sits at",
    r"""Coverage sits at \slotPConMeanCoverage{} on average, a little below the nominal
\slotConfLevel{}\% level, which is what a marginal guarantee buys on a heavy-tailed error.
Appendix~\ref{app:ablation} tabulates the four masks. The radius grows by more than an order
of magnitude between the shortest and the longest mask, from \slotPConAMedianCm{} to
\slotPConDMedianCm{} cm in median terms, so a single radius cannot serve both ends.""",
)

main.write_text("\n\n".join(paras), encoding="utf-8")
print("ok", len(main.read_text(encoding="utf-8").encode("utf-8")))
