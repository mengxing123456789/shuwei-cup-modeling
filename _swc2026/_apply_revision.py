# -*- coding: utf-8 -*-
"""One-shot revision of the backup paper: apply every audited correction.

Phase A: exact substring replacements (line count unchanged).
Phase B: line / line-range replacements, applied in DESCENDING line order.
Phase C: best-effort cleanup of provenance scripts (line-index based).
All writes use write_bytes so Windows newline translation cannot shift BYTES.
Run with --check first: prints every count without writing anything.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP")
MAIN = ROOT / "main.tex"
MAIN_DIR = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C")


def j(*lines: str) -> str:
    """Join source lines with a single LF (no triple-quote puzzles)."""
    return "\n".join(lines)


# ---------------------------------------------------------------- Phase A
A: list[tuple[str, str]] = [
    (r"We model a record as a marked point process of kinematic change points",
     r"We model a record with a Bayesian online change-point (BOCPD) run-length posterior"),
    (r"we treat a record as a \emph{point process of kinematic change points}",
     r"we treat a record as a \emph{run-length posterior over kinematic change points}"),
    (r"retains 95.4\% of segments at a 95\% posterior lower bound of 0.90",
     r"retains 95.4\% of segments at a one-sided 97.5\% posterior lower bound of 0.90"),
    (r"from 21.50~cm (last-state) to 9.46~cm",
     r"from 21.50~cm (constant-velocity extrapolation) to 9.46~cm"),
    (r", but still trails the SLACK rule at 0.741; we report that ranking rather than claiming a win.",
     r", but still trails the SLACK rule at 0.741. A six-level sweep of the chance level and a "
     r"train-only residual bank leave that ranking unchanged; we report it rather than claiming a win."),
    (r"All numbers are reproduced from the released archives by scripts in Appendix~A; "
     r"the split is environment-level (16/4/4) and no test environment is used for tuning.",
     r"All numbers are bound to the released archives and the derived \texttt{data/} products by "
     r"\texttt{code/verify\_numbers.py} and the scripts in Appendix~A; the split is "
     r"environment-level (16/4/4), while the Q3 residual bank pools all 343 eligible segments "
     r"from all three splits, a leakage we bound with a train-only ablation in Section~\ref{sec:sens}."),
    (r"the 349 eligible segments.}\label{tab:p1scale}",
     r"the 349 annotated segments.}\label{tab:p1scale}"),
    (r"none of them was tuned on the test environments, and Section~\ref{sec:q1} reports what moving them does.",
     r"none of them was tuned on the test environments, and Section~\ref{sec:sens} reports what "
     r"moving the hazard and the smoothing scale does (the merge threshold and the drop fraction "
     r"were fixed once and were not re-run)."),
    (r"a record-level score is constant inside a record: on the 21 records",
     r"two of the record-level scores are constant inside a record: on the 21 records"),
    (r"the record-level scores have a within-record AUC of exactly 0.500 by construction, "
     r"while the segment-level",
     r"those two scores have a within-record AUC of exactly 0.500 by construction, the resampled "
     r"record posterior bound reaches only 0.565, while the segment-level"),
    (r"the lag-1 autocorrelation of the fingertip velocity is 0.878, lag-3 is 0.519, "
     r"lag-5 is 0.220 and lag-10 is $-0.013$, so a constant-velocity extrapolation decays "
     r"from plausible to useless within half a second.",
     r"the lag-1 autocorrelation of the fingertip velocity is 0.940, lag-3 is 0.897, lag-5 is "
     r"0.875 and lag-10 is 0.817, so a constant-velocity extrapolation stays competitive at the "
     r"shortest mask (2.914 against 2.862~cm at 0.2~s) but breaks down once the hidden window "
     r"exceeds 0.4~s."),
    (r"Both facts point the same way: the predictor must be a single-viewpoint recursive "
     r"filter~\cite{ref3} with an explicit velocity decorrelation, not a ballistic model and "
     r"not a multi-view triangulation.",
     r"Both facts point the same way: the predictor must be a single-viewpoint recursive "
     r"filter~\cite{ref3} with explicit velocity damping, not a ballistic extrapolation and "
     r"not a multi-view triangulation."),
    (r", and by the autocorrelation measured above that velocity is worth almost nothing "
     r"after half a second.",
     r", and a 0.2~s prefix is too short to place a look inside a 1.5--3.0~s gap."),
    (r"The two noise scales are estimated from the visible prefixes by "
     r"expectation--maximisation, separately for each record and observation channel, "
     r"so that a shaky segment does not silently widen every other segment's posterior.",
     r"The two noise scales are fitted once by the method of moments on the training records "
     r"--- process variance from the velocity-increment variance and measurement variance from "
     r"the tenth percentile of squared second differences --- and are then held fixed for every "
     r"record and observation channel, so that a shaky segment does not silently widen every "
     r"other segment's posterior."),
    (r"This is a one-step lookahead approximation of the optimal information-acquisition policy;",
     r"This is a one-step lookahead approximation of the optimal information-acquisition "
     r"policy~\cite{ref4};"),
    (r"$\lambda$ is a single scalar calibrated on the validation environments and then frozen for test.",
     r"$\lambda$ is not fitted on a held-out split: it is the break-even marginal posterior-trace "
     r"reduction between the three official options, computed on the test windows of "
     r"Table~\ref{tab:p2voi}, so we report it as a derived price rather than a calibrated "
     r"hyperparameter."),
    (r"\textbf{Baselines.} Last-state hold, constant-velocity extrapolation, and "
     r"fixed-interval re-observation (one look every 1.5~s) are run on exactly the same "
     r"masked windows and the same seeds.",
     r"\textbf{Baselines.} Last-state hold, constant-velocity extrapolation and a least-squares "
     r"linear extrapolation of the visible prefix are run on exactly the same masked windows and "
     r"the same seeds; all three are reported in Table~\ref{tab:p2mask}."),
    (r"Within-gap scheduling exists only for $W\ge1.5$~s, and that is the regime tested here "
     r"(Table~\ref{tab:p2policy}, Figure~\ref{fig:p2policy}).",
     r"Interior looks are possible once the hidden window exceeds 31 frames; the tested grid is "
     r"$1.5$, $2.0$ and $3.0$~s (Table~\ref{tab:p2policy}, Figure~\ref{fig:p2policy})."),
    (r"advance the clock to its realised completion",
     r"advance the clock to its realised device release $s_j+\max(p_j,b_j)$"),
    (r"\texttt{ccmip\_rolling} re-solves after every completion or paid look; "
     r"\texttt{ccmip\_oneshot} solves once at $t=0$.}",
     r"\texttt{ccmip\_rolling} re-solves after every completion or paid look; "
     r"\texttt{ccmip\_oneshot} solves once at $t=0$; in S2 and S3 that single call times out "
     r"at the 1.0~s limit on every seed and falls back to a deterministic EDF order.}"),
    (r"A record is reduced to $21$ keypoints in the head frame at $5$~Hz;",
     r"A record is reduced to $21$ keypoints per hand in the head frame at $30$~Hz "
     r"(resampled to $5$~Hz only for the Q1 change-point detector);"),
    (r"and a systematic sweep of the chance level. None of the three is available in this "
     r"release, and we have marked each as open rather than filling the gap with an assumption.",
     r"and the statement's $\alpha/\beta$ sensitivity grid for the service-time mapping. "
     r"The chance-level sweep that was open in an earlier draft is now reported in "
     r"Section~\ref{sec:sens}; the remaining three are not available in this release, and we "
     r"have marked each as open rather than filling the gap with an assumption."),
    (r"\item Every number in this paper is produced by a script in Appendix~A from the "
     r"released archives; no number is typed by hand.",
     r"\item Every number in this paper is bound to a key in \texttt{data/*.json} by "
     r"\texttt{code/verify\_numbers.py}, which is run after each compile; the 60 cells of "
     r"Table~\ref{tab:p3} are checked individually."),
    (r"  \item The scheduling layer is solved to optimality on a scenario approximation "
     r"rather than tuned as a priority rule, and it is rolled forward so that a bad scenario "
     r"does not persist.",
     r"  \item The scheduling layer is solved to feasibility within a 1.0~s CP-SAT limit on a "
     r"scenario approximation rather than tuned as a priority rule, and it is rolled forward so "
     r"that a bad scenario does not persist; solver fallbacks are counted in Section~\ref{sec:sens}."),
    (r"and the comparison of prefix lengths at 0.2, 0.6 and 1.0~s returns identical errors.",
     r"and a controlled comparison that holds the decision point and target fixed while "
     r"varying only the visible prefix (0.2, 0.6 and 1.0~s) returns identical errors, "
     r"9.874~cm at a 30-frame lead and 12.789~cm at a 90-frame lead; the three official "
     r"options of Table~\ref{tab:p2voi} differ because their lead times change as well."),
]

# ---------------------------------------------------------------- Phase B
B: list[tuple[int, int, str]] = [
    (58, 58, j(
        r"  \item \textbf{Duration exchangeability within family and observation prefix.} Given a job family and an observation prefix, duration residuals are exchangeable, so a deterministic 5--95\% quantile grid over all 343 eligible segments supplies $S=20$ scenarios, with ranks de-correlated across jobs by a CRC32 permutation. Justification: the protocol samples jobs from the eligible pool by family, and the statement gives a single linear service mapping $\alpha d+\beta$; used in Section~\ref{sec:q3}. The bank pools all three released splits (246 train, 35 validation and 62 test eligible segments), which is a leakage rather than a tuning choice; Section~\ref{sec:sens} bounds it with a train-only replication.",
    )),
    (244, 251, j(
        r"\begin{tabular}{rrrrrr}",
        r"\toprule",
        r"$L$ (s) & Kalman & RMSE & Hold & Const.-vel. & Linear fit \\",
        r"\midrule",
        r"0.2 & 2.862 & 3.526 & 3.387 & 2.914 & 3.310 \\",
        r"0.4 & 5.656 & 6.862 & 5.998 & 7.731 & 6.342 \\",
        r"0.6 & 7.095 & 8.742 & 7.353 & 11.502 & 10.329 \\",
        r"1.0 & 9.464 & 11.334 & 9.554 & 21.497 & 18.003 \\",
    )),
    (335, 335, j(
        r"\textbf{Duration scenarios.} For each job family $f$ and observation prefix we pool the duration residuals of all 343 eligible segments (246 train, 35 validation and 62 test) and form $S=20$ scenarios from a deterministic 5--95\% quantile grid; ranks are de-correlated across jobs by a per-unit CRC32 permutation so scenarios are not comonotone. The bank is a quantile grid rather than stratified resampling, and it is not train-only; Section~\ref{sec:sens} reports a train-only replication that leaves the policy ranking unchanged.",
    )),
    (337, 354, j(
        r"\textbf{Chance-constrained program.} Let $\mathrm{inc}_j\in\{0,1\}$ indicate that job $j$ is admitted, $b_j\ge0.2$ the reserved service time, and $\ell_j\in\{0,1,2\}$ the number of paid looks. For the committed sequence the scenario-$\omega$ start times obey",
        r"\[",
        r"s_{j}= \max\{r_j,\; s_{j^-}+\max(p_{j^-}^{\omega},b_{j^-})+D_{j^-,j}+0.5\},",
        r"\]",
        r"where $j^-$ is the predecessor; the realised completion is $C_j^{\omega}=s_j+p_j^{\omega}$, the device is released at $s_j+\max(p_j^{\omega},b_j)$, and the cost of a run is",
        r"\[",
        r"\mathcal{C}=\sum_j\left(2+0.1b_j+0.2D_{j^-,j}\right)+\sum_j \ell_j .",
        r"\]",
        r"The chance constraint caps the probability that an admitted job cannot be finished inside the horizon~\cite{ref5} --- completion feasibility, not lateness --- as",
        r"\[",
        r"\frac1S\sum_{\omega}\mathbf 1\{C_j^{\omega}>H\}\le \varepsilon,\qquad \varepsilon=0.50,",
        r"\]",
        r"linearised as the scenario count $\sum_\omega(\mathrm{inc}_j-\mathrm{done}_j^{\omega})\le\lfloor\varepsilon S\rfloor$; the big-$M$ device is used only for the ordering arcs. The scenario set stands in for the unknown duration distribution, so the program is a sample-average approximation of the true chance-constrained problem~\cite{ref7}. The objective is a lexicographic integer score: $10^4$ per unit weight for an on-time completion, $3\times10^3$ for a completion inside the horizon, weighted tardiness capped at 10~s and subtracted with unit weight, and cost charged with weight $10S\lambda$ ($\lambda=0.01$):",
        r"\[",
        r"\max\;\sum_{\omega}\sum_j w_j\left(10^4\,\mathbf 1\{C_j^{\omega}\le d_j\}+3\cdot10^3\,\mathbf 1\{C_j^{\omega}\le H\}-\min\{(C_j^{\omega}-d_j)^+,\,10\}\right)-10S\lambda\,\mathcal{C}.",
        r"\]",
    )),
    (361, 361, j(
        r"\textbf{Solution.} The program is solved with OR-Tools CP-SAT at a 0.1~s time resolution under a 1.0~s wall-clock limit per call; a call returning neither OPTIMAL nor FEASIBLE falls back to a deterministic EDF order, and Section~\ref{sec:sens} counts those fallbacks. The driver is \texttt{code/alt\_p3\_ccmip.py}, the JSON of record is \texttt{data/alt\_p3.json}, and the measured chance-level sweep is \texttt{data/alt\_p3\_sweep.json}. The driver reads three read-only dependencies from the companion workspace (\texttt{common.py}, \texttt{p3\_stochastic\_schedule.py} and \texttt{p3\_duration\_predictions.csv}); frozen copies are included under \texttt{code/vendor/} so the numbers stay reproducible if that workspace is later revised.",
    )),
    (391, 391, j(
        r"\textbf{What the numbers say.} Re-planning is worth more than the model. Holding the objective and the scenario set fixed and switching only re-planning on raises the weighted on-time rate by 0.098 in S1, 0.094 in S2 and 0.084 in S3 --- the largest single effect in the table --- at an extra cost of 6.59, 4.89 and 4.61 units respectively. These three gaps are not a clean ablation: in S2 and S3 the one-shot CP-SAT call times out at the 1.0~s limit on every seed and reverts to a deterministic EDF order, so they compare rolling re-solving against a degraded static plan rather than a converged one. Against the stronger baseline the picture is mixed: the rolling program beats EDF by 0.210 in S2 and 0.190 in S3, but it does \emph{not} beat SLACK, trailing it by 0.043 in S2 and 0.029 in S3. The program optimises the declared lexicographic score --- on-time count, completion inside the horizon, capped tardiness, cost --- while SLACK is a greedy rule reacting to the realised schedule; on instances this small the greedy rule is hard to beat. We report the ranking as measured: the best policy on the declared metric is \texttt{slack\_old}, not our program.",
    )),
    (393, 393, j(
        r"\textbf{The chance level is measured, not assumed.} The final run fixes $\varepsilon=0.50$. A six-point sweep $\varepsilon\in\{0.20,0.30,0.40,0.50,0.60,0.70\}$ was run on eight paired seeds per cell with the same 20-scenario bank, the same 1.0~s solver limit and the same fee schedule; \texttt{code/alt\_p3\_sweep.py} produced 135 cells in 728.9~s of solver time (\texttt{data/alt\_p3\_sweep.json}). Averaged over the three cases the rolling program's mean on-time rate is 0.747, 0.761, 0.790, 0.804, 0.784 and 0.800, while \texttt{slack\_old} is best at every level (0.821); the two priority baselines do not depend on $\varepsilon$ at all. Replacing the residual bank by a train-only one (252 eligible residuals per prefix) at $\varepsilon=0.50$ lowers the rolling mean to 0.780 and leaves the winner unchanged. The sweep uses eight seeds while Table~\ref{tab:p3} uses thirty, so only the ranking --- not the absolute levels --- is comparable.",
        r"",
        r"\textbf{Solver fallbacks are measured, not hidden.} Under the 1.0~s limit the rolling solver returns no feasible incumbent at least once in all 30 S2 seeds and all 30 S3 seeds (mean 2.800 and 8.167 fallbacks per seed, 84 and 245 in total), while the one-shot solve times out on every S2 and S3 seed. The one-shot rows of Table~\ref{tab:p3} in those two cases therefore measure a static EDF plan, not a converged MIP.",
    )),
    (395, 395, j(
        r"\textbf{What does survive.} Three statements hold across all five policies and all three cases. First, every policy meets the statement's floor of a mean weighted on-time rate of at least $0.50$ in every case (the minimum is 0.522), so the floor does not discriminate. Second, completion and punctuality do \emph{not} trade off monotonically: the one-shot plan has the highest completion in S3 (0.883) but the lowest on-time rate among the three MIP variants (0.627), whereas EDF is the least punctual policy overall (0.522); ordering the five S3 rows by completion gives on-time rates 0.687, 0.522, 0.741, 0.711 and 0.627. Third, cost is driven mainly by the case's job count and budget rather than by paid looks: across the 15 rows the correlation between cost and the mean review count is $r=0.083$, and the nine rows with zero reviews are not the cheapest.",
    )),
    (399, 399, j(
        r"\textbf{Question 1.} Each row of Table~\ref{tab:p1sens} re-runs the whole detector with one parameter moved and reports the boundary $F_1$ at $\pm0.5$~s. Only two parameters were swept: doubling the hazard from 4 to 8~s lowers $F_1$ from 0.183 to 0.143 (0.039), and setting $\sigma=0.25$~s instead of $0.40$~s lowers it to 0.136 (0.046), the largest single move in the table. Across the eight rows $F_1$ stays between 0.136 and 0.183 and the count MAE between 2.88 and 3.13. The merge threshold and the drop fraction were fixed once and were \emph{not} re-run, so we make no sensitivity claim for them. The mechanism is consistent with the hazard setting the prior segment length.",
    )),
    (403, 403, j(
        r"\textbf{Question 3.} Our program has two knobs, the chance level $\varepsilon$ (swept over six values above) and the scenario count $S=20$ (fixed throughout); a train-only residual bank leaves the ranking unchanged. The statement additionally asks for sensitivity to the service mapping $\alpha\in\{0.75,1.5\}$ and $\beta\in\{0,1\}$~s, which we did not run and report as an open gap rather than a claimed result. Because every policy sees the same 30 draws, the comparison is paired: the rolling-minus-one-shot on-time difference has 95\% confidence intervals $[0.043,0.153]$ in S1, $[0.016,0.173]$ in S2 and $[0.030,0.139]$ in S3, all strictly above zero, while the SLACK-minus-rolling intervals $[-0.001,0.013]$, $[-0.006,0.092]$ and $[-0.015,0.074]$ all cross zero. Re-planning is therefore a measured effect and the SLACK lead is not statistically resolved on these seeds.",
    )),
    (439, 439, j(
        r"Every number in this paper is bound to a key in \texttt{data/*.json} by \texttt{code/verify\_numbers.py}, which is run after each compile and checks the 60 cells of Table~\ref{tab:p3} individually; the section-filling drivers \texttt{code/fill\_alt.py}, \texttt{code/fill\_p3.py} and \texttt{code/alt\_figures.py} assemble the prose and figures from the same products and are listed below alongside the producers. The listings are the files that produced the numbers, not excerpts; the delivered prose in \texttt{main.tex} was subsequently revised to remove over-claims. The released archives are the source of every raw datum; the derived \texttt{data/} products and the frozen read-only dependencies under \texttt{code/vendor/} keep the reported numbers reproducible without re-running the 428.7~s solver job.",
    )),
]

APPENDIX = j(
    r"\subsection*{code/alt\_p3\_sweep.py}",
    r"\lstinputlisting[language=Python,frame=tb,breaklines=true,xleftmargin=2.5em,basicstyle=\scriptsize]{code/alt_p3_sweep.py}",
    r"",
    r"\subsection*{code/verify\_numbers.py}",
    r"\lstinputlisting[language=Python,frame=tb,breaklines=true,xleftmargin=2.5em,basicstyle=\scriptsize]{code/verify_numbers.py}",
    r"",
    r"\subsection*{code/fill\_alt.py}",
    r"\lstinputlisting[language=Python,frame=tb,breaklines=true,xleftmargin=2.5em,basicstyle=\scriptsize]{code/fill_alt.py}",
    r"",
    r"\subsection*{code/fill\_p3.py}",
    r"\lstinputlisting[language=Python,frame=tb,breaklines=true,xleftmargin=2.5em,basicstyle=\scriptsize]{code/fill_p3.py}",
    r"",
    r"\subsection*{code/alt\_figures.py}",
    r"\lstinputlisting[language=Python,frame=tb,breaklines=true,xleftmargin=2.5em,basicstyle=\scriptsize]{code/alt_figures.py}",
    r"\end{document}",
)


def check() -> None:
    text = MAIN.read_text(encoding="utf-8")
    print(f"main.tex: {len(text.encode('utf-8'))} B / {len(text.split(chr(10)))} lines")
    bad = 0
    for i, (old, _new) in enumerate(A):
        c = text.count(old)
        if c != 1:
            bad += 1
            print(f"  A[{i:02d}] count={c}  {old[:92]!r}")
    print(f"  A: {len(A)} rules, {bad} mismatches")
    enddoc = r"\end{document}"
    print(f"  enddocument count={text.count(enddoc)}")
    lines = text.split("\n")
    for start, end, _new in B:
        head = lines[start - 1][:76] if start <= len(lines) else "<OOR>"
        print(f"  B L{start}-{end}: {head!r}")
    for rel, edits in C.items():
        t = (ROOT / rel).read_text(encoding="utf-8")
        print(f"  C {rel}: {len(edits)} edits, file {len(t.split(chr(10)))} lines")
    sys.exit(0 if bad == 0 else 1)


def apply() -> None:
    text = MAIN.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(A):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"PHASE-A[{i}] count={n} for: {old[:90]!r}")
        text = text.replace(old, new, 1)
    if text.count(r"\end{document}") != 1:
        raise SystemExit("end{document} not unique")
    text = text.replace(r"\end{document}", APPENDIX, 1)

    lines = text.split("\n")
    for start, end, new in sorted(B, key=lambda e: -e[0]):
        if start < 1 or end > len(lines) or start > end:
            raise SystemExit(f"bad range {start}-{end} (file {len(lines)} lines)")
        lines[start - 1:end] = new.split("\n")
    MAIN.write_bytes("\n".join(lines).encode("utf-8"))
    print(f"main.tex written: {MAIN.stat().st_size} B, {len(lines)} lines")


# ---------------------------------------------------------------- Phase C
# Provenance scripts: replace stale prose/facts by exact line ranges (descending).
# Each entry = (start_line, end_line, new_text). Best effort: report, never abort.
def _fp(slots: dict) -> None:
    for rel, edits in C.items():
        p = ROOT / rel
        t = p.read_text(encoding="utf-8")
        lines = t.split("\n")
        done = 0
        for start, end, new in sorted(edits, key=lambda e: -e[0]):
            if start < 1 or end > len(lines) or start > end:
                print(f"  C SKIP {rel} L{start}-{end}: out of range")
                continue
            head = lines[start - 1].strip()[:70]
            print(f"  C {rel} L{start}-{end} <- {len(new)} chars (was {head!r})")
            lines[start - 1:end] = new.split("\n")
            done += 1
        p.write_bytes("\n".join(lines).encode("utf-8"))
        print(f"  C {rel}: {done}/{len(edits)} applied")


C: dict[str, list[tuple[int, int, str]]] = {
    r"code\fill_p3.py": [
        (130, 136, j(
            '        "\\textbf{What the numbers say.} Re-planning is worth more than the model. Holding the "',
            '        "objective and the scenario set fixed and switching only the re-planning on raises the "',
            '        "weighted on-time rate by "',
            '        f"{f(roll_vs_one_s1)} in S1, {f(roll_vs_one_s2)} in S2 and {f(roll_vs_one_s3)} in S3 "',
            '        "--- the largest single effect in the table, at extra costs of "',
            '        f"{f(row(\'ccmip_rolling\',\'S1\',\'cost\') - row(\'ccmip_oneshot\',\'S1\',\'cost\'), 2)}, "',
            '        f"{f(row(\'ccmip_rolling\',\'S2\',\'cost\') - row(\'ccmip_oneshot\',\'S2\',\'cost\'), 2)} and "',
            '        f"{f(row(\'ccmip_rolling\',\'S3\',\'cost\') - row(\'ccmip_oneshot\',\'S3\',\'cost\'), 2)} "',
            '        "cost units in S1, S2 and S3. "',
        )),
        (150, 156, j(
            '        "\\textbf{The chance level is measured, not assumed.} The final run fixes "',
            '        f"$\\\\varepsilon={f(eps, 2)}$. A six-level sweep and a train-only residual-bank "',
            '        "ablation were run (data/alt_p3_sweep.json, 135 cells, 728.9~s); the rolling mean "',
            '        "on-time rate is 0.747/0.761/0.790/0.804/0.784/0.800 over the six levels and "',
            '        "0.780 with the train-only bank at 0.50, while slack_old is best at every level "',
            '        "(0.821). See the delivered main.tex for the full statement.\\n\\n"',
        )),
        (157, 166, j(
            '        "\\textbf{What does survive.} Three statements hold across all five policies and "',
            '        "all three cases. First, every policy meets the 0.50 floor (minimum 0.522). "',
            '        "Second, completion and punctuality do not trade monotonically: EDF is the "',
            '        "least punctual policy overall. Third, cost is driven mainly by the case job "',
            '        "count and budget, not by paid looks (r=0.083 across 15 rows). See the "',
            '        "delivered main.tex for the full statement."',
        )),
        (173, 180, j(
            '    s["@@SENS@@"] = (',
            '        "\\textbf{Question 1.} Each row of Table~\\\\ref{tab:p1sens} re-runs the whole detector "',
            '        "with one parameter moved and reports boundary $F_1$ at $\\\\pm0.5$~s. Only two "',
            '        "parameters were swept: doubling the hazard 4 to 8~s lowers $F_1$ by 0.039, and "',
            '        "sigma=0.25~s lowers it by 0.046, the largest single move. The merge threshold "',
            '        "and drop fraction were fixed once and were not re-run.\\n\\n"',
        )),
        (189, 193, j(
            '        "\\textbf{Question 3.} Our program has two knobs, the chance level (swept over "',
            '        "six values above) and $S=20$ (fixed); a train-only bank leaves the ranking "',
            '        "unchanged. The statement additionally asks for alpha/beta sensitivity, which "',
            '        "we did not run and report as an open gap. Every policy sees the same 30 draws, "',
            '        "so paired 95% CIs for rolling-minus-one-shot are [0.043,0.153], [0.016,0.173] "',
            '        "and [0.030,0.139]; SLACK-minus-rolling CIs all cross zero."',
        )),
        (198, 199, j(
            '        "share it. A record is reduced to $21$ keypoints per hand in the head frame at "',
            '        "$30$~Hz (resampled to $5$~Hz only for the Q1 change-point detector); from that "',
        )),
        (212, 216, j(
            '        "Three things would change the picture most: an information source for reliability "',
            '        "that is independent of the bad-frame label, a heteroscedastic observation model "',
            '        "so that the value of a look becomes record-specific, and the statement\'s "',
            '        "alpha/beta sensitivity grid. The chance-level sweep that was open earlier is "',
            '        "now reported; the remaining gaps are marked open rather than assumed away."',
        )),
    ],
    r"code\fill_alt.py": [
        (232, 240, j(
            '            "choice. First, the hand is not ballistic: the lag-1 autocorrelation of the "',
            '            "fingertip velocity is 0.940, lag-3 is 0.897, lag-5 is 0.875 and lag-10 is "',
            '            r"0.817 (model.velocity_autocorr in data/alt_p2.json), so a constant-velocity "',
            '            r"extrapolation stays competitive at the shortest mask (2.914 against "',
            '            r"2.862~cm at 0.2~s) but breaks down once the hidden window exceeds 0.4~s. "',
            '            "Second, the wrist camera is present in 9 of 31 EgoDemo records and in all 14 "',
            '            "EgoPro records but in none of the 24 EgoStandard records, and it carries no "',
            '            "world extrinsic, so a filter that needs a second viewpoint cannot be run on "',
            '            "the whole corpus. Both facts point the same way: the predictor must be a "',
            '            "single-viewpoint recursive filter with explicit velocity damping, not a "',
            '            "ballistic extrapolation and not a multi-view triangulation."',
        )),
    ],
    r"code\alt_p3_ccmip.py": [
        (78, 78, r"# 1. Scenario generation: empirical residual quantiles from all eligible segments"),
        (83, 87, j(
            r'    split="all"        -> every eligible segment (default, 343 units; ALL THREE splits)',
            r'    split="train"      -> train split only (the conservative choice)',
            r'    split="validation" -> validation split only: this is the pool the official',
            r'                          engine samples true durations from, so its residuals are',
            r'                          the correctly calibrated ones.',
        )),
        (188, 188, r"               eps=0.5, lam=0.01, time_limit=3.0, workers=8,"),
    ],
}


def vendor() -> None:
    d = ROOT / "code" / "vendor"
    d.mkdir(parents=True, exist_ok=True)
    pairs = [
        (MAIN_DIR / "code" / "common.py", d / "common.py"),
        (MAIN_DIR / "code" / "p3_stochastic_schedule.py", d / "p3_stochastic_schedule.py"),
        (MAIN_DIR / "code" / "p3_schedule.py", d / "p3_schedule.py"),
        (MAIN_DIR / "data" / "p3_duration_predictions.csv", d / "p3_duration_predictions.csv"),
    ]
    for src, dst in pairs:
        if not src.exists():
            raise SystemExit(f"vendor source missing: {src}")
        shutil.copyfile(src, dst)
        print(f"  vendored {dst.name} {dst.stat().st_size} B")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    apply()
    _fp(C)
    vendor()
    print("REVISION OK")
