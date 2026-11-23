# AI 辅助：本脚本由 DeepSeek Harness 命令行助手生成的补丁模板改写而来；
# 每个替换都断言命中一次，避免静默漏改。
# -*- coding: utf-8 -*-
"""P0 batch-1 fixes: P3 identity/sign, P2 units, P1 units, MCAP, multicolumn, action set."""
from pathlib import Path

TEX = Path(r"main.tex")
FN = Path(r"code\fill_numbers.py")

EDITS = [
    # --- P0-09 Boundary MAE unit ---
    ("Method & ARI & Frame F1 & Boundary MAE (s) & Count error \\\\",
     "Method & ARI & Frame F1 & Boundary MAE (frames) & Count error \\\\"),
    # --- P0-11 MCAP ---
    ("\\slotProTS{} timestamps in MCAP with head stereo and both wrist views. EgoStandard\n"
     "contributes \\slotStdRecords{} recordings and \\slotStdTS{} timestamps in MCAP with\n"
     "head stereo only.",
     "\\slotProTS{} timestamps in per-hand CSV tables plus MP4 video, with head stereo and\n"
     "both wrist views. EgoStandard contributes \\slotStdRecords{} recordings and\n"
     "\\slotStdTS{} timestamps in the same CSV-plus-video layout with head stereo only."),
    ("would not guess. No \\path{.mcap} file is shipped: the archives arrive flattened into\nCSV tables",
     "would not guess. No message-container file is shipped: the archives arrive flattened\ninto CSV tables"),
    ("drop on the MCAP formats is consistent with their coarser annotation of the",
     "drop on the CSV tables is consistent with their coarser annotation of the"),
    # --- P0-05 action set ---
    ("The simulator is one event loop over three actions --- wait, review, execute ---",
     "The simulator is one event loop over three actions --- wait, execute and drop ---"),
    # --- P0-10 multicolumn ---
    (" & \\multicolumn{\\slotCaseTwo}{c}{S\\slotCaseTwo} & \\multicolumn{\\slotCaseTwo}{c}{S\\slotCaseThree} \\\\",
     " & \\multicolumn{2}{c}{S\\slotCaseTwo} & \\multicolumn{2}{c}{S\\slotCaseThree} \\\\"),
    # --- FAIL: exactly-1.2s count ---
    ("the duration threshold, but two of the remainder sit exactly on that threshold, so a",
     "the duration threshold, but three of them sit exactly on that threshold, so a"),
    # --- P0-08 table units m -> cm ---
    ("Mask (s) & Quantile (m) & Test coverage & Mean radius (m) & Median error (m) \\\\",
     "Mask (s) & Quantile (cm) & Test coverage & Mean radius (cm) & Median error (cm) \\\\"),
    ("\\slotConfLevel{}\\% level. Radius is the mean conformal radius in metres; the last\n"
     "column repeats the empirical median error for comparison.}",
     "\\slotConfLevel{}\\% level. Radius and the last two columns are in centimetres; the last\n"
     "column repeats the empirical median error for comparison.}"),
    # --- FAIL: coverage claim ---
    ("Coverage sits at \\slotPConMeanCoverage{} on average, slightly above nominal,\n"
     "which is the expected consequence of a marginal guarantee applied to a heavy-tailed\n"
     "error.",
     "Coverage sits at \\slotPConMeanCoverage{} on average, a little below the nominal\n"
     "\\slotConfLevel{}\\% level, which is what a marginal guarantee buys on a heavy-tailed\n"
     "error."),
    ("shortest and the longest mask, from \\slotPConAMedianCm{} to\n"
     "\\slotPConDMedianCm{} m in median terms;",
     "shortest and the longest mask, from \\slotPConAMedianCm{} to\n"
     "\\slotPConDMedianCm{} cm in median terms;"),
    # --- P0-01 / P0-02 / P0-04: "goes past reference" -> bounded claim ---
    ("EDF to it. The adaptive rule goes past that reference in both cases, by\n"
     "\\slotPInfoAdvSTwoAbs{} and \\slotPInfoAdvSThreeAbs{}; Section~\\ref{sec:limits} reads that\n"
     "as evidence about the rule, not about the information.",
     "EDF to it. The adaptive rule's point estimate sits above that reference by\n"
     "\\slotPInfoAdvSTwo{} and \\slotPInfoAdvSThree, but its paired interval on the same seeds\n"
     "includes zero; Section~\\ref{sec:limits} therefore reads the gap as a statement about the\n"
     "rule, not about the information."),
    # --- P0-03: drop online-map-estimate attribution ---
    ("No\nscheduler-only change moves the rate by that much, which is why the online map\n"
     "estimate is part of the method rather than an add-on. The decomposition of the\n"
     "adaptive rule is small and is reported to keep the accounting honest: the\n"
     "implementation gap averages \\slotPAdaptImplGapMean{} and the cost of the map estimate\n"
     "\\slotPAdaptAlphaCostMean{}, with a worst-case regret of \\slotPAdaptRegretMax.",
     "No\nscheduler-only change moves the rate by that much, which is why the mapping stays in the\n"
     "paper as the dominant factor. The adaptive rule reported here holds the mapping at the\n"
     "nominal one and buys its gain from the reservation rule and the fifteen-seed selection;\n"
     "a variant that estimates the mapping online was measured separately and did not carry\n"
     "over to the test seeds, so it is not part of the reported policy."),
    # --- P0-01 in Discussion ---
    ("Even with $p$ known the reference is not perfection --- S\\slotCaseThree{} reaches only\n"
     "\\slotPStochSThreeOracleETA{} --- and our adaptive rule is ahead of it there, so not\n"
     "knowing the duration is no longer the binding loss.",
     "Even with $p$ known the reference is not perfection --- S\\slotCaseThree{} reaches only\n"
     "\\slotPStochSThreeOracleETA{} --- and our adaptive rule's point estimate is above it\n"
     "there, though the paired interval includes zero, so not knowing the duration is no\n"
     "longer the binding loss."),
    # --- Summary claim ---
    ("the same seeds, goes past the duration-aware reference in both cases, and shows that\n"
     "paid observations do not pay at the measured prefix quality.",
     "the same seeds, sits above the duration-aware reference at the point-estimate level with a\n"
     "paired interval that includes zero, and shows that paid observations do not pay at the\n"
     "measured prefix quality."),
    # --- P0-06 universal claim ---
    ("so a fifth of the weighted work cannot be\n"
     "on time for any rule that respects releases and due times, and a near-perfect claim would\n"
     "be a claim about the instance rather than the method.",
     "so a fifth of the weighted work misses its due date under this reservation rule on this\n"
     "instance, and a near-perfect claim would be a claim about the instance rather than the\n"
     "method."),
    ("the\nadaptive rule is ahead of the reference by \\slotPInfoAdvSTwoAbs{} in S\\slotCaseTwo{} and\n"
     "\\slotPInfoAdvSThreeAbs{} in S\\slotCaseThree.",
     "the\nadaptive rule's point estimate is above the reference by \\slotPInfoAdvSTwo{} in\n"
     "S\\slotCaseTwo{} and \\slotPInfoAdvSThree{} in S\\slotCaseThree, with matched intervals that\n"
     "include zero, so the ordering is suggestive rather than established."),
]

FN_EDITS = [
    ('    "PInfoAdvSTwoAbs": ("f4", "minus", ("PStochSTwoOracleETA", "PImpSTwoAllCand")),\n'
     '    "PInfoAdvSThreeAbs": ("f4", "minus", ("PStochSThreeOracleETA", "PImpSThreeAllCand")),\n', ''),
]


def apply(path, edits, label):
    t = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(edits, 1):
        n = t.count(old)
        assert n == 1, f"{label} edit {i}: matched {n} times, expected 1\n---\n{old[:120]}"
        t = t.replace(old, new, 1)
    path.write_text(t, encoding="utf-8", newline="\n")
    print(f"{label}: {len(edits)} edits applied")


apply(TEX, EDITS, "main.tex")
apply(FN, FN_EDITS, "fill_numbers.py")

# residual sanity: no claim words left
import re
txt = TEX.read_text(encoding="utf-8")
for pat in ["MCAP", ".mcap", "PInfoAdvSTwoAbs", "PInfoAdvSThreeAbs", "Boundary MAE (s)",
            "ahead of the reference", "goes past", "any rule that respects", "PAdapt"]:
    hits = len(re.findall(re.escape(pat), txt))
    print(f"  residual {pat!r}: {hits}")
print("OK")