# -*- coding: utf-8 -*-
"""Body-only measurement with the appendix cut taken from each paper's TOC."""
import json, os, re
import pymupdf

BENCH = r"E:\数学建模\_swc2026\_bench\_pdf"
OURS = r"E:\数学建模\_swc2026\SWC2026_C\CSWBMCM2634892.pdf"

# body page counts read from each paper's table of contents
CUT = {
    "CSHUWEICUP2551760": 44,
    "CSHUWEICUP2556711": 52,
    "CSHUWEICUP2556821": 38,
    "CSHUWEICUP2559001": 39,
    "CSHUWEICUP2561635": 30,
    "OURS": 25,
}

FIG = re.compile(r"(?m)^\s*(?:Figure|Fig\.)\s*(\d+(?:-\d+)?)\b")
TAB = re.compile(r"(?m)^\s*Table\s*(\d+(?:-\d+)?)\b")
EQ = re.compile(r"(?m)^\s*\((\d{1,2})\)\s*$")
SECT = re.compile(r"(?m)^\s*(\d{1,2})(?:\.\d{1,2}){0,2}\s+[A-Z][A-Za-z]{2,}")


def measure(path, cut):
    doc = pymupdf.open(path)
    body = "".join(doc[i].get_text() for i in range(cut))
    imgs = sum(len(doc[i].get_images(full=True)) for i in range(cut))
    return dict(
        pages=doc.page_count, body=cut,
        words=len(re.findall(r"[A-Za-z][A-Za-z\-']+", body)),
        fig=len(set(FIG.findall(body))),
        tab=len(set(TAB.findall(body))),
        eq=len(set(EQ.findall(body))),
        imgs=imgs,
        sect=len(SECT.findall(body)),
        subsect=len(re.findall(r"(?m)^\s*\d{1,2}\.\d{1,2}\s+[A-Z]", body)),
    )


rows = {}
for name, cut in CUT.items():
    p = OURS if name == "OURS" else os.path.join(BENCH, name + ".pdf")
    rows[name] = measure(p, cut)

keys = ["pages", "body", "words", "fig", "tab", "eq", "imgs", "sect", "subsect"]
hdr = "%-22s" % "paper" + "".join("%9s" % k for k in keys)
print(hdr); print("-" * len(hdr))
for name, v in rows.items():
    print("%-22s" % name + "".join("%9d" % v[k] for k in keys))
print()
aw = [v for k, v in rows.items() if k != "OURS"]
for k in keys[2:]:
    vals = [v[k] for v in aw]
    print("%-9s award range %3d-%3d  mean %6.1f   OURS %5d" % (
        k, min(vals), max(vals), sum(vals) / len(vals), rows["OURS"][k]))
with open(r"E:\数学建模\_swc2026\_bench\body_only.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
