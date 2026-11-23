# AI 辅助：DeepSeek Harness 助手生成的补丁模板改写；每条替换断言命中一次。
# -*- coding: utf-8 -*-
"""P0 batch-3: shave the last ~4 lines so the bibliography ends on body page 25."""
from pathlib import Path

TEX = Path(r"main.tex")

EDITS = [
    ("The reliability weight is a cross-environment quantity only after recalibration,\n"
     "and the courier-station environment demonstrates the failure. Stage agreement\n"
     "depends on the segment count; with the count fixed by BIC it is stable, with the\n"
     "count wrong it degrades quickly. Prediction is useful only up to the crossover\n"
     "horizon, and the constant-acceleration predictor is included precisely because it\n"
     "fails loudly beyond it. The economic optimum is an optimum of our cost model, not\n"
     "of the problem's, and is reported as a range. The scheduling result is a\n"
     "weighted-on-time-first result; under a tardiness-first reading the ranking changes.\n"
     "The review conclusion is conditional on the prefix error and would flip if that\n"
     "error fell by a factor of about three.",
     "The reliability weight is cross-environment only after recalibration, and the\n"
     "courier-station environment demonstrates the failure. Stage agreement depends on the\n"
     "segment count: fixed by BIC it is stable, wrong it degrades quickly. Prediction is\n"
     "useful only up to the crossover horizon, and the constant-acceleration predictor is\n"
     "included precisely because it fails loudly beyond it. The economic optimum is an\n"
     "optimum of our cost model, not of the problem's, and is reported as a range. The\n"
     "scheduling result is weighted-on-time-first; under a tardiness-first reading the\n"
     "ranking changes. The review conclusion holds while the prefix error stays as measured."),
    ("Two gaps stay open: the reliability weight does not enter the Part II regression as a\n"
     "sample weight, and the Part II conformal radius does not become the Part III reservation\n"
     "quantile, which takes duration residuals instead.",
     "Two gaps stay open: the reliability weight never enters the Part II regression as a\n"
     "sample weight, and the Part II conformal radius never becomes the Part III reservation\n"
     "quantile, which uses duration residuals instead."),
    ("\\bibitem{deepseek} DeepSeek Harness, command-line coding agent, model routes selected\n"
     "during the window, DeepSeek, used 18--20 November 2026.",
     "\\bibitem{deepseek} DeepSeek Harness, command-line coding agent, DeepSeek, used\n"
     "18--20 November 2026."),
]


def apply(path, edits):
    t = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(edits, 1):
        n = t.count(old)
        assert n == 1, f"edit {i}: matched {n}, expected 1\n---\n{old[:120]}"
        t = t.replace(old, new, 1)
    path.write_text(t, encoding="utf-8", newline="\n")
    print(f"applied {len(edits)} edits")


apply(TEX, EDITS)