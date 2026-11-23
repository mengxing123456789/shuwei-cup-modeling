# -*- coding: utf-8 -*-
"""Sync the gate table in 45-report to the current measured values."""
import io
import os
import re

P = r"E:\数学建模\_swc2026\45-逐问复查与参数核对.md"
t = io.open(P, encoding="utf-8").read()

REP = [
    ("| `page_report.py` | **body 25 / appendix 39 / total 64 / overfull 0 / undefined 0 / prose numerals 0** |",
     "| `page_report.py` | **body 25 / appendix 44 / total 69 / overfull 0 / undefined 0 / prose numerals 0** |"),
    ("| `audit/check_slots.py` | 589 defined / 584 used / 5 audit-only / **0 undefined** / 0 missing inputs / main raw numeric cells **7** |",
     "| `audit/check_slots.py` | 608 defined / 602 used / 6 audit-only / **0 undefined** / 0 missing inputs |"),
    ("| `audit/verify_claims.py` | **141 PASS / 0 FAIL / 0 NA** |",
     "| `audit/verify_claims.py` | **143 PASS / 0 FAIL / 0 NA** |"),
    ("| `code/verify_numbers.py` | **122 claims / 0 failed** |",
     "| `code/verify_numbers.py` | **136 claims / 0 failed** |"),
    ("| 论文 | `CSWBMCM2634892.pdf` **1,626,479 B / 66 页**（正文 25 / 附录 41） |",
     "| 论文 | `CSWBMCM2634892.pdf` **1,870,406 B / 69 页**（正文 25 / 附录 44） |"),
    ("| 支撑包 | `CSWBMCM2634892fj.zip` **11,851,144 B / 517 条目**，合计 **12.87 MB** |",
     "| 支撑包 | `CSWBMCM2634892fj.zip` **11,930,155 B / 536 条目**，合计 **13.18 MB** |"),
]
for a, b in REP:
    assert t.count(a) == 1, (t.count(a), a[:50])
    t = t.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("45 report synced:", len(t))
