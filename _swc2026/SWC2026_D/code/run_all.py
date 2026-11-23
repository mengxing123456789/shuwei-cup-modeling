# -*- coding: utf-8 -*-
"""跑全部实验并计时。要求总时长 < 5 分钟。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import t1_geometry  # noqa: E402
import t2_resonance  # noqa: E402
import t3_kepler  # noqa: E402
import counterexamples  # noqa: E402


def main():
    steps = [("t1_geometry", t1_geometry.main),
             ("t2_resonance", t2_resonance.main),
             ("t3_kepler", t3_kepler.main),
             ("counterexamples", counterexamples.main)]
    log = {}
    t0 = time.time()
    for name, fn in steps:
        t = time.time()
        fn()
        log[name] = round(time.time() - t, 2)
        print(f"[run_all] {name} {log[name]:.1f}s")
    total = round(time.time() - t0, 2)
    log["total_s"] = total
    log["budget_s"] = 300
    log["within_budget"] = bool(total < 300)
    log["_meta"] = {"title": "run timings", "budget_s": 300, "note": "每次浮动 ±5%，不作对账行"}
    out = HERE.parent / "data" / "run_all.json"
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[run_all] total {total}s  within_budget={log['within_budget']}")


if __name__ == "__main__":
    main()