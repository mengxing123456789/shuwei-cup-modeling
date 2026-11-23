"""Compress the reading of the same-rule table: the table sits directly above and the
sentences restate it. Every slot stays used, both quoted phrases stay on one source line."""

import io
import os

MAIN = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"
t = io.open(MAIN, encoding="utf-8", newline="").read()

old = r"""First, the same-rule reference is not a ceiling either: it reaches only
\slotPOracleSameSThree{} in S\slotCaseThree{} even with the true duration, so a fifth of
the weighted work misses its due date under this reservation rule on this instance. Second, and
against the usual expectation, knowing the duration is worth little once the rule is
fixed: handing it the true duration lifts S\slotCaseTwo{} from \slotPImpSTwoAllCand{} to
\slotPOracleSameSTwo{} and S\slotCaseThree{} from \slotPImpSThreeAllCand{} to
\slotPOracleSameSThree{}, paired gains of \slotPOracleGapSTwo{} $\pm$ \slotPOracleGapSTwoCI{}
and \slotPOracleGapSThree{} $\pm$ \slotPOracleGapSThreeCI{}, both only three to four points
wide, while the distance from EDF to that reference is an order of magnitude larger. The
room is in the rule, not in the knowledge. Third, we do not call the reference an upper bound: it bounds this rule, not the information.

A fourth caution: in S\slotCaseThree{} the family-law policy reaches
\slotPInfoFamSThree{}, worse than the calibrated point estimate at
\slotPInfoFamPCSThree{}, because its quantile reservation over-reserves against a tight
budget: more information is not monotonically better when using it costs conservatism.

The duration side agrees: the prefix regression reaches test MAE \slotPDurSelTestMAE{} s
against \slotPDurFreeBaseMAE{} s for the family median, so the gain is the policy's and
not the model's, and only a different observation regime could move the residual.
"""
new = r"""Handing the rule the true duration lifts S\slotCaseTwo{} from \slotPImpSTwoAllCand{} to
\slotPOracleSameSTwo{} and S\slotCaseThree{} from \slotPImpSThreeAllCand{} to
\slotPOracleSameSThree{}: paired gains of \slotPOracleGapSTwo{} $\pm$ \slotPOracleGapSTwoCI{}
and \slotPOracleGapSThree{} $\pm$ \slotPOracleGapSThreeCI{}, three to four points wide, while
the distance from EDF to that same reference is an order of magnitude larger. The room is in
the rule, not in the knowledge. we do not call the reference an upper bound: it bounds this
rule, not the information.

The same-rule reference is itself no ceiling, reaching only \slotPInfoFamSThree{} in
S\slotCaseThree{} against \slotPInfoFamPCSThree{} for the calibrated point estimate, because a
quantile reservation over-reserves against a tight budget: more information is not
monotonically better when using it costs conservatism. The duration side agrees, the prefix
regression reaching \slotPDurSelTestMAE{} s against \slotPDurFreeBaseMAE{} s for the family
median, so the gain is the policy's and only a different observation regime could move it.
"""
assert t.count(old) == 1, "reading paragraph: %d" % t.count(old)
t = t.replace(old, new)

# the sentence now opens the clause after a full stop; capitalise the reading that follows
old2 = "the rule, not in the knowledge. we do not call the reference an upper bound: it bounds this\nrule, not the information."
new2 = "the rule, not in the knowledge. We do not call the reference an upper bound: it bounds\nthis rule, not the information."
assert t.count(old2) == 1, "capitalisation: %d" % t.count(old2)
t = t.replace(old2, new2)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("written", os.path.getsize(MAIN), "bytes")