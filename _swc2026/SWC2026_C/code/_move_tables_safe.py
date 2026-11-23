"""Move whole `table` blocks out of main.tex into an appendix table file.

Line-based and balance-checked: it finds the `\\begin{table}` line that
precedes the requested label, walks forward counting nested
`\\begin{table}` / `\\end{table}` pairs, and only cuts when the counter returns
to zero. It refuses to write if the file would shrink by more than a guard.
"""

import io
import re
import sys

MAIN = "main.tex"
APPX = "tables/app_n.tex"

WANT = sys.argv[1:] or ["tab:negative", "tab:ablation"]
GUARD_LINES = 120  # refuse if more than this many lines would be removed


def find_block(lines, label):
    lab = "\\label{%s}" % label
    li = None
    for i, l in enumerate(lines):
        if lab in l:
            li = i
            break
    if li is None:
        raise SystemExit("label not found: %s" % label)
    # walk back to the begin
    start = None
    for i in range(li, -1, -1):
        if lines[i].strip().startswith("\\begin{table}"):
            start = i
            break
        if lines[i].strip().startswith("\\end{table}"):
            raise SystemExit("crossed an end before begin for %s" % label)
    if start is None:
        raise SystemExit("no begin for %s" % label)
    # walk forward with balance
    depth = 0
    end = None
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s.startswith("\\begin{table}"):
            depth += 1
        elif s.startswith("\\end{table}"):
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        raise SystemExit("unbalanced table for %s" % label)
    # swallow one trailing blank line
    stop = end + 1
    while stop < len(lines) and lines[stop].strip() == "" and stop <= end + 1:
        stop += 1
    return start, stop


def main():
    lines = io.open(MAIN, encoding="utf-8").read().splitlines(keepends=True)
    appx = io.open(APPX, encoding="utf-8").read()

    moved = []
    spans = []
    for label in WANT:
        a, b = find_block(lines, label)
        spans.append((a, b, label))
    spans.sort(reverse=True)

    removed = 0
    for a, b, label in spans:
        block = "".join(lines[a:b])
        removed += b - a
        moved.append((label, block))
        del lines[a:b]

    if removed > GUARD_LINES:
        raise SystemExit("guard tripped: would remove %d lines" % removed)

    new_main = "".join(lines)
    if len(new_main) < 0.85 * len(io.open(MAIN, encoding="utf-8").read()):
        raise SystemExit("guard tripped: file would shrink too much")

    io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new_main)

    add = ["\n\\subsection*{Tables moved out of the body}\n"]
    for label, block in moved:
        add.append(block.rstrip() + "\n\n")
    io.open(APPX, "w", encoding="utf-8", newline="\n").write(appx.rstrip() + "\n" + "".join(add))

    for label, block in moved:
        print("moved %-16s %d lines" % (label, block.count("\n")))
    print("main lines removed:", removed)


if __name__ == "__main__":
    main()
