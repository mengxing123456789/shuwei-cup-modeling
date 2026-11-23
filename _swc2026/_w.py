import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
for i in [1,17,23]:
    d[i].get_pixmap(dpi=90).save(rf"E:\数学建模\_swc2026\_w{i+1}.png")
print(d[1].get_text()[:300])
