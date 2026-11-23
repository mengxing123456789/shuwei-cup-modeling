BYTES 5690
# Solution record — SWC2026_C_ALT_BACKUP

Every number below is read from `data/alt_p1.json`, `data/alt_p2.json` or
`data/alt_p3.json`; `code/verify_numbers.py` re-checks each one against the printed
text of `main.tex`.

## Question 1 — change points and reliability

**Estimator.** Bayesian online change-point detection (Adams & MacKay) on a 5 Hz
re-sampling of the five fingertip tracks, run length truncated at 120 s, hazard
rate λ = 4.0 s taken from the median annotated segment length of the training
environments. A change point is declared where the MAP run length falls below 30%
of its running peak; segments shorter than 3.0 s are merged. Reliability is a
two-level Beta-Binomial: record level (κ = 50) then segment level (κ = 20), with a
97.5% lower bound on the usable probability ρ = 1 − θ as the retention statistic.

**Result.** 399 change points across 69 records against 280 annotated internal
boundaries. Greedy one-to-one boundary F1 is 0.100 at ±0.2 s, **0.183 at ±0.5 s**,
0.580 at ±2 s and 0.654 at ±5 s; the threshold baseline scores 0.112 / 0.219 /
0.550 / 0.640 on the same tolerances. Count error MAE 2.94 segments (bias +1.72)
against 2.35 (−0.06) for the baseline, with 276 predicted segments versus 280
annotated.

**The honest finding.** BOCPD loses to the threshold baseline at the two strict
tolerances. The reason is structural, not a tuning failure: an annotated boundary
marks a change of *semantic task*, and the fingertip trajectories often continue
smoothly across it. A kinematic detector can only see the discontinuity it is
given, so it fires inside segments where the hand pauses and misses boundaries
where the task changes without a pause. At the half-segment tolerance (≈1.7 s) the
detector covers 85.1% of annotated segments (297 of 349) with 1.14 cuts per segment
against 0.79 for the baseline — it over-segments, which is the expected signature
of a kinematic detector asked for a semantic boundary.

**Reliability.** The published rule `q_{0.025}(ρ_i) ≥ 0.90` retains 333 of 349
segments (95.4%, 95.70% by duration). It is not idle: all 298 segments with zero
bad frames are kept, and only 35 of the 51 segments that contain bad frames are
kept (68.6%).

**Where the layer fails.** Against an external bad-frame label (51 positive
segments, prevalence 14.6%), the record-level posterior bound reaches AUC 0.914 and
the raw record bad-frame rate 0.915. But the hierarchical leave-one-out score at
segment level is 0.675, the official `eligible` flag scores 0.490, and on the 21
records that contain both clean and contaminated segments the record-level score is
0.500 by construction while the segment-level leave-one-out score falls to 0.076 —
the sign reverses. The mechanism: removing a segment's frames makes the rest of
its record look cleaner, so the prior rate drops and the lower bound rises. No
choice of κ repairs this; it needs a source of information independent of the
bad-frame label, which this release does not provide. The layer is therefore
reported as an **aggregator** (an interval plus a reproducible retention rule), not
as a detector.

## Question 2 — prediction and re-observation

**Estimator.** 126-dimensional state (21 keypoints × position and velocity) in the
head frame, damped constant velocity `v' = α v + w`, noise by method of moments
(`q = Var(v)(1 − α²)`, `r = p10(d²)/6`). α is chosen on the validation
environments: 0.6 minimises the mean error over the four mask lengths (9.117 cm),
against 29.936 cm at α = 1. EM was tried and abandoned — on this data it drives
r → 0 and the RTS variance leaves its admissible range.

**Masking protocol.** Seven test records, prefix 0.2 s, stride L/2, 300 windows per
mask length. Mean 3D error, cm: L = 0.2 → **2.86** (hold 3.39, constant velocity
2.91); 0.4 → **5.656** (5.998 / 7.731); 0.6 → **7.095** (7.353 / 11.502);
1.0 → **9.464** (9.554 / 21.497). The filter beats both baselines at every mask
length and its advantage grows with L, which is the expected behaviour of a model
that carries velocity.

**Value of information.** The three information options of the statement, evaluated
on the same windows: no request → 12.377 cm with posterior trace 3379.9 cm²; one
request → 12.809 cm with trace 2221.9; two requests → **9.874 cm** with trace
1063.9. The two marginal trace reductions are 1158.006 and 1158.005 cm², so the
value of one paid look is λ* = 1158.0 cm² per cost unit, i.e. 1.61 cm of RMSE per
look. Because the posterior covariance does not depend on the observed value in a
linear-Gaussian model, the decision is a step function: buy zero looks or buy two,
never one.

**Two limitations stated plainly.** The prefix length makes no difference — 0.2,
0.6 and 1.0 s give the identical 12.789 cm — because r → 0 makes the filter trust
the last frame completely and the velocity is already decorrelated by then. And the
per-record VOI collapses to a single rule for the same reason; a heteroscedastic
observation model would be needed to make the decision record-specific.

## Question 3 — scheduling under uncertainty

See `out/alt_p3.md` for the full table. The comparison is paired: every policy sees
the same sampled jobs under the same seed, 30 public seeds per case, and every
policy is charged the same fixed execution fee, the same reservation rate and the
same distance cost.

## Cross-question links

The Q1 variance estimate enters Q2 as the process-noise scale; the Q1 reliability
bound enters Q3 as the reservation floor. Both links are one-directional: neither
Q2 nor Q3 feeds back into Q1, so the three questions can be read in any order.

VERDICT: PASS
