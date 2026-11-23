# -*- coding: utf-8 -*-
"""Correct the Q1 section against what code/alt_p1_bocpd.py actually does.

Five defects reported by the P1 author, each fixed by an exact-text replacement:
  1. change-point rule was described as "MAP run length drops to zero" (never fires);
  2. "the only free parameter is lambda" (there are four, three tuned);
  3. the retention rule was written on the bad-frame rate instead of the usable rate;
  4. "strongest single result" rested on a record-level AUC, and the real
     within-record result is worse than chance (direction reversed);
  5. the change-point / segment-count arithmetic was left implicit.
"""
from __future__ import annotations

import pathlib
import sys

TEX = pathlib.Path(__file__).resolve().parents[1] / "main.tex"

REPL = []

# ---- 1 + 2: the detection rule and the parameter count -----------------------
REPL.append((
    "with the predictive $p(v_t\\mid\\cdot)$ a Student-$t$ density under the "
    "conjugate prior. A change point is declared when the maximum a posteriori run "
    "length drops to zero; segments shorter than 0.2~s are merged into their "
    "neighbour. The only free parameter is the hazard scale $\\lambda$, which we set "
    "from the median annotated segment length and never tune on the test environments.",
    "with the predictive $p(v_t\\mid\\cdot)$ a Student-$t$ density under the "
    "conjugate prior. Thresholding $P(r_t=0)$ does not work on this corpus: under a "
    "weak prior that probability is diluted by the many short-run hypotheses and "
    "peaks at only 0.119 across all 69 recordings, so no threshold on it finds the "
    "boundaries. We therefore read the mode of the run-length posterior instead and "
    "declare a change point when the MAP run length falls below 30\\% of its own "
    "running peak, then merge candidates closer than 3.0~s. The model has four "
    "settings: the smoothing scale $\\sigma=0.40$~s, the hazard $\\lambda=4.0$~s (the "
    "median annotated segment length of the training environments), the merge "
    "threshold $3.0$~s (the 25\\% quantile of the same distribution) and the drop "
    "fraction $0.30$. The first three were read off training data and the fourth was "
    "set once; none of them was tuned on the test environments, and "
    "Section~\\ref{sec:q1} reports what moving them does.",
))

# ---- 3: the retention rule is on the usable rate, not the bad-frame rate ----
REPL.append((
    "with $\\kappa$ a fixed over-dispersion parameter. The posterior of $\\mu$ is "
    "obtained by grid integration, and each $\\theta_i$ is summarised by its "
    "posterior mean and its 5\\% quantile. A segment is retained when "
    "$q_{0.05}(\\theta_i)\\ge 0.90$; a record is retained for fitting when it has at "
    "least three retained segments.",
    "with $\\kappa$ a fixed over-dispersion parameter. The posterior of $\\mu$ is "
    "obtained by grid integration, and each $\\theta_i$ is summarised by its "
    "posterior mean and its 2.5\\% quantile. Because $\\theta_i$ is a \\emph{bad-frame} "
    "rate, the quantity a user cares about is its complement: the usable probability "
    "$\\rho_i=1-\\theta_i$. A segment is retained when the posterior lower bound "
    "$q_{0.025}(\\rho_i)\\ge0.90$, i.e. when we are 97.5\\% confident that fewer than "
    "one frame in ten is bad; a record is retained for fitting when it has at least "
    "three retained segments. Writing the rule on $\\rho$ rather than on $\\theta$ "
    "matters: stated on $\\theta$ the same inequality would demand a bad-frame rate "
    "above 0.90, which is the opposite of the intent.",
))

# ---- 4: replace the over-claimed "strongest result" paragraph ----------------
OLD4 = (
    "\\paragraph{Reliability, and an external check that matters.} The two-level "
    "Beta--Binomial posterior retains 333 of 349 segments (95.4\\% unweighted, "
    "95.70\\% duration-weighted) under the rule $q_{0.05}(\\theta_i)\\ge0.90$. To test "
    "that the posterior measures something real we ask it to predict which segments "
    "contain at least one bad frame: 51 of 349 do (prevalence 14.6\\%). The "
    "record-level posterior bound reaches AUC 0.914 (best $F_1$ 0.610), the raw "
    "record bad-frame rate 0.915, the segment-level leave-one-out variant 0.675, and "
    "the released \\texttt{eligible} flag only 0.490 --- indistinguishable from "
    "chance. That asymmetry is the strongest single result of Question~1: the "
    "released eligibility flag does not separate bad-frame segments, while a "
    "two-level shrinkage of record counts into segment probabilities does."
)
NEW4 = (
    "\\paragraph{Reliability: what it buys, and what it does not.} The two-level "
    "Beta--Binomial posterior retains 333 of 349 segments (95.4\\% unweighted, "
    "95.70\\% duration-weighted) under the rule $q_{0.025}(\\rho_i)\\ge0.90$. The "
    "retention is not vacuous: of the 298 segments that contain no bad frame it keeps "
    "all 298, and of the 51 that do it keeps 35, so the rule removes a third of the "
    "contaminated segments while touching none of the clean ones. That is a "
    "\\emph{summary} of quality, and it is what we use it for downstream.\n\n"
    "It is not a detector, and we say so explicitly. Asked to rank segments by "
    "whether they contain a bad frame, the record-level posterior bound reaches AUC "
    "0.914 and the raw record bad-frame rate 0.915, the segment-level leave-one-out "
    "variant 0.675, and the released \\texttt{eligible} flag only 0.490 --- "
    "indistinguishable from chance. The record-level figures flatter the method, "
    "because a record-level score is constant inside a record: on the 21 records that "
    "contain both a clean and a contaminated segment, and therefore the only ones "
    "where the comparison is defined, the record-level scores have a within-record "
    "AUC of exactly 0.500 by construction, while the segment-level leave-one-out "
    "score falls to \\textbf{0.076} --- worse than chance, and pointing the wrong "
    "way. The mechanism is not noise: a contaminated segment sits in a record whose "
    "remaining segments are cleaner, so removing the segment's own frames from the "
    "record total lowers its prior rate and \\emph{raises} its usable-probability "
    "bound, which is precisely the wrong direction. No choice of $\\kappa$ repairs "
    "this, because it is a property of any leave-one-out estimator built on the "
    "record rate; breaking it needs a source of evidence that is independent of the "
    "bad-frame labels, which this release does not provide. Question~1 therefore "
    "delivers a calibrated reliability summary and a reproducible retention rule, not "
    "a way to pick out the segment that will fail."
)

# ---- 5: make the change-point arithmetic explicit ---------------------------
REPL.append((
    "BOCPD declares 399 change points over the 69 recordings against 280 annotated "
    "boundaries.",
    "Because a record with $k$ segments carries $k-1$ interior boundaries, the 349 "
    "annotated segments correspond to 280 annotated boundaries and the 468 detected "
    "segments to 399 detected change points; all boundary statistics below are "
    "counted on that interior set.",
))


def main() -> int:
    s = TEX.read_text(encoding="utf-8")
    n = 0
    for old, new in REPL:
        if old not in s:
            print(f"  MISS: {old[:60]!r}")
            continue
        s = s.replace(old, new, 1)
        n += 1
    if OLD4 in s:
        s = s.replace(OLD4, NEW4, 1)
        n += 1
    else:
        print("  MISS: the reliability paragraph")

    TEX.write_text(s, encoding="utf-8", newline="\n")
    print(f"applied {n} replacements; main.tex now {TEX.stat().st_size} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
