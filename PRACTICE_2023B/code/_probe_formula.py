# -*- coding: utf-8 -*-
"""临时探针：列出两附件全部公式单元格（用完即删）。"""
import sys, io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_skeleton as M
import fetch_annex as FA

for which in ("I", "II"):
    fc = M.formula_cells(which)
    print("=== annex", which, "count", len(fc))
    for c, f in fc:
        print("   ", c, "|", f)
    grid = FA.read_sheet(M.DATA / (FA.ANNEX_I if which == "I" else FA.ANNEX_II))
    print("   -- row labels")
    for r in sorted(grid):
        a = grid[r].get(0)
        print("    r%-3d %r" % (r, a))
