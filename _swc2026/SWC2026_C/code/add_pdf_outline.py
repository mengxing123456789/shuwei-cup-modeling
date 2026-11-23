# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-23 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# -*- coding: utf-8 -*-
"""Attach the PDF outline (bookmarks) to main.pdf from LaTeX's main.toc.

The paper class loads titlesec after hyperref, so titlesec replaces the sectioning
commands after hyperref has installed its bookmark hooks.  XeLaTeX therefore emits
only the explicit titlepage bookmark, and main.out stays at one line.  This script
rebuilds the navigation outline from the authoritative toc file.

The outline is written in the same shape the reader-side panel of a reference build
uses, because three separate things can make a viewer show only the first entry:

  * titles as PDF literal strings, where three of ours carried escaped parentheses;
  * destinations as page arrays, which readers that resolve only named destinations
    cannot follow;
  * collapsed parents, so a panel that does not auto-expand looks nearly empty.

So each entry gets a UTF-16BE hex title, a named destination taken from the hyperref
anchor recorded in main.toc, and both an /A action and an item-level /Dest.  Parent
counts are set to their expanded descendant count.  No page content and no layout is
touched: the script asserts that every page's text and 72 dpi rendering are identical
before it replaces the file.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import pymupdf
except ModuleNotFoundError:
    try:
        import fitz as pymupdf  # 旧版 PyMuPDF 的模块名
    except ModuleNotFoundError:
        sys.exit(
            "需要 PyMuPDF 才能写 PDF 书签：pip install pymupdf\n"
            "没有它前 5 步（编译与数值校验）已经全部完成，书签可以后补。"
        )

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "main.pdf"
TOC = ROOT / "main.toc"

LINE = re.compile(
    r"\\contentsline \{(section|subsection)\}\{(.*?)\}\{(\d+)\}\{([^{}]*)\}",
    re.S,
)


def parse_toc() -> list[list[object]]:
    text = TOC.read_text(encoding="utf-8")
    items: list[list[object]] = [[1, "titlepage", 1]]
    for m in LINE.finditer(text):
        kind, body, page = m.group(1), m.group(2), int(m.group(3))
        body = re.sub(r"\\numberline \{([^{}]*)\}", r"\1 ", body)
        body = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r"\1", body)
        body = body.replace("~", " ").replace("\\", "").strip()
        if body:
            items.append([1 if kind == "section" else 2, body, page])
    return items


def anchors() -> list[str]:
    """Anchor name of every heading, in toc order, as hyperref recorded it.

    main.toc ends each line with the label hyperref created, and that label is also
    a named destination in the PDF.  Bookmark entries must point at these names.
    """
    text = TOC.read_text(encoding="utf-8")
    return ["titlepage.1"] + [m.group(4).strip() for m in LINE.finditer(text)]


def xref_of(doc: pymupdf.Document, node: int, key: str) -> int | None:
    kind, value = doc.xref_get_key(node, key)
    if kind != "xref":
        return None
    return int(value.split()[0])


def walk(doc: pymupdf.Document, node: int) -> list[int]:
    """Depth-first, first-child order: the order the panel displays."""
    out: list[int] = []
    for child in iter_children(doc, node):
        out.append(child)
        out.extend(walk(doc, child))
    return out


def iter_children(doc: pymupdf.Document, node: int) -> list[int]:
    kids: list[int] = []
    cur = xref_of(doc, node, "First")
    while cur:
        kids.append(cur)
        cur = xref_of(doc, cur, "Next")
    return kids


def hex_title(doc: pymupdf.Document, xref: int) -> bool:
    """Re-emit /Title as UTF-16BE hex with a BOM.  Idempotent."""
    kind, value = doc.xref_get_key(xref, "Title")
    if kind not in ("string", "hexstring"):
        return False
    if kind == "hexstring":
        # decode the hex payload so a second run does not double-encode it
        raw = bytes.fromhex(value.strip("<>"))
        if raw[:2] == b"\xfe\xff":
            value = raw[2:].decode("utf-16-be")
        else:
            value = raw.decode("latin-1")
    doc.xref_set_key(
        xref, "Title", "<FEFF%s>" % value.encode("utf-16-be").hex().upper()
    )
    return True


def set_counts(doc: pymupdf.Document, node: int) -> int:
    """Expanded descendant count of node; negative would mean collapsed."""
    total = 0
    for child in iter_children(doc, node):
        total += 1 + set_counts(doc, child)
    if total:
        doc.xref_set_key(node, "Count", str(total))
    return total


def rewrite(doc: pymupdf.Document) -> tuple[int, int]:
    names = anchors()
    root = xref_of(doc, doc.pdf_catalog(), "Outlines")
    if root is None:
        raise SystemExit("no outline root in the PDF")
    flat = walk(doc, root)
    if len(flat) != len(names):
        raise SystemExit(
            "outline has %d items but main.toc gives %d anchors" % (len(flat), len(names))
        )
    available = doc.resolve_names()
    missing = [n for n in names if n not in available]
    if missing:
        raise SystemExit("names absent from the PDF: %s" % missing[:5])
    hexed = 0
    for xref, name in zip(flat, names):
        hexed += 1 if hex_title(doc, xref) else 0
        doc.xref_set_key(xref, "A", "<< /S /GoTo /D (%s) >>" % name)
        doc.xref_set_key(xref, "Dest", "(%s)" % name)
    set_counts(doc, root)
    return len(flat), hexed


def main() -> int:
    if not PDF.exists() or not TOC.exists():
        print("missing main.pdf or main.toc", file=sys.stderr)
        return 1
    before = pymupdf.open(PDF)
    pages = before.page_count
    texts = [p.get_text() for p in before]
    pix = [p.get_pixmap(dpi=72).samples for p in before]
    toc = parse_toc()
    before.set_toc(toc)
    if len(before.get_toc()) != len(toc):
        raise SystemExit("set_toc dropped entries")
    entries, hexed = rewrite(before)
    if entries != len(toc):
        raise SystemExit("outline entries %d != toc entries %d" % (entries, len(toc)))
    tmp = PDF.with_suffix(".outline.tmp.pdf")
    before.save(str(tmp), garbage=3, deflate=True)
    before.close()

    after = pymupdf.open(tmp)
    toc_after = after.get_toc()
    resolved = after.resolve_names()
    for (_, title, page) in toc_after:
        pass
    names = anchors()
    for (_, title, page), name in zip(toc_after, names):
        target = resolved[name]
        if target["page"] + 1 != page:
            raise SystemExit(
                "name %s points at page %d, outline says %d"
                % (name, target["page"] + 1, page)
            )
    if after.page_count != pages:
        raise SystemExit("page count changed")
    if [p.get_text() for p in after] != texts:
        raise SystemExit("text changed")
    if [p.get_pixmap(dpi=72).samples for p in after] != pix:
        raise SystemExit("rendering changed")
    after.close()
    os.replace(tmp, PDF)
    print(
        "outline: %d entries, %d hex titles, %d named destinations; "
        "pages/content unchanged" % (len(toc_after), hexed, entries)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
