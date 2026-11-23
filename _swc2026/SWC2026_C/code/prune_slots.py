# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""prune_slots.py -- keep only the number slots that the paper actually uses.

slots.tex is generated with every slot the data files can produce (1,548). The
coverage audit (audit/check_slots.py) records which 570 are referenced by
main.tex or any table. This script rewrites slots.tex with only those, after
copying the full file to slots.full.tex. Re-running code/fill_numbers.py
regenerates the full file, so pruning is a final packaging step, not a source
change.
"""
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOTS = os.path.join(ROOT, "slots.tex")
FULL = os.path.join(ROOT, "slots.full.tex")
REPORT = os.path.join(ROOT, "audit", "slots_report.json")
DEF = re.compile(r"\\newcommand\{\\(slot[A-Za-z0-9]+)\}\{")


def main():
    report = json.load(open(REPORT, encoding="utf-8"))
    used = set(report["used"])
    lines = open(SLOTS, encoding="utf-8").read().splitlines()
    defs = set()
    for line in lines:
        m = DEF.match(line)
        if m:
            defs.add(m.group(1))
    # slots that only the audit scripts read must survive pruning, otherwise
    # verify_claims.py loses the numbers it cross-checks against the PDF text
    audit = open(os.path.join(os.path.dirname(ROOT), "audit", "verify_claims.py"),
                 encoding="utf-8", errors="ignore").read()
    extra = set("slot" + x for x in re.findall(r"[\"']([A-Za-z][A-Za-z0-9]+)[\"']", audit)
                if "slot" + x in defs)
    extra |= set("slot" + x for x in re.findall(r"\\slot([A-Za-z0-9]+)", audit)
                 if "slot" + x in defs)
    used |= extra
    header = []
    i = 0
    while i < len(lines) and not DEF.match(lines[i]):
        header.append(lines[i])
        i += 1
    out = list(header)
    buf = []
    kept = dropped = 0
    for line in lines[i:]:
        m = DEF.match(line)
        if m:
            if m.group(1) in used:
                out.extend(buf)
                out.append(line)
                kept += 1
            else:
                dropped += 1
            buf = []
        else:
            buf.append(line)
    if not os.path.exists(FULL):
        shutil.copyfile(SLOTS, FULL)
    open(SLOTS, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("kept", kept, "dropped", dropped, "full backup", FULL)


if __name__ == "__main__":
    main()