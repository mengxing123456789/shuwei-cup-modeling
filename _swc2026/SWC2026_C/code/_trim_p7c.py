import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

old = r"""Three pre-declared marks were missed and each is reported with its own table rather than
quietly dropped: the detector's cross-environment floor fell below its mark while its average
precision rose, a longer mask left a reconstruction error above its mark because the residual
there is motion the context cannot see, and a paid second look bought no on-time rate in any
audited cell. Each has a reversal condition --- the floor is a dial the same sweep turns, the
mask mark would be met where the wearer is slower than the window, the second look pays where
its delay is shorter than the wait it replaces --- and each is a row of the sensitivity
tables. Leakage is controlled in three places: decoding constants, the fusion weight, the
conformal quantile and the reservation quantile are all chosen on validation records, the test
split is scored once per rule, and the two learners that cannot be refitted bit for bit are
reported as distributions over refits. The fourth is disclosed rather than controlled: one
labeller produced the reference boundaries, so our boundary precision is a lower bound on
agreement with a second labeller rather than an estimate of it."""

new = r"""Three pre-declared marks were missed and each is reported with its own table rather than
quietly dropped: the detector's cross-environment floor fell while its average precision rose,
a longer mask left a reconstruction error above its mark because the residual there is motion
the context cannot see, and a paid second look bought no on-time rate in any audited cell. Each
has a reversal condition --- the floor is a dial the same sweep turns, the mask mark would be
met where the wearer is slower than the window, the second look pays where its delay is shorter
than the wait it replaces. Leakage is controlled in three places: every tuning constant is
chosen on validation records, the test split is scored once per rule, and the two learners that
cannot be refitted bit for bit are reported as distributions over refits. One threat is
disclosed rather than controlled: a single labeller produced the reference boundaries, so our
boundary precision is a lower bound on agreement with a second labeller."""

if old not in t:
    raise SystemExit("7.1 anchor missing")
t = t.replace(old, new)

old2 = r"""The reliability weight crosses environments only after recalibration, and stage agreement is
stable when BIC fixes the segment count. Prediction pays only to the crossover horizon and the
ranking is weighted-on-time-first. One gap stays open: the Part II conformal radius never
becomes the Part III reservation quantile; Appendix~C regenerates every number."""

new2 = r"""The reliability weight crosses environments only after recalibration, and stage agreement is
stable when BIC fixes the segment count. Prediction pays only to the crossover horizon, and the
ranking is weighted-on-time-first. One gap stays open: the Part II conformal radius never
becomes the Part III reservation quantile."""

if old2 not in t:
    raise SystemExit("7.3 anchor missing")
t = t.replace(old2, new2)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("compressed 7.1 and 7.3")
