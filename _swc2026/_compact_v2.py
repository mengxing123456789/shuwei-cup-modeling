#!/usr/bin/env python
"""Compact the v2 draft back inside the official 25-page ceiling.

Three levers, no content deleted:
  1. abstract trimmed so the front matter fits on one page again;
  2. the two new Q2 tables share one float, side by side;
  3. float/caption spacing tightened (12 tables + 6 figures).
"""
from pathlib import Path

P = Path(r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.tex")
lines = P.read_text(encoding="utf-8").split("\n")
print("before:", len(lines), "lines")

# ---------------------------------------------------------------- 1. abstract
NEW_ABS = [
    r"\textbf{Background and Task} An unmanned-supermarket restocking record contains 69 episodes, 66{,}070 timestamped frames and 184 videos. The operator must decide what to believe, when to look again, and in what order to serve 8--16 jobs under hard time and cost budgets. We address three coupled problems: segmenting a record into operation states with a reliability score (Q1), predicting a hand state through missing observations and pricing a paid re-observation (Q2), and scheduling restocking jobs under uncertain service durations (Q3). \\",
    r"\textbf{Modeling Framework} We model a record with a Bayesian online change-point (BOCPD) run-length posterior and a hierarchical Beta--Binomial reliability layer (Q1); a constant-velocity Kalman filter whose observation schedule follows a one-step value-of-information rule (Q2); and a scenario-based chance-constrained mixed-integer program rolled forward after every decision (Q3). \\",
    r"\textbf{Results per Question} Q1 detects 399 change points across 69 records with boundary F1 0.183 at $\pm0.5$~s and retains 95.4\% of segments at a one-sided 97.5\% posterior lower bound of 0.90. Q2 cuts the masked-window 3D error from 21.50~cm (constant velocity) to 9.46~cm, growing as $L^{0.741}$; a look is priced at 1.61~cm of accuracy, and a blind two-look schedule beats both the no-look filter and a drift-triggered look (9.85 against 12.88~cm at a 3.0~s gap). Q3 lifts the weighted on-time rate in the tightest case from 0.522 (EDF) to 0.711, of which 0.084 is re-planning alone, yet still trails SLACK at 0.741 --- a ranking unchanged by a six-level chance-level sweep, a train-only residual bank and all five official service mappings, whose absolute level moves by 0.336. A trained ridge predictor reaches 8.65~cm at 1.0~s, so the filter is an interpretable baseline rather than the accuracy ceiling. \\",
    r"\textbf{Validation and Limitation} Every number is bound to the released archives and the derived \texttt{data/} products by \texttt{code/verify\_numbers.py}; the split is environment-level (16/4/4). The Q3 residual bank pools all 343 eligible segments across splits, a leakage bounded by a train-only ablation. The main limitation is that annotated boundaries are semantic subtask changes while the detector finds kinematic regime changes, so the reliability layer --- not the segmentation layer --- carries the paper.",
]
hits = 0
for i, l in enumerate(lines):
    for k, tag in enumerate((r"\textbf{Background and Task}", r"\textbf{Modeling Framework}",
                             r"\textbf{Results per Question}", r"\textbf{Validation and Limitation}")):
        if l.startswith(tag):
            lines[i] = NEW_ABS[k]
            hits += 1
assert hits == 4, hits

# ------------------------------------------------- 2. merge the two Q2 tables
a = next(i for i, l in enumerate(lines) if l.startswith(r"\begin{table}[htbp]") and "tab:p2train" in lines[i + 1])
e_a = next(i for i in range(a, len(lines)) if lines[i] == r"\end{table}") + 1
b = next(i for i, l in enumerate(lines) if l.startswith(r"\begin{table}[htbp]") and "tab:p2conf" in lines[i + 1])
end_b = next(i for i in range(b, len(lines)) if lines[i] == r"\end{table}") + 1
left = lines[a:e_a]
right = lines[b:end_b]
assert left[0].startswith(r"\begin{table}") and left[-1] == r"\end{table}", (a, e_a)
assert right[0].startswith(r"\begin{table}") and right[-1] == r"\end{table}", (b, end_b)

cap_l = (r"\caption{Trained predictors on the official masking windows (mean 3D error, cm). "
         r"All methods are fitted on training records; every method sees the same test windows.}"
         r"\label{tab:p2train}")
cap_r = (r"\caption{Split-conformal boxes around the ridge forecast at nominal coverage $0.90$; "
         r"coverage is empirical on 300 test windows.}\label{tab:p2conf}")


def inner(block):
    return [l for l in block[1:-1] if not l.startswith(r"\caption{")]


merged = ([r"\begin{table}[htbp]\centering\footnotesize",
           r"\begin{minipage}[t]{0.56\textwidth}\centering", cap_l]
          + inner(left)
          + [r"\end{minipage}", r"\hfill",
             r"\begin{minipage}[t]{0.41\textwidth}\centering", cap_r]
          + inner(right)
          + [r"\end{minipage}", r"\end{table}"])
lines[a:end_b] = merged
assert "\n".join(lines).count(r"\label{tab:p2train}") == 1
assert "\n".join(lines).count(r"\label{tab:p2conf}") == 1

# --------------------------------------------- 3. float and caption spacing
tex = "\n".join(lines)
SPACING = (
    "\n% Keep the 12 tables and 6 figures compact so the paper stays inside the\n"
    "% official 25-page ceiling (summary sheet and contents included).\n"
    "\\setlength{\\textfloatsep}{7pt plus 2pt minus 2pt}\n"
    "\\setlength{\\intextsep}{7pt plus 2pt minus 2pt}\n"
    "\\setlength{\\floatsep}{7pt plus 2pt minus 2pt}\n"
    "\\setlength{\\abovecaptionskip}{4pt}\n"
    "\\setlength{\\belowcaptionskip}{0pt}\n"
)
assert tex.count(r"\setlength{\emergencystretch}{4em}") == 1
tex = tex.replace(r"\setlength{\emergencystretch}{4em}",
                  r"\setlength{\emergencystretch}{4em}" + SPACING, 1)

P.write_bytes(tex.encode("utf-8"))
print("after:", P.stat().st_size, "bytes,", len(tex.split("\n")), "lines")
print("table floats:", tex.count(r"\begin{table}"),
      "labels:", tex.count(r"\label{tab:p2train}"), tex.count(r"\label{tab:p2conf}"))
