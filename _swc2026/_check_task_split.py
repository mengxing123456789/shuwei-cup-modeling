import pandas as pd, json
p = r"C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\source_segment_index.csv"
d = pd.read_csv(p)
print("rows", len(d), "eligible", int(d["eligible"].sum()))
tasks = {s: set(g["task"]) for s, g in d.groupby("split")}
for s, ts in tasks.items():
    print(f"{s:11s} n_task={len(ts):2d}  n_units={int((d.split==s).sum())}")
tr, va, te = tasks["train"], tasks["validation"], tasks["test"]
print("\nval - train:", sorted(va - tr))
print("test - train:", sorted(te - tr))
print("test & train overlap:", sorted(te & tr))
print("val & train overlap:", sorted(va & tr))
print("\ncounts: test", len(te), "| of which unseen in train:", len(te - tr))
print("all tasks:", sorted(set(d["task"])))
print("\nfamily x split:")
print(pd.crosstab(d["family_id"], d["split"]).to_string())
print("\nversion/task overlap check done")