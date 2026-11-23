# -*- coding: utf-8 -*-
"""Final layout for the last body page: no negative vspace at all.

Every negative-vspace variant either left two references on page 26 or pushed
the "References" heading into the Conclusion text.  The heading collision is not
acceptable in a submitted paper, so the space is paid for in prose: the
Conclusion and the Strengths paragraph are tightened, and the reference list
keeps a legible -1pt itemsep with the ordinary 4-baseline page extension.
"""
import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "main.tex"
t = p.read_text(encoding="utf-8")

# 1) no overlap hack
t = re.sub(r"\\vspace\*\{-[\d.]+\\baselineskip\}\n", "", t)
t = re.sub(r"\\setlength\{\\itemsep\}\{[-+]?[\d.]+pt\}", r"\\setlength{\\itemsep}{-1.0pt}", t)

# 2) Conclusion: three lines shorter, same three answers
old_c = ("Three answers, one per question. A two-layer hand state with a soft reliability weight is\n"
         "recoverable and transfers across environments only after local calibration, though as a\n"
         "training weight it moves prediction by millimetres. Prediction substitutes for observation up\n"
         "to a quarter-second crossover, and free waiting beats every paid request. Under an unknown\n"
         "affine service time a slack-aware policy with an explicit reservation quantile raises the\n"
         "weighted on-time rate over EDF in both capacity-constrained cases, while the truth is worth\n"
         "only three to four points once the rule is fixed.")
new_c = ("Three answers, one per question. A two-layer hand state with a soft reliability weight is\n"
         "recoverable and transfers across environments only after local calibration, though as a\n"
         "training weight it moves prediction by millimetres. Prediction substitutes for observation up\n"
         "to a quarter-second crossover, and free waiting beats every paid request. A slack-aware policy\n"
         "with an explicit reservation quantile raises the weighted on-time rate over EDF in both\n"
         "capacity-constrained cases, while the truth is worth three to four points once the rule is\n"
         "fixed.")
assert old_c in t, "conclusion anchor missing"
t = t.replace(old_c, new_c)

# 3) Strengths: drop the restated weakness list down to two lines
old_s = ("The reliability weight crosses environments only after recalibration, and stage agreement is\n"
         "stable when BIC fixes the segment count. Prediction pays only to the crossover horizon, the\n"
         "economic optimum is an optimum of our cost model, and the ranking is weighted-on-time-first.\n"
         "One gap stays open: the Part II conformal radius never becomes the Part III reservation\n"
         "quantile; Appendix~C regenerates every number.")
new_s = ("The reliability weight crosses environments only after recalibration, and stage agreement is\n"
         "stable when BIC fixes the segment count. Prediction pays only to the crossover horizon and the\n"
         "ranking is weighted-on-time-first. One gap stays open: the Part II conformal radius never\n"
         "becomes the Part III reservation quantile; Appendix~C regenerates every number.")
assert old_s in t, "strengths anchor missing"
t = t.replace(old_s, new_s)

p.write_text(t, encoding="utf-8", newline="\n")
print("vspace left:", "vspace*{-" in t)
print("itemsep    :", re.search(r"itemsep\}\{[^}]*\}", t).group(0))
