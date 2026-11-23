import pandas as pd, io, sys, numpy as np
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
b=r"E:\数学建模\_swc2026\SWC2026_C\data"
p=pd.read_csv(b+r"\panel_records.csv")
print("panel_records",p.shape); print(p.head(3).to_string())
print(p["dataset"].value_counts() if "dataset" in p else p.columns.tolist())
z=np.load(b+r"\panel.npz")
print("panel.npz keys",list(z.keys())[:12])
for k in list(z.keys())[:6]: print(k,z[k].shape,z[k].dtype)
s=np.load(b+r"\state.npz"); print("state.npz",list(s.keys())[:10])
