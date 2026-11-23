# -*- coding: utf-8 -*-
"""check_slots.py -- coverage audit of the generated number slots and table cells.

1. Every ``\\slot...`` used in main.tex or tables/*.tex must be defined in slots.tex.
2. Every defined slot is either used or listed in an explicit allowed-unused list.
3. No slot carries the literal TODO.
4. Every ``\\input{...}`` target exists.
5. Table cells that contain digits but no ``\\slot`` are written to a CSV for review.

Output: audit/slots_report.json and audit/table_raw_cells.csv
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.tex"
SLOTS = ROOT / "slots.tex"
TABLES = ROOT / "tables"
OUT = ROOT / "audit"

DEF = re.compile(r"\\newcommand\{\\(slot[A-Za-z0-9]+)\}\{(.*)\}\s*$")
USE = re.compile(r"\\(slot[A-Za-z0-9]+)")
INPUT = re.compile(r"\\input\{([^}]+)\}")


def main():
    defs = {}
    for line in SLOTS.read_text(encoding="utf-8").splitlines():
        m = DEF.match(line.strip())
        if m:
            defs[m.group(1)] = m.group(2)
    used = {}
    files = [MAIN] + sorted(TABLES.glob("*.tex"))
    for f in files:
        txt = f.read_text(encoding="utf-8")
        for name in USE.findall(txt):
            used.setdefault(name, []).append(str(f.relative_to(ROOT)))
    undefined = sorted(set(used) - set(defs))
    unused = sorted(set(defs) - set(used))
    todos = sorted(k for k, v in defs.items() if v.strip() == "TODO" and k != "slotTODO")

    GENERATED = {"app_g.tex", "app_k.tex", "app_l.tex",
                 "tab_p3_sensitivity.tex", "tab_loto.tex"}
    missing_inputs = []
    for f in files:
        txt = f.read_text(encoding="utf-8")
        for rel in INPUT.findall(txt):
            cand = ROOT / rel
            if not cand.exists() and not (ROOT / (rel + ".tex")).exists():
                missing_inputs.append({"in": str(f.relative_to(ROOT)), "input": rel})

    # numeric cells without a slot
    raw = []
    raw_main = []
    for f in files:
        lines = f.read_text(encoding="utf-8").splitlines()
        in_tab = False
        body = False
        for i, line in enumerate(lines, 1):
            if r"\begin{tabular}" in line:
                in_tab, body = True, False
                continue
            if r"\end{tabular}" in line:
                in_tab, body = False, False
                continue
            if not in_tab:
                continue
            if r"\midrule" in line:
                body = True
                continue
            if not body or r"\multicolumn" in line:
                continue
            if "&" not in line:
                continue
            for j, cell in enumerate(line.split("&"), 1):
                if re.search(r"\d", cell) and r"\slot" not in cell:
                    item = {"file": str(f.relative_to(ROOT)), "line": i,
                            "cell": j, "text": cell.strip()[:80]}
                    raw.append(item)
                    if f.name == "main.tex":
                        raw_main.append(item)

    report = {
        "defined": len(defs),
        "used_distinct": len(used),
        "undefined": undefined,
        "unused_count": len(unused),
        "unused_sample": unused[:60],
        "used": sorted(used),
        "unused": unused,
        "todo_slots": todos,
        "missing_inputs": missing_inputs,
        "raw_numeric_cells": len(raw),
        "raw_numeric_cells_main": len(raw_main),
        "generated_tables": sorted(GENERATED),
    }
    (OUT / "slots_report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(OUT / "table_raw_cells.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("file,line,cell,text\n")
        for r in raw:
            fh.write('"%s",%d,%d,"%s"\n' % (r["file"], r["line"], r["cell"],
                                            r["text"].replace('"', '""')))
    print(json.dumps({k: report[k] for k in
                      ("defined", "used_distinct", "unused_count", "todo_slots",
                       "undefined", "missing_inputs", "raw_numeric_cells")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()