import fitz
p = r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\04_paper\main.pdf"
d = fitz.open(p)
print("pages:", d.page_count)
marks = ["Summary", "Contents", "1 Introduction", "2 Assumptions", "3 Data", "4 Task 1", "5 Task 2", "6 Task 3", "7 Task 4", "8 Task 5", "9 Sensitivity", "References", "A Data appendix"]
for i, pg in enumerate(d):
    t = pg.get_text()
    for m in marks:
        if m in t and ("A Data appendix" not in m or t.count(m) > 0):
            print(f"p{i+1}: {m}")
