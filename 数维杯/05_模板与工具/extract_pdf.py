#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract text from a PDF (PyMuPDF) and optionally report page count."""
import sys, pathlib
import fitz

def main():
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix('.txt')
    doc = fitz.open(src)
    chunks = []
    for i, page in enumerate(doc, 1):
        chunks.append(f"\n===== PAGE {i}/{doc.page_count} =====\n")
        chunks.append(page.get_text("text"))
    dst.write_text("".join(chunks), encoding="utf-8")
    print(f"pages={doc.page_count} chars={dst.stat().st_size} -> {dst}")

if __name__ == "__main__":
    main()