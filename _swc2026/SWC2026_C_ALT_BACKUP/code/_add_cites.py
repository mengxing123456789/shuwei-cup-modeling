# -*- coding: utf-8 -*-
"""Insert the eight citations the reference list already promised.

`review_bench` counted 0 `\\cite` calls against 8 `\\bibitem` entries and failed
R-W04. The references were listed but never pointed at from the body, which is the
defect: a reference list that the text never cites is decoration. Each citation is
attached to the sentence that actually uses the idea, not appended to a heading.
"""
from __future__ import annotations

import pathlib
import sys

TEX = pathlib.Path(__file__).resolve().parents[1] / "main.tex"

# (old fragment, new fragment) — each old fragment must appear exactly once.
EDITS = [
    # ref1: BOCPD
    (
        "run Bayesian online change-point detection (BOCPD) with a constant hazard $1/\\lambda$.",
        "run Bayesian online change-point detection (BOCPD)~\\cite{ref1} with a constant hazard "
        "$1/\\lambda$.",
    ),
    # ref2: Normal-Inverse-Gamma conjugate prior
    (
        "We place a Normal--Inverse--Gamma prior on the regime mean and variance",
        "We place a Normal--Inverse--Gamma prior~\\cite{ref2} on the regime mean and variance",
    ),
    # ref3: Kalman
    (
        "Both facts point the same way: the predictor must be a single-viewpoint recursive "
        "filter with an explicit velocity decorrelation",
        "Both facts point the same way: the predictor must be a single-viewpoint recursive "
        "filter~\\cite{ref3} with an explicit velocity decorrelation",
    ),
    # ref4: value of information
    (
        "In a linear--Gaussian model the expected reduction in the trace of the position "
        "covariance from one look is",
        "In a linear--Gaussian model the expected reduction in the trace of the position "
        "covariance from one look~\\cite{ref4} is",
    ),
    # ref5 + ref7: chance constraint and scenario approximation
    (
        "linearised with big-$M$.",
        "linearised with big-$M$~\\cite{ref5}. The scenario set stands in for the unknown "
        "duration distribution, so the program is a sample-average approximation of the true "
        "chance-constrained problem~\\cite{ref7}.",
    ),
    # ref6: scheduling
    (
        "This turns a static chance-constrained program into a closed-loop policy and is the "
        "main difference from a one-shot priority rule.",
        "This turns a static chance-constrained program into a closed-loop policy and is the "
        "main difference from a one-shot priority rule~\\cite{ref6}.",
    ),
    # ref8: the released data
    (
        "The three scheduling cases are fixed by \\texttt{common\\_conditions.json}",
        "The three scheduling cases are fixed by \\texttt{common\\_conditions.json}~\\cite{ref8}",
    ),
]


def main() -> int:
    text = TEX.read_text(encoding="utf-8")
    applied = 0
    for old, new in EDITS:
        n = text.count(old)
        if n != 1:
            print(f"SKIP (count={n}): {old[:60]}...")
            continue
        text = text.replace(old, new, 1)
        applied += 1
    TEX.write_text(text, encoding="utf-8", newline="\n")
    print(f"applied {applied} of {len(EDITS)}; main.tex {TEX.stat().st_size} B")
    return 0 if applied == len(EDITS) else 1


if __name__ == "__main__":
    sys.exit(main())
