import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

pairs = []

# 1) Section 6: drop the redundant restatement of the same-rule reference
pairs.append((
r"""The same-rule reference is itself no ceiling: it reaches only \slotPInfoFamSThree{} in
S\slotCaseThree{} against \slotPInfoFamPCSThree{} for the calibrated estimate, since a quantile
reservation over-reserves a tight budget; the prefix regression, \slotPDurSelTestMAE{} s against
\slotPDurFreeBaseMAE{} s, agrees the gain is the policy's.""",
r"""The same-rule reference is itself no ceiling: it reaches only \slotPInfoFamSThree{} in
S\slotCaseThree{} against \slotPInfoFamPCSThree{} for the calibrated estimate, since a quantile
reservation over-reserves a tight budget, and the prefix regression (\slotPDurSelTestMAE{} s
against \slotPDurFreeBaseMAE{} s) agrees the gain is the policy's."""))

# 2) Section 7 lead-in + 7.3 tighten
pairs.append((
r"""Appendices~\ref{app:closedform}, \ref{app:secondround} and~\ref{app:scorecard} score us against
pre-declared marks and name the three that were not met.""",
r"""Appendices~\ref{app:closedform}, \ref{app:secondround} and~\ref{app:scorecard} score us
against pre-declared marks and name the three that were not met."""))

pairs.append((
r"""The reliability weight crosses environments only after recalibration, and stage agreement is
stable when BIC fixes the segment count. Prediction pays only to the crossover horizon, and the
ranking is weighted-on-time-first. One gap stays open: the Part II conformal radius never
becomes the Part III reservation quantile.""",
r"""The reliability weight crosses environments only after recalibration and stage agreement is
stable once BIC fixes the count; prediction pays only to the crossover horizon; the ranking is
weighted-on-time-first. One gap stays open: the conformal radius of Part II never becomes the
reservation quantile of Part III."""))

# 3) P3 discussion: drop one sentence that repeats the summary
pairs.append((
r"""Failure conditions are concrete.""",
r"""Failure conditions are concrete and stated so a reader can check them."""))

for old, new in pairs:
    if old not in t:
        raise SystemExit("anchor missing:\n" + old[:70])
    t = t.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("applied 4 micro-trims")
