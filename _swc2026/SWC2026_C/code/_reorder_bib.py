# -*- coding: utf-8 -*-
"""Reorder \\bibitem blocks so the list follows first-citation order (spec 一.5).

The spec says the reference list is numbered in the order the citations appear in
the text.  Our list was written in a different order, which is checkable by a
reviewer in one pass, so we sort the blocks to match the first \\cite occurrence
and renumber implicitly (thebibliography numbers by position).
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.tex"


def main():
    apply = "--apply" in sys.argv
    text = io.open(MAIN, encoding="utf-8").read()

    start = text.find(r"\begin{thebibliography}")
    end = text.find(r"\end{thebibliography}")
    if start < 0 or end < 0:
        print("ABORT: bibliography not found")
        return 1
    body = text[start:end]

    # split into preamble (up to first bibitem) and blocks
    first = body.find(r"\bibitem")
    preamble = body[:first]
    rest = body[first:]
    blocks = re.split(r"(?=\\bibitem\{)", rest)
    blocks = [b for b in blocks if b.strip()]
    keys = [re.match(r"\\bibitem\{([^}]*)\}", b).group(1) for b in blocks]
    print("current order:", keys)

    # first-citation order over the whole document
    order = []
    for m in re.finditer(r"\\cite\{([^}]*)\}", text):
        for k in m.group(1).split(","):
            k = k.strip()
            if k and k not in order:
                order.append(k)
    print("citation order:", order)

    missing = [k for k in keys if k not in order]
    if missing:
        print("WARNING: bibitems never cited:", missing)
    new_keys = [k for k in order if k in keys] + missing
    if new_keys == keys:
        print("already in citation order; nothing to do")
        return 0
    by_key = dict(zip(keys, blocks))
    new_blocks = [by_key[k] for k in new_keys]
    new_body = preamble + "".join(new_blocks)
    new_text = text[:start] + new_body + text[end:]
    print("new order:", new_keys)
    print("bytes %d -> %d" % (len(text), len(new_text)))
    if not apply:
        print("dry run; pass --apply to write")
        return 0
    io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new_text)
    print("written", MAIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
