# -*- coding: utf-8 -*-
"""Align the printed needles in verify_numbers.py with what main.tex actually prints."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "code" / "verify_numbers.py"

REP = [
    ('"5.66")', '"5.656")'),
    ('"7.10")', '"7.095")'),
    ('"12.38")', '"12.377")'),
    ('"12.81")', '"12.809")'),
    ('"9.46")', '"9.464")'),
    ('"9.55")', '"9.554")'),
    ('"21.50")', '"21.497")'),
    ('"2.91")', '"2.914")'),
    ('"29.94")', '"29.936")'),
    ('"9.12")', '"9.117")'),
    ('"9.87")', '"9.874")'),
    ('"1063.9")', '"1063.932")'),
]


def main() -> int:
    s = P.read_text(encoding="utf-8")
    for old, new in REP:
        n = s.count(old)
        if n:
            s = s.replace(old, new)
        print(f"{old:12s} -> {new:12s}  x{n}")
    P.write_text(s, encoding="utf-8", newline="\n")
    print(f"written {P.stat().st_size} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
