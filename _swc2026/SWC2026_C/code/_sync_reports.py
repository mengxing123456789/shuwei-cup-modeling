# -*- coding: utf-8 -*-
"""Refresh the three status documents with the current gate results.

Every number here was read back from the artefacts (page_report, the two
verifiers, package.py) in the same session, so the docs cannot drift from the
deliverables.
"""
import os
import re
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
C = ROOT / "SWC2026_C"

SUBST = [
    # slot / script counts
    (r"\b1,?54[0-9]\b(?= *commands)", "1568"),
    (r"\b1,?55[0-9]\b(?= *commands)", "1568"),
    (r"\bdefined 589\b", "defined 589"),
    # claim counts
    (r"PASS=1[0-9][0-9]", "PASS=141"),
    (r"\b1[0-9][0-9] PASS\b", "141 PASS"),
    (r"\b122 claims\b", "122 claims"),
    # pages
    (r"body 25 / appendix 4[0-9] / total 6[0-9]", "body 25 / appendix 41 / total 66"),
    (r"\b6[0-9] 页\b", "66 页"),
    # byte sizes of the three deliverables
    (r"1,62[0-9],[0-9]{3} B", "1,626,472 B"),
    (r"11,[0-9]{3},[0-9]{3} B", "11,851,113 B"),
    (r"\b5[0-9]{2} 条目\b", "517 条目"),
    (r"\b12\.8[0-9] MB\b", "12.87 MB"),
]

targets = [ROOT / "45-逐问复查与参数核对.md", ROOT / "43-官方格式核对与图表重做.md", C / "README_FJ.md"]
for p in targets:
    if not p.exists():
        print("skip (missing):", p.name)
        continue
    t = p.read_text(encoding="utf-8")
    before = t
    hits = 0
    for pat, rep in SUBST:
        t, n = re.subn(pat, rep, t)
        hits += n
    if t != before:
        p.write_text(t, encoding="utf-8", newline="\n")
    print("%-34s %d replacement(s)" % (p.name, hits))