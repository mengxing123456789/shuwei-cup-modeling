#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\u4ece code/model_skeleton.py::SYMBOLS \u751f\u6210 out/01-model.md \u7684\u9644\u5f55 A \u8868\u683c\u3002

\u7528\u6cd5\uff1a
    python code/gen_appendix.py            # \u53ea\u6253\u5370
    python code/gen_appendix.py --write    # \u5c31\u5730\u66ff\u6362 md \u91cc <!-- SYMBOLS:BEGIN/END --> \u4e4b\u95f4

\u4e3a\u4ec0\u4e48\u8981\u6709\u5b83\uff1a\u7b26\u53f7\u8868\u4e00\u7b26\u53f7\u4e00\u4e49\uff0c\u624b\u6284\u5fc5\u7136\u6f02\uff08\u6539\u540d\u3001\u6539\u91cf\u7ea7\u3001\u6539\u5355\u4f4d\uff09\u3002
\u8fd9\u91cc\u8ba9 md \u7684\u9644\u5f55 A \u5b8c\u5168\u7531 SYMBOLS \u751f\u6210 \u2014\u2014 \u6539\u7b26\u53f7\u53ea\u6539 model_skeleton.py \u4e00\u5904\uff0c
\u518d\u8dd1\u4e00\u6b21\u672c\u811a\u672c\uff0c\u9644\u5f55 A \u81ea\u52a8\u8ddf\u4e0a\u3002\u884c\u6570\u3001\u6761\u6570\u4e00\u5f8b\u73b0\u7b97\uff0c\u4e0d\u5199\u6b7b\u5728\u6b63\u6587\u91cc\u3002
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
    head = "| \u7b26\u53f7 | \u542b\u4e49 | \u5355\u4f4d | \u7c7b\u522b | \u91cf\u7ea7\uff08\u5b9e\u6d4b\uff09 | \u7528\u5728 |\n|---|---|---|---|---|---|"
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
        raise SystemExit(f"[gen_appendix] \u672a\u627e\u5230\u6807\u8bb0 {BEGIN} / {END}")
    new = text[: i + len(BEGIN)] + "\n" + body + "\n" + text[j:]
    MD.write_bytes(new.encode("utf-8"))
    print(f"[gen_appendix] \u5df2\u66ff\u6362\u9644\u5f55 A\uff1a{len(MS.SYMBOLS)} \u884c\uff08\u73b0\u7b97\uff0c\u672a\u5199\u6b7b\uff09")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
