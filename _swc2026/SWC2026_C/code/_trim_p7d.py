import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

old = r"""\subsection{What the marks measured, and what threatens them}

Three pre-declared marks were missed and each is reported with its own table rather than
quietly dropped: the detector's cross-environment floor fell while its average precision rose,
a longer mask left a reconstruction error above its mark because the residual there is motion
the context cannot see, and a paid second look bought no on-time rate in any audited cell. Each
has a reversal condition --- the floor is a dial the same sweep turns, the mask mark would be
met where the wearer is slower than the window, the second look pays where its delay is shorter
than the wait it replaces. Leakage is controlled in three places: every tuning constant is
chosen on validation records, the test split is scored once per rule, and the two learners that
cannot be refitted bit for bit are reported as distributions. One threat is disclosed rather
than controlled: a single labeller produced the reference boundaries.

\subsection{Strengths and weaknesses}"""

new = r"""\subsection{What the marks measured}

Three pre-declared marks were missed and each is reported with its own table rather than
quietly dropped: the detector's cross-environment floor fell while its average precision rose,
a longer mask left a reconstruction error above its mark, and a paid second look bought no
on-time rate in any audited cell. Appendix~\ref{app:ablation} gives each its reversal condition
--- the floor is a dial the same sweep turns, the mask mark would be met where the wearer is
slower than the window, the second look pays where its delay is shorter than the wait it
replaces --- together with the three places leakage is controlled and the one threat that is
disclosed rather than controlled, a single labeller on the reference boundaries.

\subsection{Strengths and weaknesses}"""

if old not in t:
    raise SystemExit("7.1 anchor missing")
t = t.replace(old, new)

# append the threats text to app_n
A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()
block = r"""
\subsection{Reversal conditions and threats to validity}

Each missed mark carries the condition that would reverse it. The detector's
cross-environment floor is a dial the same sweep turns: trading average precision for the
weakest environment moves it above the mark, which the eight configurations of
Table~\ref{tab:p1-loo} span. The reconstruction mark would be met where the wearer is slower
than the mask window, since the residual there is dominated by motion the context cannot see
rather than by the occlusion we remove. A paid second look would pay where its delay is
shorter than the wait it replaces; the crossover curve in Section~\ref{sec:p2} locates that
boundary for us.

Leakage is controlled in three places. Decoding constants, the fusion weight, the conformal
quantile and the reservation quantile are all selected on validation records; the test split
is scored once per rule and never per hyper-parameter; and the two learners that cannot be
refitted bit for bit, the boundary network and the detector, are reported as distributions
over refits rather than as single runs. One threat is disclosed rather than controlled: a
single labeller produced the reference boundaries, so the boundary precision we report is a
lower bound on agreement with a second labeller rather than an estimate of it.
"""

if r"\subsection{Reversal conditions and threats to validity}" not in a:
    a = a.rstrip() + "\n" + block
    io.open(A, "w", encoding="utf-8", newline="").write(a)
    print("appended threats block to app_n")
else:
    print("threats block already present")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("compressed 7.1 in main.tex")
