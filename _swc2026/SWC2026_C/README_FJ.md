# Support package — SWC 2026 Autumn, Problem C, Team SWBMCM2634892

## What this package is

Everything needed to regenerate every number printed in `main.pdf`, and to see how
each number reaches the page. No number in the paper was typed by hand: each is a
macro in `slots.tex` produced from a JSON ledger in `data/`.

```
main.tex                 LaTeX source, English, official swmcmthesis class
slots.tex                GENERATED. 626 macros used by the paper (full 1548 in slots.full.tex)
swmcmthesis.cls/.cfg     official 2026 template, with appendix-heading and listing-margin adjustments
requirements.txt         Python 3.11 environment used for every number
figures/                 every figure referenced in the text
snippets/                real code excerpts printed in Appendix B, plus reproduce.ps1
code/                   197 scripts; see the run order below
data/*.json              the result ledger, with sha256 in data/derived_manifest.json
```

## One-command reproduction

```powershell
powershell -ExecutionPolicy Bypass -File snippets\reproduce.ps1
```

The script locates Python and MiKTeX itself (override with `MM_PYTHON` and
`MM_TEXBIN`), and never hard-codes a drive letter. Raw data are read from
`MM_CDATA` (default `<parent of the paper>\cdata`); the official attachments from
`MM_C_PROBLEM_ROOT` (default `<paper>\problem\Restocking_Problem_and_Data_EN`).
The default path reproduces the main paper chain in about an hour on this machine.
Pass `-Full` to add the second-round experiments behind Appendices G, L, M, N and
the later tables; that branch reuses the first-round feature caches and takes
hours on a single GPU.

Run order, and which file each stage produces:

| Stage | Script(s) | Output |
| --- | --- | --- |
| 1 Panel and state | `code/build_panel.py`, `code/p1_state.py`, `code/state_layer.py` | `panel.npz`, `state*.npz`, `state_layer.json` |
| 2 Part I model | `code/p1_model.py` | `p1_state.json`, `p1_reliability.json` |
| 3 P1-a selection protocol | `code/best_p1a_ksweep.py`, `code/best_p1a_select.py`, `code/best_p1a_traincv.py` | `best_p1a_*.json` |
| 4 P1-a learned boundaries (GPU) | `code/p1a_gpu_segmentation.py`, `code/p1a_tune_decode.py`, `code/p1a_final_decode.py` | `p1a_gpu_segmentation*.json`, probabilities |
| 5 P1-b temporal route and calibration | `code/train_gpu_p1b.py`, `code/p1b_calib.py`, `code/p1b_cost_threshold.py` | `p1b_gpu.json`, `p1b_calib.json` |
| 6 Part II predictors | `code/p2_predict.py`, `code/p2_crossover.py` | `p2_prediction.json`, `p2_crossover.json` |
| 7 Intervals, extra horizons and masked arms | `code/p2_interval.py`, `code/p2_extra.py`, `code/p2_masked.py`, `code/p2_frontier.py`, `code/p2_reliability_weight.py`, `code/train_gpu_p2.py` | `p2_interval.json`, `p2_extra.json`, `p2_masked.json`, `p2_gru.json` |
| 8 Part III, corrected protocol | `code/p3_stochastic_schedule.py` | `p3_stochastic_schedule.json` |
| 9 Part III sensitivity, bounds and search | `code/best_p3_sens.py`, `code/p3_adaptive.py`, `code/p3_adaptive_stats.py`, `code/p3_oracle_same_rule.py`, `code/p3_improved_search.py` | `best_p3_sens.json`, `p3_adaptive.json`, `p3_improved*.json` |
| 10 Online map estimation and closed form | `code/p3_online_alpha2.py`, `code/p3_visual_sched.py`, `code/p3_closedform.py`, `code/closedform_calib.py` | `p3_online_alpha2.json`, `p3_closedform*.json` |
| 11 Ledger and slots | `code/make_numbers.py`, `code/verify_numbers.py`, `code/audit_recompute.py`, `code/fill_numbers.py`, `code/prune_slots.py` | `slots.tex`, audit JSON |
| 12 Second round (`-Full`) | `code/up2_*.py`, `code/up3_video_badframe.py`, `code/up4_p1b_video.py`, `code/up5_video_badframe_10hz.py`, `code/up6_video_late_fusion.py`, `code/up10_*.py`–`code/up15_*.py`, `code/p2_official_distance.py`, `code/p3_official_audit.py` | `data/up*.json`, official re-scoring |
| 13 Figures and appendices | `code/remake_body_figures.py`, `code/make_phase_figure.py`, `code/make_value_figure.py`, `code/make_framework_figure.py`, `code/make_chain_figure.py`, `code/make_appendix_g.py`, `code/make_appendix_k.py`, `code/make_appendix_l.py`, `code/make_appendix_n_p1p3.py`, `code/make_table_loto.py` | `figures/*.png`, `tables/app_*.tex` |
| 14 Compile and page check | `xelatex main.tex` twice, then `code/page_report.py` | `main.pdf` |

## Two things a reader must know before re-running

**The service law is the affine map.** The statement fixes
`p = alpha * source_annotation_duration_s + beta_s`. Only
`code/p3_stochastic_schedule.py` implements that law; the older
`code/p3_schedule.py` uses `d` directly and is kept for comparison only. Every
Part III number in the paper comes from the corrected file.

**RMS error units.** `p2_masked.json` stores the three-dimensional RMS error in
centimetres. The paper reports per-coordinate RMS, so `code/fill_numbers.py`
divides by sqrt(3) (operator `pc3`). Mixing the two gives a factor 1.732 error.

## Deliberate exclusions, and how to get them back

The released raw package is 5.8 GB and must not be redistributed here. Large
intermediate arrays are left out of the zip; each is produced by the stage named:

| Excluded file | Size | Regenerated by |
| --- | --- | --- |
| `data/pre_cache.npz` | 102 MB | `code/pre_ssl.py` |
| `data/panel.npz` | 30 MB | `code/build_panel.py` |
| `data/state.npz`, `data/state_layer.npz` | 35 MB | `code/p1_state.py`, `code/state_layer.py` |
| model weights `*.pt` | ~3 MB | `code/train_gpu_p1b.py`, `code/pre_ssl.py` |
| `data/p1b_probs.npz` | 1.7 MB | `code/p1b_calib.py` |

All `data/*.json` result ledgers are included, so the numbers in the paper can be
checked against the ledger without re-running anything. `data/derived_manifest.json`
records the byte size and sha256 of every one of the 165 ledgers.

## Negative results are kept on purpose

Three arms that did not beat the frozen baseline are reported as negative results
rather than removed: the mask-aware channel in §4.3, the self-supervised
pre-training arms (`data/pre_p2_results.json`), and the $k$-cap variants of P1-a
(`data/best_p1a_ksweep.json`). Each is in the ledger and can be reproduced.

## AI tool usage

Declared in the paper's AI tool usage report. The assistant was used only for
drafting and debugging utility scripts and for repetitive text transformations
(renaming slots, updating cross-references, re-running mechanical consistency
checks). The model design, derivations, choice and interpretation of every result,
and the writing of the report are the team's own work.
