#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\u6b63\u6587\u81ea\u68c0\uff1a\u81ea\u6307\u6570\u5b57\u3001\u53e3\u5f84\u6807\u7b7e\u3001\u9644\u5f55\u6307\u9488\u3001\u8868\u683c\u5217\u6570\u3002

\u7528\u6cd5\uff1a
    python code/check_md.py out/01-model.md

\u4e09\u9053\u68c0\u67e5\uff0c\u4efb\u4e00\u4e0d\u8fc7\u5c31 FAIL\uff1a
  R1 \u81ea\u6307\u6570\u5b57 \u2014\u2014 \u6b63\u6587\u4e0d\u8bb8\u51fa\u73b0\u300c\u672c\u6587 N \u4e2a\u300d\u300c\u5171 N \u884c\u300d\u300cN \u4e2a\u7b26\u53f7\u300d\u8fd9\u7c7b
     \u7531\u4ea7\u7269\u81ea\u5df1\u51b3\u5b9a\u7684\u503c\uff08\u5b57\u8282\u6570\u7531 fix_bytes.py \u73b0\u8bfb\uff0c\u884c\u6570\u7531 gen_appendix.py \u73b0\u7b97\uff09\u3002
  R2 \u53e3\u5f84\u6807\u7b7e \u2014\u2014 \u6bcf\u5904\u300c\u663e\u8457\u300d\u9644\u8fd1 60 \u5b57\u5185\u5fc5\u987b\u51fa\u73b0 single/diff/trend \u4e4b\u4e00\u3002
  R3 \u9644\u5f55\u6307\u9488 \u2014\u2014 \u6b63\u6587\u5fc5\u987b\u6070\u597d\u4e00\u6b21\u6307\u5411\u9644\u5f55 A\uff0c\u4e14\u9644\u5f55 A \u5b58\u5728\u3002
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SELF_REF = [
    "\u672c\u6587\\s*\\d+\\s*\u4e2a",
    "\u672c\u6587\u5171\\s*\\d+",
    "\u5171\\s*\\d+\\s*\u884c",
    "\\d+\\s*\u4e2a\u7b26\u53f7",
    "\u811a\u672c\\s*\\d+\\s*\u5b57\u8282",
    "\u6587\u4ef6\\s*\\d+\\s*\u5b57\u8282",
    "\u5168\u6587\\s*\\d+\\s*\u5b57",
]
PATH_TAGS = ("single", "diff", "trend")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out" / "01-model.md"
    if not path.is_absolute():
        path = ROOT / path
    text = path.read_text(encoding="utf-8")
    fails: list[str] = []

    # R1
    for pat in SELF_REF:
        for m in re.finditer(pat, text):
            line = text[: m.start()].count("\n") + 1
            fails.append(f"R1 \u81ea\u6307\u6570\u5b57 @L{line}: {text[m.start():m.end()]!r}")

    # R2
    for m in re.finditer("\u663e\u8457", text):
        lo = max(0, m.start() - 60)
        window = text[lo : m.start() + 60]
        if not any(t in window for t in PATH_TAGS):
            line = text[: m.start()].count("\n") + 1
            fails.append(f"R2 \u663e\u8457\u672a\u6807\u8def\u5f84 @L{line}: ...{window[50:80]}...")

    # R3
    n_ptr = text.count("\u9644\u5f55 A")
    if n_ptr < 2:
        fails.append(f"R3 \u9644\u5f55 A \u6307\u9488\u4e0d\u8db3\uff08\u51fa\u73b0 {n_ptr} \u6b21\uff0c\u6b63\u6587+\u6807\u9898\u5e94 >= 2\uff09")
    if "## \u9644\u5f55 A" not in text:
        fails.append("R3 \u7f3a\u9644\u5f55 A \u6807\u9898")

    # \u9996\u672b\u884c
    lines = text.split("\n")
    if not re.match(r"^BYTES\s+\d+\s*$", lines[0].strip()):
        fails.append(f"\u9996\u884c\u4e0d\u662f BYTES <n>: {lines[0]!r}")
    if "VERDICT: PASS" not in text and "VERDICT: FAIL" not in text:
        fails.append("\u7f3a VERDICT \u884c")
    if path.stat().st_size == 0:
        fails.append("\u6587\u4ef6\u4e3a 0 \u5b57\u8282")

    for f in fails:
        print("  FAIL", f)
    print(f"{len(fails)} failures")
    print("PASS" if not fails else "FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
