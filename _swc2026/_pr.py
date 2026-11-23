import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
d=json.load(open(r"E:\数学建模\_swc2026\SWC2026_A\models\surrogate_r0.json",encoding="utf-8"))
for k,v in d["folds"].items():
    if isinstance(v,list):
        print(k)
        for i,f in enumerate(v): print("  fold",i,{t:round(f[t]["r2"],3) for t in f})
    else:
        print(k,{t:round(v[t]["r2"],3) for t in v})
print("elapsed",d["elapsed_s"])
