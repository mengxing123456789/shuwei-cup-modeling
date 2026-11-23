"""Convert a page-breaking `table[H]` + `tabular` block into a `longtable`.

Two appendix tables are taller than a page and currently overflow the bottom
margin (Overfull \\vbox).  longtable lets them break across pages and repeat
their header, which is what the appendix needs.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"


def convert(path: Path, label: str, apply: bool) -> bool:
    text = io.open(path, encoding="utf-8").read()
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"\\label{{{label}}}":
            for j in range(i, -1, -1):
                if lines[j].strip().startswith("\\begin{table}"):
                    start = j
                    break
            end = None
            for k in range(i, len(lines)):
                if lines[k].strip() == "\\end{table}":
                    end = k
                    break
            if start is None or end is None:
                print(f"  {label}: could not bound the block")
                return False
            block = lines[start : end + 1]
            break
    else:
        print(f"  {label}: label not found")
        return False

    cap_idx = next(i for i, l in enumerate(block) if l.strip().startswith("\\caption{"))
    lab_idx = next(i for i, l in enumerate(block) if l.strip() == f"\\label{{{label}}}")
    tab_idx = next(i for i, l in enumerate(block) if l.strip().startswith("\\begin{tabular}"))
    spec = block[tab_idx].strip()[len("\\begin{tabular}"):]
    top_idx = next(i for i, l in enumerate(block) if l.strip() == "\\toprule")
    mid_idx = next(i for i, l in enumerate(block) if l.strip() == "\\midrule")
    bot_idx = next(i for i, l in enumerate(block) if l.strip() == "\\bottomrule")
    end_tab = next(i for i, l in enumerate(block) if l.strip() == "\\end{tabular}")

    caption = block[cap_idx : lab_idx]  # possibly multi-line caption
    header = block[top_idx + 1 : mid_idx]
    body = block[mid_idx + 1 : bot_idx]

    out = [f"\\begin{{longtable}}{spec}"]
    out += caption
    out.append(f"\\label{{{label}}}\\\\")
    out.append("\\toprule")
    out += header
    out.append("\\midrule")
    out.append("\\endfirsthead")
    out.append("\\toprule")
    out += header
    out.append("\\midrule")
    out.append("\\endhead")
    out.append("\\bottomrule")
    out.append("\\endfoot")
    out += body
    out.append("\\end{longtable}")

    new_lines = lines[:start] + out + lines[end + 1 :]
    new_text = "\n".join(new_lines)
    print(f"  {label}: {len(block)} -> {len(out)} lines, bytes {len(text)} -> {len(new_text)}")
    if apply:
        io.open(path, "w", encoding="utf-8", newline="\n").write(new_text)
    return True


def main() -> int:
    apply = "--apply" in sys.argv
    jobs = [(TABLES / "app_m.tex", "tab:params"), (TABLES / "app_n.tex", "tab:ablation-register")]
    for path, label in jobs:
        convert(path, label, apply)
    print("APPLIED" if apply else "dry run (pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
