import fitz, re
p = r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\04_paper\main.pdf"
d = fitz.open(p)
print("pages:", d.page_count)
pats = [r"^1\s+Introduction", r"^2\s+Assumptions", r"^3\s+Data", r"^4\s+Task 1", r"^5\s+Task 2", r"^6\s+Task 3", r"^7\s+Task 4", r"^8\s+Task 5", r"^9\s+Sensitivity", r"^References", r"^A\s+Data appendix"]
for i, pg in enumerate(d):
    txt = pg.get_text()
    for pat in pats:
        if re.search(pat, txt, re.M):
            print(f"p{i+1}: {pat}")
