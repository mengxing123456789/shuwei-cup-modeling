# -*- coding: utf-8 -*-
"""Merge the alternative paper's result JSONs into one file the gate can stage.

`submission_gate.stage_data` copies `data/results_*.json` (and `data/results.json`)
into the staged view; this project names its files `alt_p*.json`, so the gate saw an
empty data directory and could not cross-check a single number. The merge keeps the
values unchanged and only re-keys them by the name of the file they came from.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "results_swc2026.json"

SKIP = {"results_swc2026.json", "ledger.json"}


def main() -> int:
    merged: dict = {}
    n = 0
    for p in sorted(DATA.glob("*.json")):
        if p.name in SKIP:
            continue
        try:
            merged[p.stem] = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"skip {p.name}: {exc}")
            continue
        n += 1
    OUT.write_text(
        json.dumps(merged, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"merged {n} files -> {OUT.name} {OUT.stat().st_size} B")
    for k in merged:
        print(f"  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
