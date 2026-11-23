import sys,io,pandas as pd,numpy as np
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
f=r"E:\数学建模\_swc2026\SWC2026_A\data\附件C Synthetic_Production_Data（英文版）.xlsx"
df=pd.read_excel(f)
print("rows",len(df),"cols",list(df.columns))
print("cases",sorted(df.Case_ID.unique()))
print("Cn",sorted(df['Nano_Concentration_wt%'].unique()))
print("ts",sorted(df.Soak_Time_Days.unique()))
print("days",df.Production_Day.min(),df.Production_Day.max(),df.Production_Day.nunique())
g=df.groupby(['Case_ID','Nano_Concentration_wt%','Soak_Time_Days']).Cum_Oil_m3.max()
print("\n=== Cn=1.0, ts in {5,30,60}, day360 Cum_Oil ===")
for c in sorted(df.Case_ID.unique()):
    vals=[]
    for ts in [5,30,60]:
        try: vals.append(round(float(g.loc[(c,1.0,ts)]),2))
        except Exception as e: vals.append("NA")
    print(c, vals)
# also B1 baseline presence
print("\ngroups:",len(g),"3*3*12 =",3*3*12)
