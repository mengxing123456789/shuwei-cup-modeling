# -*- coding: utf-8 -*-
"""Driver: reproduce every number in the paper, in order.

    python code/main.py             Q1, Q2, Q3, the convention audits, the trainer
    python code/main.py --fast      same, but skips the trainer (69 s)

Every step writes its own JSON into data/; nothing is recomputed twice and no
figure is drawn here (code/figures.py reads the JSON instead, because it needs a
matplotlib build that this numerical interpreter cannot provide).

Interpreter used for every reported number:
    E:\\Mini\\envs\\mathmodel\\python.exe -X utf8
Interpreter used for the figures:
    E:\\Mini\\python.exe -X utf8 code/figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import convention      # noqa: E402
import make_results    # noqa: E402
import q1_alt          # noqa: E402
import q1_axis         # noqa: E402
import solve_q1        # noqa: E402
import solve_q2        # noqa: E402
import solve_q3        # noqa: E402
import train_lead      # noqa: E402

STEPS = [
    ("Q1", solve_q1),
    ("Q2", solve_q2),
    ("Q3", solve_q3),
    ("conventions", convention),
    ("reference axis (published numbers reproduced)", q1_alt),
    ("reference axis (four readings)", q1_axis),
]
SLOW = [("trained forecaster", train_lead)]
LAST = [("flatten for the data checker", make_results)]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    steps = STEPS if "--fast" in argv else STEPS + SLOW
    for name, mod in steps + LAST:
        print(f"\n{'=' * 12} {name} {'=' * 12}", flush=True)
        rc = mod.main()
        if rc:
            print(f"{name} failed with {rc}", flush=True)
            return rc
    print("\nevery reported number reproduced", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
