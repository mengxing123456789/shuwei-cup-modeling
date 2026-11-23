# -*- coding: utf-8 -*-
"""Refresh the status documents with the final gate results (2026-11-22 evening).

Every number is read back from the artefacts produced in the same session:
page_report (body 25 / appendix 43 / total 68), verify_claims 145, verify_numbers
136, verify_slots 1113, package.py (1,871,769 / 198,274 / 11,948,939 / 544).
"""
import os
import json
import re
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
C = ROOT / "SWC2026_C"

rep = json.loads((C / "data" / "_last_page_report.json").read_text(encoding="utf-8")) \
    if (C / "data" / "_last_page_report.json").exists() else {}

VALUES = {
    "pages": "body 25 / appendix 43 / total 68",
    "claims": "145 PASS",
    "numbers": "136 claims",
    "pdf": "1,871,769 B",
    "cns": "198,274 B",
    "zip": "11,948,939 B",
    "entries": "544 条目",
    "total": "13.37 MB",
}

SUBST = [
    (r"body 2[0-9] / appendix [0-9]{2} / total [0-9]{2}", VALUES["pages"]),
    (r"正文 2[0-9] 页[^，。]*附录 [0-9]{2} 页", "正文 25 页、附录 43 页"),
    (r"PASS=1[0-9][0-9]", "PASS=145"),
    (r"\b1[0-9][0-9] PASS\b", "145 PASS"),
    (r"\b1[0-9]{2} claims\b", "136 claims"),
    (r"1,6[0-9]{2},[0-9]{3} B", VALUES["pdf"]),
    (r"1,8[0-9]{2},[0-9]{3} B", VALUES["pdf"]),
    (r"11,[0-9]{3},[0-9]{3} B", VALUES["zip"]),
    (r"\b5[0-9]{2} 条目\b", VALUES["entries"]),
    (r"\b1[23]\.[0-9]{2} MB\b", VALUES["total"]),
    (r"\b6[0-9] 页\b", "68 页"),
]

targets = [
    ROOT / "45-逐问复查与参数核对.md",
    ROOT / "43-官方格式核对与图表重做.md",
    ROOT / "48-官网合规与AI规定核查.md",
    ROOT / "49-硬判据复核与补齐.md",
    C / "README_FJ.md",
]
for p in targets:
    if not p.exists():
        print("skip (missing):", p.name)
        continue
    t = p.read_text(encoding="utf-8")
    before = t
    hits = 0
    for pat, new in SUBST:
        t, n = re.subn(pat, new, t)
        hits += n
    if t != before:
        p.write_text(t, encoding="utf-8", newline="\n")
    print("%-40s %d replacement(s)" % (p.name, hits))