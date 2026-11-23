import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

old = r"""Two quantities bound Part III: what the instance allows with $p$ known, and what our
information allows; the table in Appendix~\ref{app:ablation} separates them by running
the reservation rule with and without the true duration.

Handing the rule the true duration lifts S\slotCaseTwo{} from \slotPImpSTwoAllCand{} to
\slotPOracleSameSTwo{} and S\slotCaseThree{} from \slotPImpSThreeAllCand{} to
\slotPOracleSameSThree{}: paired gains of \slotPOracleGapSTwoPt{} $\pm$ \slotPOracleGapSTwoCIPt{}
and \slotPOracleGapSThreePt{} $\pm$ \slotPOracleGapSThreeCIPt{}, three to four points wide, while
the distance from EDF to that same reference is an order of magnitude larger. The room is in
the rule, not in the knowledge. We do not call the reference an upper bound: it bounds
this rule, not the information.

The same-rule reference is itself no ceiling: it reaches only \slotPInfoFamSThree{} in
S\slotCaseThree{} against \slotPInfoFamPCSThree{} for the calibrated estimate, since a quantile
reservation over-reserves a tight budget, and the prefix regression (\slotPDurSelTestMAE{} s
against \slotPDurFreeBaseMAE{} s) agrees the gain is the policy's."""

new = r"""Two quantities bound Part III: what the instance allows with $p$ known, and what our
information allows. Appendix~\ref{app:ablation} separates them by running the reservation rule
with and without the true duration. Handing the rule the true duration lifts S\slotCaseTwo{}
from \slotPImpSTwoAllCand{} to \slotPOracleSameSTwo{} and S\slotCaseThree{} from
\slotPImpSThreeAllCand{} to \slotPOracleSameSThree{}: paired gains of \slotPOracleGapSTwoPt{}
$\pm$ \slotPOracleGapSTwoCIPt{} and \slotPOracleGapSThreePt{} $\pm$ \slotPOracleGapSThreeCIPt{},
three to four points wide, while the distance from EDF to that same reference is an order of
magnitude larger --- the room is in the rule, not in the knowledge. The reference is not an
upper bound: it bounds this rule, not the information. It is itself no ceiling either, reaching
only \slotPInfoFamSThree{} in S\slotCaseThree{} against \slotPInfoFamPCSThree{} for the
calibrated estimate, since a quantile reservation over-reserves a tight budget, and the prefix
regression (\slotPDurSelTestMAE{} s against \slotPDurFreeBaseMAE{} s) agrees the gain is the
policy's."""

if old not in t:
    raise SystemExit("section 6 anchor missing")
t = t.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("section 6 merged into two paragraphs")
