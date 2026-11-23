# -*- coding: utf-8 -*-
"""Repair the misplaced slot block: it landed inside the nested mapping loop.

The patch inserted its block at the first line of the inner ``for a, b, lab`` body, which
split the loop and left an empty block. This script removes the inserted lines and puts
them back at module level, just above the enclosing ``for case, tag`` loop.
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FN = ROOT / "code" / "fill_numbers.py"

START = "# --- five-mapping spread (up22) ---------------------------------------------"
END = 'add("PQuantLSixRMSE", "up_p2_final", ["aggregate", "L6", "rmse_3d_cm", "mean"], "f2")'
LOOP = 'for case, tag in (("S2", "STwo"), ("S3", "SThree")):\n    for a, b, lab in ((0.75, 0.5, "LowAlpha"), (1.5, 0.5, "HighAlpha")):'


def main():
    apply = "--apply" in sys.argv
    t = io.open(FN, encoding="utf-8").read()
    i = t.find(START)
    j = t.find(END)
    if i < 0 or j < 0:
        print("markers missing", i, j)
        return 1
    block = t[i : j + len(END)]
    rest = t[:i] + t[j + len(END) :]
    # Drop the leftover blank line the insertion left behind.
    rest = rest.replace("\n\n\nadd(f\"PMap{tag}{lab}\"", "\n\nadd(f\"PMap{tag}{lab}\"")
    k = rest.find(LOOP)
    if k < 0:
        print("loop marker missing")
        return 1
    out = rest[:k] + block + "\n\n" + rest[k:]
    print("removed", len(block), "chars from the loop body, reinserted at module level")
    if not apply:
        print("dry run; pass --apply")
        return 0
    io.open(FN, "w", encoding="utf-8", newline="\n").write(out)
    print("written", FN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
