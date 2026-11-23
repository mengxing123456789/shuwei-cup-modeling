
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Two-line trim in Model Evaluation so the reference list closes on page 25."""
import pathlib

p = pathlib.Path(r"main.tex")
s = p.read_text(encoding="utf-8")

old = (
    "Two gaps are stated rather than bridged. The reliability weight does not enter the\n"
    "Part II regression as a sample weight, and the Part II conformal radius does not\n"
    "become the Part III reservation quantile, which uses duration residuals instead.\n"
    "The chain is therefore a sequence of informed modules, not a single end-to-end\n"
    "estimator, and we do not describe it as one."
)
new = (
    "Two gaps stay open: the reliability weight does not enter the Part II regression as a\n"
    "sample weight, and the Part II conformal radius does not become the Part III\n"
    "reservation quantile, which uses duration residuals instead. The chain is a\n"
    "sequence of informed modules, not one end-to-end estimator."
)
assert old in s, "anchor missing"
p.write_text(s.replace(old, new, 1), encoding="utf-8", newline="\n")
print("trimmed")