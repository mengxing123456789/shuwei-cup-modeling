
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Decisive test left by the failed video agent: does the visual-feature duration
model actually change the scheduling headline?

`p3_stochastic_schedule.py` reads `data/p3_duration_predictions.csv`, which is the
v1 table produced at 15:06. `data/p3_duration_predictions_v2.csv` (15:28) comes
from the validation-selected `visual_a300` design, whose test MAE is 2.5746 s
against 3.153 s for the v1 selection. Swapping the source therefore asks exactly
one question: does a more accurate duration prediction raise the weighted on-time
rate, or does the reservation policy absorb the improvement anyway?

Writes `data/p3_visual_schedule.json`; the frozen `p3_stochastic_schedule.json` is
left untouched so the submitted table keeps its provenance.
"""
import re
from pathlib import Path

SRC = Path(r"code\p3_stochastic_schedule.py")
DST = Path(r"code\p3_visual_sched.py")

s = SRC.read_text(encoding="utf-8")

# 1. point it at the v2 duration table
s = s.replace('"p3_duration_predictions.csv"', '"p3_duration_predictions_v2.csv"', 1)
assert 'p3_duration_predictions_v2.csv' in s

# 2. a separate output, and no trial-level CSV clobbering
s = s.replace('write_json("p3_stochastic_schedule.json",out)',
              'write_json("p3_visual_schedule.json",out)', 1)
s = s.replace('"p3_trials.csv"', '"p3_visual_trials.csv"')
s = s.replace('"p3_summary.csv"', '"p3_visual_summary.csv"')

# 3. record the provenance in _meta
s = s.replace('model="validation-selected fusion; conditional family/prefix train residual distributions"',
              'model="visual_a300 duration model (v2 table); conditional family/prefix train residual distributions"', 1)

DST.write_text(s, encoding="utf-8", newline="\n")
print("wrote", DST, len(s), "bytes")