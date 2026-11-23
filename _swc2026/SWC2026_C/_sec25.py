# -*- coding: utf-8 -*-
"""Add §2.5 (one notation + three propositions) and pay for it by trimming filler."""
import pathlib, sys
P = pathlib.Path("main.tex"); t = P.read_text(encoding="utf-8")
edits = []

edits.append((
r"""\subsection{Organisation}

Section~\ref{sec:data} fixes conventions and protocol;
Sections~\ref{sec:partone}--\ref{sec:partthree} answer the three questions in the
six-part form; Section~\ref{sec:limits} states the empirical decision limits,
Section~\ref{sec:eval} the limitations and reproduction commands, and
Section~\ref{sec:concl} concludes. Appendices hold notation, code excerpts and the
command list.""",
r"""\subsection{Organisation}

Section~\ref{sec:data} fixes conventions, protocol and notation;
Sections~\ref{sec:partone}--\ref{sec:partthree} answer the three questions in the
six-part form; Sections~\ref{sec:limits}--\ref{sec:concl} state the empirical
decision limits, the limitations and the conclusion."""))

edits.append((
r"""\subsection{Reproduction}

One command regenerates every number above. The pipeline is in
Appendix~\ref{app:repro}.""",
r"""\subsection{Reproduction}

One command regenerates every number above; the pipeline is in
Appendix~\ref{app:repro}."""))

edits.append((
r"""\section{Part I: State and Observation Reliability}""",
r"""\subsection{One notation for state, observation and decision}
\label{sec:notation}

Everything that follows is about one object. Let $z_t=(x_t,\varphi_t,d)$ be the
state of a work unit after $t$ seconds of its own service: the hand configuration
$x_t$, the phase $\varphi_t$ among the \slotNStages{} stages, and the total duration
$d$, which is never observed before the unit finishes. The observable history
$o_{1:t}$ contains the hands, the per-frame quality flags and the boundary
probabilities, truncated to whatever prefix the protocol has released. A decision
$u_t\in\{\text{wait},\text{execute},\text{drop}\}$, together with an optional review
request, extends that prefix at a cost and a delay; a policy $\pi$ maps $o_{1:t}$ to
$u_t$; the duration law $F_d$ is estimated on training segments only; and $b$ is the
reservation the policy holds.

Three claims are stated in this language and each is settled later on evidence
rather than asserted. The phase is identifiable from geometry only when the stages
separate, which is tested and refuted in Section~\ref{sec:p1res}. The reservation
cancels out of the punctuality probability once the start time is fixed, which is
derived in Section~\ref{sec:p3closed}. The released prefix carries almost no
information about $d$, which is measured in Section~\ref{sec:p2res}.

\section{Part I: State and Observation Reliability}"""))

for old, new in edits:
    if t.count(old) != 1:
        print("MISS (%d):" % t.count(old), old[:60].replace("\n", " ")); sys.exit(1)
    t = t.replace(old, new)
P.write_text(t, encoding="utf-8", newline="\n")
print("edits applied:", len(edits))
