BYTES 3882
# Problem Analysis — ShuWei Cup 2026 C (backup paper, second line of attack)

## The task in one paragraph

An unmanned supermarket is restocked by a single worker whose hands are recorded with 21 keypoints each, together with head-mounted RGB, depth and (on some records) wrist cameras. The released corpus is three archives: EgoDemo (31 records, JSON + Parquet + MP4), EgoPro (14 records, MCAP-derived CSVs) and EgoStandard (24 records, MCAP-derived CSVs). In total 69 records, 66,070 timestamped frames, 24 environments, 41 operators and 30 scenes; the official split is by environment, 16 train / 4 validation / 4 test. The package also contains seven constraint files: `common_conditions.json`, `tasks.csv`, `source_segment_index.csv`, `record_split.csv`, `service_zones.csv`, `job_families.csv` and `Problem_3_Requirements.pdf`.

## Question 1 — state and observation reliability

The statement asks for operation-state changes, a reliability model, and a defensible retention rule with at least one simple baseline. The difficulty is that there is no labelled state sequence: the only supervision is the natural-language annotation and the human quality flags. Our answer is to define a state change as a change in the regime of the hand-velocity field, detect it with Bayesian online change-point detection (BOCPD), and model segment usability with a hierarchical Beta-Binomial layer whose inputs are the per-record bad-frame ratio and the per-segment bad-frame count. Retention is then a posterior decision ("lower 95% bound of usability at least 0.90"), not a hand-set threshold.

## Question 2 — prediction under missing observations

The protocol fixes the masking window, the observation budget, the per-request cost and the delay in advance, so the only freedom is the policy: when to spend an observation. Our answer is a constant-velocity Kalman filter in 3D keypoint space, with process and observation noise estimated from the visible prefixes, and a one-step value-of-information rule that compares the expected reduction in posterior trace against the cost of a look. Baselines are last-state hold, constant-velocity extrapolation and fixed-interval observation.

## Question 3 — restocking scheduling under uncertainty

The statement fixes S1/S2/S3 at 8/12/16 jobs, horizons 100/100/125 s, cost budgets 32/34/40 and paid-observation limits 4/6/8. Service duration is `alpha*d + beta` with nominal `alpha=1`, `beta=0.5`. Our answer is a scenario-based chance-constrained mixed-integer program: the reservation `b_j` and the job order are decision variables, the chance constraint caps the probability of overrun, and the whole program is re-solved after every decision (rolling horizon) rather than committed once.

## Why this is a different paper

The main paper builds a 32-dimensional hand-crafted state vector, clusters it with Ward's method, trains a supervised reliability classifier, regresses masked windows with ridge regression plus conformal calibration, and schedules with a tuned SLACK/EDF rule. This backup paper shares only the released data and the official protocol; every model family is different: point-process change detection with a Bayesian reliability layer, a physical state-space filter with an information-theoretic observation rule, and a chance-constrained integer program with re-planning.

## Corpus query record

`E:\数学建模\.mh\corpus.json` (318,958 bytes, 195 records, all `contest = 数维杯`) was queried with `corpus_index.py`. Queries on `restock`, `shelf`, `unmanned` return 0 records — this exact task has no precedent paper in the local corpus. Neighbouring queries return: `inventory` 8, `missing observation` 10, `pose` 18. The benchmark in `refs/official_standard.json` is the 48-paper ShuWei Cup set (median 7,943.5 words, 14 figures, 5 tables, 14 equations, 8 references).

VERDICT: PASS
