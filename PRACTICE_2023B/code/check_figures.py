#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gate-check every figures/*.pdf for the two hard figure rules.

1. The PDF's own MediaBox is the page: width must be 416.5 pt (1:1 placement in
   main.tex) and no text span may sit closer than 2.0 pt to any page edge, else
   it is cropped for the reader.
2. Every text span of 3+ characters must be at least 6.0 pt (matplotlib stores
   6.0 as 5.98, so the build target is 6.2+).

Also verifies that every PDF has a sibling PNG of the expected pixel width.

Run with the mathmodel interpreter, which ships pymupdf:

    & "E:\\Mini\\envs\\mathmodel\\python.exe" -X utf8 code\\check_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf
from PIL import Image

W_PT = 416.5
EDGE_PT = 2.0
MIN_PT = 6.0
MIN_CHARS = 3
PNG_DPI = 300


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    figdir = root / "figures"
    pdfs = sorted(figdir.glob("*.pdf"))
    if not pdfs:
        print("[FAIL] no PDFs in", figdir)
        return 1

    failures = 0
    print(f"{'figure':38s} {'W':>6s} {'H':>6s} {'min_pt':>6s} {'x0':>5s} {'x1':>6s} {'y0':>5s} {'y1':>6s} spans")
    for pdf in pdfs:
        doc = pymupdf.open(pdf)
        page = doc[0]
        rect = page.rect
        W, H = rect.width, rect.height
        if abs(W - W_PT) > 0.05:
            print(f"[FAIL] {pdf.name}: width {W:.3f} != {W_PT}")
            failures += 1
        png = pdf.with_suffix(".png")
        if not png.exists():
            print(f"[FAIL] {pdf.name}: missing PNG")
            failures += 1
        else:
            im = Image.open(png)
            want = round(W_PT / 72.0 * PNG_DPI)
            if abs(im.size[0] - want) > 2:
                print(f"[FAIL] {png.name}: width {im.size[0]} px != {want}")
                failures += 1

        spans = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if not text:
                        continue
                    spans.append(
                        (
                            span["size"],
                            text,
                            span["bbox"][0],
                            span["bbox"][1],
                            span["bbox"][2],
                            span["bbox"][3],
                        )
                    )

        worst = min((s[0] for s in spans if len(s[1]) >= MIN_CHARS), default=999.0)
        x0 = min(s[2] for s in spans)
        y0 = min(s[3] for s in spans)
        x1 = max(s[4] for s in spans)
        y1 = max(s[5] for s in spans)

        bad_font = [s for s in spans if len(s[1]) >= MIN_CHARS and s[0] < MIN_PT]
        bad_edge = [s for s in spans if s[2] < EDGE_PT or s[4] > W - EDGE_PT or s[3] < EDGE_PT or s[5] > H - EDGE_PT]
        if bad_font:
            failures += 1
            print(f"[FAIL] {pdf.name}: {len(bad_font)} span(s) under {MIN_PT} pt")
            for s in sorted(bad_font)[:5]:
                print(f"        {s[0]:.3f} pt  {s[1]!r}")
        if bad_edge:
            failures += 1
            print(f"[FAIL] {pdf.name}: {len(bad_edge)} span(s) within {EDGE_PT} pt of an edge")
            for s in bad_edge[:5]:
                print(f"        bbox=({s[2]:.2f},{s[3]:.2f},{s[4]:.2f},{s[5]:.2f})  {s[1]!r}")

        print(
            f"{pdf.stem:38s} {W:6.1f} {H:6.1f} {worst:6.2f} {x0:5.1f} {x1:6.1f} {y0:5.1f} {y1:6.1f} {len(spans):5d}"
        )
        doc.close()

    print()
    if failures:
        print(f"[FAIL] {failures} check(s) failed")
        return 1
    print(f"[PASS] {len(pdfs)} PDFs: width {W_PT} pt, min type >= {MIN_PT} pt, all spans inside 2.0 pt edge margin, PNG present")
    return 0


if __name__ == "__main__":
    sys.exit(main())