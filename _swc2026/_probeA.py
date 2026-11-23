import openpyxl
p = r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx"
wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
print("sheets:", wb.sheetnames)
ws = wb[wb.sheetnames[0]]
print("dims:", ws.max_row, ws.max_column)
rows = list(ws.iter_rows(min_row=1, max_row=6, values_only=True))
for r in rows: print(r)
