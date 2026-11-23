# -*- coding: utf-8 -*-
"""Refresh the three AIGC proxy rows to the values measured after the last edits."""
import io
from pathlib import Path

P = Path(r"48-官网通知逐条核对与AIGC风险.md")

REPS = [
    ("| 破折号 | 1.734 | 0.688 | 1.976 | within |",
     "| 破折号 | 1.712 | 0.688 | 1.976 | within |"),
    ("| 分号 `;` | 0.816 | 1.503 | 2.605 | **within** |",
     "| 分号 `;` | 0.906 | 1.503 | 2.605 | **within** |"),
    ("| `first/second/third` | 1.632 | 0.993 | 1.616 | **超上限 1.01 倍** |",
     "| `first/second/third` | 1.611 | 0.993 | 1.616 | within max |"),
    ("`first/second/third` 的 1.632 是**原始计数**，其中时间单位占 1.122/千词、名词序数占 0.510/千词、**话语序数（First,/Second,/Third,）为 0.000**（已清零）。",
     "`first/second/third` 的 1.611 是**原始计数**，其中时间单位占 1.208/千词、名词序数占 0.403/千词、**话语序数（First,/Second,/Third,）为 0.000**（已清零）。"),
    ("| C | 话语序数 `First,/Second,/Third,` 清零、名词序数减量 | 话语序数 **0**；原始计数 1.632（时间单位占大头） |",
     "| C | 话语序数 `First,/Second,/Third,` 清零、名词序数减量 | 话语序数 **0**；原始计数 1.611（时间单位占 1.208） |"),
    ("- 分号由 4.381 降到 0.816（8 处，69 → 8），落在人类均值与上限之间；",
     "- 分号由 4.381 降到 0.906（9 处，69 → 9），落在人类均值与上限之间；"),
    ("| B | 句内分号拆句（69 → 8 处） | **4.381 → 0.816**，回到人类上限内 |",
     "| B | 句内分号拆句（69 → 9 处） | **4.381 → 0.906**，回到人类上限内 |"),
    ("破折号 1.734 仍高于均值但在上限内", "破折号 1.712 仍高于均值但在上限内"),
]


def main():
    t = io.open(P, encoding="utf-8").read()
    hit = 0
    for a, b in REPS:
        n = t.count(a)
        print(n, a[:44])
        if n:
            t = t.replace(a, b)
            hit += n
    io.open(P, "w", encoding="utf-8", newline="\n").write(t)
    print("replaced", hit)


if __name__ == "__main__":
    main()
