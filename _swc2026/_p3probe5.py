# -*- coding: utf-8 -*-
"""Find elapsed-time and censoring fields anywhere in the P3 artefacts."""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
keys = set()


def walk(o, depth=0):
    if depth > 3:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            keys.add(k)
            walk(v, depth + 1)
    elif isinstance(o, list):
        for v in o[:3]:
            walk(v, depth + 1)


for name in ["p3_improved_verify.json", "p3_scheduling.json", "p3_stochastic_schedule.json"]:
    keys.clear()
    j = json.loads((D / name).read_text(encoding="utf-8"))
    walk(j)
    hits = sorted(k for k in keys if any(t in k.lower() for t in ("elaps", "censor", "invalid", "wall", "seconds", "finish")))
    print(name, "->", hits)
    if name == "p3_improved_verify.json":
        c = j["cases"]
        k0 = next(iter(c))
        print("  case keys:", list(c[k0].keys())[:20])
