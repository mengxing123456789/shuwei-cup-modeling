#!/usr/bin/env python
"""对账骨架：正文里印出来的每个数，都要能回到 data/*.json 里的一个键。

这里只放**结构**，没有 claim —— 空着也必须能跑通并打印 0 claims / PASS，
这样"没填"不会被误读成"没问题"（真论文里，claims 为 0 等于没对上账，评审会判 FAIL）。

三种断言写法：
    add("键名", json里的值, "正文里印的字符串")           # 逐点绑，容差按印刷小数位
    RANGES = [(名字, (实测min, 实测max), ("印的下界", "印的上界"))]   # 会漂的量绑区间
    # 派生量在源码里算：1 - auc、1 - ci[1]、sum(sorted(w)[:5])*100
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"


def _tol(expected: float, needle: str) -> float:
    """容差按**印刷的小数位**定：印 3.1 就容 0.05，印 96.4 就容 0.964。"""
    dp = len(needle.split(".")[1]) if "." in needle else 0
    return max(0.011, abs(expected) * 0.01, 0.5000001 * 10 ** (-dp))


def main() -> int:
    claims: list[tuple[str, float, str]] = []
    fails: list[tuple] = []
    tex = TEX.read_text(encoding="utf-8")

    def add(path: str, value: float, needle: str) -> None:
        claims.append((path, value, needle))

    # ---- 在这里填 claim（示例被注释掉，别照抄键名） ----
    # j = json.loads((ROOT / "data" / "model.json").read_text(encoding="utf-8"))
    # add("model.auc", j["auc"], "0.705")

    RANGES: list[tuple[str, tuple[float, float], tuple[str, str]]] = [
        # ("timing.end_band", (7.55, 7.71), ("7.4", "10.5")),
    ]

    print(f"{len(claims)} claims, {len(RANGES)} ranges (both empty = nothing is bound yet)")
    for path, value, needle in claims:
        if not re.search(r"(?<![\d.])" + re.escape(needle) + r"(?![\d])", tex):
            fails.append((path, value, needle, "not printed"))
    for path, (lo_m, hi_m), (lo_p, hi_p) in RANGES:
        if float(lo_p) > lo_m + 1e-9 or float(hi_p) < hi_m - 1e-9:
            fails.append((path, (lo_m, hi_m), (lo_p, hi_p), "printed band too narrow"))
    for f in fails:
        print("  FAIL", f)
    print("PASS" if not fails else "FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
