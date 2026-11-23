import pandas as pd,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
b=r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"
s=pd.read_csv(b+r"\source_segment_index.csv")
print(s.groupby(["split","family_id"]).size())
print("durations",s["duration_s"].describe().to_dict())
t=pd.read_csv(b+r"\tasks.csv"); print(t.to_string())
