#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 code/model_skeleton.py::SYMBOLS 生成 out/01-model.md 的附录 A 表格。

用法：
    python code/gen_appendix.py            # 只打印
    python code/gen_appendix.py --write    # 就地替换 md 里 <!-- SYMBOLS:BEGIN/END --> 之间

为什么要有它：符号表一符号一义，手抄必然漂（改名、改量级、改单位）。
这里让 md 的附录 A 完全由 SYMBOLS 生成 —— 改符号只改 model_skeleton.py 一处，
再跑一次本脚本，附录 A 自动跟上。行数、条数一律现算，不写死在正文里。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import model_skeleton as MS  # noqa: E402

MD = ROOT / "out" / "01-model.md"
BEGIN = "<!-- SYMBOLS:BEGIN -->"
END = "<!-- SYMBOLS:END -->"


def table() -> str:
    head = "| 符号 | 含义 | 单位 | 类别 | 量级（实测） | 用在 |\n|---|---|---|---|---|---|"
    rows = [f"| `{s}` | {m} | {u} | {k} | {g} | {w} |" for s, m, u, k, g, w in MS.SYMBOLS]
    return "\n".join([head] + rows)


def main() -> int:
    body = table()
    if "--write" not in sys.argv:
        print(body)
        return 0
    text = MD.read_text(encoding="utf-8")
    i, j = text.find(BEGIN), text.find(END)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"[gen_appendix] 未找到标记 {BEGIN} / {END}")
    new = text[: i + len(BEGIN)] + "\n" + body + "\n" + text[j:]
    MD.write_bytes(new.encode("utf-8"))
    print(f"[gen_appendix] 已替换附录 A：{len(MS.SYMBOLS)} 行（现算，未写死）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
