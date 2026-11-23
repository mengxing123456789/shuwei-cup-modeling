import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

old = r"""\subsection{What the marks measured}

Three pre-declared marks were missed, and each is reported with its own table rather than
quietly dropped. The detector's cross-environment floor fell below its pre-declared level
while its average precision rose; a longer mask left a reconstruction error above the mark,
because the residual there is dominated by motion the context cannot see; and a paid second
look bought no on-time rate in any audited cell. Each has a stated reversal condition: the
floor is a dial the same sweep turns, the mask mark would be met where the wearer is slower
than the window, and the second look pays where its delay is shorter than the wait it
replaces.

\subsection{Threats to validity}

Leakage is controlled in three places and disclosed in a fourth. Decoding constants, the
fusion weight, the conformal quantile and the reservation quantile are all selected on
validation records; the test split is scored once per rule; and the two learners that cannot
be refitted bit for bit are reported as distributions over refits. The fourth is the
annotation: one labeller produced the reference boundaries, so our boundary precision is a
lower bound on agreement with a second labeller rather than an estimate of it."""

new = r"""\subsection{What the marks measured, and what threatens them}

Three pre-declared marks were missed and each is reported with its own table rather than
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

if old not in t:
    raise SystemExit("anchor missing")
t = t.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("merged 7.1 and 7.2")
