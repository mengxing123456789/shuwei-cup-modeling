BYTES 2952
# P2 part 2 - when to spend a look inside a gap

Same decision points, same targets, same clean-window filter as `alt_p2_kalman.py`. Prefix 6 frames (0.2 s), return delay 30 frames (1.0 s), a look discloses 0.2 s, at most 2 looks per window.

**Structural fact.** A look requested at gap-frame u is usable only if u + 30 < W, so a gap of 31 frames (1.03 s) or less admits no interior look at all. The official options A/B/C therefore get their information from a longer prefix, not from a look inside the gap; within-gap scheduling only exists for W >= 1.5 s.

| gap (s) | usable frames | policy | mean err (cm) | rmse (cm) | p90 (cm) | looks/window |
|---|---|---|---|---|---|---|
| 1.0 | 0 | hold | 10.488 | 12.458 | 19.773 | 0.000 |
| 1.0 | 0 | damped | 10.351 | 12.273 | 19.494 | 0.000 |
| 1.0 | 0 | fixed | 10.351 | 12.273 | 19.494 | 0.000 |
| 1.0 | 0 | drift | 10.351 | 12.273 | 19.494 | 0.000 |
| 1.5 | 14 | hold | 11.265 | 13.634 | 22.009 | 0.000 |
| 1.5 | 14 | damped | 11.231 | 13.600 | 21.802 | 0.000 |
| 1.5 | 14 | fixed | 9.544 | 11.532 | 17.901 | 2.000 |
| 1.5 | 14 | drift | 10.663 | 12.757 | 20.169 | 0.960 |
| 2.0 | 29 | hold | 12.466 | 14.728 | 25.196 | 0.000 |
| 2.0 | 29 | damped | 12.425 | 14.708 | 25.079 | 0.000 |
| 2.0 | 29 | fixed | 10.099 | 12.200 | 19.929 | 2.000 |
| 2.0 | 29 | drift | 11.898 | 14.147 | 24.443 | 0.964 |
| 3.0 | 59 | hold | 12.819 | 14.879 | 24.679 | 0.000 |
| 3.0 | 59 | damped | 12.876 | 14.955 | 24.593 | 0.000 |
| 3.0 | 59 | fixed | 9.850 | 11.740 | 18.647 | 2.000 |
| 3.0 | 59 | drift | 12.969 | 15.067 | 24.664 | 0.040 |

Threshold calibration on validation (drift fraction -> validation mean error / looks):

* 1.0 s: no interior look possible, threshold not calibrated
* 1.5 s: best fraction 0.2 (tau = 0.73 cm) -> 10.370 cm with 1.028 looks
* 2.0 s: best fraction 0.2 (tau = 0.70 cm) -> 11.489 cm with 1.016 looks
* 3.0 s: best fraction 1.0 (tau = 2.30 cm) -> 11.587 cm with 0.139 looks

Paired differences on the same windows (negative = the first policy is better):

| gap (s) | comparison | mean diff (cm) | t | W/T/L |
|---|---|---|---|---|
| 1.0 | damped - hold | -0.137 | -3.09 | 144/0/106 |
| 1.0 | fixed - damped | 0.000 | 0.00 | 0/250/0 |
| 1.0 | drift - damped | 0.000 | 0.00 | 0/250/0 |
| 1.0 | drift - fixed | 0.000 | 0.00 | 0/250/0 |
| 1.5 | damped - hold | -0.034 | -0.79 | 118/0/132 |
| 1.5 | fixed - damped | -1.687 | -5.24 | 158/0/92 |
| 1.5 | drift - damped | -0.568 | -3.11 | 77/112/61 |
| 1.5 | drift - fixed | 1.118 | 4.76 | 89/0/161 |
| 2.0 | damped - hold | -0.041 | -0.98 | 127/0/123 |
| 2.0 | fixed - damped | -2.326 | -5.51 | 159/0/91 |
| 2.0 | drift - damped | -0.527 | -2.76 | 80/110/60 |
| 2.0 | drift - fixed | 1.800 | 4.87 | 91/0/159 |
| 3.0 | damped - hold | 0.057 | 1.32 | 106/0/144 |
| 3.0 | fixed - damped | -3.026 | -6.25 | 161/0/89 |
| 3.0 | drift - damped | 0.093 | 1.90 | 3/241/6 |
| 3.0 | drift - fixed | 3.119 | 6.44 | 87/0/163 |


VERDICT: PASS
