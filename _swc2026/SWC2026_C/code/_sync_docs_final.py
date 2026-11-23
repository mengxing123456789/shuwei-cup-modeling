# -*- coding: utf-8 -*-
"""One-off: refresh the headline numbers in the two summary documents after the
identifiability-robustness change (slots 1,557; claims 140; package 474 entries)."""
import io

DOC45 = r"45-逐问复查与参数核对.md"
DOC43 = r"43-官方格式核对与图表重做.md"

REP45 = [
    ("（2026-11-22 10:05 更新）", "（2026-11-22 10:15 更新）"),
    ("`slots.tex` 定义 **582** 条（精简前 1,556，见 §3），正文与表格使用 **578** 条",
     "`slots.tex` 定义 **584** 条（精简前 1,557，见 §3），正文与表格使用 **580** 条"),
    ("4. **139 条结构/文本断言**由", "4. **140 条结构/文本断言**由"),
    ("+ 122 条数值不变量 + 139 条结构断言", "+ 122 条数值不变量 + 140 条结构断言"),
    ("| `audit/verify_claims.py` | **139 PASS / 0 FAIL / 0 NA** |",
     "| `audit/verify_claims.py` | **140 PASS / 0 FAIL / 0 NA** |"),
    ("| `audit/check_slots.py` | 582 defined / 578 used / 4 audit-only",
     "| `audit/check_slots.py` | 584 defined / 580 used / 4 audit-only"),
    ("从 1,556 条裁到 **582 条**（正文/表格用 578 条", "从 1,557 条裁到 **584 条**（正文/表格用 580 条"),
    ("`defined 582 / used 578 / unused 4", "`defined 584 / used 580 / unused 4"),
    ("保留 582 条", "保留 584 条"),
    ("| 论文 | `CSWBMCM2634892.pdf` **1,625,595 B / 66 页** |",
     "| 论文 | `CSWBMCM2634892.pdf` **1,625,666 B / 66 页** |"),
    ("| 支撑包 | `CSWBMCM2634892fj.zip` **11,701,431 B / 467 条目**，合计 **12.73 MB** |",
     "| 支撑包 | `CSWBMCM2634892fj.zip` **11,731,658 B / 474 条目**，合计 **12.75 MB** |"),
    ("`SWC2026_C/slots.tex`（582 条）、`slots.full.tex`（1,556 条备份）",
     "`SWC2026_C/slots.tex`（584 条）、`slots.full.tex`（1,557 条备份）"),
]

REP43 = [
    ("verify_claims.py  PASS=139  FAIL=0  NA=0  total=139",
     "verify_claims.py  PASS=140  FAIL=0  NA=0  total=140"),
    ("paper   CSWBMCM2634892.pdf       1,625,595 B   66 页",
     "paper   CSWBMCM2634892.pdf       1,625,666 B   66 页"),
    ("package CSWBMCM2634892fj.zip     11,701,431 B   467 条目",
     "package CSWBMCM2634892fj.zip     11,731,658 B   474 条目"),
    ("total                               12.73 MB   (cap 20 MB)",
     "total                               12.75 MB   (cap 20 MB)"),
    ("支撑包 467 条目", "支撑包 474 条目"),
]

for path, rep in ((DOC45, REP45), (DOC43, REP43)):
    s = io.open(path, encoding="utf-8").read()
    hit = 0
    for a, b in rep:
        if a in s:
            s = s.replace(a, b)
            hit += 1
        else:
            print("MISS(%s): %s" % (path[-20:], a[:50]))
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print(path[-24:], "replaced", hit, "of", len(rep))
