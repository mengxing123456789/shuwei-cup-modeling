import pymupdf
d=pymupdf.open(r"E:\数学建模\_swc2026\SWC2026_A\main.pdf")
for i in range(d.page_count):
    t=d[i].get_text()
    if "Dimensionless groups of the coupled" in t: print("tab_pi page",i+1)
    if "Radii at" in t: print("tab_scaling page",i+1)
    if "Pareto fronts for the three" in t: print("tab_pareto page",i+1)
for i in [7,8,9]:
    d[i].get_pixmap(dpi=100).save(rf"E:\数学建模\_swc2026\_r{i+1}.png")
