
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Drop the duplicated validation-vs-test caveat from the visual paragraph.

The same warning already appears twice in the paper (the k-cap study in Part I and
the seed-split footnote in Part V), so repeating it here costs two lines the body
budget does not have.
"""
import pathlib

p = pathlib.Path(r"main.tex")
s = p.read_text(encoding="utf-8")

old = (
    "precision of the forecast. The same table warns against the validation column, where a\n"
    "gradient-boosted design scored \\slotPVisHGBVal{} s and degraded to \\slotPVisHGBTest{} s\n"
    "on test.\n"
)
new = "precision of the forecast.\n"
assert old in s, "anchor missing"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8", newline="\n")
print("dropped duplicated caveat")