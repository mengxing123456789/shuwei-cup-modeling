"""Move a `figure` block that carries a given label from one file to another.

Line based and balance counted, same discipline as _move_tables_safe.py: find the
label, walk back to `\\begin{figure}`, walk forward counting nested
begin/end figure pairs, cut only when balanced, and refuse to write when the
source would shrink implausibly.
"""

import io
import sys

SRC = "tables/app_k.tex"
DST = "main.tex"

# label -> anchor text in DST (the block is inserted immediately after the line
# containing the anchor, plus a blank line)
JOBS = [
    (
        "fig:phase",
        "\\input{tables/tab_p3_scorecard.tex}",
    ),
]


def cut_block(lines, label):
    lab = "\\label{%s}" % label
    li = None
    for i, l in enumerate(lines):
        if lab in l:
            li = i
            break
    if li is None:
        raise SystemExit("label not found: " + label)
    start = None
    for i in range(li, -1, -1):
        if lines[i].strip().startswith("\\begin{figure}"):
            start = i
            break
        if lines[i].strip().startswith("\\end{figure}"):
            raise SystemExit("crossed an end before begin: " + label)
    if start is None:
        raise SystemExit("no begin for " + label)
    depth = 0
    end = None
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s.startswith("\\begin{figure}"):
            depth += 1
        elif s.startswith("\\end{figure}"):
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        raise SystemExit("unbalanced: " + label)
    stop = end + 1
    while stop < len(lines) and lines[stop].strip() == "":
        stop += 1
    block = lines[start:end + 1]
    del lines[start:stop]
    return block


def main():
    src = io.open(SRC, encoding="utf-8").read().splitlines(keepends=True)
    dst = io.open(DST, encoding="utf-8").read().splitlines(keepends=True)

    moved = []
    for label, anchor in JOBS:
        block = cut_block(src, label)
        moved.append((label, block))
        hit = None
        for i, l in enumerate(dst):
            if anchor in l:
                hit = i
                break
        if hit is None:
            raise SystemExit("anchor not found: " + anchor)
        dst[hit + 1 : hit + 1] = ["\n"] + block + ["\n"]

    new_src = "".join(src)
    new_dst = "".join(dst)
    if len(new_src) < 0.6 * len(io.open(SRC, encoding="utf-8").read()):
        raise SystemExit("guard: source shrank too much")

    io.open(SRC, "w", encoding="utf-8", newline="\n").write(new_src)
    io.open(DST, "w", encoding="utf-8", newline="\n").write(new_dst)
    for label, block in moved:
        print("moved %-14s %d lines" % (label, len(block)))


if __name__ == "__main__":
    main()
