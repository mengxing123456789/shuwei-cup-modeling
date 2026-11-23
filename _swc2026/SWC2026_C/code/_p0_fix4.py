# AI 辅助：DeepSeek Harness 助手生成的补丁模板改写；每条替换断言命中一次。
# -*- coding: utf-8 -*-
"""P0 batch-4: last ~2 lines so the final reference lands on body page 25."""
from pathlib import Path

TEX = Path(r"main.tex")

EDITS = [
    ("Two gaps stay open: the reliability weight never enters the Part II regression as a\n"
     "sample weight, and the Part II conformal radius never becomes the Part III reservation\n"
     "quantile, which uses duration residuals instead.",
     "Two gaps stay open: the reliability weight never enters the Part II regression as a sample\n"
     "weight, and the Part II conformal radius never becomes the Part III reservation quantile."),
    ("The economic optimum is an\n"
     "optimum of our cost model, not of the problem's, and is reported as a range. The\n"
     "scheduling result is weighted-on-time-first; under a tardiness-first reading the\n"
     "ranking changes.",
     "The economic optimum is an optimum\n"
     "of our cost model, not of the problem's. The scheduling result is weighted-on-time-first;\n"
     "under a tardiness-first reading the ranking changes."),
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