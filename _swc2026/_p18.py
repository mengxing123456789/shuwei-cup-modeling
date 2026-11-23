import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
pg=d[17]
for b in pg.get_text("dict")["blocks"]:
    for l in b.get("lines",[]):
        txt="".join(s["text"] for s in l["spans"])
        small=[s for s in l["spans"] if s["size"]<6]
        if small:
            print(repr(txt)[:200])
