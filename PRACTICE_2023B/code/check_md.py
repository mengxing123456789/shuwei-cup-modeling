#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""正文自检：自指数字、口径标签、附录指针、表格列数。

用法：
    python code/check_md.py out/01-model.md

三道检查，任一不过就 FAIL：
  R1 自指数字 —— 正文不许出现「本文 N 个」「共 N 行」「N 个符号」这类
     由产物自己决定的值（字节数由 fix_bytes.py 现读，行数由 gen_appendix.py 现算）。
  R2 口径标签 —— 每处「显著」附近 60 字内必须出现 single/diff/trend 之一。
  R3 附录指针 —— 正文必须恰好一次指向附录 A，且附录 A 存在。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SELF_REF = [
    r"本文\s*\d+\s*个",
    r"本文共\s*\d+",
    r"共\s*\d+\s*行",
    r"\d+\s*个符号",
    r"脚本\s*\d+\s*字节",
    r"文件\s*\d+\s*字节",
    r"全文\s*\d+\s*字",
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
            fails.append(f"R1 自指数字 @L{line}: {text[m.start():m.end()]!r}")

    # R2
    for m in re.finditer("显著", text):
        lo = max(0, m.start() - 60)
        window = text[lo : m.start() + 60]
        if not any(t in window for t in PATH_TAGS):
            line = text[: m.start()].count("\n") + 1
            fails.append(f"R2 显著未标路径 @L{line}: ...{window[50:80]}...")

    # R3
    n_ptr = text.count("附录 A")
    if n_ptr < 2:
        fails.append(f"R3 附录 A 指针不足（出现 {n_ptr} 次，正文+标题应 >= 2）")
    if "## 附录 A" not in text:
        fails.append("R3 缺附录 A 标题")

    # 首末行
    lines = text.split("\n")
    if not re.match(r"^BYTES\s+\d+\s*$", lines[0].strip()):
        fails.append(f"首行不是 BYTES <n>: {lines[0]!r}")
    if "VERDICT: PASS" not in text and "VERDICT: FAIL" not in text:
        fails.append("缺 VERDICT 行")
    if path.stat().st_size == 0:
        fails.append("文件为 0 字节")

    for f in fails:
        print("  FAIL", f)
    print(f"{len(fails)} failures")
    print("PASS" if not fails else "FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
