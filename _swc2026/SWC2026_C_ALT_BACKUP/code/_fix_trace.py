# -*- coding: utf-8 -*-
"""Point the trace_c claim back at the value the table actually prints."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "code" / "verify_numbers.py"


def main() -> int:
    s = P.read_text(encoding="utf-8")
    old = 'add("p2.trace_c", oo["C_two_requests"]["trace_cm2"], "1063.932")'
    new = 'add("p2.trace_c", oo["C_two_requests"]["trace_cm2"], "1063.9")'
    if old not in s:
        print("anchor not found")
        return 2
    s = s.replace(old, new, 1)
    P.write_text(s, encoding="utf-8", newline="\n")
    print(f"written {P.stat().st_size} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
