# -*- coding: utf-8 -*-
"""Measure the surface features judges actually score, for our paper and for
the five 2025 C-track award papers, so the gap is a number and not an opinion.
"""
import json, os, re
import pymupdf

BENCH = r"E:\数学建模\_swc2026\_bench"
OURS = r"E:\数学建模\_swc2026\SWC2026_C\CSWBMCM2634892.pdf"


def body_span(doc):
    """Page index where the appendix starts (first page whose header says Appendix)."""
    for i in range(doc.page_count):
        head = doc[i].get_text().split("\n")[:3]
        if any(h.strip().lower().startswith("appendix") for h in head):
            return i
    return doc.page_count


def count(path):
    doc = pymupdf.open(path)
    cut = body_span(doc)
    body = "".join(doc[i].get_text() for i in range(cut))
    allt = "".join(doc[i].get_text() for i in range(doc.page_count))
    # figures: caption lines "Figure N." or "Fig. N"
    fig_caps = re.findall(r"(?im)^\s*(?:Figure|Fig\.)\s*(\d+)[.:]", allt)
    fig_body = re.findall(r"(?im)^\s*(?:Figure|Fig\.)\s*(\d+)[.:]", body)
    tab_caps = re.findall(r"(?im)^\s*Table\s*(\d+)[.:]", allt)
    tab_body = re.findall(r"(?im)^\s*Table\s*(\d+)[.:]", body)
    # display equations: "(N)" alone on a line, or right-aligned tags
    eq_tags = re.findall(r"(?m)^\s*\((\d{1,2})\)\s*$", allt)
    eq_body = re.findall(r"(?m)^\s*\((\d{1,2})\)\s*$", body)
    return dict(pages=doc.page_count, body_pages=cut, appendix_pages=doc.page_count - cut,
                figures_all=len(set(fig_caps)), figures_body=len(set(fig_body)),
                tables_all=len(set(tab_caps)), tables_body=len(set(tab_body)),
                eq_all=len(set(eq_tags)), eq_body=len(set(eq_body)))


rows = {"OURS": count(OURS)}
for f in sorted(os.listdir(BENCH)):
    if f.endswith(".txt") and f.startswith("CSHUWEI"):
        # rebuild a pdf-free count from the text is unreliable; re-open the zip pdf instead
        pass

import zipfile
ZIP = r"C:\Users\29900\Downloads\AsterLink\2025年数维杯秋季赛优秀论文.zip"
z = zipfile.ZipFile(ZIP)
tmp = os.path.join(BENCH, "_pdf")
os.makedirs(tmp, exist_ok=True)
for n in z.namelist():
    if n.lower().endswith(".pdf") and "/C题/" in n:
        tag = n.split("/")[-1].replace(".pdf", "").strip()
        p = os.path.join(tmp, tag + ".pdf")
        with open(p, "wb") as fh:
            fh.write(z.read(n))
        rows[tag] = count(p)

hdr = ("%-22s %5s %5s %5s %6s %6s %6s %6s %5s %5s" %
       ("paper", "pages", "body", "appx", "figAll", "figBdy", "tabAll", "tabBdy", "eqAll", "eqBdy"))
print(hdr); print("-" * len(hdr))
for k, v in rows.items():
    print("%-22s %5d %5d %5d %6d %6d %6d %6d %5d %5d" % (
        k, v["pages"], v["body_pages"], v["appendix_pages"],
        v["figures_all"], v["figures_body"], v["tables_all"], v["tables_body"],
        v["eq_all"], v["eq_body"]))

with open(os.path.join(BENCH, "surface.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
