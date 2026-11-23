# -*- coding: utf-8 -*-
"""Set the first line of each out/*.md to the file's real byte count, to a fixed point.

The byte count depends on how many digits the count itself has, so the line is
rewritten until the reported value equals the on-disk size. Bytes are written with
newline="\\n" so the count does not shift under Windows newline translation.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def fix(path: pathlib.Path) -> tuple[int, int, int]:
    raw = path.read_bytes()
    lines = raw.decode("utf-8").split("\n")
    if not lines or not lines[0].startswith("BYTES"):
        return (0, len(raw), len(raw))
    body = "\n".join(lines[1:])
    reported = -1
    for _ in range(12):
        n = len(body.encode("utf-8")) + len(f"BYTES {reported}\n".encode("utf-8"))
        if n == reported:
            break
        reported = n
    text = f"BYTES {reported}\n{body}"
    path.write_bytes(text.encode("utf-8"))
    return (len(raw), reported, len(text.encode("utf-8")))


def main() -> int:
    total = 0
    for p in sorted(OUT.glob("*.md")):
        before, reported, after = fix(p)
        flag = "OK " if reported == after else "BAD"
        print(f"{flag} {p.name:20s} was {before:7d} -> {after:7d} (claims {reported})")
        total += 1
    print(f"{total} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
