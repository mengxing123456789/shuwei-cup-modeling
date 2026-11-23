import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
d=json.load(open(r"E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json",encoding="utf-8"))
print(json.dumps(d["design_space"],indent=1,ensure_ascii=False)[:1500])
