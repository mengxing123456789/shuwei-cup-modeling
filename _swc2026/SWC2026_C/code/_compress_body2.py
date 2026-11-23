# -*- coding: utf-8 -*-
"""Second A2 pass: compress two long P3 results paragraphs."""
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
    "The statement asks for eleven measures",
    r"""The statement asks for eleven measures for every method, not only the rate, so
Tables~\ref{tab:p3score} and~\ref{tab:p3nom} in Appendix~\ref{app:ablation} report all of
them on the same seeds and the same sampler. The gain is bought with tardiness, not with
capacity: the incumbent completes \slotPStochSTwoSlackOldComp{} and
\slotPStochSThreeSlackOldComp{} of the weighted work against
\slotPStochSTwoEDFOldComp{} and \slotPStochSThreeEDFOldComp{} for the reference, one to two
points, while the weighted on-time rate moves by more than twenty. It finishes no more
jobs; it finishes the ones that matter before their due time and abandons the rest, so
weighted tardiness rises from \slotPStochSTwoEDFOldTard{} to \slotPStochSTwoSlackOldTard{}
s. Reserved idle is \slotPStochSTwoSlackOldIdle{} s against \slotPStochSTwoEDFOldIdle{} s,
and the overrun \slotPStochSTwoSlackOldOverrun{} s against
\slotPStochSTwoEDFOldOverrun{} s: reservations run slightly tight, the direction the
objective penalises. Cost stays inside budget (\slotPStochSTwoSlackOldCost{} of
\slotBudgetSTwo{}, \slotPStochSThreeSlackOldCost{} of \slotBudgetSThree{}), and the frozen
rule below is tighter still: reserved idle \slotPIdleSTwoOurs{} s against
\slotPIdleSTwoSlack{} s for the capacity-aware reference, at the price of overrun rising to
\slotPOverrunSTwoOurs{} s against \slotPOverrunSTwoSlack{} s.""",
)

replace_para(
    "The remaining gap is a policy problem",
    r"""The remaining gap is a policy problem, not an information problem, so we searched
reservation rules, not predictors. \slotPImpNCandidates{} candidates over the quantile
level, the review gate and the late-tolerance constant were scored on the earlier fifteen
seeds only, with the official changeover and floor untouched; the rule was then frozen and
evaluated on the last fifteen, a rescheduling rule in the sense surveyed by
\cite{ouelhadj2009}. On all \slotNSeeds{} seeds it reaches \slotPImpSTwoAllCand{} in
S\slotCaseTwo{} and \slotPImpSThreeAllCand{} in S\slotCaseThree, paired gains
\slotPImpSTwoAllMean{} $\pm$ \slotPImpSTwoAllCI{} and \slotPImpSThreeAllMean{} $\pm$
\slotPImpSThreeAllCI{}. Averaged over the two informative cases the held-out gain is
\slotPImpMixedHoldDelta{} $\pm$ \slotPImpMixedHoldCI{}, excluding zero, although
S\slotCaseThree{} alone crosses zero; because the candidate family came from earlier
experiments, the fifteen-fifteen split confirms, not blinds.""",
)

replace_para(
    "The search fixes the rule but not the level",
    r"""The search fixes the rule but not the level. Holding everything except the quantile
fixed and sweeping it from \slotPQSweepLow{} to \slotPQSweepHigh{} on the same tuning seeds,
the on-time rate falls with the level, by no more than \slotPQWiggleMax{} points of local
reversal: \slotPQTuneLowSTwo{} to \slotPQTuneHighSTwo{} in S\slotCaseTwo{} and
\slotPQTuneLowSThree{} to \slotPQTuneHighSThree{} in S\slotCaseThree. Over-reservation is
the failure mode, and \eqref{eq:cfprob} says why: a reservation buys capacity, which a
lateness-only metric charges as pure cost. The held-out curves are flatter
(\slotPQHoldLowSTwo{}--\slotPQHoldHighSTwo{} and
\slotPQHoldLowSThree{}--\slotPQHoldHighSThree{}), so the plateau, not a point, is what the
data support; the sweep never went below \slotPQSweepLow{}, which bounds the claim.""",
)

main.write_text("\n\n".join(paras), encoding="utf-8")
print("ok", len(main.read_text(encoding="utf-8").encode("utf-8")))
