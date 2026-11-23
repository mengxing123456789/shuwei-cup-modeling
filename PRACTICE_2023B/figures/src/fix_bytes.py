#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\u628a md \u6587\u4ef6\u9996\u884c\u7684 `BYTES <n>` \u91cd\u7b97\u5230\u81ea\u6d3d\uff08\u4ece\u78c1\u76d8\u73b0\u8bfb\uff0c\u4e0d\u624b\u5199\uff09\u3002

\u7528\u6cd5\uff1a
    python code/fix_bytes.py out/01-model.md

\u4e3a\u4ec0\u4e48\u9700\u8981\u5b83\uff1amd \u7684\u9996\u884c\u8981\u5199\u81ea\u5df1\u7684\u5b57\u8282\u6570\uff0c\u624b\u5199\u5fc5\u7136\u5dee\u51e0\u4e2a\u5b57\u8282\uff1b
\u8fd9\u91cc\u8bfb\u76d8 \u2192 \u6539\u9996\u884c \u2192 \u518d\u8bfb\u76d8\uff0c\u8fed\u4ee3\u5230\u4e0d\u52a8\u70b9\uff08\u6362\u884c\u4e00\u5f8b LF\uff0c\u5199 bytes \u4e0d\u5199 text\uff0c
\u907f\u5f00 Windows \u7684 CRLF \u8f6c\u6362\u8ba9\u5b57\u8282\u6570\u6c38\u4e0d\u6536\u655b \u2014\u2014 \u4e0e fetch_annex.render \u540c\u4e00\u5957\u505a\u6cd5\uff09\u3002
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
        raise SystemExit(f"[fix_bytes] {path} \u9996\u884c\u4e0d\u662f `BYTES <n>`\uff1a{lines[0]!r}")
    n = 0
    for _ in range(12):
        lines[0] = f"BYTES {n}"
        body = "\n".join(lines).encode("utf-8")
        if len(body) == n:
            path.write_bytes(body)
            back = len(path.read_bytes())
            if back != n:
                raise SystemExit(f"[fix_bytes] \u5199\u56de\u540e\u4e0d\u4e00\u81f4\uff1a\u58f0\u660e {n}\uff0c\u5b9e\u9645 {back}")
            return back
        n = len(body)
    raise SystemExit("[fix_bytes] 12 \u6b21\u8fed\u4ee3\u672a\u6536\u655b")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("\u7528\u6cd5: python code/fix_bytes.py <md \u8def\u5f84>")
    p = Path(sys.argv[1])
    if not p.is_absolute():
        p = ROOT / p
    size = fix(p)
    print(f"[fix_bytes] {p.name}  BYTES {size}  \uff08\u5df2\u8bfb\u76d8\u590d\u6838\uff09")
