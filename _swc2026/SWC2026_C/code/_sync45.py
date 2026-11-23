# -*- coding: utf-8 -*-
"""One-off: refresh the headline numbers in 45-逐问复查与参数核对.md."""
import io

P = r"45-逐问复查与参数核对.md"
s = io.open(P, encoding="utf-8").read()

REP = [
    ("（2026-11-21 23:05 更新）", "（2026-11-22 10:05 更新）"),
    ("`slots.tex` 定义 **574** 条（精简前 1,548，见 §3），正文与表格使用 **570** 条",
     "`slots.tex` 定义 **582** 条（精简前 1,556，见 §3），正文与表格使用 **578** 条"),
    ("4. **137 条结构/文本断言**由", "4. **139 条结构/文本断言**由"),
    ("+ 122 条数值不变量 + 137 条结构断言", "+ 122 条数值不变量 + 139 条结构断言"),
    ("| `audit/verify_claims.py` | **137 PASS / 0 FAIL / 0 NA** |",
     "| `audit/verify_claims.py` | **139 PASS / 0 FAIL / 0 NA** |"),
    ("| `audit/check_slots.py` | 574 defined / 570 used / 4 audit-only / **0 undefined** / 0 missing inputs / main raw numeric cells **7** |",
     "| `audit/check_slots.py` | 582 defined / 578 used / 4 audit-only / **0 undefined** / 0 missing inputs / main raw numeric cells **7** |"),
    ("**槽清理**：`code/prune_slots.py` 把 `slots.tex` 从 1,548 条裁到 **574 条**（正文/表格用 570 条 + 审计脚本交叉核对用的 4 条），完整版备份在 `slots.full.tex`",
     "**槽清理**：`code/prune_slots.py` 把 `slots.tex` 从 1,556 条裁到 **582 条**（正文/表格用 578 条 + 审计脚本交叉核对用的 4 条），完整版备份在 `slots.full.tex`"),
    ("清理后 `audit/check_slots.py`：`defined 574 / used 570 / unused 4 / undefined 0 / missing_inputs 0`。",
     "清理后 `audit/check_slots.py`：`defined 582 / used 578 / unused 4 / undefined 0 / missing_inputs 0`。"),
    ("`prune_slots.py` 增加 audit keep-list，保留 574 条", "`prune_slots.py` 增加 audit keep-list，保留 582 条"),
    ("| 论文 | `CSWBMCM2634892.pdf` **1,617,520 B / 64 页** |",
     "| 论文 | `CSWBMCM2634892.pdf` **1,625,595 B / 66 页** |"),
    ("| 支撑包 | `CSWBMCM2634892fj.zip` **11,602,277 B / 431 条目**，合计 **12.62 MB** |",
     "| 支撑包 | `CSWBMCM2634892fj.zip` **11,701,431 B / 467 条目**，合计 **12.73 MB** |"),
    ("`SWC2026_C/slots.tex`（574 条）、`slots.full.tex`（1,548 条备份）",
     "`SWC2026_C/slots.tex`（582 条）、`slots.full.tex`（1,556 条备份）"),
]

n = 0
for a, b in REP:
    if a in s:
        s = s.replace(a, b)
        n += 1
    else:
        print("MISS:", a[:60])

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("replaced", n)
