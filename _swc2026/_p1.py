import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
d[0].get_pixmap(dpi=110).save(r"E:\数学建模\_swc2026\_p1.png")
print(d[0].get_text()[:400])
