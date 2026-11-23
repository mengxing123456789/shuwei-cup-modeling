# -*- coding: utf-8 -*-
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import fitz  # pymupdf

ROOT = r"E:\数学建模\_swc2026\award_corpus_2023intl"
OUT = r"E:\数学建模\_swc2026\award_corpus_2023intl\_extract"
os.makedirs(OUT, exist_ok=True)

targets = [
    "A2023101419943.pdf",
    "A2023101519953.pdf",
    "A2023101519958.pdf",
    "B2023081819323.pdf",
    "B2023090819411.pdf",
    "B2023091819500.pdf",
]

meta = {}
for name in targets:
    path = os.path.join(ROOT, name)
    doc = fitz.open(path)
    n = doc.page_count
    pages = []
    for i in range(n):
        page = doc[i]
        txt = page.get_text("text")
        pages.append(txt)
    doc.close()
    # count images per page as proxy for figures; rough
    doc = fitz.open(path)
    img_count = []
    for i in range(n):
        imgs = doc[i].get_images(full=True)
        img_count.append(len(imgs))
    doc.close()
    full = "\n".join(pages)
    outname = name.replace(".pdf", ".txt")
    with open(os.path.join(OUT, outname), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"=== {name} | pages={n} ===\n")
        for i, p in enumerate(pages):
            f.write(f"\n----- PAGE {i+1} (imgs={img_count[i]}) -----\n")
            f.write(p)
    meta[name] = {
        "pages": n,
        "chars": len(full),
        "img_total": sum(img_count),
        "img_pages_nonzero": sum(1 for c in img_count if c > 0),
    }
    print(f"{name}: pages={n}, chars={len(full)}, images={sum(img_count)}")

with open(os.path.join(OUT, "_meta.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(meta, f, ensure_ascii=False, indent=1)
print("DONE")
