import pandas as pd, glob, json, os
base = r"E:\数学建模\_swc2026\cdata\EgoDemo"
p = glob.glob(base + r"\E001\data\chunk-000\*.parquet")[0]
df = pd.read_parquet(p)
print("shape:", df.shape)
print("columns:", list(df.columns))
print(df.dtypes.to_string())
print("\nhead:\n", df.head(3).to_string()[:2000])
print("\n--- meta/info.json ---")
info = json.load(open(base + r"\E001\meta\info.json", encoding="utf-8"))
print(json.dumps(info, ensure_ascii=False)[:2500])
print("\n--- tasks ---")
print(open(base + r"\E001\meta\tasks.json", encoding="utf-8").read()[:600] if os.path.exists(base + r"\E001\meta\tasks.json") else "no tasks.json")
print("\n--- annotation.json ---")
print(open(base + r"\E001\annotation.json", encoding="utf-8").read()[:800])
print("\n--- bad_frame_ratio.json ---")
print(open(base + r"\E001\bad_frame_ratio.json", encoding="utf-8").read()[:600] if os.path.exists(base+r"\E001\bad_frame_ratio.json") else "none")
print("\nrecords:", sorted(os.listdir(base)))
