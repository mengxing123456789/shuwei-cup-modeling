# AI 辅助：DeepSeek Harness 助手生成的补丁模板改写；每条替换断言命中一次。
# -*- coding: utf-8 -*-
"""P0 batch-5: trim the closing paragraphs so the last reference fits on body page 25."""
from pathlib import Path

TEX = Path(r"main.tex")

EDITS = [
    ("The negative results are part of the contribution: the label-free reliability route\n"
     "fails on one environment, the longest prefix estimates worse than the middle one,\n"
     "and the value-of-information gate closes. Each comes with the condition under which\n"
     "it would reverse, which is what a decision-maker needs in order to know when to re-run\n"
     "rather than trust the table.",
     "Negative results are part of the contribution: the label-free reliability route fails on\n"
     "one environment, the longest prefix estimates worse than the middle one, and the\n"
     "value-of-information gate closes; each comes with the condition that would reverse it."),
    ("\\caption{Pre-declared pass marks and the observed verdicts. Marks were fixed before\n"
     "the experiments and are repeated here so that a reader can re-score us.}",
     "\\caption{Pre-declared pass marks and observed verdicts; the marks were fixed before the\n"
     "experiments so that a reader can re-score us.}"),
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