#!/usr/bin/env python
"""把 data/*.json 里的标量展平成 `data/results_summary.json`，给数据核对工具用。

`paper_data_check.py` 找的是 `results_*.json`，而本项目的原始结果分散在
`q1.json` / `q2.json` / `q3.json` / `lead.json` / `convention.json` 里，且大部分
数值埋在嵌套结构与长数组里。这个脚本**只做搬运**：把每个标量按点分路径摊平，
不做任何计算，所以摊平后的数与原始文件逐位相同（`verify_numbers.py` 也是直接
读原始文件，两者不会互相污染）。

数组只保留标量元素（`window_sweep[0].I` 会变成 `window_sweep.0.I`），
上千个采样点的波形数组（`t`/`y`/`a`/`theta`/`fa`）跳过——它们不是「结果数字」，
而且会让文件涨到几十兆。

跑法：`python code/make_results.py`，写 `data/results_summary.json`。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SOURCES = ("q1.json", "q2.json", "q3.json", "lead.json", "convention.json",
           "q1_alt.json", "q1_sin.json", "q1_variants.json")

# 波形数组：长度 > 32 的数值列表一律跳过，只留长度与首尾值
SKIP_LONG = True
LONG = 32


def flatten(obj, prefix: str, out: dict, depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, f"{prefix}.{k}" if prefix else str(k), out, depth + 1)
    elif isinstance(obj, list):
        if SKIP_LONG and len(obj) > LONG and all(isinstance(v, (int, float)) for v in obj):
            out[f"{prefix}.__len"] = len(obj)
            out[f"{prefix}.__first"] = float(obj[0])
            out[f"{prefix}.__last"] = float(obj[-1])
            return
        for i, v in enumerate(obj):
            flatten(v, f"{prefix}.{i}" if prefix else str(i), out, depth + 1)
    elif isinstance(obj, bool):
        out[prefix] = obj
    elif isinstance(obj, (int, float)):
        out[prefix] = float(obj)
    elif isinstance(obj, str):
        out[prefix] = obj


def main() -> int:
    summary: dict[str, object] = {"_note": "flattened from data/*.json by code/make_results.py"}
    total = 0
    for name in SOURCES:
        p = DATA / name
        if not p.exists():
            continue
        raw = json.loads(p.read_text(encoding="utf-8"))
        flat: dict[str, object] = {}
        flatten(raw, name.replace(".json", ""), flat)
        summary.update(flat)
        total += len(flat)
        print(f"{name}: {len(flat)} scalars")
    out = DATA / "results_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"{out.name}: {total} scalars, {out.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
