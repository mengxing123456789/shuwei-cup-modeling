BYTES 7176
# Modelling Report — SWC2026_C_ALT_BACKUP (backup paper)

This report describes the model that is actually delivered in `main.tex`. It is
a different construction from the primary paper `SWC2026_C` (which uses a
supervised ridge + conformal predictor and a fixed decision threshold); here
all three questions are built on Bayesian/state-space estimators with honest
negative results. `main.tex` and the JSON products in `data/` are authoritative;
where an earlier design brief disagreed, it was superseded.

## 0. One line per question

1. **Q1** — a recording is segmented by a BOCPD run-length posterior over the
   speed of the fingertip centroid (resampled to 5 Hz); each segment carries a
   hierarchical Beta-Binomial posterior on its usable probability `rho = 1 - theta`.
2. **Q2** — the hand is a damped constant-velocity target (126-dimensional
   state) observed through a single wrist camera; the value of a paid look is a
   derived price from the marginal posterior trace reduction.
3. **Q3** — restocking is a stochastic scheduling problem; a scenario
   chance-constrained CP-SAT program chooses order and reservation and is rolled
   forward after each job, with a deterministic EDF fallback on solver timeout.

## 1. Data layer

The corpus is three archives with three containers. After unification the panel
is keyed by `(record, t)` and carries, per hand, 21 keypoints in 3D in the head
frame, a bad-frame quality flag, and for some records a wrist camera. The split
is environment-level, 16 train / 4 validation / 4 test, so no environment is
shared between fitting and evaluation. The record identifier is not the
directory name: the true `episode_uuid` lives in `session_metadata.csv` (MCAP)
or `meta/episodes/*.parquet` (EgoDemo). The 1.2 s eligibility threshold in
`source_segment_index.csv` is subject to floating-point subtraction: a 1e-9
tolerance gives 343 eligible of 349 annotated segments, matching the statement.
`out/alt_p2.md` and `data/alt_full_audit.json` hold the full audit.

## 2. Q1 — change points and reliability

### 2.1 BOCPD
Within a regime the centroid speed is a noisy constant with unknown mean and
variance; the conjugate Normal-Inverse-Gamma prior gives a Student-t predictive,
and the run-length posterior is updated recursively with hazard `1/lambda`.
Four settings are fixed before any evaluation: smoothing `sigma = 0.40 s`,
hazard `lambda = 4.0 s` (the median annotated training segment length), merge
threshold `3.0 s`, drop fraction `0.30`. A boundary is declared when the
run-length posterior falls below 30% of its running peak; the raw `P(r_t = 0)`
never exceeds 0.119, so a literal "return to zero" rule would almost never fire.
Segments shorter than 3.0 s are merged. `code/alt_p1_bocpd.py` is the producer.

### 2.2 Hierarchical reliability
For segment `i` with `y_i` bad frames out of `n_i`:
`y_i ~ Binomial(n_i, theta_i)`, `theta_i ~ Beta(mu*kappa, (1-mu)*kappa)`,
`mu ~ Beta(a0, b0)`. The posterior of `mu` is computed on a grid; each segment
is reported by its posterior mean and one-sided 2.5% lower bound on
`rho_i = 1 - theta_i`. The retention rule `q_0.025(rho_i) >= 0.90` keeps 333 of
349 annotated segments (95.4%, 95.70% duration-weighted).

### 2.3 The honest negative result
The kinematic detector **loses** to a fixed speed-threshold baseline at strict
tolerance (boundary F1 0.183 vs 0.219 at +/-0.5 s), because annotated boundaries
are semantic subtask changes while the detector finds motion regime changes.
The reliability layer, not the segmentation layer, is the deliverable; its
within-record AUC reverses to 0.076 under leave-one-segment-out, which is
reported rather than hidden. A record-level AUC of 0.914 is exposed as an
artefact of aggregation. `data/alt_p1.json` holds all four diagnostics.

## 3. Q2 — damped Kalman filter and value of information

### 3.1 Filter
State `[p_t, v_t]` with `v_{t+1} = alpha*v_t + w_t`; `alpha = 0.6` is chosen on
the validation split. `Q` and `R` are estimated by the **method of moments** on
visible training prefixes (`q = Var(v)(1 - alpha^2)`, `r` from the 10th
percentile of squared second differences / 6); expectation-maximisation
degenerates to the numerical floor (`R` median 1.6e-9) and was abandoned.

### 3.2 Value of information
In a linear-Gaussian model the posterior covariance is observation-independent,
so the expected trace reduction is the same for every record: VOI collapses to
a step (0 or 2 looks, no interior solution). The threshold `lambda* = 1158.0
cm^2` per look (= 1.61 cm RMSE) is a **derived price** from the marginal
posterior trace reduction, not a calibrated hyperparameter. Masked-window error
follows `e(L) = 10.07 L^0.741` (R^2 = 0.967). Baselines are last-state hold,
constant-velocity extrapolation, and a linear fit on the same windows and seeds.
`data/alt_p2.json` holds the tables; the delivered paper also reports the
measured scaling law and the fair-prefix comparison.

## 4. Q3 — chance-constrained scheduling

### 4.1 Scenarios
`S = 20` scenarios are built from the 5-95% quantile grid of residuals of all
343 eligible segments (246 train, 35 validation, 62 test), grouped by family x
observation prefix, with per-unit rank de-correlation by CRC32 so scenarios are
not comonotone. Pooling all three splits is a leakage; a train-only ablation
(`data/alt_p3_sweep.json`) bounds it and leaves the ranking unchanged.

### 4.2 Program
Chance constraint on **completion feasibility** `P(C_j^omega > H) <= epsilon =
0.50`, enforced by the scenario count `floor(epsilon*S)`; the big-M constant is
used only on ordering arcs. Start times `s_j = max(r_j, s_{j-} +
max(p_{j-}^omega, b_{j-}) + D + 0.5)`; the device is released at
`s_j + max(p_j, b_j)` and the clock advances to that release. Objective:
`1e4` weighted on-time + `3e3` completion - truncated (10 s) tardiness -
`10*S*lambda*cost` with `lambda = 0.01`. Solved to feasibility within a 1.0 s
CP-SAT limit with a deterministic EDF fallback; solver fallbacks are counted in
the trials and reported in the paper.

### 4.3 Result, stated as measured
The rolling program beats EDF but **does not beat SLACK**; the best policy on
the declared metric is `slack_old`, not our program. A six-level `epsilon` sweep
(0.20-0.70) and a train-only residual bank leave that ranking unchanged.
Baselines are EDF and SLACK with prediction-based and pressure-adaptive reserves
(the official `p3_stochastic_schedule.py`), on the same 30 seeds. The
opportunity-constraint MIP's one-shot rows in S2/S3 fall back to EDF on every
seed, which is disclosed. `data/alt_p3.json` is the record; the frozen read-only
dependencies are in `code/vendor/`.

## 5. Verification
`code/verify_numbers.py` binds every printed number to a key in `data/*.json`
(221 claims, including all 60 cells of Table~`tab:p3` cell by cell) and fails on
any unbound token; it also asserts the measured `epsilon` sweep, paired 30-seed
confidence intervals and fallback counts. `data/alt_p3_sweep.json` is produced
by `code/alt_p3_sweep.py`. The six judgement/figure/appendix records in `out/`
and `review/` were aligned to this 111-page revision in the same round.

VERDICT: PASS
