#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 md 文件首行的 `BYTES <n>` 重算到自洽（从磁盘现读，不手写）。

用法：
    python code/fix_bytes.py out/01-model.md

为什么需要它：md 的首行要写自己的字节数，手写必然差几个字节；
这里读盘 → 改首行 → 再读盘，迭代到不动点（换行一律 LF，写 bytes 不写 text，
避开 Windows 的 CRLF 转换让字节数永不收敛 —— 与 fetch_annex.render 同一套做法）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAT = re.compile(r"^BYTES\s+(\d+)\s*$")


def fix(path: Path) -> int:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.split("\n")
    if not lines or not PAT.match(lines[0].strip()):
        raise SystemExit(f"[fix_bytes] {path} 首行不是 `BYTES <n>`：{lines[0]!r}")
    n = 0
    for _ in range(12):
        lines[0] = f"BYTES {n}"
        body = "\n".join(lines).encode("utf-8")
        if len(body) == n:
            path.write_bytes(body)
            back = len(path.read_bytes())
            if back != n:
                raise SystemExit(f"[fix_bytes] 写回后不一致：声明 {n}，实际 {back}")
            return back
        n = len(body)
    raise SystemExit("[fix_bytes] 12 次迭代未收敛")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法: python code/fix_bytes.py <md 路径>")
    p = Path(sys.argv[1])
    if not p.is_absolute():
        p = ROOT / p
    size = fix(p)
    print(f"[fix_bytes] {p.name}  BYTES {size}  （已读盘复核）")
