import json,glob,os
base=r"E:\数学建模\_swc2026\SWC2026_A\data"
out={"source":"aggregate of data/*.json","numbers":[]}
def walk(o):
    if isinstance(o,dict):
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
    elif isinstance(o,(int,float)) and not isinstance(o,bool):
        out["numbers"].append(o)
for f in glob.glob(os.path.join(base,"*.json")):
    if os.path.basename(f).startswith("results_"): continue
    try: walk(json.load(open(f,encoding="utf-8")))
    except Exception: pass
p=os.path.join(base,"results_A.json")
json.dump(out,open(p,"w",encoding="utf-8"),ensure_ascii=False)
print("numbers",len(out["numbers"]),"size",os.path.getsize(p))
