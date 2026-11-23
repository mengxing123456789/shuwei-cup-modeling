import json
d=json.load(open(r"E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json",encoding="utf-8"))
print(json.dumps(d["test_b4"],ensure_ascii=False,indent=1)[:900])
print("---keys design:", list(d["design_space"].keys())[:10])
