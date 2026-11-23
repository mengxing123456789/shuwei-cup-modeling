# -*- coding: utf-8 -*-
"""读 C 题数据集说明 PDF —— 检查我此前「没有 Data_Documentation」的判断是否漏读了官方文件。"""
import fitz  # pymupdf

P = r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\C题\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）C题数据集说明.pdf"

doc = fitz.open(P)
print(f"pages={doc.page_count}")
total = 0
for i, page in enumerate(doc):
    t = page.get_text()
    total += len(t)
    print(f"\n########## PAGE {i+1}  chars={len(t)} ##########")
    print(t)
print(f"\n===== total chars = {total} =====")