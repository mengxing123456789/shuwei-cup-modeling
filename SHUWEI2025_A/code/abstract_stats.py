# -*- coding: utf-8 -*-
"""Abstract length / number-density report (the R-V07 numbers, measured locally).

    python code/abstract_stats.py

The gauntlet reads these from the PDF; this prints the same three quantities from
main.tex so the abstract can be trimmed without a rebuild.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    tex = (ROOT / "main.tex").read_text(encoding="utf-8")
    body = tex.split(r"\begin{abstract}")[1].split(r"\end{abstract}")[0]
    plain = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", body)
    plain = plain.replace("$", " ").replace("\\", " ")
    words = re.findall(r"[A-Za-z][A-Za-z\-]+", plain)
    nums = re.findall(r"\d+(?:\.\d+)?", plain)
    print(f"abstract words   : {len(words)}")
    print(f"abstract numbers : {len(nums)}")
    print(f"numbers per 100w : {100 * len(nums) / max(1, len(words)):.1f}")
    print(f"distinct numbers : {len(set(nums))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
