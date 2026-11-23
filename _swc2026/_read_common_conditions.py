# -*- coding: utf-8 -*-
"""把 common_conditions.json 全文摊开 —— 看它到底覆盖了多少 P2/P3 协议。"""
import json

P = (r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data"
     r"\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN"
     r"\Restocking_Tasks_and_Constraints\common_conditions.json")

with open(P, encoding="utf-8") as f:
    d = json.load(f)

print(json.dumps(d, ensure_ascii=False, indent=1))