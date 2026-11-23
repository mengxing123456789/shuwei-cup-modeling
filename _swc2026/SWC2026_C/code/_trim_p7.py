import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

pairs = []

# 1. Compress "What the marks measured" (drop the third reversal clause detail)
pairs.append((
r"""Three pre-declared marks were missed, and each is reported with its own table rather than
quietly dropped. The detector's cross-environment floor fell below its pre-declared level
while its average precision rose; a longer mask left a reconstruction error above the mark,
because the residual there is dominated by motion the context cannot see rather than by the
occlusion we remove; and a paid second look bought no on-time rate in any of the audited
cells. Each has a stated reversal condition. The floor would be met by trading average
precision for the weakest environment, which the same sweep shows is a dial rather than a
wall. The mask mark would be met where the wearer is slower than the window. The second look
would pay where its delay is shorter than the wait it replaces, which the crossover curve
locates for us.""",
r"""Three pre-declared marks were missed, and each is reported with its own table rather than
quietly dropped. The detector's cross-environment floor fell below its pre-declared level
while its average precision rose; a longer mask left a reconstruction error above the mark,
because the residual there is dominated by motion the context cannot see; and a paid second
look bought no on-time rate in any audited cell. Each has a stated reversal condition: the
floor is a dial the same sweep turns, the mask mark would be met where the wearer is slower
than the window, and the second look pays where its delay is shorter than the wait it
replaces."""))

# 2. Compress "Threats to validity"
pairs.append((
r"""Leakage is controlled in three places and disclosed in a fourth. Decoding constants, the
fusion weight, the conformal quantile and the reservation quantile are all selected on
validation records; the test split is scored once per rule, never per hyper-parameter; and
the two learners that cannot be refitted bit for bit are reported as distributions over
refits instead of as single runs. The fourth is the annotation: one labeller produced the
reference boundaries, so the boundary precision we report is a lower bound on agreement
with a second labeller rather than an estimate of it. A reader who wants to overturn a
conclusion should start with the sensitivity tables, since every headline is a row there.""",
r"""Leakage is controlled in three places and disclosed in a fourth. Decoding constants, the
fusion weight, the conformal quantile and the reservation quantile are all selected on
validation records; the test split is scored once per rule; and the two learners that cannot
be refitted bit for bit are reported as distributions over refits. The fourth is the
annotation: one labeller produced the reference boundaries, so our boundary precision is a
lower bound on agreement with a second labeller rather than an estimate of it."""))

# 3. Compress the second-round detector paragraph in P1 results
pairs.append((
r"""A second-round detector, adding left-right symmetric augmentation and test-time averaging,
reaches test AUC \slotPDetVEightAUC{} and average precision \slotPDetVEightAP{} (all seeds
above \slotPDetVEightAPLow{}; weakest environment \slotPDetVEightWorst{}) with
\slotPDetVEightParams{} parameters, against \slotPRelFusTestAP{} for the fused route. It is
the model we would deploy; the confirmatory chain above stays on the simpler route.
Appendix~\ref{app:audit} shows the flag is an occlusion annotation rather than a
boundary artefact, and that \slotPBTRecsWithBad{} of \slotPBTRecsTotal{} records hold
every flag, so average precision estimates a handful of episodes rather than a mechanism
we can repair.""",
r"""A second-round detector, adding left-right symmetric augmentation and test-time averaging,
reaches test AUC \slotPDetVEightAUC{} and average precision \slotPDetVEightAP{} (all seeds
above \slotPDetVEightAPLow{}; weakest environment \slotPDetVEightWorst{}) with
\slotPDetVEightParams{} parameters, against \slotPRelFusTestAP{} for the fused route; it is
the model we would deploy. Appendix~\ref{app:audit} shows the flag is an occlusion
annotation rather than a boundary artefact, and that \slotPBTRecsWithBad{} of
\slotPBTRecsTotal{} records hold every flag, so average precision estimates a handful of
episodes rather than a mechanism we can repair."""))

# 4. Compress the three-arm sensitivity paragraph
pairs.append((
r"""The sensitivity study trains three arms of the same architecture (an exact
replica, a variant with standardisation only, and a variant with augmentation and a
longer schedule) and bootstraps them over \slotPBootNCluster{} record clusters.
Their test AUCs are \slotPArmAAUC{}, \slotPArmBAUC{} and \slotPArmCAUC{}, and the
paired differences are \slotPBootBADiff{} (interval \slotPBootBALo{} to
\slotPBootBAHi) and \slotPBootCADiff{} (\slotPBootCALo{} to \slotPBootCAHi). Neither
interval excludes zero, and none of the three reaches the production score, so the
replica is a stress test of the recipe rather than a replacement for it. The one
realised move inside the replica is calibration: the Brier score goes from
\slotPArmABrier{} to \slotPArmBBrier{} and the calibration error from
\slotPArmAECE{} to \slotPArmBECE{}. We therefore claim calibration and a reproduced
headline, not a better recipe. The reason the pooled number is modest is visible in the threshold sweep:
at $\tau=\slotPTauOneTau$ the retained share is
\slotPTauOneRetained{}\% with recall \slotPTauOneRecall{}\% and precision
\slotPTauOnePrec{}\%, so the weight separates the extreme tail and nothing more.""",
r"""The sensitivity study trains three arms of the same architecture (an exact replica, a
variant with standardisation only, and a variant with augmentation and a longer schedule)
and bootstraps them over \slotPBootNCluster{} record clusters. Their test AUCs are
\slotPArmAAUC{}, \slotPArmBAUC{} and \slotPArmCAUC{}, with paired differences
\slotPBootBADiff{} (interval \slotPBootBALo{} to \slotPBootBAHi) and \slotPBootCADiff{}
(\slotPBootCALo{} to \slotPBootCAHi). Neither interval excludes zero and none reaches the
production score, so the replica is a stress test of the recipe, not a replacement. The one
realised move is calibration: the Brier score goes from \slotPArmABrier{} to
\slotPArmBBrier{} and the calibration error from \slotPArmAECE{} to \slotPArmBECE{}, so we
claim calibration and a reproduced headline. The threshold sweep shows why the pooled
number is modest: at $\tau=\slotPTauOneTau$ the retained share is
\slotPTauOneRetained{}\% with recall \slotPTauOneRecall{}\% and precision
\slotPTauOnePrec{}\%, so the weight separates the extreme tail and nothing more."""))

for old, new in pairs:
    if old not in t:
        raise SystemExit("anchor missing:\n" + old[:90])
    t = t.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("trimmed 4 blocks")
