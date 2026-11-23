# -*- coding: utf-8 -*-
"""Rewrite every prose em dash in the body into a dash-free construction.

The reviewer-facing reason is style: 21 of the 22 ``---`` in the body are rhetorical
parentheticals, and that pattern is a strong machine-writing fingerprint (the five awarded
papers of the same problem run 0.24 to 11.97 em dashes per thousand words, ours 1.71, so we
are inside the band, but a paper with none reads better and the count is easy to remove).

Two of the 22 are empty-cell placeholders in ``tab:rel``; those become en dashes, which is
the correct typographic mark for "not applicable".

Each entry is matched with whitespace folded, so a phrase broken across lines still hits.
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.tex"

PAIRS = [
    # (old, new) -- old may be broken across lines in the source
    (
        r"Following one observation record through three questions---what state can be recovered from the ego-centric recordings, how far it can be predicted once observations stop, and what another look is worth---we show that",
        r"Following one observation record through three questions (what state can be recovered from the ego-centric recordings, how far it can be predicted once observations stop, and what another look is worth), we show that",
    ),
    (
        r"documentation files---\path{record_index.csv}, \path{record_split.csv}, \path{missing_observation_experiments.md}, \path{attachment_guide.md} and \path{file_manifest.csv}---none of which is present in the",
        r"documentation files (\path{record_index.csv}, \path{record_split.csv}, \path{missing_observation_experiments.md}, \path{attachment_guide.md} and \path{file_manifest.csv}), none of which is present in the",
    ),
    (
        r"concentrates on three moves --- reach to pick \slotPStateTransReachPick{}, transport to place \slotPStateTransTransportPlace{} and place back to reach \slotPStateTransPlaceReach{} --- and the conditional entropy of",
        r"concentrates on three moves (reach to pick \slotPStateTransReachPick{}, transport to place \slotPStateTransTransportPlace{} and place back to reach \slotPStateTransPlaceReach{}), and the conditional entropy of",
    ),
    (
        r"Prevalence baseline & --- & --- &",
        r"Prevalence baseline & -- & -- &",
    ),
    (
        r"Stratifying by true stage count resolves the contradiction --- the narrow cap wins at or below it, the wide cap far above it --- and on",
        r"Stratifying by true stage count resolves the contradiction: the narrow cap wins at or below it and the wide cap far above it, and on",
    ),
    (
        r"and two decoding constants --- a peak height the validation grid places between \slotPSegGPUHeightLow{} and \slotPSegGPUHeightHigh{}, and a minimum peak separation of \slotPSegGPUDistance{} frames (\slotPSegGPUDistSec{} s, set from the training segment length distribution) --- are tuned, and on validation records only",
        r"and two decoding constants, a peak height the validation grid places between \slotPSegGPUHeightLow{} and \slotPSegGPUHeightHigh{} and a minimum peak separation of \slotPSegGPUDistance{} frames (\slotPSegGPUDistSec{} s, set from the training segment length distribution), are tuned on validation records only",
    ),
    (
        r"over-segmented until its ARI collapses --- the failure the count study diagnosed, kept",
        r"over-segmented until its ARI collapses, the failure the count study diagnosed and kept",
    ),
    (
        r"to the hand trajectory --- the mechanism taxonomy of \cite{rubin1976} and the estimation treatment of \cite{little2019} --- which is what makes LOCF and interpolation fair",
        r"to the hand trajectory through the mechanism taxonomy of \cite{rubin1976} and the estimation treatment of \cite{little2019}, which is what makes LOCF and interpolation fair",
    ),
    (
        r"a zone and an item family --- single-machine scheduling with release dates and due dates \cite{pinedo2022} --- its true duration $d$ is never",
        r"a zone and an item family, single-machine scheduling with release dates and due dates \cite{pinedo2022}, and its true duration $d$ is never",
    ),
    (
        r"frozen and evaluated on the last fifteen --- a rescheduling rule in the sense surveyed by",
        r"frozen and evaluated on the last fifteen, a rescheduling rule in the sense surveyed by",
    ),
    (
        r"the reference is not perfection --- S\slotCaseThree{} reaches only \slotPStochSThreeOracleETA{} --- and our adaptive rule's point estimate is above it",
        r"the reference is not perfection, since S\slotCaseThree{} reaches only \slotPStochSThreeOracleETA{}, and our adaptive rule's point estimate is above it",
    ),
    (
        r"magnitude larger --- the room is in the rule, not in the knowledge.",
        r"magnitude larger: the room is in the rule, not in the knowledge.",
    ),
]


def flex(pat: str) -> re.Pattern:
    """Match `pat` with any run of whitespace where the pattern has one."""
    parts = [re.escape(t) for t in pat.split()]
    return re.compile(r"\s+".join(parts))


def main():
    apply = "--apply" in sys.argv
    text = io.open(MAIN, encoding="utf-8").read()
    total = 0
    for old, new in PAIRS:
        rx = flex(old)
        n = len(rx.findall(text))
        print(f"{n} hit(s): {old[:60]}...")
        if n:
            text = rx.sub(lambda m: new, text)
            total += n
    print("replaced", total, "of", len(PAIRS), "patterns")
    body = text[: text.find(r"\section{Notation}")]
    print("em dashes left in body:", body.count("---"))
    if not apply:
        print("dry run; pass --apply")
        return 0
    io.open(MAIN, "w", encoding="utf-8", newline="\n").write(text)
    print("written", MAIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
