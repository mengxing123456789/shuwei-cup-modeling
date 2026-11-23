import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
d[0].get_pixmap(dpi=100).save(r"E:\数学建模\_swc2026\_final1.png")
print(d.page_count)
