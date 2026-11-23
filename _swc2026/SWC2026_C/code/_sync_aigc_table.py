# -*- coding: utf-8 -*-
"""Update the AIGC proxy table in report 48 to the post-rewrite values."""
import io
from pathlib import Path

P = Path(r"48-官网通知逐条核对与AIGC风险.md")

REPS = [
    ("| 分号 | 4.381 | 1.503 | 2.605 | 超上限 1.68 倍 |",
     "| 分号 | 0.906 | 1.503 | 2.605 | within |"),
    ("| `first/second/third` | 4.585 | 0.993 | 1.616 | 超上限 2.84 倍 |",
     "| `first/second/third` | 1.611 | 0.993 | 1.616 | above mean, within max |"),
    ("| `therefore/thus/hence` | 0.713 | 0.255 | 0.539 | 超上限 1.32 倍 |",
     "| `therefore/thus/hence` | 0.000 | 0.255 | 0.539 | within |"),
    ("| `not X but Y` | 0.102 | 0.005 | 0.026 | 超上限 3.9 倍 |",
     "| `not X but Y` | 0.000 | 0.005 | 0.026 | within |"),
    ("| 破折号 em dash | 1.732 | 0.688 | 1.976 | above mean |",
     "| 破折号 em dash | 1.712 | 0.688 | 1.976 | above mean, within max |"),
    ("| 句长变异系数 CV | 0.561 | 1.197 | 2.161 | within |",
     "| 句长变异系数 CV | 0.561 | 1.197 | 2.161 | within |"),
    ("| 平均句长（词） | 24.416 | 43.327 | 98.479 | 偏均匀 |",
     "| 平均句长（词） | 24.431 | 43.327 | 98.479 | 偏均匀 |"),
]


def main():
    t = io.open(P, encoding="utf-8").read()
    hit = 0
    for a, b in REPS:
        n = t.count(a)
        print(n, a[:36])
        if n:
            t = t.replace(a, b)
            hit += n
    io.open(P, "w", encoding="utf-8", newline="\n").write(t)
    print("replaced", hit)


if __name__ == "__main__":
    main()
