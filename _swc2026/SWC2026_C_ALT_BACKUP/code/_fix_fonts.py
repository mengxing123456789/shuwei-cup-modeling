# -*- coding: utf-8 -*-
"""Raise every in-figure font below 6.2 pt and shorten the two longest notes.

The gate rejects any text span with three or more characters under 6.0 pt, and
matplotlib writes 6.0 as 5.98 often enough that 6.2 is the safe floor. Two notes
were long enough that raising them would have widened them past the canvas, so
their wording is shortened at the same time.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "code" / "alt_figures.py"

# wording shortened so the larger type still fits the declared canvas width
TEXT = [
    (
        'cross-question links: Q1 variance -> Q2 process noise;  Q1 reliability -> Q3 reservation',
        'cross-links: Q1 variance -> Q2 noise; Q1 reliability -> Q3 reservation',
    ),
    (
        'per segment: BOCPD 1.14 cuts, threshold 0.79',
        'cuts per segment: 1.14 vs 0.79',
    ),
]


def main() -> int:
    s = SRC.read_text(encoding="utf-8")
    n_total = 0

    for old, new in TEXT:
        n = s.count(old)
        if n:
            s = s.replace(old, new)
        print(f"text  x{n}  {new[:52]}")

    def bump(m: re.Match) -> str:
        nonlocal n_total
        value = float(m.group(1))
        if value < 6.2:
            n_total += 1
            return f"fontsize={6.2}"
        return m.group(0)

    s = re.sub(r"fontsize=([0-9.]+)", bump, s)
    print(f"fontsize raised: {n_total}")

    SRC.write_text(s, encoding="utf-8", newline="\n")
    print(f"written {SRC.stat().st_size} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
