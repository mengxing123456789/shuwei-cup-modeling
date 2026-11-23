# Reproduction for the SWC 2026 Problem C paper.
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File snippets\reproduce.ps1
# Optional second-round chain:  ... -File snippets\reproduce.ps1 -Full
#
# Every number in main.tex is a macro generated from data/*.json by
# code/fill_numbers.py, so the order below matters: data first, slots second,
# LaTeX last.  The script is portable: it locates the Python interpreter and
# MiKTeX itself, and never hard-codes a drive letter.
param([switch]$Full)
$ErrorActionPreference = 'Stop'

$Paper = Split-Path -Parent $PSScriptRoot
Set-Location $Paper

# --- locate Python -----------------------------------------------------------
$PY = $env:MM_PYTHON
if (-not $PY) {
    foreach ($c in @((Join-Path $Paper '.venv\Scripts\python.exe'),
                     (Join-Path $Paper '..\.venv\Scripts\python.exe'))) {
        if (Test-Path $c) { $PY = $c; break }
    }
}
if (-not $PY) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $PY = $cmd.Source }
}
if (-not $PY) { throw 'Python not found. Set MM_PYTHON to a python.exe with numpy, pandas, scipy, scikit-learn and torch.' }

# --- locate xelatex ----------------------------------------------------------
if (-not (Get-Command xelatex -ErrorAction SilentlyContinue)) {
    $texCandidates = @()
    if ($env:MM_TEXBIN) { $texCandidates += $env:MM_TEXBIN }
    $texCandidates += @('E:\MIKTEX\miktex\miktex\bin\x64',
                        'C:\Program Files\MiKTeX\miktex\bin\x64',
                        "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64")
    foreach ($d in $texCandidates) {
        if (Test-Path (Join-Path $d 'xelatex.exe')) {
            $env:PATH = $d + ';' + $env:PATH
            break
        }
    }
}
if (-not (Get-Command xelatex -ErrorAction SilentlyContinue)) {
    throw 'xelatex not found. Set MM_TEXBIN to the MiKTeX bin directory.'
}

# --- raw data locations (only needed by stage 1) -----------------------------
if (-not $env:MM_ROOT)   { $env:MM_ROOT   = Split-Path -Parent $Paper }
if (-not $env:MM_CDATA)  { $env:MM_CDATA  = Join-Path $env:MM_ROOT 'cdata' }
if (-not (Test-Path $env:MM_CDATA)) {
    Write-Host "[warn] raw data not found at $env:MM_CDATA; stage 1 will stop."
    Write-Host "       Set MM_CDATA (or MM_ROOT) to the directory that contains EgoDemo/EgoPro/EgoStandard."
}

$T0 = Get-Date
function Step($name) { Write-Host ("[{0,7:N1} s] {1}" -f ((Get-Date) - $T0).TotalSeconds, $name) }

# 1. panel, state layer and the reliability features  -> data/panel.npz, state*.npz
Step 'build_panel + p1_state'
& $PY code\build_panel.py
& $PY code\p1_state.py
& $PY code\state_layer.py

# 2. Part I: clustering, the selection protocol, the learned boundary detector (GPU),
#    the temporal route (GPU) and its calibration
Step 'p1_model'
& $PY code\p1_model.py
Step 'p1-a selection protocol (validation-only)'
& $PY code\best_p1a_ksweep.py
& $PY code\best_p1a_select.py
& $PY code\best_p1a_traincv.py
Step 'p1-a learned boundaries (GPU, ~5 min) + decoding constants + three-seed ensemble'
& $PY code\p1a_gpu_segmentation.py
& $PY code\p1a_tune_decode.py
& $PY code\p1a_final_decode.py
Step 'p1-b temporal route (GPU, ~20 s) + calibration'
& $PY code\train_gpu_p1b.py
& $PY code\p1b_calib.py
& $PY code\p1b_cost_threshold.py

# 3. Part II: predictors, conformal intervals, masked-input arms, the GRU (GPU)
Step 'p2_predict + crossover'
& $PY code\p2_predict.py
& $PY code\p2_crossover.py
Step 'p2_interval + p2_extra'
& $PY code\p2_interval.py
& $PY code\p2_extra.py
Step 'p2_masked (GPU, ~10 min) + p2 GRU (GPU, ~3 min)'
& $PY code\p2_masked.py
& $PY code\p2_frontier.py
& $PY code\p2_reliability_weight.py
& $PY code\train_gpu_p2.py

# 4. Part III: the corrected protocol, the adaptive search, the online map estimate,
#    the visual probe, and the closed form behind Appendix D
#    p3_stochastic_schedule.py is the ONLY scheduler that implements p = alpha*d + beta.
Step 'p3_stochastic_schedule (corrected protocol)'
& $PY code\p3_stochastic_schedule.py
Step 'p3 sensitivity + adaptive bounds + adaptive search (~4.5 min)'
& $PY code\best_p3_sens.py
& $PY code\p3_adaptive.py
& $PY code\p3_adaptive_stats.py
& $PY code\p3_oracle_same_rule.py
& $PY code\p3_improved_search.py
Step 'p3 online map estimate + visual prefix probe'
& $PY code\p3_online_alpha2.py
& $PY code\p3_visual_sched.py
Step 'closed form: per-job log (~2 min) then calibration (~1 min)'
& $PY code\p3_closedform.py
& $PY code\closedform_calib.py

# 5. number ledger, slot generation, consistency audit
Step 'make_numbers + verify_numbers'
& $PY code\make_numbers.py
& $PY code\verify_numbers.py
& $PY code\audit_recompute.py
Step 'fill_numbers'
& $PY code\fill_numbers.py

if ($Full) {
    # 5b. second-round experiments.  These reuse the first-round feature caches and
    #     take from minutes to a few hours depending on the GPU.  They regenerate
    #     the tables of Appendices G, L, M, N and the second-round numbers.
    Step 'second round: P1 state / P1-b detector'
    & $PY code\up2_p1state_v2.py
    & $PY code\up2_p1b_v2.py
    Step 'second round: P2 models and merge'
    & $PY code\up2_p2_models.py
    & $PY code\up2_p2_merge.py
    Step 'second round: P3 policy and review'
    & $PY code\up2_p3_final.py
    & $PY code\up2_p3review_run.py
    Step 'second round: video features and probes'
    & $PY code\up3_video_badframe.py
    & $PY code\up4_p1b_video.py
    & $PY code\up6_video_late_fusion.py
    Step 'second round: official re-scoring and checks'
    & $PY code\p2_official_distance.py
    & $PY code\p3_official_audit.py
    & $PY code\up10_p1_keypoint_loo.py
    & $PY code\up11_p1_stage_threshold.py
    & $PY code\up12_p3_full_factorial.py
    & $PY code\up14_p3_three_level.py
    & $PY code\up15_p1a_final_repeats.py
    Step 'second round: tables and slots'
    & $PY code\make_appendix_g.py
    & $PY code\make_appendix_k.py
    & $PY code\make_appendix_l.py
    & $PY code\make_appendix_n_p1p3.py
    & $PY code\make_table_loto.py
    & $PY code\fill_numbers.py
    & $PY code\prune_slots.py
}

# 6. compile twice (toc + cross-references), then page accounting
Step 'xelatex x2'
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
Step 'page_report'
& $PY code\page_report.py
Step 'PDF outline'
& $PY code\add_pdf_outline.py

Write-Host ("done in {0:N1} min" -f ((Get-Date) - $T0).TotalMinutes)
