import pymupdf, glob, os
for f in sorted(glob.glob(r"E:\数学建模\_swc2026\SWC2026_A\figures\*.pdf")):
    d=pymupdf.open(f); mn=99; tx=''
    for pg in d:
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines",[]):
                for s in l.get("spans",[]):
                    if s["size"]<mn: mn=s["size"]; tx=s["text"]
    print(os.path.basename(f), round(mn,2), repr(tx)[:40])
