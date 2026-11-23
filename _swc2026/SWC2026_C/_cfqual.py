# -*- coding: utf-8 -*-
"""Qualify the closed form on the start time (08 audit P0 item) without adding pages."""
import pathlib, sys
P = pathlib.Path("main.tex"); t = P.read_text(encoding="utf-8")
edits = [
(r"""where $F_d$ is the law of the source duration within the family. Nothing else in the
protocol enters, and three consequences follow that the earlier draft had only observed.""",
 r"""where $F_d$ is the law of the source duration within the family. Nothing else in the
protocol enters; three consequences follow."""),
(r"""\emph{The reservation is absent}. The quantity $b$ postpones the next start,
$t=s+\max(p,b)$, so it buys capacity rather than punctuality: a slack rule changes which
jobs finish in time, not when a given job finishes.""",
 r"""\emph{The reservation is absent from \eqref{eq:cfprob}, but only conditional on $s$. The
quantity $b$ postpones the next start, $t=s+\max(p,b)$, so it buys capacity rather than
punctuality for the job it guards, while moving every later start: a slack rule changes
which jobs finish in time, not when a given job finishes, and a reservation that is too
large still costs capacity later, which is the mechanism behind the reversal in
Section~\ref{sec:limits}."""),
(r"""Under \eqref{eq:cfprob} that is exactly the condition for re-observing to lose value, which
is the value-of-information argument of \cite{howard1966} stated in this protocol.""",
 r"""Under \eqref{eq:cfprob} that is the condition for re-observing to lose value, which is the
value-of-information argument of \cite{howard1966} in this protocol."""),
]
for old, new in edits:
    if t.count(old) != 1:
        print("MISS (%d):" % t.count(old)); sys.exit(1)
    t = t.replace(old, new)
P.write_text(t, encoding="utf-8", newline="\n")
print("edits applied:", len(edits))
