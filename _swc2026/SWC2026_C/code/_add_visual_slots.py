
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Wire the visual-modality probe into the paper.

The two scheduler deltas are differences between two saved runs, so they enter
SPEC with an explicit pointer (the same pattern used for protocol constants);
everything else is selected straight out of the JSON with the `@` selector, so a
rerun moves the numbers instead of silently disagreeing with the text.
"""
import pathlib

p = pathlib.Path(r"code\fill_numbers.py")
s = p.read_text(encoding="utf-8")

anchor = 'add("PSegTestRecords"'
assert anchor in s, "PSegTestRecords anchor missing"

slots = '''# --- visual modality probe: does a better duration model move the schedule? ---
add("PVisDurBase", "p3_visual_duration.json",
    ["rows", "@design=pose_old8,model=ridge,split=test", "mae"], "f4")
add("PVisHGBVal", "p3_visual_duration.json",
    ["rows", "@design=all_fused,model=hgb,split=validation", "mae"], "f4")
add("PVisHGBTest", "p3_visual_duration.json",
    ["rows", "@design=all_fused,model=hgb,split=test", "mae"], "f4")
add("PVisDurSel", "p3_final_duration.json",
    ["evaluation", "@split=test", "mae"], "f4")

'''
s = s.replace(anchor, slots + anchor, 1)

spec_anchor = '    "PProductStateVars":'
assert spec_anchor in s, "SPEC anchor missing"
spec_new = '''    "PVisDurRel": ("-16.7", "relative: p3_final_duration.json visual_a300 test MAE 2.5746 vs pose_old8 ridge 3.0920 (p3_visual_duration.json)"),
    "PVisSchedS2D": ("+0.031", "p3_visual_schedule.json minus p3_stochastic_schedule.json, slack_fusion S2, same 30 seeds"),
    "PVisSchedS3D": ("-0.009", "p3_visual_schedule.json minus p3_stochastic_schedule.json, slack_fusion S3, same 30 seeds"),
    "PVisOracleS3D": ("+0.025", "p3_visual_schedule.json minus p3_stochastic_schedule.json, oracle S3, ceiling shift"),
'''
s = s.replace(spec_anchor, spec_new + spec_anchor, 1)

p.write_text(s, encoding="utf-8", newline="\n")
print("fill_numbers.py patched")