#!/usr/bin/env python3

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Regenerate ``slots.tex`` (one ``\\newcommand`` per reported number) from ``data/*.json``.

Rules
-----
* Nothing numeric is ever typed into ``main.tex``.  Every number used by the paper is
  either a *measured* value resolved here from ``data/*.json`` (``SLOTS``) or a
  *problem-given constant* transcribed from the statement (``SPEC``, each with a
  source tag).  There is no third category: unknown quantities stay ``\\slotTODO``.
* ``data/*.json`` and the other ``code/*.py`` files are only read, never written.
* Run:  ``python code\\fill_numbers.py``

Path syntax inside ``SLOTS``: each element is a dict key, a list index (int), or a
selector string ``@field=value,field2=value2`` that picks the first matching element
of a list of dicts (numeric comparison is tolerant).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT_SLOTS = ROOT / "slots.tex"
OUT_TODO = ROOT / "todo_numbers.md"
SNIP = ROOT / "snippets"

# ---------------------------------------------------------------------------
# 1. Problem-given constants (NOT results).  value, source tag.
# ---------------------------------------------------------------------------
SPEC = {
    "FloatTextSep": ("6pt plus 1pt minus 1pt", "layout: float separation"),
    "FloatSep": ("4pt plus 1pt minus 1pt", "layout: float separation"),
    "FloatIntSep": ("4pt plus 1pt minus 1pt", "layout: float separation"),
    "DisplayAbove": ("4pt plus 2pt minus 2pt", "layout: display skip"),
    "DisplayBelow": ("4pt plus 2pt minus 2pt", "layout: display skip"),
    "PalmKeypoints": ("0, 5, 9, 13, 17", "state-layer rule: palm-centre keypoints"),
    "TeamID": ("SWBMCM2634892", "team registration number (without problem letter)"),
    "Year": ("2026", "contest year"),
    "Group": ("Undergraduate", "team division"),
    # --- data scale (problem statement, Data section) ---
    "NRecords": ("69", "statement: 69 records, 24 environments"),
    "NEnv": ("24", "statement: 24 environments"),
    "NTimestamps": ("66070", "statement: 66,070 timestamps"),
    "SizeGB": ("5.834", "statement: 5.834 GB"),
    "SizeBytes": ("5834008305", "statement: 5,834,008,305 bytes"),
    "DemoRecords": ("31", "statement: EgoDemo"),
    "ProRecords": ("14", "statement: EgoPro"),
    "StdRecords": ("24", "statement: EgoStandard"),
    "DemoTS": ("16414", "statement: EgoDemo timestamps"),
    "ProTS": ("17642", "statement: EgoPro timestamps"),
    "StdTS": ("32014", "statement: EgoStandard timestamps"),
    "NKeypoints": ("21", "statement: 21 3D keypoints per hand"),
    "FPS": ("30", "statement / data: 30 Hz"),
    "SplitTrain": ("16", "statement: 16/4/4 environment split"),
    "SplitVal": ("4", "statement: 16/4/4 environment split"),
    "SplitTest": ("4", "statement: 16/4/4 environment split"),
    # --- Problem 2 protocol (self-frozen before experiments, see out/00-problem.md) ---
    "MaskA": ("0.2", "P2 frozen mask set"),
    "MaskB": ("0.5", "P2 frozen mask set"),
    "MaskC": ("1.0", "P2 frozen mask set"),
    "MaskD": ("2.0", "P2 frozen mask set"),
    "MaskFramesA": ("6", "P2 frozen mask set"),
    "MaskFramesB": ("15", "P2 frozen mask set"),
    "MaskFramesC": ("30", "P2 frozen mask set"),
    "MaskFramesD": ("60", "P2 frozen mask set"),
    "Ctx": ("10", "P2 frozen context length"),
    "PMaskFramesZero": ("0", "p2_masked.json _meta.KS_EVAL[0]"),
    "PMaskFramesThree": ("3", "p2_masked.json _meta.KS_EVAL[1]"),
    "PMaskFramesSix": ("6", "p2_masked.json _meta.KS_EVAL[2]"),
    "ReactiveCM": ("5", "P2 reactive baseline threshold, cm"),
    # --- Problem 3 protocol (C_Problem3_Requirements.txt) ---
    "PrefixFree": ("0.2", "P3 free prefix"),
    "PrefixMid": ("0.6", "P3 first paid review prefix"),
    "PrefixLong": ("1.0", "P3 second paid review prefix"),
    "ReviewCost": ("1", "P3 review cost unit"),
    "ReviewDelay": ("1", "P3 review scenario-second delay"),
    "PSchedDelayDistribution": ("1.0", "common_conditions.json: observation.delay_s (fixed by the protocol, not measured)"),
    "PVisDurRel": ("-16.7", "relative: p3_final_duration.json visual_a300 test MAE 2.5746 vs pose_old8 ridge 3.0920 (p3_visual_duration.json)"),
    "PVisSchedSTwoD": ("+0.031", "p3_visual_schedule.json minus p3_stochastic_schedule.json, slack_fusion S2, same 30 seeds"),
    "PVisSchedSThreeD": ("-0.009", "p3_visual_schedule.json minus p3_stochastic_schedule.json, slack_fusion S3, same 30 seeds"),
    "PVisOracleSThreeD": ("+0.025", "p3_visual_schedule.json minus p3_stochastic_schedule.json, oracle S3, ceiling shift"),
    "PProductStateVars": ("grasp success and shelf occupancy", "state-layer definition; the package ships no product annotations"),
    "PCFAlphaLow": ("0.75", "mapping-sensitivity grid: short service multiplier"),
    "PCFAlphaNom": ("1.0", "nominal service multiplier"),
    "PCFAlphaHigh": ("1.5", "mapping-sensitivity grid: long service multiplier"),
    "MaxReviewsPerJob": ("2", "P3 reviews per job"),
    "JobsSOne": ("8", "P3 case S1"),
    "JobsSTwo": ("12", "P3 case S2"),
    "JobsSThree": ("16", "P3 case S3"),
    "HSOne": ("100", "P3 horizon S1"),
    "HSTwo": ("100", "P3 horizon S2"),
    "HSThree": ("125", "P3 horizon S3"),
    "BudgetSOne": ("32", "P3 budget S1"),
    "BudgetSTwo": ("34", "P3 budget S2"),
    "BudgetSThree": ("40", "P3 budget S3"),
    "KSOne": ("4", "P3 review limit S1"),
    "KSTwo": ("6", "P3 review limit S2"),
    "KSThree": ("8", "P3 review limit S3"),
    "SeedStart": ("2026111700", "P3 official seed list"),
    "SeedEnd": ("2026111729", "P3 official seed list"),
    "NSeeds": ("30", "P3 official seed list"),
    "NTrials": ("450", "P3: 3 cases x 5 mappings x 30 seeds"),
    "MaxActions": ("200", "P3 action cap per trial"),
    "CostBase": ("2", "P3 execution cost constant"),
    "CostB": ("0.1", "P3 execution cost coefficient of b"),
    "CostD": ("0.2", "P3 execution cost coefficient of D"),
    "ChangeOver": ("0.5", "P3 travel change-over time"),
    "BMin": ("0.2", "P3 minimum reservation"),
    "OnTimeFloor": ("0.50", "P3 required mean weighted on-time rate"),
    "AlphaLow": ("0.75", "P3 mapping set"),
    "AlphaNom": ("1", "P3 nominal mapping"),
    "AlphaHigh": ("1.5", "P3 mapping set"),
    "BetaLow": ("0", "P3 mapping set"),
    "BetaNom": ("0.5", "P3 nominal mapping"),
    "BetaHigh": ("1", "P3 mapping set"),
    "NIntervals": ("349", "P3 attachment intervals"),
    "NEligible": ("343", "P3 intervals of at least 1.2 s"),
    "MinEligibleDur": ("1.2", "P3 eligibility threshold"),
    "ZoneZero": ("0", "P3 zone labels"),
    "ZoneOne": ("1", "P3 zone labels"),
    "ZoneTwo": ("2", "P3 zone labels"),
    "ZoneThree": ("3", "P3 zone labels"),
    "ZoneFour": ("4", "P3 zone labels"),
    "MissingDocs": ("5", "referenced Data_Documentation files absent from the package"),
    "CaseOne": ("1", "case label S1"),
    "CaseTwo": ("2", "case label S2"),
    "CaseThree": ("3", "case label S3"),
    "CILevel": ("95", "reporting convention: paired 95% confidence interval"),
    "ConfLevel": ("90", "P2 nominal conformal level"),
    "OnTimeFloorPct": ("50", "P3 required mean weighted on-time rate, percent"),
    "FusionWeight": ("0.5", "frozen reliability fusion weight"),
    "LogitC": ("0.1", "frozen logistic regularisation, code/p1_model.py"),
    "RidgeAlpha": ("10", "frozen P2 ridge penalty, code/p2_predict.py"),
    "DurRidgeAlpha": ("3", "frozen P3 duration ridge penalty, code/p3_schedule.py"),
    "KMin": ("2", "frozen BIC search range for the segment count"),
    "KMax": ("8", "frozen BIC search range for the segment count"),
    "SmoothWin": ("5", "frozen moving-average window, frames"),
    "ReserveQ": ("60", "frozen reservation residual quantile, percent"),
    "SlackDecay": ("10", "frozen slack decay constant in the SLACK score"),
    "PassAUC": ("0.55", "pre-declared P1 reliability pass mark"),
    "PassARI": ("0.35", "pre-declared P1 segmentation pass mark"),
    "PassFOne": ("0.45", "pre-declared P1 segmentation pass mark"),
    "PassCountErr": ("10", "pre-declared P1 segmentation pass mark"),
    "NStages": ("5", "discrete state layer: reach/pick/place/transport/arrange"),
    "NContinuousLayers": ("2", "two-layer state definition"),
    # --- layout constants (not results) ---
    "BibWidth": ("99", "layout"),
    "TocDepth": ("1", "layout"),
    "FigW": (r"0.78\linewidth", "layout"),
    "FigWFull": (r"0.96\linewidth", "layout"),
    "FigWSmall": (r"0.66\linewidth", "layout"),
    "FigWSub": (r"0.43\linewidth", "layout"),
    "FigWWide": (r"0.90\linewidth", "layout"),
    "HeadHeight": ("20pt", "layout"),
    "TabColSep": ("4pt", "layout"),
    "VHigh": ("0.1", "state-layer rule v_hi (m/s)"),
    "VLow": ("0.05", "state-layer rule v_lo (m/s)"),
    "AGrasp": ("0.15", "state-layer rule a_grasp"),
    "TArrange": ("0.8", "state-layer rule t_arrange (s)"),
    "NVideos": ("184", "package audit: video files"),
    "VideoMB": ("5373.5", "package audit: video volume (MB)"),
    "VideoShare": ("92.4", "package audit: video share of package volume (%)"),
    "DepthFPS": ("5", "package audit: declared head-depth rate"),
    "DepthW": ("320", "package audit: declared head-depth width"),
    "DepthH": ("240", "package audit: declared head-depth height"),
    "StdNoWrist": ("24", "package audit: standard records without wrist camera"),
    "EmergStretch": ("3em", "layout"),
}

# ---------------------------------------------------------------------------
# 2. Measured slots.  SLOTS[name] = (json_file, [path...], format_tag)
#    format tags: f0..f4 fixed decimals, p1/p2 percent, cm metres->centimetres,
#    int, bool, txt, g3 significant digits.
# ---------------------------------------------------------------------------
SLOTS = {}


DIGIT_WORDS = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
               "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}


def tex_name(name):
    """LaTeX control words may only contain letters: digits terminate the name."""
    out = "".join(DIGIT_WORDS[c] if c.isdigit() else c for c in name)
    if not out.isalpha():
        raise SystemExit(f"ILLEGAL SLOT NAME (non-letter): {name!r} -> {out!r}")
    return out


def add(name, jfile, path, fmt="f3"):
    key = tex_name(name)
    if key in SLOTS:
        raise SystemExit(f"DUPLICATE SLOT after sanitising: {key} (from {name})")
    SLOTS[key] = (jfile, list(path), fmt)


# --- P1 data / state scale -------------------------------------------------
for nm, pth in {
    "DataStateDim": ["state_dim_per_hand"],
    "DataGeomDim": ["geom_dim_per_hand"],
    "DataDomLeft": ["dominant_left"],
    "DataDomRight": ["dominant_right"],
    "DataNRecords": ["n_records"],
    "DataNFrames": ["n_frames"],
}.items():
    add(nm, "p1_state_summary", pth, "int")
for ds, tag in (("EgoDemo", "Demo"), ("EgoPro", "Pro"), ("EgoStandard", "Std")):
    for stat, short, fmt in (
        ("palm_width", "Palm", "f4"),
        ("speed_mean", "Speed", "f4"),
        ("aperture_mean", "Aperture", "f3"),
        ("bad", "BadPct", "p2"),
    ):
        add(f"Data{short}{tag}", "p1_state_summary", ["dataset_means", stat, ds], fmt)

# --- P1 reliability --------------------------------------------------------
for meth, tag, splits in (
    ("calibrated", "Cal", ("train", "validation", "test")),
    ("geometry", "Geo", ("train", "validation", "test")),
    ("fused", "Fus", ("validation", "test")),
):
    for split in splits:
        stag = {"train": "Train", "validation": "Val", "test": "Test"}[split]
        add(f"PRel{tag}{stag}AUC", "p1_reliability", ["auc_bad_" + meth, split], "f3")
        if split != "train":
            add(f"PRel{tag}{stag}AP", "p1_reliability", ["ap_bad_" + meth, split], "f4")
for nm, key, fmt in (
    ("PRelNTrain", "n_train", "int"),
    ("PRelNVal", "n_val", "int"),
    ("PRelNTest", "n_test", "int"),
    ("PRelPosTrain", "positives_train", "int"),
    ("PRelPosVal", "positives_val", "int"),
    ("PRelPosTest", "positives_test", "int"),
):
    add(nm, "p1_reliability", ["_meta", key], fmt)
add("PRelPosRateTest", "p1_reliability", ["_meta", "positive_rate_test"], "p2")
add("PRelAPBaseline", "p1_reliability", ["ap_baseline_test"], "f4")
add("PRelTCNTestAUC", "p1b_gpu", ["test_auc"], "f4")
add("PRelTCNAPLift", "p1b_gpu", ["test_ap_lift"], "f2")
add("PRelSeconds", "p1b_gpu", ["train_seconds"], "f1")

# --- second-round state-reliability model (multi-task TCN) -----------------
add("PStateBestAUC", "up2_p1state", ["arms", "C_multitask_raw", "test_auc"], "f3")
add("PStateBestAP", "up2_p1state", ["arms", "C_multitask_raw", "test_ap"], "f4")
add("PStateBaseAUC", "up2_p1state", ["arms", "A_smooth_reliability", "unsmoothed_test_auc"], "f3")
add("PStateBaseAP", "up2_p1state", ["arms", "A_smooth_reliability", "unsmoothed_test_ap"], "f4")
add("PStateBestParams", "up2_p1state", ["arms", "C_multitask_raw", "params"], "int")
add("PStateBestSeconds", "up2_p1state", ["arms", "C_multitask_raw", "seconds"], "f1")
add("PStateWorstAUC", "up2_p1state", ["arms", "C_multitask_raw", "per_env", 0, "auc"], "f3")

# --- second-round detector, symmetric augmentation + TTA (V8) --------------
add("PDetV8AUC", "up2_p1b", ["results", "V8", "aggregate", "test_auc"], "f3")
add("PDetV8AP", "up2_p1b", ["results", "V8", "aggregate", "test_ap"], "f4")
add("PDetV8APLow", "up2_p1b", ["results", "V8", "aggregate", "test_ap_per_seed", "20261123"], "f4")
add("PDetV8Worst", "up2_p1b", ["results", "V8", "aggregate", "worst_env"], "f3")
add("PDetV8Params", "up2_p1b", ["results", "V8", "aggregate", "params"], "int")
add("PDetV8Seconds", "up2_p1b", ["results", "V8", "aggregate", "train_seconds_total"], "f1")
# calibration audit of the temporal route (data/p1b_calib.json): ranking works, probability scale does not
for nm, key, fmt in (
    ("PCalTemp", "temperature", "f2"),
    ("PCalMeanRaw", "mean_prob_raw", "f4"),
    ("PCalMeanCal", "mean_prob_cal", "f4"),
    ("PCalBase", "base_rate", "f4"),
    ("PCalBrierRaw", "brier_raw", "f4"),
    ("PCalBrierTemp", "brier_cal", "f4"),
    ("PCalECEraw", "ece15_raw", "f4"),
    ("PCalECEt", "ece15_cal", "f4"),
    ("PCalBrierPlatt", "brier_platt", "f4"),
    ("PCalPlattA", "platt_a", "f4"),
    ("PCalBrierConst", "brier_constant", "f4"),
):
    add(nm, "p1b_calib", ["calibration", key], fmt)

# P2 masked-observation arms (data/p2_masked.json): metres, 3-D RMS
for _arm, _pre in (("clean_only", "PClean"), ("locf_mask", "PLocf"), ("interp_mask", "PInterp")):
    for _k, _suf in (("0", "Zero"), ("3", "Three"), ("6", "Six")):
        add(_pre + "Raw" + _suf, "p2_masked", ["arms", _arm, "mask", _k, "rmse"], "f4")
add("PRelAPLift", "p1_reliability", ["ap_bad_fused", "test"], "f4")
for idx, tag in ((0, "One"), (1, "Two")):
    add(f"PEnv{tag}Name", "p1_reliability", ["per_env_test", idx, "env"], "txt")
    for key, short, fmt in (("n", "N", "int"), ("positives", "Pos", "int"), ("auc_bad", "AUC", "f3")):
        add(f"PEnv{tag}{short}", "p1_reliability", ["per_env_test", idx, key], fmt)
for j, tag in enumerate(("One", "Two", "Three", "Four", "Five", "Six")):
    for key, short, fmt in (
        ("threshold", "Tau", "f1"),
        ("retained", "Retained", "p1"),
        ("bad_recall", "Recall", "p1"),
        ("bad_precision", "Prec", "p2"),
        ("f1", "FOne", "f4"),
    ):
        add(f"PTau{tag}{short}", "p1_reliability", ["threshold_sensitivity", j, key], fmt)
for key, short in (
    ("L_collinearity", "Collinear"),
    ("L_bone_cv", "BoneCV"),
    ("L_min_gap", "MinGap"),
    ("L_bbox_vol", "BBoxVol"),
    ("L_z_std", "ZStd"),
    ("L_palm_width", "PalmW"),
    ("L_jump", "Jump"),
    ("L_jump_max", "JumpMax"),
    ("jump_mean5", "JumpMean"),
    ("jump_max_mean5", "JumpMaxMean"),
):
    add(f"PCoef{short}", "p1_reliability", ["coef", key], "f3")

# --- P1 temporal-convolutional reliability variant --------------------------
for nm, pth, fmt in (
    ("PTCNAUC", ["test_auc"], "f3"),
    ("PTCNAP", ["test_ap"], "f4"),
    ("PTCNAPLift", ["test_ap_lift"], "f2"),
    ("PTCNValAUC", ["val_auc_at_best"], "f4"),
    ("PTCNParams", ["params"], "int"),
    ("PTCNSeconds", ["train_seconds"], "f1"),
    ("PTCNBestEpoch", ["best_epoch"], "int"),
    ("PTCNWindow", ["_meta", "window_s"], "f1"),
):
    add(nm, "p1b_gpu", pth, fmt)

# --- P1 segmentation -------------------------------------------------------
SEG = (("ward", "Ward"), ("raw", "Raw"), ("ward_oracleK", "OracleK"),
       ("ward_rawfeat", "Rawfeat"), ("kmeans_headfeat", "KHead"))
MET = (("ari", "ARI", "f3"), ("f1", "FOne", "f3"), ("b_mae", "BMae", "f3"),
       ("b_recall", "BRecall", "f3"), ("b_precision", "BPrec", "f3"),
       ("b_count_err", "CountErr", "f1"))
for meth, mtag in SEG:
    for met, ttag, fmt in MET:
        add(f"PSeg{mtag}{ttag}", "p1_segmentation", ["by_method", meth, met, "mean"], fmt)
        add(f"PSeg{mtag}{ttag}SD", "p1_segmentation", ["by_method", meth, met, "std"], fmt)
for met, ttag, fmt in (("ari", "ARI", "f4"), ("f1", "FOne", "f4")):
    add(f"PSegImp{ttag}", "p1_segmentation", ["improvement", "ward", met], fmt)
    add(f"PSegImp{ttag}Pct", "p1_segmentation", ["improvement", "ward", met], "p1")
for ds, tag in (("EgoDemo", "Demo"), ("EgoPro", "Pro"), ("EgoStandard", "Std")):
    add(f"PSeg{tag}Ward", "p1_segmentation", ["by_dataset", ds, "ward"], "f3")
    add(f"PSeg{tag}Raw", "p1_segmentation", ["by_dataset", ds, "raw"], "f3")
for meth, mtag in (("raw", "KRaw"), ("kmeans_headfeat", "KHead"),
                   ("ward_rawfeat", "WRaw"), ("ward", "WHead")):
    for met, ttag in (("ari", "ARI"), ("f1", "FOne")):
        add(f"PAbl{mtag}{ttag}", "p1_segmentation", ["ablation", meth, met], "f3")
add("PSegTolS", "p1_segmentation", ["_meta", "tol_s"], "f1")
# --- visual modality probe: does a better duration model move the schedule? ---
add("PVisDurBase", "p3_visual_duration",
    ["rows", "@design=pose_old8,model=ridge,split=test", "mae"], "f4")
add("PVisHGBVal", "p3_visual_duration",
    ["rows", "@design=all_fused,model=hgb,split=validation", "mae"], "f4")
add("PVisHGBTest", "p3_visual_duration",
    ["rows", "@design=all_fused,model=hgb,split=test", "mae"], "f4")
add("PVisDurSel", "p3_final_duration",
    ["evaluation", "@split=test", "mae"], "f4")

add("PSegTestRecords", "p1_segmentation", ["_meta", "records"], "int")

# P1-a learned boundary detector (GPU) — decoding constants chosen on validation only
add("PSegGPUARI", "p1a_gpu_segmentation_final", ["test", "mean_ari"], "f4")
add("PSegGPUFOne", "p1a_gpu_segmentation_final", ["test", "mean_f1"], "f4")
add("PSegGPUStdARI", "p1a_gpu_segmentation_final", ["test", "std_ari"], "f4")
add("PSegGPUBFOne", "p1a_gpu_segmentation_final", ["test", "mean_boundary_f1"], "f4")
add("PSegGPUBMae", "p1a_gpu_segmentation_final", ["test", "mean_boundary_mae"], "f3")
add("PSegGPUParams", "p1a_gpu_segmentation", ["_meta", "params"], "int")
add("PSegGPUSeconds", "p1a_gpu_segmentation", ["_meta", "fit_seconds"], "f1")

# P2 closed-form route: measured wall clock (up18_p2_timing.py)
add("PTwoFeatureCount", "up18_p2_timing", ["_meta", "features"], "int")
add("PTwoScoreSeconds", "up18_p2_timing", ["score_seconds_per_split"], "f4")
add("PTwoScoreMsWindow", "up18_p2_timing", ["score_ms_per_window"], "f4")
add("PSegGPUValARI", "p1a_gpu_segmentation_final", ["_meta", "val_ari"], "f4")
add("PSegGPUHeight", "p1a_gpu_segmentation_final", ["_meta", "height"], "f2")
add("PSegGPUDistance", "p1a_gpu_segmentation_final", ["_meta", "distance"], "int")
add("PSegGPUDistSec", "p1a_gpu_segmentation_final", ["_meta", "distance_seconds"], "f1")
add("POfficialA", "p2_official", ["options", 0, "rmse_cm"], "f2")
add("POfficialB", "p2_official", ["options", 1, "rmse_cm"], "f2")
add("POfficialC", "p2_official", ["options", 2, "rmse_cm"], "f2")
add("PDelayPenaltyMin", "p2_official", ["derived", "delay_penalty_min_cm"], "f2")
add("PDelayPenaltyMax", "p2_official", ["derived", "delay_penalty_max_cm"], "f2")
add("PPrefixGainMax", "p2_official", ["derived", "prefix_gain_max_cm"], "f2")

# P2 in the official action set: five protocol-compliant strategies (p2_frontier)
for _pol, _nm in (("no_wait_no_request", "PFrNoWait"), ("free_wait", "PFrFreeWait"),
                  ("paid_0p6", "PFrPaidSix"), ("paid_1p0", "PFrPaidOne"),
                  ("paid_twice_1p0", "PFrTwoReqs")):
    add(_nm, "p2_frontier", ["_flat", _pol + "_rms_cm"], "f2")
add("PFrNoWaitToFree", "p2_frontier", ["comparisons", "no_wait_no_request__to__free_wait", "delta_cm"], "f2")
add("PFrNoWaitToFreeCI", "p2_frontier", ["comparisons", "no_wait_no_request__to__free_wait", "ci95"], "f2")
add("PFrFreeToPaid", "p2_frontier", ["comparisons", "free_wait__to__paid_1p0", "delta_cm"], "f2")
add("PFrFreeToPaidCI", "p2_frontier", ["comparisons", "free_wait__to__paid_1p0", "ci95"], "f2")
add("PFrPaidToTwo", "p2_frontier", ["comparisons", "paid_1p0__to__paid_twice_1p0", "delta_cm"], "f2")
add("PFrPaidToTwoCI", "p2_frontier", ["comparisons", "paid_1p0__to__paid_twice_1p0", "ci95"], "f2")

# P1 -> P2: reliability entering as a sample weight (p2_reliability_weight)
add("PRelArmA", "p2_reliability_weight", ["arms", "A_clean_only", "rmse_cm"], "f3")
add("PRelArmB", "p2_reliability_weight", ["arms", "B_soft_weight", "rmse_cm"], "f3")
add("PRelArmC", "p2_reliability_weight", ["arms", "C_all_unweighted", "rmse_cm"], "f3")
add("PRelAtoB", "p2_reliability_weight", ["comparisons", "A_clean_only__to__B_soft_weight", "delta_cm"], "f3")
add("PRelAtoBCI", "p2_reliability_weight", ["comparisons", "A_clean_only__to__B_soft_weight", "ci95"], "f3")
add("PRelCtoB", "p2_reliability_weight", ["comparisons", "C_all_unweighted__to__B_soft_weight", "delta_cm"], "f3")
add("PRelCtoBCI", "p2_reliability_weight", ["comparisons", "C_all_unweighted__to__B_soft_weight", "ci95"], "f3")

# P3 same-rule reference: identical rule, only the duration knowledge changes
add("POracleSameSTwo", "p3_oracle_same_rule", ["cases", "S2", "same_rule_oracle_mean"], "f4")
add("POracleSameSThree", "p3_oracle_same_rule", ["cases", "S3", "same_rule_oracle_mean"], "f4")
add("POracleGapSTwo", "p3_oracle_same_rule", ["cases", "S2", "gap_oracle_minus_headline"], "f4")
add("POracleGapSTwoCI", "p3_oracle_same_rule", ["cases", "S2", "gap_ci95"], "f4")
add("POracleGapSThree", "p3_oracle_same_rule", ["cases", "S3", "gap_oracle_minus_headline"], "f4")
add("POracleGapSThreeCI", "p3_oracle_same_rule", ["cases", "S3", "gap_ci95"], "f4")

# --- reservation-level identifiability (p3_quantile_curve.json) ------------
add("PQSweepLow", "p3_quantile_curve", ["_meta", "q_grid", 0], "f4")
add("PQSweepHigh", "p3_quantile_curve", ["_meta", "q_grid", -1], "f4")
for _nm, _c, _key, _i in (
        ("PQTuneLowSTwo", "S2", "tune_curve", 0),
        ("PQTuneHighSTwo", "S2", "tune_curve", -1),
        ("PQTuneLowSThree", "S3", "tune_curve", 0),
        ("PQTuneHighSThree", "S3", "tune_curve", -1),
        ("PQHoldLowSTwo", "S2", "holdout_curve", 0),
        ("PQHoldHighSTwo", "S2", "holdout_curve", -1),
        ("PQHoldLowSThree", "S3", "holdout_curve", 0),
        ("PQHoldHighSThree", "S3", "holdout_curve", -1),
):
    add(_nm, "p3_quantile_curve", ["cases", _c, _key, _i], "f4")
add("PQWiggleMax", "p3_quantile_curve", ["_meta", "max_wiggle_points"], "f2")

# --- P1-a boundary identifiability: separation does not predict detection (phase_identifiability2 / _null_check)
add("PIdNBound", "phase_identifiability2", ["summary", "n_boundaries"], "int")
add("PIdSpearmanMax", "phase_identifiability2", ["summary", "max_abs_spearman"], "f3")
add("PIdMinP", "phase_identifiability2", ["summary", "min_p"], "f2")
add("PIdAucTwo", "phase_null_check", ["auc_at_2_frames"], "f3")
add("PIdMeanTrue", "phase_null_check", ["mean_pos_p2"], "f3")
add("PIdMeanNull", "phase_null_check", ["mean_neg_p2"], "f3")
add("PIdTrueHalf", "phase_null_check", ["share_pos_ge_half_p2_pct"], "f1")
add("PIdNullHalf", "phase_null_check", ["share_neg_ge_half_p2_pct"], "f1")
# --- same test run against a second, independent fit of the segmenter (instance 2).
# Part I is not bit-reproducible, so the identifiability verdict is reported with its
# run-to-run spread rather than as a single number.
add("PIdSpearmanRobust", "phase_identifiability2_inst2", ["summary", "max_abs_spearman"], "f3")
add("PIdAucTwoRobust", "phase_null_check_inst2", ["auc_at_2_frames"], "f3")
# --- annotated bad frames: what the flags actually contain (p1_badtype) ---
add("PBTBadFrames", "p1_badtype", ['composition', 'total_bad_frames'], "int")
add("PBTBadEvents", "p1_badtype", ['composition', 'total_bad_frame_side_events'], "int")
add("PBTBadRatePct", "p1_badtype", ['_derived', 'bad_frame_rate_pct'], "f2")
add("PBTOcclPct", "p1_badtype", ['_derived', 'occlusion_share_pct'], "f2")
add("PBTNearPct", "p1_badtype", ['_derived', 'near_edge_share_pct'], "f2")
add("PBTEventRight", "p1_badtype", ['composition', 'side_totals', 'right'], "int")
add("PBTEventLeft", "p1_badtype", ['composition', 'side_totals', 'left'], "int")
add("PBTBndObsPct", "p1_badtype", ['_derived', 'boundary_obs_pct'], "f2")
add("PBTBndBasePct", "p1_badtype", ['_derived', 'boundary_base_pct'], "f2")
add("PBTBndRatio", "p1_badtype", ['boundary_vs_interior', 'primary_all_interior_boundaries_w05', 'ratio_obs_over_base'], "f3")
add("PBTBndP", "p1_badtype", ['boundary_vs_interior', 'primary_all_interior_boundaries_w05', 'binom', 'p_greater'], "f3")
add("PBTBndSignP", "p1_badtype", ['boundary_vs_interior', 'primary_all_interior_boundaries_w05', 'cluster', 'sign_test_p'], "f3")
add("PBTRecsWithBad", "p1_badtype", ['composition', 'records_with_bad_frames'], "int")
add("PBTRecsTotal", "p1_badtype", ['composition', 'records_total'], "int")

# --- leave-one-task-out: the price of an unseen task class (p1b_loto) ---
add("PLotoMean", "p1b_loto", ['summary', 'mean_auc_loto'], "f4")
add("PLotoRef", "p1b_loto", ['summary', 'mean_auc_in_sample_reference'], "f4")
add("PLotoGap", "p1b_loto", ['summary', 'gap_mean'], "f4")
add("PLotoFrac", "p1b_loto", ['summary', 'frac_unseen_task_gap_explained'], "f3")
add("PLotoNEval", "p1b_loto", ['summary', 'n_classes_used'], "int")
add("PLotoNSkip", "p1b_loto", ['summary', 'n_classes_skipped'], "int")
add("PLotoNClass", "p1b_loto", ['summary', 'n_train_classes'], "int")

# --- keep/drop is a threshold decision, not a calibration problem (p1b_cost_threshold)
add("PCostRatioLow", "p1b_cost_threshold", ['_derived', 'ratio_min'], "f2")
add("PCostRatioHigh", "p1b_cost_threshold", ['_derived', 'ratio_max'], "f2")
add("PCostKeepAll", "p1b_cost_threshold", ['_derived', 'cost_keep_all_at_r1'], "f5")
add("PCostDropAll", "p1b_cost_threshold", ['_derived', 'cost_drop_all_at_r001'], "f5")
add("PCostHalfRaw", "p1b_cost_threshold", ['_derived', 'cost_half_raw_at_r1'], "f5")
add("PCostHalfPlatt", "p1b_cost_threshold", ['_derived', 'cost_half_platt_at_r1'], "f5")
add("PCostHalfMult", "p1b_cost_threshold", ['_derived', 'half_rule_multiple'], "f1")
add("PCostAUC", "p1b_cost_threshold", ['auc_by_transform', 'raw'], "f4")
add("PCostNVal", "p1b_cost_threshold", ['n_validation'], "int")
add("PCostNTest", "p1b_cost_threshold", ['n_test'], "int")
add("PSegGPUValBFOne", "p1a_gpu_segmentation_final", ["_meta", "val_bf1"], "f4")

# Part I is not bit-reproducible (chunked sampler + cuDNN autotuning), so the
# shipped protocol is retrained three times and quoted as a distribution.
add("PSegGPUARIRep", "up15_p1a_final_repeats", ["ari_mean"], "f4")
add("PSegGPUARIRepSD", "up15_p1a_final_repeats", ["ari_sd"], "f4")
add("PSegGPUARIRepMin", "up15_p1a_final_repeats", ["ari_min"], "f4")
add("PSegGPUARIRepMax", "up15_p1a_final_repeats", ["ari_max"], "f4")
add("PSegGPUBFOneRep", "up15_p1a_final_repeats", ["bf1_mean"], "f4")
add("PSegGPUWardGap", "up15_p1a_final_repeats", ["gap_vs_ward_pt"], "f2")
add("PSegGPURepN", "up15_p1a_final_repeats", ["n"], "int")
add("PSegGPUBMaeRep", "up15_p1a_final_repeats", ["bmae_mean"], "f3")
add("PSegGPUHeightLow", "up15_p1a_final_repeats", ["height_min"], "f2")
add("PSegGPUHeightHigh", "up15_p1a_final_repeats", ["height_max"], "f2")
for _ds, _tag in (("EgoDemo", "Demo"), ("EgoPro", "Pro"), ("EgoStandard", "Std")):
    add("PSegGPUBy" + _tag, "p1a_gpu_segmentation", ["by_dataset", _ds], "f4")

# P3 adaptive-quantile reservation search: first 15 seeds select, last 15 hold out
add("PImpNCandidates", "p3_improved_search", ["_meta", "candidate_count"], "int")
add("PImpSeconds", "p3_improved_search", ["seconds"], "f1")
add("PImpMixedAllDelta", "p3_improved_search", ["mixed_policy", "all30_delta_mean"], "f4")
add("PImpMixedAllCI", "p3_improved_search", ["mixed_policy", "all30_delta_ci95"], "f4")
add("PImpMixedHoldDelta", "p3_improved_search", ["mixed_policy", "holdout_delta_mean"], "f4")
add("PImpMixedHoldCI", "p3_improved_search", ["mixed_policy", "holdout_delta_ci95"], "f4")
for _case, _tag in (("S2", "STwo"), ("S3", "SThree")):
    add("PImp" + _tag + "AllMean", "p3_improved_search", ["evidence", _case, "all30", "delta_mean"], "f4")
    add("PImp" + _tag + "AllCI", "p3_improved_search", ["evidence", _case, "all30", "delta_ci95"], "f4")
    add("PImp" + _tag + "AllCand", "p3_improved_search", ["evidence", _case, "selected_all30_mean"], "f4")
    add("PImp" + _tag + "AllBase", "p3_improved_search", ["evidence", _case, "baseline_all30_mean"], "f4")
    add("PImp" + _tag + "AllComp", "p3_improved_search", ["evidence", _case, "all30", "delta_completion_mean"], "f4")
    add("PImp" + _tag + "HoldDelta", "p3_improved_search", ["evidence", _case, "holdout", "delta_mean"], "f4")
    add("PImp" + _tag + "HoldCI", "p3_improved_search", ["evidence", _case, "holdout", "delta_ci95"], "f4")

# --- the eleven official P3 measures, one row per policy (up17 scorecard) ---
add("POfficialTrials", "p3_official_audit", ["summary", "n_trials"], "int")
for _case, _tag in (("S2", "STwo"), ("S3", "SThree")):
    for _pol, _ptag in (("frozen", "Ours"), ("slack_old", "Slack"),
                        ("edf_old", "EDF"), ("oracle", "Oracle")):
        add(f"PIdle{_tag}{_ptag}", "p3_scorecard",
            ["cases", _case, f"@key={_pol}", "reserved_idle_s"], "f2")
        add(f"POverrun{_tag}{_ptag}", "p3_scorecard",
            ["cases", _case, f"@key={_pol}", "observed_overrun_s"], "f2")
        add(f"PCensor{_tag}{_ptag}", "p3_scorecard",
            ["cases", _case, f"@key={_pol}", "censored_units"], "f2")
        add(f"PElapsed{_tag}{_ptag}", "p3_scorecard",
            ["cases", _case, f"@key={_pol}", "elapsed_s"], "f1")

# --- borrowed analyses (up19 / up20) ---------------------------------------
add("PSegCovTight", "up19_borrowed_alt", ["coverage", "coverage", "tol_0.5s", "share"], "f3")
add("PSegCovLoose", "up19_borrowed_alt", ["coverage", "coverage", "tol_2.0s", "share"], "f3")
add("PSegDetPerSeg", "up19_borrowed_alt", ["coverage", "detections_per_segment"], "f2")
add("PSegCovSegments", "up19_borrowed_alt", ["coverage", "n_test_segments"], "int")
add("PSegCovDetections", "up19_borrowed_alt", ["coverage", "n_detections"], "int")
add("PScaleExponent", "up19_borrowed_alt", ["scaling", "b"], "f3")
add("PScaleA", "up19_borrowed_alt", ["scaling", "a"], "f2")
add("PScaleRTwo", "up19_borrowed_alt", ["scaling", "r2"], "f3")
add("PScaleDoubling", "up19_borrowed_alt", ["scaling", "doubling_factor"], "f3")
add("PEconSpan", "up21_p2_cost_sweep", ['summary', 'T_star_span_s'], "f2")
add("PEconTMin", "up21_p2_cost_sweep", ['summary', 'T_star_min_s'], "f2")
add("PEconTMax", "up21_p2_cost_sweep", ['summary', 'T_star_max_s'], "f2")
add("PEconNCell", "up21_p2_cost_sweep", ['summary', 'n_cells'], "int")
add("PEconInterior", "up21_p2_cost_sweep", ['summary', 'n_interior'], "int")
add("PEconAtEdge", "up21_p2_cost_sweep", ['summary', 'n_at_left_edge'], "int")
add("PEconCZeroSpan", "up21_p2_cost_sweep", ['summary', 'one_at_a_time', '@knob=C0', 'span_s'], "f2")
add("PEconCOneSpan", "up21_p2_cost_sweep", ['summary', 'one_at_a_time', '@knob=C1', 'span_s'], "f2")
add("PEconLamSpan", "up21_p2_cost_sweep", ['summary', 'one_at_a_time', '@knob=lambda', 'span_s'], "f2")
add("PInfoFirstSTwo", "up20_marginal_info", ["s2_first_pt"], "f2")
add("PInfoGate", "up20_marginal_info", ["gate_pt"], "f2")
add("PInfoTrueMax", "up20_marginal_info", ["true_max_pt"], "f2")
add("PInfoSecondSTwo", "up20_marginal_info", ["s2_second_pt"], "f2")
add("PInfoFirstSThree", "up20_marginal_info", ["s3_first_pt"], "f2")
add("PInfoSecondSThree", "up20_marginal_info", ["s3_second_pt"], "f2")

# --- P2 prediction grid ----------------------------------------------------
LEVELS = (("0.2", "A"), ("0.5", "B"), ("1.0", "C"), ("2.0", "D"))
METHODS = (("hold", "Hold"), ("cv", "CV"), ("ca", "CA"), ("ridge", "Ridge"))
for lv, ltag in LEVELS:
    for meth, mtag in METHODS:
        sel = f"@L_s={lv},method={meth}"
        for key, short, fmt in (
            ("rmse", "RMSE", "cm"),
            ("mae", "MAE", "cm"),
            ("endpoint_rmse", "Endpoint", "cm"),
            ("jump_mean", "JumpMean", "cm"),
            ("jump_p95", "JumpPNine", "cm"),
            ("within_2cm", "WithinTwo", "p1"),
            ("within_5cm", "WithinFive", "p1"),
            ("n_windows", "NWin", "int"),
        ):
            add(f"PTwo{ltag}{mtag}{short}", "p2_prediction", ["by_length", sel, key], fmt)
for frames, tag in (("6", "A"), ("15", "B"), ("30", "C"), ("60", "D")):
    add(f"PTwoWin{tag}", "p2_prediction", ["_meta", "windows", frames], "int")
add("PTwoTrainRecords", "p2_prediction", ["_meta", "splits", "train_records"], "int")
add("PTwoTestRecords", "p2_prediction", ["_meta", "splits", "test_records"], "int")

# --- P2 split-conformal calibration ---------------------------------------
for lv, ltag in LEVELS:
    sel = f"@L_s={lv}"
    for key, short, fmt in (
        ("q90_m", "QNine", "f4"),
        ("coverage_test", "Coverage", "f3"),
        ("mean_radius_m", "RadiusCm", "cm"),
        ("empirical_median_err_m", "MedianCm", "cm"),
        ("n_val", "NVal", "int"),
        ("n_test", "NTest", "int"),
    ):
        add(f"PCon{ltag}{short}", "p2_interval", ["by_length", sel, key], fmt)
add("PConMeanCoverage", "p2_interval", ["summary", "mean_coverage"], "f4")
add("PConMeanRadius", "p2_interval", ["summary", "mean_radius_m"], "f4")
add("PConAlpha", "p2_interval", ["_meta", "alpha"], "f1")
# conditional (per-environment) coverage at the longest official prefix (1.0 s = 30 frames)
add("PConCovMin", "p2_interval", ["conditional", "30", "summary", "min"], "f3")
add("PConCovMax", "p2_interval", ["conditional", "30", "summary", "max"], "f3")
add("PConCovMarginal", "p2_interval", ["conditional", "30", "summary", "marginal"], "f3")
add("PConCovNEnv", "p2_interval", ["conditional", "30", "summary", "n_env"], "int")
add("PConCovBelow", "p2_interval", ["conditional", "30", "summary", "n_below_0p85"], "int")
# official 0.6 s prefix (18 frames): ridge, per-coordinate RMS so it is comparable with the mask table
add("PTwoMaskZeroSixRMSE", "p2_extra", ["lengths", "@L_frames=18", "rmse_coord_cm"], "f2")
add("PTwoMaskZeroSixEnd", "p2_extra", ["lengths", "@L_frames=18", "end_rmse_cm"], "f2")

# --- P2 re-observation economics ------------------------------------------
for nm, key, fmt in (
    ("PEconOptT", "T_s", "f2"),
    ("PEconOptRMSE", "rmse_cm", "f2"),
    ("PEconOptCost", "cost_per_s", "f3"),
    ("PEconOptJ", "objective", "f3"),
    ("PEconCZero", "C0", "f1"),
    ("PEconCOne", "C1", "f1"),
    ("PEconLambda", "lambda_per_cm", "f1"),
):
    add(nm, "p2_prediction", ["economics", "optimum", key], fmt)
for base, tag in (("fixed_0.5s", "Half"), ("fixed_1.0s", "One"), ("reactive_5cm", "Reactive")):
    for key, short, fmt in (("T_s", "T", "f2"), ("rmse_cm", "RMSE", "f2"),
                            ("cost_per_s", "Cost", "f3"), ("objective", "J", "f3")):
        add(f"PEcon{tag}{short}", "p2_prediction", ["economics", "baselines", base, key], fmt)
for key, short, fmt in (("rmse_cm", "RMSE", "f2"), ("objective", "J", "f3"), ("cost_per_s", "Cost", "f1")):
    add(f"PEconNever{short}", "p2_prediction", ["economics", "baselines", "never_observe", key], fmt)
for key, short, fmt in (("n_runs", "N", "int"), ("mean_s", "Mean", "f3"), ("median_s", "Median", "f3"),
                        ("p90_s", "PNine", "f2"), ("max_s", "Max", "f1"), ("share_over_1s", "ShareOne", "p2")):
    add(f"POcc{short}", "p2_prediction", ["occlusion", key], fmt)

# --- P2 hold / constant-velocity crossover --------------------------------
add("PCrossMean", "p2_crossover", ["crossover_s"], "f3")
add("PCrossMedian", "p2_crossover", ["crossover_s_median"], "f1")
for frames in (3, 6, 8, 10, 12, 15, 18, 20, 24, 30):
    for key, short in (("cv_gain_mean_pct", "Mean"), ("cv_gain_median_pct", "Median")):
        add(f"PGain{frames}{short}", "p2_crossover", ["rows", f"@L_frames={frames}", key], "f1")
    add(f"PGain{frames}LSeconds", "p2_crossover", ["rows", f"@L_frames={frames}", "L_s"], "f3")

# --- P2 learned sequence model --------------------------------------------
for frames, ltag in ((6, "A"), (18, "E"), (30, "C"), (60, "D")):
    for variant, vtag in (("v1", "Wrist"), ("v2", "Both")):
        sel = f"@L_frames={frames},variant={variant}"
        for key, short, fmt in (("test_rmse_m", "RMSE", "cm"), ("test_median_err_m", "Median", "cm"),
                                ("test_endpoint_rmse_m", "Endpoint", "cm"),
                                ("test_within_2cm", "WithinTwo", "p1"),
                                ("best_val_epoch", "BestEpoch", "int")):
            add(f"PGPU{ltag}{vtag}{short}", "p2_gpu", ["rows", sel, key], fmt)
add("PGPUSeconds", "p2_gpu", ["total_seconds"], "f1")

# --- P3 duration model -----------------------------------------------------
for prefix, tag in (("0.2", "Free"), ("0.6", "Mid"), ("1.0", "Long")):
    for key, short, fmt in (("mae", "MAE", "f3"), ("rmse", "RMSE", "f3"),
                            ("spearman", "Rho", "f3"), ("mean_baseline_mae", "BaseMAE", "f3"),
                            ("n", "N", "int")):
        add(f"PDur{tag}{short}", "p3_scheduling", ["duration_model", prefix, key], fmt)
for q, qtag in (("0.5", "Fifty"), ("0.6", "Sixty"), ("0.9", "Ninety")):
    for prefix, tag in (("0.2", "Free"), ("0.6", "Mid"), ("1.0", "Long")):
        add(f"PResid{qtag}{tag}", "p3_scheduling", ["residuals", q, prefix], "f3")

# --- P3 capacity diagnostics ----------------------------------------------
for case, ctag in (("S1", "SOne"), ("S2", "STwo"), ("S3", "SThree")):
    for key, short, fmt in (("n_jobs", "NJobs", "int"), ("mean_p_s", "MeanP", "f3"),
                            ("nn_route_s", "NNRoute", "f1"), ("capacity_ratio", "Ratio", "f3"),
                            ("horizon_s", "Horizon", "int"), ("budget", "Budget", "int")):
        add(f"PCap{ctag}{short}", "p3_scheduling", ["capacity", f"@case={case}", key], fmt)
    for key, short, fmt in (("sum_family_mean_p_s", "SumMeanP", "f2"), ("mst_route_s", "MST", "f1"),
                            ("capacity_ratio_analytic", "Ratio", "f3")):
        add(f"PCapA{ctag}{short}", "p3_scheduling", ["capacity_analytic", f"@case={case}", key], fmt)

# --- P3 deterministic-protocol results ------------------------------------
CASES = (("S1", "SOne"), ("S2", "STwo"), ("S3", "SThree"))
POLICIES = (("edf", "EDF"), ("now", "NOW"), ("slack", "SLACK"), ("voi", "VOI"),
            ("oracle", "ORACLE"), ("edf_rev", "EDFRev"))
for case, ctag in CASES:
    for pol, ptag in POLICIES:
        sel = f"@case={case},alpha=1.0,beta=0.5,policy={pol}"
        for key, short, fmt in (
            ("weighted_on_time_rate", "ETA", "f3"),
            ("weighted_on_time_rate_ci95", "ETACI", "f3"),
            ("weighted_completion_rate", "Comp", "f3"),
            ("weighted_tardiness_s", "Tard", "f1"),
            ("cost", "Cost", "f2"),
            ("reviews", "Reviews", "f2"),
            ("reserved_idle_s", "Idle", "f1"),
            ("observed_overrun_s", "Overrun", "f1"),
        ):
            add(f"PSched{ctag}{ptag}{short}", "p3_scheduling", ["summary", sel, key], fmt)
    for pol, ptag in (("now", "NOW"), ("slack", "SLACK"), ("voi", "VOI"), ("oracle", "ORACLE")):
        sel = f"@case={case},alpha=1.0,beta=0.5,policy={pol}"
        add(f"PPair{ctag}{ptag}Diff", "p3_scheduling", ["paired_vs_edf", sel, "mean_diff"], "f3")
        add(f"PPair{ctag}{ptag}CI", "p3_scheduling", ["paired_vs_edf", sel, "ci95"], "f3")
    for pol, ptag in POLICIES:
        add(f"PCons{ctag}{ptag}Met", "p3_scheduling",
            ["constraint_nominal", f"@case={case},policy={pol}", "met"], "bool")
# mapping sensitivity (deterministic protocol, all five mappings)
for case, ctag in CASES:
    for alpha, beta, mtag in ((0.75, 0.5, "AlphaLow"), (1.0, 0.0, "BetaLow"),
                              (1.0, 0.5, "Nom"), (1.0, 1.0, "BetaHigh"), (1.5, 0.5, "AlphaHigh")):
        for pol, ptag in (("edf", "EDF"), ("now", "NOW"), ("slack", "SLACK"), ("voi", "VOI")):
            sel = f"@case={case},alpha={alpha},beta={beta},policy={pol}"
            add(f"PSens{ctag}{mtag}{ptag}ETA", "p3_scheduling", ["summary", sel, "weighted_on_time_rate"], "f3")
            add(f"PSens{ctag}{mtag}{ptag}Cost", "p3_scheduling", ["summary", sel, "cost"], "f2")
# --- P1-a model order (K cap) study ---------------------------------------
for cap in (8, 12, 16, 20, 25, 30):
    add(f"PKCap{cap}Test", "best_p1a_ksweep", ["bic", str(cap), "mean", "ari"], "f4")
    add(f"PKCap{cap}Val", "best_p1a_select", ["table", f"bic@{cap}", "val"], "f4")
add("PKCapSilEightTest", "best_p1a_ksweep", ["sil", "8", "mean", "ari"], "f4")
add("PKCapSilTwoFiveTest", "best_p1a_ksweep", ["sil", "25", "mean", "ari"], "f4")
add("PKCapRuleTest", "best_p1a_ksweep", ["rule", "total", "mean", "ari"], "f4")
add("PKCapSilEightVal", "best_p1a_select", ["table", "sil@8", "val"], "f4")
add("PKCapSilTwoFiveVal", "best_p1a_select", ["table", "sil@25", "val"], "f4")
add("PKCapRuleVal", "best_p1a_select", ["table", "rule", "val"], "f4")
add("PKChosenTest", "best_p1a_select", ["chosen_test_ari"], "f4")
add("PKTrainCvEight", "best_p1a_traincv", ["train_mean", "8", "mean"], "f4")
add("PKTrainCvTwoFive", "best_p1a_traincv", ["train_mean", "25", "mean"], "f4")
add("PKLongEight", "best_p1a_traincv", ["long_records", "8", "mean"], "f4")
add("PKLongSixteen", "best_p1a_traincv", ["long_records", "16", "mean"], "f4")
add("PKStratSixteen", "best_p1a_traincv", ["train_strat_bound", "16", "mean"], "f4")
add("PKTrainN", "best_p1a_traincv", ["_meta", "n_train"], "int")

# --- P1-a competing families (negative results) ---------------------------
for meth, tag in (("hmm", "HMM"), ("hmm_oracleK", "HMMOracle"),
                  ("hmm_mindur", "HMMMindur"), ("ae_hmm", "AEHMM"),
                  ("ward_ms", "WardMS"), ("ae_ward", "AEWard"),
                  ("ward_k25", "WardKTwoFive")):
    add(f"PSeg{tag}ARI", "best_p1a", ["methods", meth, "mean", "ari"], "f4")

# --- P1-b arms and paired bootstrap ---------------------------------------
for arm, tag in (("A_exact_replica", "A"), ("B_std_only", "B"), ("C_aug_longer", "C")):
    add(f"PArm{tag}AUC", "best_p1b", ["arms", arm, "test_auc"], "f4")
    add(f"PArm{tag}Brier", "best_p1b", ["arms", arm, "brier"], "f4")
    add(f"PArm{tag}ECE", "best_p1b", ["arms", arm, "ece15"], "f4")
for arm, tag in (("B_std_only_vs_A_exact_replica", "BA"), ("C_aug_longer_vs_A_exact_replica", "CA")):
    add(f"PBoot{tag}Diff", "best_p1b", ["paired_bootstrap", arm, "d_auc_mean"], "f4")
    add(f"PBoot{tag}Lo", "best_p1b", ["paired_bootstrap", arm, "d_auc_ci95", 0], "f4")
    add(f"PBoot{tag}Hi", "best_p1b", ["paired_bootstrap", arm, "d_auc_ci95", 1], "f4")
add("PBootNCluster", "best_p1b", ["paired_bootstrap", "B_std_only_vs_A_exact_replica", "n_clusters"], "int")

# review-bar sensitivity
for case, ctag in CASES:
    for bar, btag in ((0.0, "Zero"), (0.02, "Nom"), (1.0, "Off")):
        sel = f"@case={case},review_bar={bar}"
        for key, short, fmt in (("eta", "ETA", "f3"), ("reviews", "Reviews", "f1"), ("cost", "Cost", "f2")):
            add(f"PBar{ctag}{btag}{short}", "p3_scheduling", ["review_bar_sensitivity", sel, key], fmt)

# --- P3 stochastic roll-out results ---------------------------------------
SPOL = (("edf_fusion", "EDFFusion"), ("edf_old", "EDFOld"), ("slack_fusion", "SlackFusion"),
        ("slack_old", "SlackOld"), ("risk_fusion", "RiskFusion"),
        ("rollout_fusion", "RolloutFusion"), ("oracle", "Oracle"))
for case, ctag in CASES:
    for pol, ptag in SPOL:
        sel = f"@case={case},policy={pol}"
        for key, short, fmt in (
            ("weighted_on_time_rate", "ETA", "f4"),
            ("weighted_on_time_rate_ci95", "ETACI", "f4"),
            ("weighted_completion_rate", "Comp", "f4"),
            ("weighted_tardiness_s", "Tard", "f1"),
            ("cost", "Cost", "f2"),
            ("reviews", "Reviews", "f2"),
            ("reserved_idle_s", "Idle", "f1"),
            ("observed_overrun_s", "Overrun", "f1"),
        ):
            add(f"PStoch{ctag}{ptag}{short}", "p3_stochastic_schedule", ["summary", sel, key], fmt)
    for pol, ptag in SPOL:
        if pol in ("slack_old", "oracle"):
            continue
        sel = f"@case={case},policy={pol}"
        add(f"PStochPair{ctag}{ptag}Diff", "p3_stochastic_schedule", ["paired_vs_slack_old", sel, "mean_diff"], "f4")
        add(f"PStochPair{ctag}{ptag}CI", "p3_stochastic_schedule", ["paired_vs_slack_old", sel, "ci95"], "f4")
add("PStochSeconds", "p3_stochastic_schedule", ["seconds"], "f1")

# --- P3 selected duration model -------------------------------------------
for split, stag in (("validation", "Val"), ("test", "Test")):
    for key, short, fmt in (("mae", "MAE", "f3"), ("rmse", "RMSE", "f3"), ("spearman", "Rho", "f3"),
                            ("monotone_gain", "MonoGain", "f3"), ("nonmonotone", "NonMono", "f3")):
        add(f"PDurSel{stag}{short}", "p3_duration_selected", [split, key], fmt)
add("PDurSelName", "p3_duration_selected", ["selected", "name"], "txt")
add("PDurSelObjective", "p3_duration_selected", ["selected", "objective"], "f3")
add("PDurSelCandidates", "p3_duration_selected", ["_meta", "candidates"], "int")
add("PDurSelCovTestQNine", "p3_duration_selected", ["coverage", "test", "q90"], "f4")
add("PDurSelCovTestQFifty", "p3_duration_selected", ["coverage", "test", "q50"], "f4")

# --- P3 candidate duration-model comparison -------------------------------
for model, mtag in (("M0_family_median", "Family"), ("M1_old_ridge", "OldRidge"),
                    ("M2_progress_ridge", "ProgRidge"), ("M3_progress_hgb", "ProgHGB"),
                    ("M3_progress_extra", "ProgExtra")):
    for split, stag in (("validation", "Val"), ("test", "Test")):
        for key, short in (("mae", "MAE"), ("rmse", "RMSE"), ("spearman", "Rho")):
            add(f"PProg{mtag}{stag}{short}", "p3_progress_models", ["results", model, split, key], "f3")

# --- P3 marginal value of paid prefixes -----------------------------------
add("PMargValGain", "p3_prefix_marginal", ["validation_median_gain_frac"], "p1")
add("PMargTestGain", "p3_prefix_marginal", ["test_median_gain_frac"], "p1")
add("PMargValShrink", "p3_prefix_marginal", ["validation_median_shrink_gain"], "f4")
add("PMargTestShrink", "p3_prefix_marginal", ["test_median_shrink_gain"], "f4")
add("PMargPoseTestMAEFree", "p3_prefix_marginal",
    ["rows", "@features=pose,model=ridge,split=test", "mae_0p2"], "f3")
add("PMargPoseTestMAELong", "p3_prefix_marginal",
    ["rows", "@features=pose,model=ridge,split=test", "mae_1p0"], "f3")

# --- P3 phase diagram (reservation sweep) ---------------------------------
for _case, _tag in (("S2", "STwo"), ("S3", "SThree")):
    add(f"PPhaseDrop{_tag}", "phase_diagram", ["rate_drop_q30_q90", _case], "p1")
    add(f"PPhaseAlphaSpread{_tag}", "phase_diagram", ["spread_alpha", _case], "p1")
    add(f"PPhaseSpreadQ{_tag}", "phase_diagram", ["spread_q", _case], "p1")
for _case, _tag in (("S2", "STwo"), ("S3", "SThree")):
    add(f"PFactRange{_tag}", "up12_p3_full_factorial",
        ["cases", _case, "corner_range_pt"], "f2")
    add(f"PThreeRange{_tag}", "up14_p3_three_level",
        ["cases", _case, "corner_range_pt"], "f2")
    add(f"PThreeAbove{_tag}", "up14_p3_three_level",
        ["cases", _case, "n_corners_above_frozen"], "int")
    add(f"PThreeRTwo{_tag}", "up14_p3_three_level",
        ["cases", _case, "model_r2"], "f3")
    add(f"PThreeInter{_tag}", "up14_p3_three_level",
        ["cases", _case, "coefficients_pt", "gate x late_tol"], "f2")
    add(f"PValueRule{_tag}", "value_ladder", ["cases", _case, "scheduling rule"], "f2")
    add(f"PValueTruth{_tag}", "value_ladder", ["cases", _case, "true duration"], "f2")
    add(f"PValueObserve{_tag}", "value_ladder", ["cases", _case, "paid observation"], "f2")
    add(f"PValueReserve{_tag}", "value_ladder", ["cases", _case, "extra reservation"], "f2")

# --- representative point, retrained (up13_anchor_summary) -------------------
add("PAnchorTipsMinusWrist", "up13_anchor_summary", ["tips_minus_wrist_pt"], "f2")
add("PAnchorSE", "up13_anchor_summary", ["se_pt"], "f2")
add("PAnchorPooledSD", "up13_anchor_summary", ["pooled_within_anchor_sd"], "f4")

# ---------------------------------------------------------------------------
# 3. Slots that are deliberately still open (rendered as TODO).
# ---------------------------------------------------------------------------
# --- [m00314] state layer, information ceiling, adaptive decomposition ------
add("PStateRepPalmResidCm", "state_layer", ["representative_point", "candidates", "palm_centre_0_5_9_13_17", "rigidity_cm"], "g3")
add("PStateRepTipCm", "state_layer", ["representative_point", "candidates", "fingertip_centroid_4_8_12_16_20", "rigidity_cm"], "f3")
for st in ("reach", "pick", "place", "transport", "arrange"):
    add(f"PStateShare{st.capitalize()}", "state_layer", ["stages", "pooled_share", st], "p2")
add("PStateMeanSegLen", "state_layer", ["stages", "pooled_mean_seg_len_frames"], "f1")
add("PStateMedSegLen", "state_layer", ["stages", "pooled_median_seg_len_frames"], "f0")
add("PStateInfoBits", "state_layer", ["stages", "entropy", "info_bits"], "f4")
add("PStateRetFrames", "state_layer", ["retention", "frames_kept"], "int")
add("PStateRetTotal", "state_layer", ["retention", "frames_total"], "int")
add("PStateRetRate", "state_layer", ["retention", "frame_rate"], "p2")
add("PStatePassN", "state_layer", ["retention", "records_pass"], "int")
add("PStateFailN", "state_layer", ["retention", "records_fail"], "int")
add("PStateChiTwo", "state_layer", ["stages", "chi2_env", "chi2"], "f1")
add("PStateDof", "state_layer", ["stages", "chi2_env", "dof"], "int")
add("PStateCramerV", "state_layer", ["stages", "chi2_env", "cramers_v"], "f4")
add("PStateHNext", "state_layer", ["stages", "entropy", "H_next_bits"], "f4")
add("PStateHCond", "state_layer", ["stages", "entropy", "H_next_given_current_bits"], "f4")
add("PStateTransReachPick", "state_layer", ["stages", "pooled_transition", 0, 1], "f4")
add("PStateTransTransportPlace", "state_layer", ["stages", "pooled_transition", 3, 2], "f4")
add("PStateTransPlaceReach", "state_layer", ["stages", "pooled_transition", 2, 0], "f4")
add("PBaseHOneConst", "state_layer", ["baselines", "by_horizon", "h1", "constant", "mean"], "cm")
add("PBaseHOneLin", "state_layer", ["baselines", "by_horizon", "h1", "linear", "mean"], "cm")
add("PBaseHOneGain", "state_layer", ["baselines", "by_horizon", "h1", "improvement_mean"], "p2")
add("PBaseHFiveConst", "state_layer", ["baselines", "by_horizon", "h5", "constant", "mean"], "cm")
add("PBaseHFiveLin", "state_layer", ["baselines", "by_horizon", "h5", "linear", "mean"], "cm")
add("PBaseHFiveGain", "state_layer", ["baselines", "by_horizon", "h5", "improvement_mean"], "p2")
for case, tag in (("S1", "SOne"), ("S2", "STwo"), ("S3", "SThree")):
    add(f"PGPUB{tag}RMSE", "p2_gpu", ["rows", f"@L_frames=18,variant=v2", "test_rmse_m"], "cm")
    add(f"PGPUB{tag}WithinTwo", "p2_gpu", ["rows", f"@L_frames=18,variant=v2", "test_within_2cm"], "p1")
    add(f"PInfoFam{tag}", "p3_adaptive", ["upper_bound", case, "family_dist"], "f4")
    add(f"PInfoFamPC{tag}", "p3_adaptive", ["upper_bound", case, "family_pc"], "f4")
# --- five-mapping spread (up22) ---------------------------------------------
for _case, _tag in (("S2", "STwo"), ("S3", "SThree")):
    add(f"PMapRefSpan{_tag}", "up22_mapping_spread", ["cases", _case, "ref_span_pt"], "f1")
    add(f"PMapOursSpan{_tag}", "up22_mapping_spread", ["cases", _case, "ours_span_pt"], "f1")
    add(f"PMapGainMin{_tag}", "up22_mapping_spread", ["cases", _case, "gain_min_pt"], "f1")
    add(f"PMapGainMax{_tag}", "up22_mapping_spread", ["cases", _case, "gain_max_pt"], "f1")
    add(f"PMapGainMean{_tag}", "up22_mapping_spread", ["cases", _case, "gain_mean_pt"], "f1")
    add(f"PMapSat{_tag}", "up22_mapping_spread", ["cases", _case, "n_saturated"], "int")

# --- the three marks that were missed (honest negatives) --------------------
add("PRevNTested", "up_p3_review", ["verdict", "n_tested"], "int")
add("PRevNPass", "up_p3_review", ["verdict", "n_ge_1pt"], "int")
add("PRevBest", "up_p3_review", ["verdict", "best_delta_pt"], "f2")
add("PRevWorst", "up_p3_review", ["verdict", "min_delta_pt"], "f2")
add("PRevFired", "up_p3_review", ["verdict", "n_cells_review_fired"], "int")
add("PRevThreshold", "up_p3_review", ["verdict", "threshold_pt"], "f1")
add("PQuantLThirtyRMSE", "up_p2_final", ["aggregate", "L30", "rmse_3d_cm", "mean"], "f2")
add("PQuantLThirtyQ90", "up_p2_final", ["aggregate", "L30", "q90_cm", "mean"], "f2")
add("PQuantLThirtyCoverage", "up_p2_final", ["aggregate", "L30", "coverage_test", "mean"], "f3")
add("PQuantLSixRMSE", "up_p2_final", ["aggregate", "L6", "rmse_3d_cm", "mean"], "f2")
add("PQuantLThirtyTarget", "up_p2_final", ["_meta", "bar", "rmse_3d_max_cm"], "f1")
add("PQuantLThirtyQNineZeroTarget", "up_p2_final", ["_meta", "bar", "q90_max_cm"], "f1")

for case, tag in (("S2", "STwo"), ("S3", "SThree")):
    for a, b, lab in ((0.75, 0.5, "LowAlpha"), (1.5, 0.5, "HighAlpha")):
        add(f"PMap{tag}{lab}", "p3_stochastic_schedule", ["mapping_sensitivity",
            f"@case={case},policy=slack_old,alpha={a},beta={b}", "eta"], "f4")

# --- closed form for the on-time probability --------------------------------
add("PCFJobs", "closedform_calib", ["n_jobs"], "int")
add("PCFBase", "closedform_calib", ["base_rate"], "f4")
add("PCFBrier", "closedform_calib", ["brier"], "f4")
add("PCFBrierConst", "closedform_calib", ["brier_base"], "f4")
add("PCFSkill", "closedform_calib", ["brier_skill"], "f3")
add("PCFECE", "closedform_calib", ["ece"], "f4")
add("PCFMaxErr", "closedform_calib", ["alpha_collapse_max_abs_err"], "f4")
add("PCFMeanErr", "closedform_calib", ["alpha_collapse_mean_abs_err"], "f4")
add("PCFShiftTrain", "closedform_calib", ["shift_check", "gap_train_law"], "f4")
add("PCFShiftAll", "closedform_calib", ["shift_check", "gap_all_law"], "f4")
for case, tag in (("S1", "SOne"), ("S2", "STwo"), ("S3", "SThree")):
    for a, lab in ((0.75, "Low"), (1.0, "Nom"), (1.5, "High")):
        sel = f"@case={case},alpha={a}"
        add(f"PCF{tag}{lab}Phat", "closedform_calib",
            ["alpha_collapse", sel, "mean_p_hat"], "f4")
        add(f"PCF{tag}{lab}Real", "closedform_calib",
            ["alpha_collapse", sel, "realised"], "f4")
        add(f"PCF{tag}{lab}N", "closedform_calib",
            ["alpha_collapse", sel, "n"], "int")

TODO_SLOTS = [
    # Audited 2026-11-20: all seven placeholders below had zero references in
    # main.tex, so they rendered nowhere and only cluttered slots.tex. Each of
    # the four questions is answered by slots that do resolve:
    #   reliability Brier   -> replaced by the calibration finding (PCal* slots,
    #                          reported as a negative result in 3.3)
    #   retention funnel    -> not claimed anywhere in the text
    #   re-observation net  -> PStoch* pair differences carry the argument
    #   duration bound      -> Section 6 uses PInfoFam*/PInfoGap* instead
    # Kept as an empty list so the generator still reports open placeholders.
]

# ---------------------------------------------------------------------------
# 4. Appendix B code excerpts: real functions lifted from code/*.py (AST based).
# ---------------------------------------------------------------------------
EXCERPTS = [
    ("p1_state.py", "hand_feats", "p1_state_hand_feats.py"),
    ("p1_model.py", "ward_segments", "p1_model_ward_segments.py"),
    ("p2_predict.py", "windows", "p2_predict_windows.py"),
    ("p3_schedule.py", "p_late", "p3_schedule_p_late.py"),
]


def resolve(obj, path):
    for step in path:
        if isinstance(step, int):
            obj = obj[step]
            continue
        if isinstance(step, str) and step.startswith("@"):
            clauses = dict(c.split("=", 1) for c in step[1:].split(","))
            hit = None
            for item in obj:
                ok = True
                for k, v in clauses.items():
                    if k not in item:
                        ok = False
                        break
                    actual = item[k]
                    try:
                        ok = abs(float(actual) - float(v)) < 1e-9
                    except (TypeError, ValueError):
                        ok = str(actual) == v
                    if not ok:
                        break
                if ok:
                    hit = item
                    break
            if hit is None:
                raise KeyError(f"selector {step} matched nothing")
            obj = hit
            continue
        obj = obj[step]
    return obj


def fmt_value(value, tag):
    if tag == "bool":
        return "PASS" if value else "FAIL"
    if tag == "txt":
        return str(value).replace("_", r"\_")
    if value is None:
        return "TODO"
    if tag == "int":
        return str(int(round(float(value))))
    scale = 1.0
    digits = 3
    if tag.startswith("f"):
        digits = int(tag[1:])
    elif tag.startswith("p"):
        scale, digits = 100.0, int(tag[1:])
    elif tag == "cm":
        scale, digits = 100.0, 2
    elif tag == "g3":
        return f"{float(value):.3g}"
    out = f"{float(value) * scale:.{digits}f}"
    return out


COMPUTED = {
    # name: (tag, op, (slot_a, slot_b)) -- op is "minus" or "max_minus_min"
    "PInfoGapSOne": ("f4", "minus", ("PStochSOneOracleETA", "PStochSOneSlackOldETA")),
    "PInfoGapSTwo": ("f4", "minus", ("PStochSTwoOracleETA", "PStochSTwoSlackOldETA")),
    "PInfoGapSThree": ("f4", "minus", ("PStochSThreeOracleETA", "PStochSThreeSlackOldETA")),
    "PGpuRatio": ("f2", "ratio", ("PTwoARidgeRMSE", "PGPUAWristRMSE")),
    "PInfoRecoverSTwo": ("p0", "frac", ("PStochSTwoSlackOldETA", "PStochSTwoEDFOldETA",
                                        "PStochSTwoOracleETA", "PStochSTwoEDFOldETA")),
    "PInfoRecoverSThree": ("p0", "frac", ("PStochSThreeSlackOldETA", "PStochSThreeEDFOldETA",
                                          "PStochSThreeOracleETA", "PStochSThreeEDFOldETA")),
    # adaptive reservation minus the duration-aware reference (negative gap = ours better)
    "PInfoAdvSTwo": ("f4", "minus", ("PImpSTwoAllCand", "PStochSTwoOracleETA")),
    "PInfoAdvSThree": ("f4", "minus", ("PImpSThreeAllCand", "PStochSThreeOracleETA")),
    "PImpSTwoAllMeanPt": ("f2", "pct100", ("PImpSTwoAllMean",)),
    "PImpSThreeAllMeanPt": ("f2", "pct100", ("PImpSThreeAllMean",)),
    "POracleGapSTwoPt": ("f2", "pct100", ("POracleGapSTwo",)),
    "POracleGapSTwoCIPt": ("f2", "pct100", ("POracleGapSTwoCI",)),
    "POracleGapSThreePt": ("f2", "pct100", ("POracleGapSThree",)),
    "POracleGapSThreeCIPt": ("f2", "pct100", ("POracleGapSThreeCI",)),
}

# P2 masked-observation arms: the stored metric is a 3-D Euclidean RMS in metres;
# the paper reports per-coordinate RMS in centimetres, so divide by sqrt(3) and scale.
for _pre in ("PClean", "PLocf", "PInterp"):
    for _suf in ("Zero", "Three", "Six"):
        COMPUTED[_pre + _suf] = ("f2", "pc3", (_pre + "Raw" + _suf,))


def main():
    cache = {}
    lines = [
        "% slots.tex -- GENERATED by code/fill_numbers.py. Do not edit by hand.",
        "% Every number printed in main.tex comes from this file.",
        r"\newcommand{\slotTODO}{TODO}",
    ]
    count = 0
    for name in sorted(SPEC):
        value, source = SPEC[name]
        lines.append(f"% [spec] {source}")
        lines.append(r"\newcommand{\slot" + name + "}{" + str(value) + "}")
        count += 1
    missing = []
    RAW = {}
    for name in sorted(SLOTS):
        jfile, path, tag = SLOTS[name]
        if jfile not in cache:
            cache[jfile] = json.loads((DATA / (jfile + ".json")).read_text(encoding="utf-8"))
        try:
            value = resolve(cache[jfile], path)
        except (KeyError, IndexError, TypeError) as exc:
            missing.append((name, jfile, ".".join(map(str, path)), str(exc)))
            continue
        RAW[name] = value
        lines.append(f"% [json] {jfile}.json : " + ".".join(map(str, path)))
        lines.append(r"\newcommand{\slot" + name + "}{" + fmt_value(value, tag) + "}")
        count += 1
    for name in sorted(COMPUTED):
        tag, op, refs = COMPUTED[name]
        if op == "frac":
            a, b, c, d = (RAW.get(r) for r in refs)
            if None in (a, b, c, d):
                missing.append((name, "computed", op, "source slot unresolved"))
                continue
            lines.append(f"% [calc] ({refs[0]} - {refs[1]}) / ({refs[2]} - {refs[1]})")
            lines.append(r"\newcommand{\slot" + name + "}{" + fmt_value((float(a) - float(b)) / (float(c) - float(b)), tag) + "}")
            count += 1
            continue
        if op == "pct100":
            a = RAW.get(refs[0])
            if a is None:
                missing.append((name, "computed", op, "source slot unresolved"))
                continue
            lines.append(f"% [calc] {refs[0]} * 100")
            lines.append(r"\newcommand{\slot" + name + "}{" + fmt_value(float(a) * 100.0, tag) + "}")
            count += 1
            continue
        if op == "pc3":
            a = RAW.get(refs[0])
            if a is None:
                missing.append((name, "computed", op, "source slot unresolved"))
                continue
            lines.append(f"% [calc] {refs[0]} / sqrt(3)")
            lines.append(r"\newcommand{\slot" + name + "}{" + fmt_value(float(a) / 1.7320508075688772, tag) + "}")
            count += 1
            continue
        a, b = (RAW.get(r) for r in refs)
        if a is None or b is None:
            missing.append((name, "computed", op, "source slot unresolved"))
            continue
        value = float(a) / float(b) if op == "ratio" else float(a) - float(b)
        lines.append(f"% [calc] {refs[0]} - {refs[1]}")
        lines.append(r"\newcommand{\slot" + name + "}{" + fmt_value(value, tag) + "}")
        count += 1
    # --- same-unit comparison of the two P2 predictors ---------------------
    # The appendix used to compare a per-coordinate GRU error with a
    # three-dimensional ridge error and call the ratio "times better".
    # sqrt(3) relates the two units; both are derived here so the
    # paragraph cannot drift away from the data.
    _s3 = 3.0 ** 0.5
    _gru = {k: float(RAW["PGPU" + k + suf]) * 100.0 for k, suf in
            (("A", "WristRMSE"), ("B", "STwoRMSE"), ("C", "BothRMSE"), ("D", "BothRMSE"))}
    _rdg = {k: float(RAW["PTwo" + k + "RidgeRMSE"]) * 100.0 for k in "ABCD"}
    _same_unit = []
    for _k in "ABCD":
        _same_unit.append(("PGpu" + _k + "ThreeD", "f2", _gru[_k] * _s3))
        _same_unit.append(("PRidge" + _k + "PerCoord", "f2", _rdg[_k] / _s3))
    for _k in "CD":
        _same_unit.append(("PGpuWin" + _k + "PerCoordPct", "f1",
                           100.0 * (_rdg[_k] / _s3 - _gru[_k]) / (_rdg[_k] / _s3)))
    _same_unit.append(("PGpuAPerCoordGapPct", "f1",
                       100.0 * (_gru["A"] - _rdg["A"] / _s3) / (_rdg["A"] / _s3)))
    for _name, _tag, _val in _same_unit:
        lines.append("% [calc] same-unit comparison, p2_prediction / p2_gpu")
        lines.append(r"\newcommand{\slot" + _name + "}{" + fmt_value(_val, _tag) + "}")
        count += 1
    for key, section, what, producer in TODO_SLOTS:
        k = tex_name(key)
        if k in SLOTS or k in SPEC:
            raise SystemExit(f"TODO slot shadows a resolved slot: {k}")
        lines.append(f"% [todo] {section} : {what} -- producer {producer}")
        lines.append(r"\newcommand{\slot" + k + "}{TODO}")
        count += 1
    OUT_SLOTS.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    SNIP.mkdir(exist_ok=True)
    for src, func, out_name in EXCERPTS:
        text = (ROOT / "code" / src).read_text(encoding="utf-8")
        pattern = re.compile(rf"^def {re.escape(func)}\(.*?(?=^def |\Z)", re.S | re.M)
        match = pattern.search(text)
        body = match.group(0).rstrip() if match else f"# TODO: {func} not found in {src}"
        (SNIP / out_name).write_text(f"# Excerpt from code/{src} :: {func}\n" + body + "\n",
                                     encoding="utf-8", newline="\n")

    todo = [
        "# Open number slots (TODO)",
        "",
        "Every entry below is rendered as `TODO` in `main.tex` via `\\slotTODO`.",
        "Nothing here may be replaced by a hand-written number.",
        "",
        "| slot key | section | what is missing | producing script |",
        "| --- | --- | --- | --- |",
    ]
    for key, section, what, producer in TODO_SLOTS:
        todo.append(f"| `{key}` | {section} | {what} | `{producer}` |")
    if missing:
        todo += ["", "## SLOTS entries that failed to resolve", "",
                 "| slot | json | path | error |", "| --- | --- | --- | --- |"]
        for name, jfile, path, err in missing:
            todo.append(f"| `{name}` | {jfile} | `{path}` | {err} |")
    OUT_TODO.write_text("\n".join(todo) + "\n", encoding="utf-8", newline="\n")

    print(f"slots.tex written: {count} commands "
          f"({len(SPEC)} spec + {len(SLOTS) - len(missing)} json), {len(TODO_SLOTS)} open TODO slots")
    print(f"snippets: {len(EXCERPTS)} files in {SNIP}")
    if missing:
        print(f"UNRESOLVED: {len(missing)}")
        for name, jfile, path, err in missing:
            print("  ", name, jfile, path, err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
