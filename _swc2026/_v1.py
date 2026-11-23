import sys,io,os,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
f=r"E:\数学建模\_swc2026\SWC2026_A\data\附件C Synthetic_Production_Data（英文版）.xlsx"
xl=pd.ExcelFile(f)
print("sheets:",xl.sheet_names)
for s in xl.sheet_names[:4]:
    df=xl.parse(s,nrows=3)
    print("--",s,df.shape,"cols:",list(df.columns)[:12])
