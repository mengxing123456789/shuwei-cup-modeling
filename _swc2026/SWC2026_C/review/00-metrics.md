# 00 口径基线（由 run_review.py metrics 自动生成，不是审读员写的）

生成时刻 2026-11-22 13:05:42　论文目录 `E:\数学建模\_swc2026\SWC2026_C`

## 0. 被测件的身份（先看这一节，再读任何报告）

| 文件 | mtime / 大小 / 摘要 |
|---|---|
| `main.pdf` | 2026-11-22 13:05:39    1871306 B  sha256:184ED31391343537DA387E0FC390E2F4 |
| `main.tex` | 2026-11-22 13:04:24      99586 B  sha256:A99497B7E57FF122501D28E848B90D16 |
| `data/*.json` (161 个) | 最早 14:41:43 → 最新 2026-11-22 12:49:00 |

## 1. 机器判据原始输出

### review_check　exit=0　（python.exe）

```
paper: E:\数学建模\_swc2026\SWC2026_C
pdf: main.pdf   pages: 70
[ OK ] C4    p1 has summary/abstract=True
[ OK ] C4    p2 has contents/directory=False
[ OK ] C5    header lines matched=25
[ OK ] C5    headers leaking identity=0
[ OK ] C7    chinese chars in body=0 (appendix, not judged=0)
[ OK ] C6    total pages=70
[ OK ] C9    appendix=True code=True
[ OK ] C11   placeholder team number hits=0
[ OK ] C11   self-declared invalid identifier in body=0
[ OK ] C11   has References section=True
[ OK ] C8    reference type markers=9

VERDICT: PASS  (fail=0 unknown=0)
```

### gauntlet_check　exit=0　（python.exe）

```
[band] benchmark: E:\数学建模\_swc2026\SWC2026_C\refs\official_standard.json  n=48  median sections=8.5
[PASS] paper resolved                      E:\数学建模\_swc2026\SWC2026_C
[PASS] R-V01 body <= 30 pages              body=22 (header numerator of first Appendix A page)
[PASS] R-V02 single denominator            distinct totals=1
[PASS] R-V02 numbers contiguous            header numerators form 1..n with no gaps
[PASS] R-V03 zero CJK in body              body cjk=0 (appendix, not judged=0)
[PASS] R-V04 zero 'university'             hits=0
[PASS] R-V05 team number filled            KNOWN OPEN: \baominghao placeholders must be filled before submission
[PASS] R-W06 no unsupported phrases        no 众所周知/显而易见/obviously,
[PASS] R-W11 front matter order            ['summary', 'contents']
[PASS] R-W04 references have type markers  10 type markers on 9 entries
[PASS] R-W04 >=70% references cited        cite calls=9, [n] uses before bibliography=0, entries=9
[PASS] R-V06 verify_numbers present        claims=122 exit=0
[PASS] R-V09 no stale artefact             KNOWN OPEN (explain each): 105 pair(s): data\up2_p3_engine_check.json<-code\up2_p3_engine.py(24.33h), data\up2_p3.json<-code\up2_p3_engine.py(24.31h), data\p2_official.json<-code\p2_official_distance.py(14.72h) …+102
[PASS] R-V07 band measured on both sides   figures/equations non-zero, so project was read from PDF text
[PASS] R-V07 out-of-band count             ABOVE=['words', 'abstract_numbers', 'abstract_density', 'distinct_numbers', 'pct_mentions', 'density_per_100w', 'subsections', 'tables'] BELOW=[]
[PASS] R-V14 figure text >= 6 pt           min=5.98 pt median=11.96 pt violations=0 single-char<6pt=9 (measured by python.exe)

16/16 PASS
pdftotext: security risk: running with elevated privileges
```

### figfont　exit=0　（python.exe）

```
pdf: E:\数学建模\_swc2026\SWC2026_C\main.pdf
spans=11688  min=5.98 pt  median=11.96 pt
violations (>= 3 chars and < 6.0 pt): 0
single-character spans below 6.0 pt (not judged): 9
PASS
```

### verify_numbers　exit=0　（python.exe）

```
PASS P1 scale 69 records / >60k frames
PASS P1 dims 32 state / 8 geom
PASS P1 segmentation evaluated on test only
PASS P1 Ward ARI in [0.30,0.55]
PASS P1 Ward ARI > raw KMeans
PASS P1 Ward F1 > raw KMeans
PASS auc_bad_fused test AUC in [0.5,0.8]
PASS auc_bad_geometry test AUC in [0.5,0.8]
PASS auc_bad_calibrated test AUC in [0.5,0.8]
PASS P1 fused AP > positive-rate baseline
PASS P2 L=6 windows 2207 >= 200
PASS P2 L=15 windows 1499 >= 200
PASS P2 L=30 windows 738 >= 200
PASS P2 L=60 windows 348 >= 200
PASS P2 4 lengths x 4 predictors
PASS P2 ridge RMSE monotone in L
PASS P2 hold RMSE monotone in L
PASS P2 CA diverges at L=2s
PASS P2 ridge beats hold at 0.2s
PASS P2 conformal coverage 0.895 at L=0.2
PASS P2 conformal coverage 0.902 at L=0.5
PASS P2 conformal coverage 0.905 at L=0.6
PASS P2 conformal coverage 0.893 at L=1.0
PASS P2 conformal coverage 0.887 at L=2.0
PASS P2 CV mean crossover earlier than median
PASS P3 every deployable policy contributes 450 trials
PASS P3 oracle upper bound 3 cases x 30 seeds (nominal only)
PASS P3 legacy sweep carries six policies
PASS P3 30 seeds per cell
PASS P3 eta in [0,1]
PASS P3 completion in [0,1]
PASS P3 S1 cost <= budget 32
PASS P3 S2 cost <= budget 34
PASS P3 S3 cost <= budget 40
PASS P3 nominal constraint eta>=0.5 met for all
PASS P3 nominal table 3 cases x 6 policies
PASS P3 analytic capacity S1 in [0.5,1.2]
PASS P3 analytic capacity S2 in [0.5,1.2]
PASS P3 analytic capacity S3 in [0.5,1.2]
PASS P3 prefix model beats mean baseline
PASS P1a learned detector beats the agglomeration baseline by a wide margin
PASS P1a learned detector beats the agglomeration baseline
PASS P1a decoding constants are a point of the validation grid
PASS P1a selection value came from validation records
PASS P1a test record count
PASS P1a by-dataset averages bracket the pooled average
PASS P1a every source dataset has a positive ARI
PASS P3 search candidate count
PASS P3 S2 verdict: usable improvement
PASS P3 S2 all-30 gain positive
PASS P3 S2 hold-out gain positive
PASS P3 S2 selected minus baseline equals the paired mean
PASS P3 S2 candidate not worse on completion
PASS P3 S3 verdict: usable improvement
PASS P3 S3 all-30 gain positive
PASS P3 S3 hold-out gain positive
PASS P3 S3 selected minus baseline equals the paired mean
PASS P3 S3 candidate not worse on completion
PASS P3 mixed all-30 interval excludes zero
PASS P3 mixed hold-out interval excludes zero
PASS P3 mixed policy averaged over 30 seeds
PASS closed form calibrated on 8000 executed jobs
PASS closed form base rate inside (0,1)
PASS closed form beats the constant forecast in Brier
PASS closed form Brier skill above 0.5
PASS closed form calibration error below 0.10
PASS closed form tracks every alpha cell within 0.10
PASS reported mean alpha error equals the per-cell mean
PASS fitting the law on train only is the more optimistic of the two
PASS alpha collapse reported on the nine-cell grid
PASS a larger service multiplier lowers the on-time probability in every case
PASS phase grid is 13 quantiles by 4 multipliers
PASS S2 phase grid dimensions match axes
PASS S2 raising the quantile never raises the rate
PASS S2 q0.30 to q0.90 costs more than five points
PASS S2 alpha 0.75 to 1.50 moves the rate by more than 25 points
PASS S2 the service multiplier dominates the reservation quantile
PASS S3 phase grid dimensions match axes
PASS S3 raising the quantile never raises the rate
PASS S3 q0.30 to q0.90 costs more than five points
PASS S3 alpha 0.75 to 1.50 moves the rate by more than 25 points
PASS S3 the service multiplier dominates the reservation quantile
PASS phase diagram reports cost for both cases
PASS S2 scheduling rule is worth more than fifteen points
PASS S2 the rule is worth more than the truth
PASS S2 paid observation is recorded at zero
PASS S2 an extra reservation costs more than five points
PASS S3 scheduling rule is worth more than fifteen points
PASS S3 the rule is worth more than the truth
PASS S3 paid observation is recorded at zero
PASS S3 an extra reservation costs more than five points
PASS P1-b V8 passes both pre-registered bars
PASS P1-b V8 average precision above 0.13
PASS P1-b V8 weakest environment above the first-round baseline
PASS P1-a decoder upgrade boundary F1
PASS P1-a decoder upgrade ARI
PASS P2 second-round architecture search fails its pre-registered bars
PASS P2 best second-round L30 RMSE
PASS P2 best second-round L30 q90
PASS P1 keypoint LOO has four palm and five tip rows
PASS P1 palm rigidity changes by less than 0.001 cm when any MCP is removed
PASS P1 fingertip centroid stays above one centimetre of within-record scatter
PASS P1 stage sweep: v_lo is the most sensitive threshold at 6.35 pp
PASS P1 stage sweep: reach share at the default is 65.63 per cent
PASS P1 stage sweep names v_lo as the worst knob
PASS P3 full factorial covers both cases
PASS P3 S2 full factorial has 128 corners
PASS P3 S2 frozen policy beats every corner
PASS P3 S2 corner range stays below seven points
PASS P3 S2 slack coefficient is structurally inert
PASS P3 S2 slack quantile is structurally inert
PASS P3 S3 full factorial has 128 corners
PASS P3 S3 frozen policy beats every corner
PASS P3 S3 corner range stays below seven points
PASS P3 S3 slack coefficient is structurally inert
PASS P3 S3 slack quantile is structurally inert
PASS figure chain.png exists >10kB
PASS figure fig0_framework.png exists >10kB
PASS figure fig2_bad_ratio.png exists >10kB
PASS figure fig4_p2_error_vs_mask.png exists >10kB
PASS figure fig5_p2_cost_tradeoff.png exists >10kB
PASS figure fig8_p2_crossover.png exists >10kB

122 claims passed, 0 failed
claims=122 declared=122 checked=122 failures=0 verdict=PASS exit=0
```

### freshness　exit=0　（python.exe）

```
WARN  105 artefact(s) older than a name-matched script:
  data\up2_p3_engine_check.json      older than code\up2_p3_engine.py        by  24.33 h
  data\up2_p3.json                   older than code\up2_p3_engine.py        by  24.31 h
  data\p2_official.json              older than code\p2_official_distance.py by  14.72 h
  data\p3_neural_progress.json       older than code\p3_neural_progress.py   by   5.15 h
  data\p3_duration_selected.json     older than code\p3_final_duration.py    by   5.12 h
  data\p3_duration_predictions.csv   older than code\p3_final_duration.py    by   5.12 h
  data\p3_duration_residuals.csv     older than code\p3_final_duration.py    by   5.12 h
  data\p3_prefix_informativeness.json older than code\p3_prefix_informativeness.py by   4.92 h
  data\p3_visual_duration.json       older than code\p3_final_duration.py    by   4.79 h
  data\p3_visual_duration.json       older than code\p3_visual_duration.py   by   4.79 h
  data\p3_prefix_marginal.json       older than code\p3_prefix_marginal.py   by   4.78 h
  data\p3_prefix_marginal_value.csv  older than code\p3_prefix_marginal.py   by   4.78 h
  data\p3_final_duration.json        older than code\p3_final_duration.py    by   4.77 h
  data\p3_final_duration.json        older than code\p3_visual_duration.py   by   4.77 h
  data\p3_duration_predictions_v2.csv older than code\p3_final_duration.py    by   4.77 h
  data\p3_duration_residuals_v2.csv  older than code\p3_final_duration.py    by   4.77 h
  data\best_p1a.json                 older than code\best_p1a_hybrid.py      by   4.39 h
  data\best_p1a.json                 older than code\best_p1a_k.py           by   4.39 h
  data\best_p1a.json                 older than code\best_p1a_ksweep.py      by   4.39 h
  data\best_p1a.json                 older than code\best_p1a_seg.py         by   4.39 h
  -> each line needs one sentence: either re-run the script, or say why the artefact is still valid. A green verify_numbers.py does NOT clear this (a stale artefact is exactly what makes it green).
```

## 2. 怎么用这份文件

- 你的结论若与这里的数字不同，并列两个数并写清"我在何时对哪个文件重跑"，不许只写你自己的（R-V11：报告是快照）。
- 这里的 PASS 只覆盖它能自动判的那几条；它**不**等于论文没问题 —— `verify_numbers.py` 绿着也照样可以有数字过期（R-V09）。