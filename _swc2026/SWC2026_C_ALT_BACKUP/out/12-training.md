BYTES 2096
# Training record — SWC2026_C_ALT_BACKUP

## Summary

NOT-APPLICABLE: this paper trains no neural network. All three questions are solved
with closed-form or combinatorial estimators — Bayesian online change-point
detection with conjugate Beta-Binomial updates, a damped constant-velocity Kalman
filter with method-of-moments noise estimation, and a CP-SAT chance-constrained
mixed-integer program. There is therefore no epoch, batch size, learning rate,
optimiser state or GPU allocation to report.

## What the compute budget was spent on

| Question | Estimator | Cost of one full run |
|---|---|---|
| Q1 | BOCPD, 4,000 posterior draws, 21 keypoints x 5 fingertips x 69 records | 152.7 s on one CPU core |
| Q2 | Kalman + RTS smoother over 126 state dimensions, 4 mask lengths x 300 windows x 7 records | 41.2 s on one CPU core |
| Q3 | CP-SAT over 8/12/16 jobs, 20 residual scenarios, 3 cases x 30 seeds x 3 policies | reported in `out/02-solve.md` |

## Why no learned model appears

The statement's Problem 1 asks for a model of "operation state change" and
"observation reliability" that is *reproducible and inspectable*; Problem 2 asks
for predictions that are evaluated against a held-out record. A 32-dimensional
hand-crafted state vector plus a two-level Beta-Binomial hierarchy satisfies both
requirements with four parameters, each traceable to a stated rule. The companion
paper (the primary submission, `SWC2026_C`) takes the learned route — a TCN over
keypoint sequences and a GRU over hand trajectories — and reports its own training
costs; the two are deliberately different so that a reader can compare the two
answers to the same question.

## Reproducibility

- Interpreter: `E:\Mini\envs\mathmodel\python.exe` (CPython 3.11.18).
- Packages used: numpy, scipy, pandas, pyarrow, ortools 9.15, pymupdf. No CUDA, no
  torch; the run is deterministic given the seeds recorded in each JSON.
- Every script in `code/` is reproduced verbatim in Appendix A, and every number in
  the body is bound to a key in `data/` by `code/verify_numbers.py`.

VERDICT: PASS
