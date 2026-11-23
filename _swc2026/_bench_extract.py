# -*- coding: utf-8 -*-
"""Extract text + structural metrics from the 2025 autumn award papers (C track)
and from our own submission, so the comparison is measured rather than asserted.
"""
import os, re, zipfile, json, io
import pymupdf

ROOT = r"C:\Users\29900\Downloads\AsterLink"
ZIP = os.path.join(ROOT, "2025年数维杯秋季赛优秀论文.zip")
OUT = r"E:\数学建模\_swc2026\_bench"
os.makedirs(OUT, exist_ok=True)

def metrics(text, n_pages):
    lines = [l.strip() for l in text.splitlines()]
    heads = []
    for l in lines:
        # numbered section headings: 1 Introduction / 2.1 Data / 3 Model ...
        if re.match(r"^\d+(\.\d+){0,2}\s+[A-Z][A-Za-z]", l) and len(l) < 90:
            heads.append(l)
        elif re.match(r"^(Abstract|Summary|Introduction|Conclusion|References|Appendix)\b", l) and len(l) < 40:
            heads.append(l)
    figs = len(re.findall(r"(?i)\bfig(?:ure)?\.?\s*\d+", text))
    tabs = len(re.findall(r"(?i)\btable\s*\d+", text))
    eqs = len(re.findall(r"\(\d{1,2}\)", text))
    refs = len(re.findall(r"^\s*\[\d+\]", text, re.M))
    words = len(re.findall(r"[A-Za-z][A-Za-z\-']+", text))
    nums = len(re.findall(r"\d+\.\d+", text))
    return dict(pages=n_pages, words=words, figures_mentions=figs, table_mentions=tabs,
                eq_labels=eqs, ref_entries=refs, decimal_numbers=nums,
                headings=len(heads), head_list=heads[:40])

rows = {}
z = zipfile.ZipFile(ZIP)
for n in z.namelist():
    if not n.lower().endswith(".pdf"):
        continue
    if "/C题/" not in n:
        continue
    data = z.read(n)
    doc = pymupdf.open(stream=data, filetype="pdf")
    text = "".join(doc[i].get_text() for i in range(doc.page_count))
    tag = n.split("/")[-1].replace(".pdf", "").strip()
    rows[tag] = metrics(text, doc.page_count)
    with open(os.path.join(OUT, tag + ".txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print("%-22s pages=%3d words=%5d fig=%3d tab=%3d eq=%3d refs=%2d heads=%2d" % (
        tag, doc.page_count, rows[tag]["words"], rows[tag]["figures_mentions"],
        rows[tag]["table_mentions"], rows[tag]["eq_labels"], rows[tag]["ref_entries"],
        rows[tag]["headings"]))

# our own paper
mine = r"E:\数学建模\_swc2026\SWC2026_C\CSWBMCM2634892.pdf"
doc = pymupdf.open(mine)
t = "".join(doc[i].get_text() for i in range(doc.page_count))
rows["OURS_CSWBMCM2634892"] = metrics(t, doc.page_count)
with open(os.path.join(OUT, "OURS.txt"), "w", encoding="utf-8") as f:
    f.write(t)
print("%-22s pages=%3d words=%5d fig=%3d tab=%3d eq=%3d refs=%2d heads=%2d" % (
    "OURS", doc.page_count, rows["OURS_CSWBMCM2634892"]["words"],
    rows["OURS_CSWBMCM2634892"]["figures_mentions"], rows["OURS_CSWBMCM2634892"]["table_mentions"],
    rows["OURS_CSWBMCM2634892"]["eq_labels"], rows["OURS_CSWBMCM2634892"]["ref_entries"],
    rows["OURS_CSWBMCM2634892"]["headings"]))

with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
print("wrote", os.path.join(OUT, "metrics.json"))
