# -*- coding: utf-8 -*-
"""Sync the delivery numbers in the two audit reports and the support-package
README after the contents-page and pipeline-figure pass."""
import io

EDITS = {
    r"43-官方格式核对与图表重做.md": [
        ("1,889,011 B   66 页 (body 24 / appendix 42)",
         "1,996,415 B   67 页 (body 25 / appendix 42)"),
        ("1,889,011 B   66 页 (body 24 / appendix 42)",
         "1,996,415 B   67 页 (body 25 / appendix 42)"),
        ("11,971,236 B   544 条目", "12,077,269 B   546 条目"),
        ("11,971,236 B   544 条目 (11.42 MB)", "12,077,269 B   546 条目 (11.52 MB)"),
        ("13.41 MB", "13.61 MB"),
    ],
    r"45-逐问复查与参数核对.md": [
        ("**626** 条（全量 1,548，见 §3），正文与表格使用 **620** 条",
         "**626** 条（全量 1,548，见 §3），正文与表格使用 **619** 条"),
        ("**626 条**（正文/表格用 620 条 + 审计脚本交叉核对用的 6 条）",
         "**626 条**（正文/表格用 619 条 + 审计脚本交叉核对用的 7 条）"),
        ("626 defined / 620 used / 6 audit-only",
         "626 defined / 619 used / 7 audit-only"),
        ("**1,889,011 B / 66 页**（正文 24 / 附录 42）",
         "**1,996,415 B / 67 页**（正文 25 / 附录 42）"),
        ("**11,971,236 B / 544 条目**，合计 **13.41 MB**",
         "**12,077,269 B / 546 条目**，合计 **13.61 MB**"),
    ],
    r"README_FJ.md": [
        ("333 scripts; see the run order below", "342 scripts; see the run order below"),
    ],
}

for path, pairs in EDITS.items():
    s = io.open(path, encoding="utf-8").read()
    n = 0
    for a, b in pairs:
        if a in s:
            s = s.replace(a, b)
            n += 1
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print(path, "replacements:", n)
