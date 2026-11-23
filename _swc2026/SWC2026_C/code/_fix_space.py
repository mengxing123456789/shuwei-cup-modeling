"""Repair the spacing the mechanical rewrite left behind: ' ,' -> ',', '  ' -> ' '.

Only touches prose punctuation that follows a word character, so math like
'\\{\\,x\\,\\}' and '\\left[ , \\right]' is left alone.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"

RULES = [
    (re.compile(r"(?<=[A-Za-z0-9\)\}]) ,(?=\s)"), ","),
    (re.compile(r"(?<=[A-Za-z0-9\)\}]) ;(?=\s)"), ";"),
    (re.compile(r"(?<=[A-Za-z0-9\)\}]) \.(?=\s)"), "."),
    (re.compile(r"(?<=[a-z\)\}])  (?=[a-z])"), " "),
]


def main() -> int:
    apply = "--apply" in sys.argv
    text = io.open(TEX, encoding="utf-8").read()
    before = len(text)
    hits = []
    for pat, rep in RULES:
        for m in pat.finditer(text):
            line = text[: m.start()].count("\n") + 1
            hits.append((line, text[max(0, m.start() - 40) : m.start() + 25].replace("\n", " | ")))
        text = pat.sub(rep, text)
    print(f"candidates: {len(hits)}")
    for line, ctx in hits[:25]:
        print(f"  {line}: ...{ctx}...")
    if len(hits) > 25:
        print(f"  ... {len(hits)} total")
    print(f"bytes {before} -> {len(text)}")
    if apply:
        io.open(TEX, "w", encoding="utf-8", newline="\n").write(text)
        print("APPLIED")
    else:
        print("dry run (pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
