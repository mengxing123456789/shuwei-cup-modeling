import json,io,sys,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
b=r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"
print(open(b+r"\common_conditions.json",encoding="utf-8").read())
t=pd.read_csv(b+r"\tasks.csv"); print("\ntasks",t.shape); print(t.head(4).to_string())
s=pd.read_csv(b+r"\source_segment_index.csv"); print("\nsegments",s.shape); print(s.columns.tolist()); print(s.head(3).to_string())
r=pd.read_csv(b+r"\record_split.csv"); print("\nsplit",r.shape, r.columns.tolist()); print(r["split"].value_counts().to_dict() if "split" in r else "")
print("\nzones"); print(open(b+r"\service_zones.csv",encoding="utf-8").read())
print("families"); print(open(b+r"\job_families.csv",encoding="utf-8").read())
