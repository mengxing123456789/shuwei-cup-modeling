import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\figures\fig7_shape_discrimination.pdf")
for pi,pg in enumerate(d):
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines",[]):
            for s in l.get("spans",[]):
                if s["size"]<6:
                    print(pi, round(s["size"],2), repr(s["text"])[:60])
