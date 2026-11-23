import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
for pn in [7,8]:
    pg=d[pn]
    print("=== page",pn+1)
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines",[]):
            txt="".join(s["text"] for s in l["spans"])
            if "num" in txt or "face" in txt or "max" in txt or "prod" in txt or "soak" in txt:
                print(round(l["spans"][0]["size"],2), repr(txt)[:160])
