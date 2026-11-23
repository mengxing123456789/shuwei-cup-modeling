# -*- coding: utf-8 -*-
"""Count what the judges see: body figures, body tables, display equations,
inline images, and how many figures sit in the body versus the appendix."""
import json, os, re
import pymupdf

OURS = r"E:\数学建模\_swc2026\SWC2026_C\CSWBMCM2634892.pdf"
BENCH = r"E:\数学建模\_swc2026\_bench\_pdf"

FIG = re.compile(r"(?m)^\s*Figure\s+(\d+)\b")
TAB = re.compile(r"(?m)^\s*Table\s+(\d+)\b")
EQ = re.compile(r"(?m)^\s*\((\d{1,2})\)\s*$")


def split_index(doc):
    for i in range(doc.page_count):
        head = doc[i].get_text().split("\n")[:2]
        if any(h.strip().lower().startswith("appendix") for h in head):
            return i
    return doc.page_count


def measure(path):
    doc = pymupdf.open(path)
    cut = split_index(doc)
    body = "".join(doc[i].get_text() for i in range(cut))
    allt = "".join(doc[i].get_text() for i in range(doc.page_count))
    imgs_body = sum(len(doc[i].get_images(full=True)) for i in range(cut))
    imgs_app = sum(len(doc[i].get_images(full=True)) for i in range(cut, doc.page_count))
    return dict(
        pages=doc.page_count, body=cut, appendix=doc.page_count - cut,
        fig_body=len(set(FIG.findall(body))), fig_all=len(set(FIG.findall(allt))),
        tab_body=len(set(TAB.findall(body))), tab_all=len(set(TAB.findall(allt))),
        eq_body=len(set(EQ.findall(body))), eq_all=len(set(EQ.findall(allt))),
        imgs_body=imgs_body, imgs_app=imgs_app,
        words=len(re.findall(r"[A-Za-z][A-Za-z\-']+", body)),
    )


rows = {"OURS": measure(OURS)}
for f in sorted(os.listdir(BENCH)):
    if f.lower().endswith(".pdf"):
        rows[f[:-4]] = measure(os.path.join(BENCH, f))

keys = ["pages", "body", "appendix", "fig_body", "fig_all", "tab_body", "tab_all",
        "eq_body", "eq_all", "imgs_body", "imgs_app", "words"]
print("%-22s" % "paper" + "".join("%8s" % k[:7] for k in keys))
for name, v in rows.items():
    print("%-22s" % name + "".join("%8d" % v[k] for k in keys))
with open(r"E:\数学建模\_swc2026\_bench\surface2.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
