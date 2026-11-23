import sys,io,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
B=r"E:\数学建模\_swc2026\SWC2026_B\data"
p=json.load(open(B+r"\p3.json",encoding="utf-8"))["p3"]
print("contributions:"); print(json.dumps(p["contributions"],ensure_ascii=False,indent=1))
print("linearization_check:"); print(json.dumps(p["linearization_check"],ensure_ascii=False,indent=1))
print("ab_constraint:"); print(json.dumps(p["ab_constraint"],ensure_ascii=False,indent=1))
print("calibers:"); print(json.dumps(p["calibers"],ensure_ascii=False,indent=1))
