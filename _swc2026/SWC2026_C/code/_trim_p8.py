import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

old = r"""Three answers, one per question. A two-layer hand state with a soft reliability weight is
recoverable and transfers across environments only after local calibration, though as a
training weight it moves prediction by millimetres. Prediction substitutes for observation up
to a quarter-second crossover, and free waiting beats every paid request. A slack-aware policy
with an explicit reservation quantile raises the weighted on-time rate over EDF in both
capacity-constrained cases, while the truth is worth three to four points once the rule is
fixed."""

new = r"""Three answers, one per question. A two-layer hand state with a soft reliability weight is
recoverable and transfers across environments only after local calibration, though as a
training weight it moves prediction by millimetres. Prediction substitutes for observation up
to a quarter-second crossover, and free waiting beats every paid request. A slack-aware policy
with an explicit reservation quantile raises the weighted on-time rate over EDF in both
capacity-constrained cases, and the truth is worth three to four points once the rule is
fixed: punctuality is bought by the rule, not by the data."""

if old not in t:
    raise SystemExit("conclusion anchor missing")
t = t.replace(old, new)

old2 = r"""Three pre-declared marks were missed and each is reported with its own table rather than
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

new2 = r"""Three pre-declared marks were missed and each is reported with its own table rather than
quietly dropped: the detector's cross-environment floor fell while its average precision rose,
a longer mask left a reconstruction error above its mark because the residual there is motion
the context cannot see, and a paid second look bought no on-time rate in any audited cell. Each
has a reversal condition --- the floor is a dial the same sweep turns, the mask mark would be
met where the wearer is slower than the window, the second look pays where its delay is shorter
than the wait it replaces. Leakage is controlled in three places: every tuning constant is
chosen on validation records, the test split is scored once per rule, and the two learners that
cannot be refitted bit for bit are reported as distributions. One threat is disclosed rather
than controlled: a single labeller produced the reference boundaries."""

if old2 not in t:
    raise SystemExit("7.1 anchor missing")
t = t.replace(old2, new2)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("trimmed conclusion and 7.1")
