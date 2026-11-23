#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Structural profile of a contest paper PDF: pages, words, sections, figures, tables, equations."""
import sys, pathlib, re, json
import fitz

def main():
    p = pathlib.Path(sys.argv[1])
    doc = fitz.open(p)
    pages = doc.page_count
    text = "\n".join(pg.get_text("text") for pg in doc)
    words = len(re.findall(r"[A-Za-z][A-Za-z\-']+", text))
    heads = []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^\d+(\.\d+)*\s+[A-Z][A-Za-z].{2,80}$", s) and len(s) < 90:
            heads.append(s)
    uniq_fig = len(set(re.findall(r"\bFigure\s+(\d+)", text)))
    uniq_tab = len(set(re.findall(r"\bTable\s+(\d+)", text)))
    eqs = len(re.findall(r"\(\d+\)\s*$", text, re.M))
    out = {
        "file": p.name, "pages": pages, "words": words,
        "unique_figure_refs": uniq_fig, "unique_table_refs": uniq_tab,
        "numbered_equation_lines": eqs,
        "headings": heads[:80],
        "toc": doc.get_toc()[:60],
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()