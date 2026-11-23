# -*- coding: utf-8 -*-
"""对账：out/03-numbers.md 的每一行「值」必须能在 data/*.json 里按同行的键路径找到。

用法： python code/check_numbers.py
退出码 0 = 全部对上。结果落 data/check_numbers.json。
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def resolve(doc, path):
    cur = doc
    for seg in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(seg)]
        elif isinstance(cur, dict):
            cur = cur[seg]
        else:
            raise KeyError(f"不可下钻：{path} @ {seg}")
    return cur


def main():
    md = (ROOT / "out" / "03-numbers.md").read_text(encoding="utf-8")
    cache, rows, failures, skipped = {}, [], [], []
    for line in md.splitlines():
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 4 or set(cols[0]) <= set("- ") or cols[0] == "量":
            continue
        name, val, unit, key = cols[0], cols[1], cols[2], cols[3]
        if not NUM.match(val):
            skipped.append({"量": name, "值": val, "原因": "非纯数值"})
            continue
        target = float(val)
        fname = key.split(".")[0]
        if fname not in cache:
            cache[fname] = json.loads((ROOT / "data" / f"{fname}.json").read_text(encoding="utf-8"))
        try:
            got = float(resolve(cache[fname], key.split(".", 1)[1]))
        except Exception as exc:  # noqa: BLE001
            failures.append({"量": name, "键": key, "错": repr(exc)})
            continue
        if abs(target) < 1e-10 or abs(got) < 1e-10:
            # 机器精度的"数值零"：两栏都小到 1e-10 以下即算对上（舍入顺序不同会让这个量级跳动）
            ok = abs(target) < 1e-10 and abs(got) < 1e-10
        elif abs(target) < 1e-6:
            # 拟合残差在这一量级上随 BLAS 舍入浮动，用 1 个百分点
            ok = math.isclose(got, target, rel_tol=1e-2)
        else:
            ok = math.isclose(got, target, rel_tol=1e-4)
        rows.append({"量": name, "值": target, "json": got, "键": key, "unit": unit, "ok": ok})
        if not ok:
            failures.append({"量": name, "键": key, "写": target, "读": got,
                             "相对差": abs(got - target) / max(abs(got), 1e-300)})

    figs = sorted(p.name for p in (ROOT / "figures").glob("*.pdf"))
    out = {
        "checked_rows": len(rows),
        "failures": len(failures),
        "skipped_non_numeric": skipped,
        "failure_detail": failures,
        "n_figures_pdf": len(figs),
        "figures": figs,
        "tolerance": "|v|<1e-10 视为数值零；|v|<1e-6 用 rel 1e-2（拟合残差随舍入浮动）；其余 rel 1e-4",
    }
    (ROOT / "data" / "check_numbers.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"rows={len(rows)} failures={len(failures)} skipped={len(skipped)} figures={len(figs)}")
    for f in failures[:20]:
        print("FAIL", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())