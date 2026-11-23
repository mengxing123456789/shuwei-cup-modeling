# -*- coding: utf-8 -*-
"""Replace the last three abstract slots with the measured Q3 ranking.

The first draft of the abstract claimed the scheduling program "raises the on-time
rate while cutting cost". The 30-seed run does not support that: the program beats
EDF but trails the SLACK rule, and its cost is not uniformly lower. The sentence is
rewritten around what the table actually shows, including the fact that the largest
effect comes from re-planning rather than from the chance constraint.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"


def main() -> int:
    p3 = json.loads((ROOT / "data" / "alt_p3.json").read_text(encoding="utf-8"))
    cells = {(d["policy"], d["case"]): d for d in p3["summary"]}
    edf = cells[("edf_old", "S3")]["weighted_on_time_rate"]
    roll = cells[("ccmip_rolling", "S3")]["weighted_on_time_rate"]
    slack = cells[("slack_old", "S3")]["weighted_on_time_rate"]
    one = cells[("ccmip_oneshot", "S3")]["weighted_on_time_rate"]

    text = TEX.read_text(encoding="utf-8")
    old = (
        "Q3 raises the weighted on-time rate from @@P3EDF@@ (EDF) to @@P3CCMIP@@ while "
        "cutting cost by @@P3COSTCUT@@\\%."
    )
    new = (
        f"Q3 raises the weighted on-time rate in the tightest case from {edf:.3f} (EDF) to "
        f"{roll:.3f}, of which {roll - one:.3f} comes from re-planning alone, but still trails "
        f"the SLACK rule at {slack:.3f}; we report that ranking rather than claiming a win."
    )
    if old not in text:
        print("abstract anchor not found")
        return 2
    text = text.replace(old, new, 1)
    TEX.write_text(text, encoding="utf-8", newline="\n")
    print(f"abstract rewritten; main.tex {TEX.stat().st_size} B")
    print(f"  EDF {edf:.3f} -> rolling {roll:.3f} (one-shot {one:.3f}), SLACK {slack:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
