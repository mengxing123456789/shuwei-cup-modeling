import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
for i in [8,18]:
    d[i].get_pixmap(dpi=85).save(fr"E:\数学建模\_swc2026\_pg{i+1}.png")
print("ok",d.page_count)
