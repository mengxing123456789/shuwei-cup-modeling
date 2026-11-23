# -*- coding: utf-8 -*-
"""Move two body tables into Appendix N and drop them from the body.

Rationale (46-整体测评与一等奖判定.md, A2): the body carries 13 tables against a
mean of 8.8 in the five awarded C papers, while it carries 3 figures against a
mean of 17.2. Both tables moved here are already discussed in the ablation
register, so the move costs no argument and buys space for figures.
"""
import os
import re
import pathlib

C = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
main = C / "main.tex"
appn = C / "tables" / "app_n.tex"
text = main.read_text(encoding="utf-8")

moved = []
for label in ("tab:negative", "tab:ablation"):
    m = re.search(r"\\begin\{table\}\[htbp\]\n(?:.*?\n)*?\\label\{%s\}\n(?:.*?\n)*?\\end\{table\}\n\n?"
                  % re.escape(label), text)
    if not m:
        raise SystemExit("block not found: " + label)
    block = m.group(0)
    moved.append((label, block))
    text = text[:m.start()] + text[m.end():]

main.write_text(text, encoding="utf-8", newline="\n")

tail = appn.read_text(encoding="utf-8")
add = ["\n", "\\subsection*{Two tables moved out of the body}", "",
       "The two tables below were carried in the body of the first draft. They are the",
       "same measurements, moved here so that the body can spend its page budget on",
       "figures rather than on tables; every claim that refers to them is unchanged.", ""]
for label, block in moved:
    add.append(block.rstrip("\n"))
    add.append("")
appn.write_text(tail.rstrip("\n") + "\n" + "\n".join(add), encoding="utf-8", newline="\n")
print("moved", [l for l, _ in moved])
print("main.tex lines", len(text.splitlines()))