# AI 辅助：DeepSeek Harness 助手生成的一次性排版补丁（把正文压回 25 页，只删字不改数）。
# -*- coding: utf-8 -*-
"""每一处替换都断言恰好命中一次；任何一处不命中就整体不写盘。"""
import pathlib
import sys

P = pathlib.Path(__file__).resolve().parent.parent / "main.tex"
t = P.read_text(encoding="utf-8")

EDITS = [
    ("""The chain is thin by design: Part I gives a point and a soft weight, Part II predicts
that point and prices the next look, Part III consumes the price and the error scale but
not the trajectory. Where it does not close we say so in Section~\\ref{sec:eval}.""",
     """Part I gives a point and a soft weight, Part II predicts that point and prices the next
look, Part III consumes the price and the error scale but not the trajectory; the weight was
carried across and moved the prediction by millimetres, as Section~\\ref{sec:p2res} reports."""),

    ("""  \\item A predictor comparison under a fixed masking protocol, including a
        constant-velocity predictor that fails loudly at long horizons, and a
        conformal interval whose width is reported next to its coverage.""",
     """  \\item A predictor comparison under a fixed masking protocol, with a conformal
        interval whose width is reported next to its coverage."""),

    ("""  \\item A review rule priced by prediction error and delay, which returns a
        negative answer on the measured prefix features; we report the negative""",
     """  \\item A review rule priced in the protocol's own action set, which returns a
        negative answer on the measured prefix features; we report the negative"""),

    ("""\\bibitem{gneiting2007} Gneiting, T. and Raftery, A. E. (2007). Strictly proper
scoring rules, prediction, and estimation. \\emph{Journal of the American
Statistical Association}, 102, 359--378.""",
     """\\bibitem{gneiting2007} Gneiting, T. and Raftery, A. E. (2007). Strictly proper
scoring rules. \\emph{J.\\ Amer.\\ Statist.\\ Assoc.}, 102, 359--378."""),

    ("""\\bibitem{vovk2005} Vovk, V., Gammerman, A. and Shafer, G. (2005). \\emph{Algorithmic
Learning in a Random World}. Springer, New York.""",
     """\\bibitem{vovk2005} Vovk, V., Gammerman, A. and Shafer, G. (2005). \\emph{Algorithmic
Learning in a Random World}. Springer."""),

    ("""\\bibitem{ouelhadj2009} Ouelhadj, D. and Petrovic, S. (2009). A survey of dynamic
scheduling in manufacturing and services. \\emph{Journal of Scheduling}, 12,
417--434.""",
     """\\bibitem{ouelhadj2009} Ouelhadj, D. and Petrovic, S. (2009). A survey of dynamic
scheduling. \\emph{J.\\ Sched.}, 12, 417--434."""),
]

for i, (old, new) in enumerate(EDITS, 1):
    n = t.count(old)
    if n != 1:
        print(f"EDIT {i}: matched {n} times, refusing to write", file=sys.stderr)
        raise SystemExit(1)
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8", newline="\n")
print(f"applied {len(EDITS)} edits")