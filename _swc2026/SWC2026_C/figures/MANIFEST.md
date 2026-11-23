# Figure manifest — SWC2026 C (team CSWBMCM2634892)

All eight figures shipped in this directory are referenced by `main.tex`, and every
caption states what the panel shows. No figure contains a number that is not also a
slot in `slots.tex`; where a caption quotes a value it uses the same macro name as the
text, so a single regeneration updates both.

## Referenced figures

| # | File | Label | Section | Producer | What it shows | Data source (json keys) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `fig2_bad_ratio.png` | `fig:bad` | 2.1 | `code/build_panel.py`, `code/p1_state.py` | share of quality-flagged frames per dataset, with the recording-level spread | `p1_state_summary.dataset_means.bad`, `p1_reliability._meta.positive_rate_test` |
| 2 | `fig1_keypoint_tracks.png` | `fig:key` | 3.1 | `code/p1_state.py` | one recording's wrist and fingertip tracks in the head frame, with the flagged spans shaded | `data/panel.npz`, `data/state.npz`, `feature_names.json` |
| 3 | `fig7_reliability_roc.png` | `fig:rel` | 3.4 | `code/p1_model.py` | test ROC of the calibrated, geometric and fused reliability routes against the prevalence line | `p1_reliability.auc_bad_calibrated.test`, `auc_bad_geometry.test`, `auc_bad_fused.test` |
| 4 | `fig3_segmentation.png` | `fig:seg` | 3.4 | `code/p1_model.py`, `code/best_p1a_ksweep.py` | stage boundaries for one record: reference annotations, chain-Ward output at the frozen cap, and the oracle-K variant | `p1_segmentation.by_method.ward`, `by_method.ward_oracleK`, `best_p1a_ksweep.bic` |
| 5 | `fig4_p2_error_vs_mask.png` | `fig:p2err` | 4.3 | `code/p2_predict.py` | RMSE against mask length for hold-last, constant velocity, constant acceleration and the regularised predictor | `p2_prediction.by_length[*].{L_s,method,rmse}` |
| 6 | `fig5_p2_cost_tradeoff.png` | `fig:econ` | 4.3 | `code/p2_predict.py` | the priced objective `J(T)` and its two components against the re-observation interval | `p2_prediction.economics.optimum`, `economics.baselines` |
| 7 | `fig8_p2_crossover.png` | `fig:cross` | 4.3 | `code/p2_crossover.py` | the horizon at which constant velocity overtakes hold-last, mean and median conventions | `p2_crossover.rows[*].{L_frames,hold_rmse_m,cv_rmse_m}` |
| 8 | `fig6_p3_policy.png` | `fig:p3pol` | 5.3 | `code/p3_report.py` | weighted on-time rate by policy and case on the nominal mapping, reference to ceiling | `p3_stochastic_schedule.summary[*].{case,policy,weighted_on_time_rate}` |

## Planned slots (not drawn yet)

| Label | Section | To show | Needed input |
| --- | --- | --- | --- |
| `fig:layers` | 3.1 | the two-layer state: continuous channels on one axis, the five rule-derived stages on the other, with the transition arrows and their probabilities | `data/state_layer.json` transitions; no new measurement needed |
| `fig:protocol` | 5.1 | one job's timeline: release, travel, reservation `b`, realised service `p`, the resulting idle or overrun, and where the free and paid prefixes sit | `data/p3_stochastic_schedule` trial trace plus the design constants |

Neither planned figure is referenced by `main.tex` yet, so the page budget is unaffected
until they are drawn.

## Conventions

- Raster only (PNG, 200 dpi at 0.62–0.86 `\linewidth`); LaTeX scales with
  `\resizebox{\slotFigW}{!}{...}` or `\slotFigWSmall`, because `graphicx` does not
  expand a macro inside `width=`.
- Every panel is generated from `data/*.json` or `data/*.npz`; no figure is traced or
  hand-drawn.
- Section numbers in the table are the current `main.tex` placement. If a section moves,
  update this table rather than the caption.