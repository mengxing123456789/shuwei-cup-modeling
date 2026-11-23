import fitz
d=fitz.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
for i in [23]:
    p=d[i]; pix=p.get_pixmap(dpi=110); pix.save(rf"E:\数学建模\_swc2026\_pg{i+1}.png")
print(len(d), d[0].rect)
